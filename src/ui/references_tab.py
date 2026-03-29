"""References tab UI."""

from __future__ import annotations

import streamlit as st

from src import references as ref_store


def render_references_tab() -> None:
    st.header("Reference Images")

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
                    saved_path = ref_store.save_reference(ref_save_name.strip(), ref_upload.read(), ext)
                    st.success(f"Saved '{saved_path.name}'")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.divider()
    saved_refs = ref_store.list_references()
    if not saved_refs:
        st.info("No saved references yet.")
        return

    cols = st.columns(4)
    for index, ref_path in enumerate(saved_refs):
        with cols[index % 4]:
            st.image(ref_path.read_bytes(), caption=ref_path.name, width="stretch")
            if st.button("Delete", key=f"del_ref_{ref_path.name}"):
                ref_path.unlink()
                st.rerun()
