"""History tab UI."""

from __future__ import annotations

import json

import streamlit as st

from src import database as db
from src.generator import PROVIDERS, get_provider_api_key
from src.storage import load_image_bytes

_PROMPT_PREVIEW_LEN = 40


def _reuse_generation_inputs(generation: dict) -> None:
    st.session_state.rerun_base_prompt = generation["base_prompt"]
    st.session_state.provider = generation["provider"]
    default_model = PROVIDERS[generation["provider"]]["default_model"]
    saved_model = generation.get("model") or default_model
    st.session_state.selected_model = (
        saved_model if saved_model in PROVIDERS[generation["provider"]]["models"] else default_model
    )
    st.rerun()


def _render_backfill_section() -> None:
    missing = db.get_generations_missing_descriptions()
    if not missing:
        return

    provider = st.session_state.get("provider", "google-gemini")
    api_key = get_provider_api_key(provider)

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"{len(missing)} history item(s) are missing short descriptions.")
    with col2:
        if not api_key:
            st.caption("Set API key to backfill.")
        elif st.button("Backfill descriptions", key="backfill_btn"):
            from src.services.description_service import generate_short_description
            progress = st.progress(0, text="Generating descriptions…")
            for i, gen in enumerate(missing):
                desc = generate_short_description(gen["base_prompt"], api_key)
                if desc:
                    db.update_short_description(gen["id"], desc)
                progress.progress((i + 1) / len(missing), text=f"Processing {i + 1}/{len(missing)}…")
            progress.empty()
            st.rerun()
    st.divider()


def render_history_tab() -> None:
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
        return

    _render_backfill_section()

    st.caption(f"{len(generations)} generation(s) found.")
    for generation in generations:
        short_desc = generation.get("short_description")
        label = short_desc or generation.get("title") or f"Generation #{generation['id']}"
        raw_prompt = generation.get("base_prompt") or ""
        prompt_preview = raw_prompt[:_PROMPT_PREVIEW_LEN] + ("…" if len(raw_prompt) > _PROMPT_PREVIEW_LEN else "")
        with st.expander(f"**{label}** — {generation['created_at'][:19]} | {generation['provider']} | {prompt_preview}"):
            c_img, c_detail = st.columns([2, 3])
            with c_img:
                image_bytes = load_image_bytes(generation["output_path"] or "")
                if image_bytes:
                    st.image(image_bytes)
                    st.download_button(
                        "Download",
                        data=image_bytes,
                        file_name=f"gen_{generation['id']}.png",
                        mime="image/png",
                        key=f"dl_{generation['id']}",
                    )
                else:
                    st.warning("Image file not found.")

            with c_detail:
                if short_desc:
                    st.markdown(f"**Description:** {short_desc}")
                st.markdown(f"**Base prompt:** {generation['base_prompt']}")
                if generation.get("style_prompt"):
                    st.markdown(f"**Style prompt:** {generation['style_prompt']}")
                if generation.get("final_prompt") != generation.get("base_prompt"):
                    st.markdown(f"**Final prompt:** {generation['final_prompt']}")
                st.markdown(f"**Provider:** `{generation['provider']}` / `{generation.get('model', '')}`")
                if generation.get("project_name"):
                    st.markdown(f"**Project:** {generation['project_name']}")
                if generation.get("tags"):
                    st.markdown(f"**Tags:** {generation['tags']}")
                if generation.get("settings"):
                    try:
                        settings_dict = json.loads(generation["settings"])
                        if settings_dict:
                            st.json(settings_dict)
                    except (json.JSONDecodeError, TypeError):
                        pass

                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("Reuse prompt", key=f"rerun_{generation['id']}"):
                        _reuse_generation_inputs(generation)
                with btn_col2:
                    if st.button("Delete", key=f"del_gen_{generation['id']}", type="secondary"):
                        db.delete_generation(generation["id"])
                        st.rerun()
