"""Streamlit app for reproducible presentation image generation.

Tabs:
  ✨ Generate  — create images with prompt + style preset
  📂 History   — browse, search, download, and rerun past generations
  🎭 Presets   — manage reusable style prompts
  ⚙️ Settings  — configure provider, API keys, and generation parameters
"""

import json
from pathlib import Path

import streamlit as st

from src import database as db
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
_default("rerun_style_prompt", "")
_default("rerun_provider", "google-gemini")
_default("rerun_model", "")
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

    env_key_var = PROVIDERS[provider]["api_key_env"]
    env_key_val = get_provider_api_key(provider)

    api_key_input = st.text_input(
        f"API key (`{env_key_var}`)",
        value=env_key_val,
        type="password",
        help=f"Set {env_key_var} env var or enter here.",
    )

    model_options = PROVIDERS[provider]["models"]
    selected_model = st.selectbox("Model", model_options)

    st.divider()
    st.caption("Keys entered here are kept in session memory only and not persisted.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_generate, tab_history, tab_presets = st.tabs(
    ["✨ Generate", "📂 History", "🎭 Presets"]
)

# ============================================================
# TAB 1 — Generate
# ============================================================

with tab_generate:
    st.header("Generate an Image")

    col_prompt, col_meta = st.columns([3, 2])

    with col_prompt:
        base_prompt = st.text_area(
            "Base prompt",
            value=st.session_state.rerun_base_prompt,
            height=120,
            placeholder="A professional headshot of a data scientist presenting at a conference…",
        )
        # reset rerun trigger
        st.session_state.rerun_base_prompt = base_prompt

        presets = db.get_presets()
        preset_options = ["— none —"] + [p["name"] for p in presets]
        selected_preset_name = st.selectbox("Style preset", preset_options)

        style_prompt_from_preset = ""
        selected_preset_id = None
        if selected_preset_name != "— none —":
            preset = next(p for p in presets if p["name"] == selected_preset_name)
            style_prompt_from_preset = preset["style_prompt"]
            selected_preset_id = preset["id"]

        style_prompt = st.text_area(
            "Style prompt (optional — override or add to preset)",
            value=st.session_state.rerun_style_prompt or style_prompt_from_preset,
            height=80,
            placeholder="Clean corporate style, white background, 4k, photorealistic…",
        )

        enhance = st.checkbox(
            "Enhance prompt with Gemini before generation",
            value=False,
            help="Uses chatlas ChatGoogle to refine your prompt. Requires Google Gemini provider.",
        )

    with col_meta:
        title = st.text_input("Title (optional)", placeholder="Q1 Roadmap hero image")
        project_name = st.text_input("Project / deck (optional)", placeholder="Q1 2025 All-Hands")
        tags = st.text_input("Tags (optional, comma-separated)", placeholder="roadmap, blue, wide")

        st.subheader("Provider settings")
        current_provider = st.session_state.provider

        extra_settings: dict = {}

        if current_provider == "google-gemini":
            extra_settings["aspect_ratio"] = st.selectbox(
                "Aspect ratio", ["1:1", "16:9", "9:16", "4:3", "3:4"]
            )
            extra_settings["num_images"] = st.slider("Images to generate", 1, 4, 1)

        elif current_provider == "openai":
            size_map = {
                "dall-e-3": ["1024x1024", "1792x1024", "1024x1792"],
                "dall-e-2": ["256x256", "512x512", "1024x1024"],
            }
            extra_settings["size"] = st.selectbox(
                "Size", size_map.get(selected_model, ["1024x1024"])
            )
            if selected_model == "dall-e-3":
                extra_settings["quality"] = st.selectbox("Quality", ["standard", "hd"])
                extra_settings["style"] = st.selectbox("Style", ["vivid", "natural"])

        elif current_provider == "fal":
            extra_settings["image_size"] = st.selectbox(
                "Image size",
                ["square_hd", "square", "portrait_4_3", "portrait_16_9",
                 "landscape_4_3", "landscape_16_9"],
            )
            extra_settings["num_inference_steps"] = st.slider("Steps", 1, 50, 28)
            seed_input = st.text_input("Seed (leave blank for random)")
            if seed_input.strip().isdigit():
                extra_settings["seed"] = int(seed_input)

        elif current_provider == "replicate":
            extra_settings["width"] = st.number_input("Width", 512, 2048, 1024, step=64)
            extra_settings["height"] = st.number_input("Height", 512, 2048, 1024, step=64)
            extra_settings["num_inference_steps"] = st.slider("Steps", 1, 50, 28)

    generate_btn = st.button("Generate Image", type="primary", use_container_width=True)

    if generate_btn:
        if not base_prompt.strip():
            st.error("Please enter a base prompt.")
        elif not api_key_input.strip():
            st.error(f"Please enter an API key for {current_provider}.")
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
                    )

                    gen_id = db.save_generation(
                        base_prompt=base_prompt,
                        final_prompt=result.final_prompt,
                        provider=result.provider,
                        output_path=result.output_path,
                        title=title or None,
                        project_name=project_name or None,
                        tags=tags or None,
                        style_preset_id=selected_preset_id,
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
                        st.session_state.rerun_style_prompt = gen.get("style_prompt") or ""
                        st.session_state.provider = gen["provider"]
                        st.rerun()


# ============================================================
# TAB 3 — Presets
# ============================================================

with tab_presets:
    st.header("Style Presets")

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
                    db.save_preset(
                        name=preset_name.strip(),
                        style_prompt=preset_style.strip(),
                        description=preset_desc.strip() or None,
                    )
                    st.success(f"Preset '{preset_name}' saved.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save preset: {exc}")

    st.divider()
    st.subheader("Existing presets")

    presets = db.get_presets()
    if not presets:
        st.info("No presets yet.")
    else:
        for preset in presets:
            with st.expander(f"**{preset['name']}**"):
                if preset.get("description"):
                    st.markdown(f"*{preset['description']}*")
                st.code(preset["style_prompt"])
                st.caption(f"Created: {preset['created_at'][:19]}")
                if st.button("Delete preset", key=f"del_preset_{preset['id']}"):
                    db.delete_preset(preset["id"])
                    st.rerun()
