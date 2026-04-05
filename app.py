"""Streamlit app for reproducible presentation image generation."""

from dotenv import load_dotenv

load_dotenv()

import streamlit as st
from extra_streamlit_components import CookieManager

from src import database as db
from src.auth import require_auth
from src.generator import PROVIDERS
from src.ui.generate_tab import render_generate_tab
from src.ui.history_tab import render_history_tab
from src.ui.presets_tab import render_presets_tab
from src.ui.references_tab import render_references_tab
from src.ui.sidebar import render_sidebar


def _default_session_state(key: str, value) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def _init_session_state() -> None:
    _default_session_state("rerun_base_prompt", "")
    _default_session_state("provider", "google-gemini")
    _default_session_state("selected_model", PROVIDERS["google-gemini"]["default_model"])


st.set_page_config(
    page_title="The Banana Stand",
    page_icon="img/favicon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    button[data-baseweb="tab"] > div > p {
        font-size: 1.1rem;
        font-weight: 500;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

_cookie_manager = CookieManager(key="nano_banana_auth")
require_auth(_cookie_manager)
db.init_db()
_init_session_state()

sidebar_config = render_sidebar(_cookie_manager)

tab_generate, tab_history, tab_presets, tab_refs = st.tabs(
    ["✨ Generate", "📂 History", "🎭 Presets", "🖼️ References"]
)

with tab_generate:
    render_generate_tab(sidebar_config)

with tab_history:
    render_history_tab()

with tab_presets:
    render_presets_tab()

with tab_refs:
    render_references_tab()
