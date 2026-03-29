"""Sidebar rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import streamlit as st

from src.auth import get_user, is_configured, logout
from src.generator import PROVIDERS, get_provider_api_key


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
        model = st.selectbox(
            "Model",
            model_options,
            index=model_options.index(st.session_state.selected_model),
            key="selected_model",
        )

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
            settings["size"] = st.selectbox("Size", size_map.get(model, ["1024x1024"]))
            if model == "dall-e-3":
                settings["quality"] = st.selectbox("Quality", ["standard", "hd"])
                settings["style"] = st.selectbox("Style", ["vivid", "natural"])

    return SidebarConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        api_key_env_var=api_key_env_var,
        settings=settings,
    )
