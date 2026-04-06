"""Dark/light mode theme management."""

from __future__ import annotations

from datetime import datetime, timedelta

import streamlit as st

_COOKIE_NAME = "theme_preference"
_DEFAULT_THEME = "light"

_DARK_CSS = """
<style>
/* ============================================================
   DARK MODE — Streamlit theme overrides
   ============================================================ */

/* Root + main backgrounds */
.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"] {
    background-color: #0e1117 !important;
}

/* Header */
[data-testid="stHeader"] {
    background-color: rgba(14, 17, 23, 0.95) !important;
    border-bottom: 1px solid #2d2d3a !important;
}

/* Sidebar */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background-color: #262730 !important;
}

/* Main block container */
[data-testid="block-container"],
.block-container {
    background-color: #0e1117 !important;
}

/* General text */
p, span, label, h1, h2, h3, h4, h5, h6, li {
    color: #fafafa !important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] div {
    color: #fafafa !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #b0b0b0 !important;
}

/* Text inputs and text areas */
[data-baseweb="input"],
[data-baseweb="textarea"] {
    background-color: #262730 !important;
    border-color: #4a4a5a !important;
}
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
input[type="text"],
input[type="email"],
input[type="password"],
input[type="number"],
input[type="search"],
textarea {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4a5a !important;
    caret-color: #fafafa !important;
}

/* Select / dropdown trigger */
[data-baseweb="select"] > div:first-child,
[data-baseweb="select"] [role="combobox"] {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4a5a !important;
}
/* Dropdown option list */
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="menu"] {
    background-color: #262730 !important;
}
[data-baseweb="menu"] [role="option"],
[data-baseweb="menu"] li {
    background-color: #262730 !important;
    color: #fafafa !important;
}
[data-baseweb="menu"] [role="option"]:hover,
[data-baseweb="menu"] li:hover {
    background-color: #3a3a4a !important;
}

/* Tabs */
[data-baseweb="tab-list"] {
    background-color: #0e1117 !important;
    border-bottom-color: #2d2d3a !important;
}
[data-baseweb="tab"] {
    background-color: transparent !important;
    color: #c0c0c0 !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    color: #ff4b4b !important;
    background-color: transparent !important;
}
[data-baseweb="tab-highlight"] {
    background-color: #ff4b4b !important;
}
[data-baseweb="tab-border"] {
    background-color: #2d2d3a !important;
}

/* Buttons (secondary / default) */
[data-testid="stBaseButton-secondary"],
button[kind="secondary"] {
    background-color: #262730 !important;
    color: #fafafa !important;
    border-color: #4a4a5a !important;
}
[data-testid="stBaseButton-secondary"]:hover,
button[kind="secondary"]:hover {
    background-color: #3a3a4a !important;
    border-color: #6a6a7a !important;
}

/* Dividers */
hr {
    border-color: #2d2d3a !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #1a1c24 !important;
    border-color: #2d2d3a !important;
}
[data-testid="stExpander"] summary span {
    color: #fafafa !important;
}

/* Alert boxes */
[data-testid="stAlert"] {
    background-color: #1a1c24 !important;
    border-color: #2d2d3a !important;
}
[data-testid="stAlert"] p {
    color: #fafafa !important;
}

/* Code blocks */
code, pre {
    background-color: #1a1c24 !important;
    color: #e0e0e0 !important;
}

/* Scrollbars */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #1a1c24; }
::-webkit-scrollbar-thumb { background: #4a4a5a; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #6a6a7a; }
</style>
"""


def init_theme(cookie_manager) -> None:
    """Initialize theme from cookie or fall back to the default.

    Must be called once near the top of app.py, after the cookie manager
    is ready but before ``apply_theme``.
    """
    if "theme" not in st.session_state:
        saved = cookie_manager.get(_COOKIE_NAME)
        st.session_state["theme"] = saved if saved in ("light", "dark") else _DEFAULT_THEME


def apply_theme() -> None:
    """Inject CSS for the active theme.

    Must be called on every render (i.e., at the top level of app.py) so
    the styles are present regardless of which tab the user is viewing.
    """
    if st.session_state.get("theme") == "dark":
        st.markdown(_DARK_CSS, unsafe_allow_html=True)


def toggle_theme(cookie_manager) -> None:
    """Flip the active theme and persist the choice to a cookie."""
    current = st.session_state.get("theme", _DEFAULT_THEME)
    new_theme = "dark" if current == "light" else "light"
    st.session_state["theme"] = new_theme
    expires_at = datetime.now() + timedelta(days=365)
    cookie_manager.set(_COOKIE_NAME, new_theme, expires_at=expires_at)
    st.rerun()
