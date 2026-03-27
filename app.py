"""Streamlit app for reproducible presentation image generation.

Tabs:
  ✨ Generate  — create images with prompt + style preset
  📂 History   — browse, search, download, and rerun past generations
  🎭 Presets   — manage reusable style prompts
  ⚙️ Settings  — configure provider, API keys, and generation parameters
"""

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from src import database as db
from src import presets as preset_store
from src import references as ref_store
from src.generator import PROVIDERS, generate_image, get_provider_api_key
from src.storage import load_image_bytes

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

db.init_db()

# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


_default("rerun_base_prompt", "")
_default("rerun_provider", "google-gemini")
_default("active_tab", 0)


# ---------------------------------------------------------------------------
# Sidebar — provider & API key quick-config
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Provider")

    provider_options = list(PROVIDERS.keys())
    provider_labels = [PROVIDERS[p]["label"] for p in provider_options]

    # Use session state to allow tab-triggered provider changes
    _default("provider", "google-gemini")
    selected_provider_label = st.selectbox(
        "Image provider",
        provider_labels,
        index=provider_options.index(st.session_state.provider),
        key="sidebar_provider_select",
    )
    st.session_state.provider = provider_options[provider_labels.index(selected_provider_label)]
    provider = st.session_state.provider

    model_options = PROVIDERS[provider]["models"]
    selected_model = st.selectbox("Model", model_options)

    env_key_var = PROVIDERS[provider]["api_key_env"]
    api_key_input = get_provider_api_key(provider)
    if not api_key_input:
        st.warning(f"`{env_key_var}` not set.")

    st.divider()
    st.header("Generation settings")

    title = st.text_input("Title", placeholder="Q1 Roadmap hero image")
    project_name = st.text_input("Project / deck", placeholder="Q1 2025 All-Hands")
    tags = st.text_input("Tags (comma-separated)", placeholder="roadmap, blue, wide")

    st.subheader("Provider settings")
    extra_settings: dict = {}
    current_provider = st.session_state.provider

    if current_provider == "google-gemini":
        extra_settings["aspect_ratio"] = st.selectbox(
            "Aspect ratio", ["16:9", "1:1", "9:16", "4:3", "3:4"]
        )
        extra_settings["num_images"] = st.slider("Images to generate", 1, 4, 1)

    elif current_provider == "openai":
        size_map = {
            "dall-e-3": ["1792x1024", "1024x1024", "1024x1792"],
            "dall-e-2": ["256x256", "512x512", "1024x1024"],
        }
        extra_settings["size"] = st.selectbox(
            "Size", size_map.get(selected_model, ["1024x1024"])
        )
        if selected_model == "dall-e-3":
            extra_settings["quality"] = st.selectbox("Quality", ["standard", "hd"])
            extra_settings["style"] = st.selectbox("Style", ["vivid", "natural"])

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_generate, tab_history, tab_presets, tab_refs = st.tabs(
    ["✨ Generate", "📂 History", "🎭 Presets", "🖼️ References"]
)

# ============================================================
# TAB 1 — Generate
# ============================================================

with tab_generate:
    st.header("Generate an Image")

    base_prompt = st.text_area(
        "Base prompt",
        value=st.session_state.rerun_base_prompt,
        height=120,
        placeholder="A professional headshot of a data scientist presenting at a conference…",
    )
    st.session_state.rerun_base_prompt = base_prompt

    presets = preset_store.get_presets()
    preset_options = ["— none —"] + [p["name"] for p in presets]
    selected_preset_name = st.selectbox("Style preset", preset_options)

    style_prompt = ""
    if selected_preset_name != "— none —":
        preset = next(p for p in presets if p["name"] == selected_preset_name)
        style_prompt = preset["style_prompt"]

    enhance = st.checkbox(
        "Enhance prompt with Gemini before generation",
        value=False,
        help="Uses chatlas ChatGoogle to refine your prompt. Requires Google Gemini provider.",
    )

    st.markdown("**Reference image** (optional, Google Gemini only)")
    saved_refs = ref_store.list_references()
    ref_options = ["— none —"] + [p.name for p in saved_refs]
    selected_ref_name = st.selectbox("Saved references", ref_options)

    reference_file = st.file_uploader(
        "Or upload a one-off reference",
        type=["png", "jpg", "jpeg"],
    )

    reference_image_bytes = None
    if reference_file is not None:
        reference_image_bytes = reference_file.read()
        st.image(reference_image_bytes, caption="Uploaded reference", width=200)
        save_ref_name = st.text_input("Save this image to references as (optional)", placeholder="matt_headshot")
        if save_ref_name and st.button("Save to references"):
            ext = reference_file.name.rsplit(".", 1)[-1] if "." in reference_file.name else "jpg"
            try:
                ref_store.save_reference(save_ref_name, reference_image_bytes, ext)
                st.success(f"Saved as '{save_ref_name}.{ext}'")
                st.rerun()
            except ValueError as e:
                st.error(str(e))
    elif selected_ref_name != "— none —":
        ref_path = next(p for p in saved_refs if p.name == selected_ref_name)
        reference_image_bytes = ref_path.read_bytes()
        st.image(reference_image_bytes, caption=selected_ref_name, width=200)

    generate_btn = st.button("Generate Image", type="primary", use_container_width=True)

    if generate_btn:
        if not base_prompt.strip():
            st.error("Please enter a base prompt.")
        elif not api_key_input:
            st.error(f"`{PROVIDERS[current_provider]['api_key_env']}` environment variable is not set.")
        else:
            with st.spinner("Generating…"):
                try:
                    result = generate_image(
                        base_prompt=base_prompt,
                        style_prompt=style_prompt,
                        provider=current_provider,
                        model=selected_model,
                        api_key=api_key_input,
                        settings=extra_settings,
                        enhance_prompt=enhance,
                        reference_image=reference_image_bytes,
                    )

                    gen_id = db.save_generation(
                        base_prompt=base_prompt,
                        final_prompt=result.final_prompt,
                        provider=result.provider,
                        output_path=result.output_path,
                        title=title or None,
                        project_name=project_name or None,
                        tags=tags or None,
                        style_prompt=style_prompt or None,
                        model=result.model,
                        settings=result.settings,
                    )

                    st.success(f"Image generated and saved (ID: {gen_id})")

                    image_bytes = load_image_bytes(result.output_path)
                    if image_bytes:
                        st.image(image_bytes, caption=result.final_prompt)
                        st.download_button(
                            "Download image",
                            data=image_bytes,
                            file_name=f"generation_{gen_id}.png",
                            mime="image/png",
                        )

                    with st.expander("Generation details"):
                        st.json({
                            "id": gen_id,
                            "provider": result.provider,
                            "model": result.model,
                            "final_prompt": result.final_prompt,
                            "settings": result.settings,
                            "output_path": result.output_path,
                        })

                except Exception as exc:
                    st.error(f"Generation failed: {exc}")


# ============================================================
# TAB 2 — History
# ============================================================

with tab_history:
    st.header("Generation History")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        projects = ["All projects"] + db.get_projects()
        selected_project = st.selectbox("Filter by project", projects)
    with col_filter2:
        search_query = st.text_input("Search prompts / titles / tags", placeholder="roadmap…")

    project_filter = None if selected_project == "All projects" else selected_project
    generations = db.get_generations(project_name=project_filter, search=search_query)

    if not generations:
        st.info("No generations yet. Head to ✨ Generate to create your first image.")
    else:
        st.caption(f"{len(generations)} generation(s) found.")
        for gen in generations:
            label = gen.get("title") or f"Generation #{gen['id']}"
            with st.expander(f"**{label}** — {gen['created_at'][:19]} | {gen['provider']}"):
                c_img, c_detail = st.columns([2, 3])
                with c_img:
                    image_bytes = load_image_bytes(gen["output_path"] or "")
                    if image_bytes:
                        st.image(image_bytes)
                        st.download_button(
                            "Download",
                            data=image_bytes,
                            file_name=f"gen_{gen['id']}.png",
                            mime="image/png",
                            key=f"dl_{gen['id']}",
                        )
                    else:
                        st.warning("Image file not found.")

                with c_detail:
                    st.markdown(f"**Base prompt:** {gen['base_prompt']}")
                    if gen.get("style_prompt"):
                        st.markdown(f"**Style prompt:** {gen['style_prompt']}")
                    if gen.get("final_prompt") != gen.get("base_prompt"):
                        st.markdown(f"**Final prompt:** {gen['final_prompt']}")
                    st.markdown(f"**Provider:** `{gen['provider']}` / `{gen.get('model', '')}`")
                    if gen.get("project_name"):
                        st.markdown(f"**Project:** {gen['project_name']}")
                    if gen.get("tags"):
                        st.markdown(f"**Tags:** {gen['tags']}")
                    if gen.get("settings"):
                        try:
                            settings_dict = json.loads(gen["settings"])
                            if settings_dict:
                                st.json(settings_dict)
                        except (json.JSONDecodeError, TypeError):
                            pass

                    if st.button("Rerun / duplicate", key=f"rerun_{gen['id']}"):
                        st.session_state.rerun_base_prompt = gen["base_prompt"]
                        st.session_state.provider = gen["provider"]
                        st.rerun()


# ============================================================
# TAB 3 — Presets
# ============================================================

with tab_presets:
    st.header("Style Presets")

    from src.presets import _presets_path
    st.caption(f"Stored in `{_presets_path()}`")

    with st.form("new_preset_form"):
        st.subheader("Create a new preset")
        preset_name = st.text_input("Preset name", placeholder="Clean Corporate")
        preset_desc = st.text_input("Description (optional)", placeholder="White background, professional look")
        preset_style = st.text_area(
            "Style prompt",
            height=80,
            placeholder="Clean corporate style, white background, 4k resolution, professional lighting, photorealistic",
        )
        submitted = st.form_submit_button("Save preset")
        if submitted:
            if not preset_name.strip():
                st.error("Preset name is required.")
            elif not preset_style.strip():
                st.error("Style prompt is required.")
            else:
                try:
                    preset_store.save_preset(
                        name=preset_name.strip(),
                        style_prompt=preset_style.strip(),
                        description=preset_desc.strip(),
                    )
                    st.success(f"Preset '{preset_name}' saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save preset: {exc}")

    st.divider()
    st.subheader("Existing presets")

    presets = preset_store.get_presets()
    if not presets:
        st.info("No presets yet.")
    else:
        for preset in presets:
            with st.expander(f"**{preset['name']}**"):
                if preset.get("description"):
                    st.markdown(f"*{preset['description']}*")
                st.code(preset["style_prompt"])
                if st.button("Delete preset", key=f"del_preset_{preset['name']}"):
                    preset_store.delete_preset(preset["name"])
                    st.rerun()


# ============================================================
# TAB 4 — References
# ============================================================

with tab_refs:
    st.header("Reference Images")
    st.caption(f"Stored in `{ref_store.get_references_dir()}`  — you can also drop files there directly.")

    with st.form("upload_ref_form"):
        st.subheader("Add a reference image")
        ref_upload = st.file_uploader("Image file", type=["png", "jpg", "jpeg"])
        ref_save_name = st.text_input("Name", placeholder="matt_headshot")
        save_submitted = st.form_submit_button("Save")
        if save_submitted:
            if not ref_upload:
                st.error("Please choose a file.")
            elif not ref_save_name.strip():
                st.error("Name is required.")
            else:
                ext = ref_upload.name.rsplit(".", 1)[-1] if "." in ref_upload.name else "jpg"
                try:
                    ref_store.save_reference(ref_save_name.strip(), ref_upload.read(), ext)
                    st.success(f"Saved '{ref_save_name}.{ext}'")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.divider()
    saved_refs = ref_store.list_references()
    if not saved_refs:
        st.info("No saved references yet.")
    else:
        cols = st.columns(4)
        for i, ref_path in enumerate(saved_refs):
            with cols[i % 4]:
                st.image(ref_path.read_bytes(), caption=ref_path.name, use_container_width=True)
                if st.button("Delete", key=f"del_ref_{ref_path.name}"):
                    ref_path.unlink()
                    st.rerun()
