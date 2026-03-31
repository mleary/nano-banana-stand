"""Presets tab UI."""

from __future__ import annotations

import streamlit as st

from src import presets as preset_store


def render_presets_tab() -> None:
    st.header("Style Presets")

    with st.form("new_preset_form"):
        st.subheader("Create a new preset")
        preset_name = st.text_input("Preset name", placeholder="Clean Corporate")
        preset_description = st.text_input(
            "Description (optional)",
            placeholder="White background, professional look",
        )
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
                        description=preset_description.strip(),
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
        return

    editing_key = "editing_preset"
    if editing_key not in st.session_state:
        st.session_state[editing_key] = None

    for preset in presets:
        with st.expander(f"**{preset['name']}**"):
            if st.session_state[editing_key] == preset["name"]:
                # Edit form
                with st.form(key=f"edit_preset_form_{preset['name']}"):
                    new_description = st.text_input(
                        "Description",
                        value=preset.get("description", ""),
                    )
                    new_style = st.text_area(
                        "Style prompt",
                        value=preset["style_prompt"],
                        height=80,
                    )
                    save_col, cancel_col = st.columns([1, 1])
                    with save_col:
                        save_clicked = st.form_submit_button("Save changes")
                    with cancel_col:
                        cancel_clicked = st.form_submit_button("Cancel")

                if save_clicked:
                    if not new_style.strip():
                        st.error("Style prompt is required.")
                    else:
                        try:
                            preset_store.update_preset(
                                name=preset["name"],
                                style_prompt=new_style.strip(),
                                description=new_description.strip(),
                            )
                            st.session_state[editing_key] = None
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Could not update preset: {exc}")
                elif cancel_clicked:
                    st.session_state[editing_key] = None
                    st.rerun()
            else:
                # Read view
                if preset.get("description"):
                    st.markdown(f"*{preset['description']}*")
                st.code(preset["style_prompt"])
                btn_col1, btn_col2 = st.columns([1, 1])
                with btn_col1:
                    if st.button("Edit preset", key=f"edit_preset_{preset['name']}"):
                        st.session_state[editing_key] = preset["name"]
                        st.rerun()
                with btn_col2:
                    if st.button("Delete preset", key=f"del_preset_{preset['name']}"):
                        preset_store.delete_preset(preset["name"])
                        st.rerun()
