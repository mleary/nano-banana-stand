"""History tab UI."""

from __future__ import annotations

import json

import streamlit as st

from src import database as db
from src.generator import PROVIDERS
from src.storage import load_image_bytes

_THUMB_COLS = 4

_SORT_LABELS = {
    "newest": "Newest first",
    "oldest": "Oldest first",
    "title": "Title (A–Z)",
    "project": "Project (A–Z)",
}


def _normalize(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    return stripped if stripped else None


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


@st.dialog("Generation Details", width="large")
def _show_detail_modal(generation: dict) -> None:
    image_bytes = _load_thumb(generation["output_path"])

    short_desc = generation.get("short_description")
    label = short_desc or generation.get("title") or f"Generation #{generation['id']}"
    st.subheader(label)
    st.caption(f"{generation['created_at'][:19]} · {generation['provider']} · {generation.get('model', '')}")

    c_img, c_detail = st.columns([2, 3])
    with c_img:
        if image_bytes:
            st.image(image_bytes, width="stretch")
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

        with st.expander("Edit metadata"):
            new_title = st.text_input(
                "Title",
                value=generation.get("title") or "",
                key=f"edit_title_{generation['id']}",
            )
            new_project = st.text_input(
                "Project",
                value=generation.get("project_name") or "",
                key=f"edit_project_{generation['id']}",
            )
            new_tags = st.text_input(
                "Tags",
                value=generation.get("tags") or "",
                key=f"edit_tags_{generation['id']}",
                placeholder="comma-separated",
            )
            if st.button("Save metadata", key=f"save_meta_{generation['id']}", width="stretch"):
                db.update_generation_metadata(
                    gen_id=generation["id"],
                    title=_normalize(new_title),
                    project_name=_normalize(new_project),
                    tags=_normalize(new_tags),
                )
                st.rerun()

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Reuse prompt", key=f"rerun_{generation['id']}", width="stretch"):
                _reuse_generation_inputs(generation)
        with btn_col2:
            if st.button("Delete", key=f"del_gen_{generation['id']}", type="secondary", width="stretch"):
                db.delete_generation(generation["id"])
                st.rerun()


def _render_thumbnail_grid(generations: list[dict]) -> None:
    for row_start in range(0, len(generations), _THUMB_COLS):
        row = generations[row_start : row_start + _THUMB_COLS]
        cols = st.columns(_THUMB_COLS)
        for col, generation in zip(cols, row):
            with col:
                image_bytes = _load_thumb(generation["output_path"])
                gen_id = generation["id"]

                if image_bytes:
                    st.image(image_bytes, width="stretch")
                else:
                    st.markdown("_No image_")

                short_desc = generation.get("short_description")
                caption = short_desc or generation.get("title") or f"#{gen_id}"
                st.caption(caption)

                if st.button("View", key=f"sel_{gen_id}", width="stretch"):
                    _show_detail_modal(generation)


def render_history_tab() -> None:
    st.header("Generation History")

    col_filter1, col_filter2, col_sort = st.columns(3)
    with col_filter1:
        projects = ["All projects"] + db.get_projects()
        selected_project = st.selectbox("Filter by project", projects)
    with col_filter2:
        search_query = st.text_input("Search prompts / titles / tags", placeholder="roadmap…")
    with col_sort:
        sort_key = st.selectbox(
            "Sort by",
            options=list(_SORT_LABELS.keys()),
            format_func=lambda k: _SORT_LABELS[k],
        )

    project_filter = None if selected_project == "All projects" else selected_project
    generations = db.get_generations(project_name=project_filter, search=search_query, sort_by=sort_key)

    if not generations:
        st.info("No generations yet. Head to ✨ Generate to create your first image.")
        return

    st.caption(f"{len(generations)} generation(s) found.")

    _render_thumbnail_grid(generations)
