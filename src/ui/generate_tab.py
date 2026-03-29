"""Generate tab UI."""

from __future__ import annotations

import streamlit as st

from src import presets as preset_store
from src import references as ref_store
from src.references import parse_reference_tokens, reference_exists
from src.services.generation_service import GenerationRequest, generate_and_store
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


def _render_reference_picker(provider: str, settings: dict) -> bytes | None:
    saved_refs = ref_store.list_references()
    reference_image_bytes = None

    st.divider()
    if provider == "google-gemini":
        ref_mode = st.radio(
            "Reference image",
            ["None", "From library", "Upload"],
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
        style_prompt = _render_preset_picker()
        reference_image_bytes = _render_reference_picker(
            sidebar_config.provider,
            sidebar_config.settings,
        )

    if not generate_button:
        return

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

    if outcome.missing_references:
        st.warning(f"Reference(s) not found in library: {', '.join(outcome.missing_references)}")

    if outcome.image_bytes:
        st.image(outcome.image_bytes, caption=outcome.result.final_prompt)
        st.download_button(
            "Download",
            data=outcome.image_bytes,
            file_name=f"generation_{outcome.generation_id}.png",
            mime="image/png",
        )

    with st.expander("Generation details"):
        st.json(
            {
                "id": outcome.generation_id,
                "provider": outcome.result.provider,
                "model": outcome.result.model,
                "final_prompt": outcome.result.final_prompt,
                "settings": outcome.result.settings,
                "output_path": outcome.result.output_path,
            }
        )
