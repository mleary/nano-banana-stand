"""Sidebar rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from src import GITHUB_REPO_URL, database as db
from src.auth import get_user, is_configured, logout
from src.generator import PROVIDERS, get_provider_api_key
from src.theme import toggle_theme


@dataclass
class SidebarConfig:
    provider: str
    model: str
    api_key: str
    api_key_env_var: str
    settings: dict[str, Any] = field(default_factory=dict)


def render_sidebar(cookie_manager) -> SidebarConfig:
    with st.sidebar:
        user = get_user()
        if is_configured() and user:
            st.markdown(f"**{user['name']}**  \n`{user['email']}`")
            if st.button("Sign out", width="stretch"):
                logout(cookie_manager)
            st.divider()

        st.header("Provider")

        provider_options = list(PROVIDERS.keys())
        provider_labels = [PROVIDERS[provider]["label"] for provider in provider_options]
        selected_provider_label = st.selectbox(
            "Image provider",
            provider_labels,
            index=provider_options.index(st.session_state.provider),
            key="sidebar_provider_select",
        )
        st.session_state.provider = provider_options[provider_labels.index(selected_provider_label)]
        provider = st.session_state.provider

        model_options = PROVIDERS[provider]["models"]
        if st.session_state.selected_model not in model_options:
            st.session_state.selected_model = PROVIDERS[provider]["default_model"]

        api_key_env_var = PROVIDERS[provider]["api_key_env"]
        api_key = get_provider_api_key(provider)
        if not api_key:
            st.warning(f"`{api_key_env_var}` not set.")

        st.divider()
        settings: dict[str, Any] = {}
        if provider == "google-gemini":
            settings["num_images"] = 1
            st.caption("The app currently saves one image per generation.")
        elif provider == "openai":
            size_map = {
                "dall-e-3": ["1792x1024", "1024x1024", "1024x1792"],
                "dall-e-2": ["256x256", "512x512", "1024x1024"],
            }
            model = st.session_state.selected_model
            settings["size"] = st.selectbox("Size", size_map.get(model, ["1024x1024"]))
            if model == "dall-e-3":
                settings["quality"] = st.selectbox("Quality", ["standard", "hd"])
                settings["style"] = st.selectbox("Style", ["vivid", "natural"])

        st.divider()
        st.caption("💰 Estimated usage")
        summary = db.get_cost_summary()
        for label, key in [("Today", "today"), ("Week", "this_week"), ("Month", "this_month")]:
            cents = summary[key] * 100
            if cents < 1:
                display = f"{cents:.2f}¢"
            elif cents < 100:
                display = f"{cents:.1f}¢"
            else:
                display = f"${summary[key]:.2f}"
            st.caption(f"{label}: **{display}**")

        st.divider()
        theme = st.session_state.get("theme", "light")
        label = "☀️ Light mode" if theme == "dark" else "🌙 Dark mode"
        if st.button(label, width="stretch"):
            toggle_theme(cookie_manager)

        st.markdown(
            f"""
            <div style="text-align: center; margin-top: 0.75rem; opacity: 0.6;">
              <a href="{GITHUB_REPO_URL}" target="_blank" title="View on GitHub"
                 style="color: inherit; text-decoration: none; display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.8rem;">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" style="fill: currentColor; vertical-align: middle;">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
                           0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
                           -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
                           .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
                           -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0
                           1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56
                           .82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07
                           -.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub
              </a>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return SidebarConfig(
        provider=provider,
        model=st.session_state.selected_model,
        api_key=api_key,
        api_key_env_var=api_key_env_var,
        settings=settings,
    )
