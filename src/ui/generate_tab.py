"""Generate tab UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src import database as db
from src import presets as preset_store
from src import references as ref_store
from src.generator import MODEL_PRICING, PROVIDERS
from src.references import parse_reference_tokens, reference_exists
from src.services.generation_service import GenerationRequest, generate_and_store
from src.storage import load_image_bytes
from src.ui.sidebar import SidebarConfig


def _render_reference_token_feedback(reference_tokens: list[str], provider: str) -> None:
    if not reference_tokens:
        return

    if provider != "google-gemini":
        st.caption("Inline `[name]` references are available only with Google Gemini.")
        return

    missing_tokens = [token for token in reference_tokens if not reference_exists(token)]
    if missing_tokens:
        st.caption(f"Unknown references (will be ignored): {', '.join(missing_tokens)}")


def _render_preset_picker() -> str:
    presets = preset_store.get_presets()
    preset_options = ["— none —"] + [preset["name"] for preset in presets]
    selected_preset_name = st.selectbox("Style preset", preset_options)

    if selected_preset_name == "— none —":
        return ""

    preset = next(preset for preset in presets if preset["name"] == selected_preset_name)
    st.caption(preset["style_prompt"])
    return preset["style_prompt"]


@st.cache_data(show_spinner=False)
def _load_gen_thumb(output_path: str | None) -> bytes | None:
    return load_image_bytes(output_path or "")


@st.dialog("Browse Generated Images", width="large")
def _pick_generated_image() -> None:
    generations = db.get_generations()
    if not generations:
        st.info("No generated images yet.")
        return

    _COLS = 3
    for row_start in range(0, len(generations), _COLS):
        row = generations[row_start : row_start + _COLS]
        cols = st.columns(_COLS)
        for col, gen in zip(cols, row):
            with col:
                thumb = _load_gen_thumb(gen["output_path"])
                if thumb:
                    st.image(thumb, width="stretch")
                else:
                    st.markdown("_No image_")
                caption = gen.get("short_description") or gen.get("title") or f"#{gen['id']}"
                st.caption(caption)
                if st.button("Use this", key=f"pick_{gen['id']}", width="stretch"):
                    st.session_state.generated_ref_path = gen["output_path"]
                    st.rerun()


def _render_reference_picker(provider: str, settings: dict) -> bytes | None:
    saved_refs = ref_store.list_references()
    reference_image_bytes = None

    st.divider()
    if provider == "google-gemini":
        ref_mode = st.radio(
            "Reference image",
            ["None", "From library", "Upload", "Previously Generated"],
            horizontal=True,
        )
        if ref_mode == "From library":
            ref_options = [path.name for path in saved_refs]
            if ref_options:
                selected_ref_name = st.selectbox("Saved reference", ref_options)
                ref_path = next(path for path in saved_refs if path.name == selected_ref_name)
                reference_image_bytes = ref_path.read_bytes()
            else:
                st.caption("No saved references yet. Add some in the References tab.")
        elif ref_mode == "Upload":
            reference_file = st.file_uploader(
                "Image file",
                type=["png", "jpg", "jpeg"],
                label_visibility="collapsed",
            )
            if reference_file is not None:
                reference_image_bytes = reference_file.read()
        elif ref_mode == "Previously Generated":
            selected_path = st.session_state.get("generated_ref_path")
            if selected_path:
                thumb = _load_gen_thumb(selected_path)
                if thumb:
                    reference_image_bytes = thumb
                    st.image(thumb, width=160)
                else:
                    st.caption("Selected image file not found.")
                if st.button("Change…", key="change_generated_ref"):
                    _pick_generated_image()
            else:
                if st.button("Browse generated images…", key="browse_generated_ref"):
                    _pick_generated_image()

        st.divider()
        settings["aspect_ratio"] = st.selectbox(
            "Aspect ratio",
            ["16:9", "1:1", "9:16", "4:3", "3:4"],
        )
    else:
        st.caption("Reference images and inline `[name]` tokens are supported only with Google Gemini.")

    return reference_image_bytes


def render_generate_tab(sidebar_config: SidebarConfig) -> None:
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        base_prompt = st.text_area(
            "Prompt",
            value=st.session_state.rerun_base_prompt,
            height=220,
            placeholder="A professional headshot of a data scientist presenting at a conference…",
            help="Use [name] to inline a saved reference image, e.g. [matt] or [logo].",
        )
        st.session_state.rerun_base_prompt = base_prompt

        reference_tokens = parse_reference_tokens(base_prompt) if base_prompt else []
        _render_reference_token_feedback(reference_tokens, sidebar_config.provider)

        generate_button = st.button("Generate", type="primary", width="stretch")

        with st.expander("Add metadata (optional)"):
            title = st.text_input("Title", placeholder="Q1 Roadmap hero image")
            project_name = st.text_input("Project / deck", placeholder="Q1 2025 All-Hands")
            tags = st.text_input("Tags (comma-separated)", placeholder="roadmap, blue, wide")

    with col_right:
        model_options = PROVIDERS[sidebar_config.provider]["models"]
        model_labels = PROVIDERS[sidebar_config.provider].get("model_labels", {})

        def _format_model(model_id: str) -> str:
            label = model_labels.get(model_id, model_id)
            cost = MODEL_PRICING.get(model_id)
            if cost is not None:
                return f"{label}  (~${cost:.2f}/img)"
            return label

        st.selectbox(
            "Model",
            model_options,
            index=model_options.index(st.session_state.selected_model),
            key="selected_model",
            format_func=_format_model,
        )

        style_prompt = _render_preset_picker()
        reference_image_bytes = _render_reference_picker(
            sidebar_config.provider,
            sidebar_config.settings,
        )

    if generate_button:
        st.session_state.pop("last_generation", None)

        request = GenerationRequest(
            base_prompt=base_prompt,
            style_prompt=style_prompt,
            provider=sidebar_config.provider,
            model=sidebar_config.model,
            api_key=sidebar_config.api_key,
            settings=sidebar_config.settings,
            reference_image=reference_image_bytes,
            reference_tokens=reference_tokens,
            title=title,
            project_name=project_name,
            tags=tags,
        )

        with st.spinner("Generating…"):
            try:
                outcome = generate_and_store(request)
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                return

        st.session_state.last_generation = {
            "id": outcome.generation_id,
            "image_bytes": outcome.image_bytes,
            "final_prompt": outcome.result.final_prompt,
            "output_path": outcome.result.output_path,
            "provider": outcome.result.provider,
            "model": outcome.result.model,
            "settings": outcome.result.settings,
            "missing_references": outcome.missing_references,
        }

    last_gen = st.session_state.get("last_generation")
    if last_gen is None:
        return

    if last_gen.get("missing_references"):
        st.warning(f"Reference(s) not found in library: {', '.join(last_gen['missing_references'])}")

    if last_gen.get("image_bytes"):
        st.image(last_gen["image_bytes"], caption=last_gen["final_prompt"])

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            st.download_button(
                "Download",
                data=last_gen["image_bytes"],
                file_name=f"generation_{last_gen['id']}.png",
                mime="image/png",
            )
        with btn_col2:
            if st.button("Delete", type="secondary"):
                db.delete_generation(last_gen["id"])
                output_path = last_gen.get("output_path")
                if output_path:
                    Path(output_path).unlink(missing_ok=True)
                del st.session_state.last_generation
                st.rerun()

    with st.expander("Generation details"):
        st.json(
            {
                "id": last_gen["id"],
                "provider": last_gen["provider"],
                "model": last_gen["model"],
                "final_prompt": last_gen["final_prompt"],
                "settings": last_gen["settings"],
                "output_path": last_gen["output_path"],
            }
        )
