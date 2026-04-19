"""History tab UI."""

from __future__ import annotations

import json

import streamlit as st

from src import database as db
from src.generator import PROVIDERS, get_provider_api_key
from src.storage import load_image_bytes

_THUMB_COLS = 4


def _reuse_generation_inputs(generation: dict) -> None:
    st.session_state.rerun_base_prompt = generation["base_prompt"]
    st.session_state.provider = generation["provider"]
    default_model = PROVIDERS[generation["provider"]]["default_model"]
    saved_model = generation.get("model") or default_model
    st.session_state.selected_model = (
        saved_model if saved_model in PROVIDERS[generation["provider"]]["models"] else default_model
    )
    st.rerun()


@st.cache_data(show_spinner=False)
def _load_thumb(output_path: str | None) -> bytes | None:
    return load_image_bytes(output_path or "")


def _render_backfill_section() -> None:
    missing = db.get_generations_missing_descriptions()
    if not missing:
        return

    api_key = get_provider_api_key("google-gemini")

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"{len(missing)} history item(s) are missing short descriptions.")
    with col2:
        if not api_key:
            st.caption("Gemini API key required to backfill.")
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


def _render_detail_panel(generation: dict) -> None:
    image_bytes = _load_thumb(generation["output_path"])

    st.divider()

    short_desc = generation.get("short_description")
    label = short_desc or generation.get("title") or f"Generation #{generation['id']}"
    st.subheader(label)
    st.caption(f"{generation['created_at'][:19]} · {generation['provider']} · {generation.get('model', '')}")

    c_img, c_detail = st.columns([2, 3])
    with c_img:
        if image_bytes:
            st.image(image_bytes, use_container_width=True)
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
        st.markdown(f"**Base prompt:** {generation['base_prompt']}")
        if generation.get("style_prompt"):
            st.markdown(f"**Style:** {generation['style_prompt']}")
        if generation.get("final_prompt") != generation.get("base_prompt"):
            st.markdown(f"**Final prompt:** {generation['final_prompt']}")
        if generation.get("project_name"):
            st.markdown(f"**Project:** {generation['project_name']}")
        if generation.get("tags"):
            st.markdown(f"**Tags:** {generation['tags']}")
        if generation.get("settings"):
            try:
                settings_dict = json.loads(generation["settings"])
                if settings_dict:
                    st.json(settings_dict, expanded=False)
            except (json.JSONDecodeError, TypeError):
                pass

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button("Reuse prompt", key=f"rerun_{generation['id']}", use_container_width=True):
                _reuse_generation_inputs(generation)
        with btn_col2:
            if st.button("Close", key=f"close_{generation['id']}", use_container_width=True):
                st.session_state.history_selected_id = None
                st.rerun()
        with btn_col3:
            if st.button("Delete", key=f"del_gen_{generation['id']}", type="secondary", use_container_width=True):
                db.delete_generation(generation["id"])
                st.session_state.history_selected_id = None
                st.rerun()


def _render_thumbnail_grid(generations: list[dict]) -> None:
    selected_id = st.session_state.get("history_selected_id")

    for row_start in range(0, len(generations), _THUMB_COLS):
        row = generations[row_start : row_start + _THUMB_COLS]
        cols = st.columns(_THUMB_COLS)
        for col, generation in zip(cols, row):
            with col:
                image_bytes = _load_thumb(generation["output_path"])
                gen_id = generation["id"]
                is_selected = gen_id == selected_id

                if image_bytes:
                    st.image(image_bytes, use_container_width=True)
                else:
                    st.markdown("_No image_")

                short_desc = generation.get("short_description")
                caption = short_desc or generation.get("title") or f"#{gen_id}"
                st.caption(caption)

                btn_label = "✓ Selected" if is_selected else "View"
                btn_type = "primary" if is_selected else "secondary"
                if st.button(btn_label, key=f"sel_{gen_id}", use_container_width=True, type=btn_type):
                    st.session_state.history_selected_id = None if is_selected else gen_id
                    st.rerun()


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

    _render_thumbnail_grid(generations)

    selected_id = st.session_state.get("history_selected_id")
    if selected_id:
        selected = next((g for g in generations if g["id"] == selected_id), None)
        if selected:
            _render_detail_panel(selected)
        else:
            st.session_state.history_selected_id = None
            st.rerun()
