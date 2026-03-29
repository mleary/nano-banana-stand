"""Google OAuth2 authentication for the Streamlit app.

Set the following environment variables to enable auth:
  GOOGLE_CLIENT_ID       — OAuth 2.0 client ID
  GOOGLE_CLIENT_SECRET   — OAuth 2.0 client secret
  APP_URL                — Public base URL of the deployed app (no trailing slash)
  GOOGLE_ALLOWED_DOMAIN  — (optional) restrict sign-in to one Google Workspace domain

If GOOGLE_CLIENT_ID is not set the module is a no-op and all users have open access.
"""

import os
import secrets
import sqlite3
import time
from typing import Optional

import streamlit as st
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

_COOKIE_NAME = "auth_session"
_SESSION_TTL = 7 * 24 * 3600   # 7 days
_STATE_TTL = 900                # 15 minutes


# ---------------------------------------------------------------------------
# Database helpers (reuse the app's SQLite database)
# ---------------------------------------------------------------------------

def _db_path() -> str:
    return os.environ.get("DB_PATH", "data/db.sqlite3")


def _init_auth_tables() -> None:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state      TEXT    PRIMARY KEY,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token      TEXT    PRIMARY KEY,
            email      TEXT    NOT NULL,
            name       TEXT    NOT NULL,
            picture    TEXT,
            created_at INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def _store_state(state: str) -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute(
        "INSERT OR REPLACE INTO oauth_states (state, created_at) VALUES (?, ?)",
        (state, int(time.time())),
    )
    conn.execute(
        "DELETE FROM oauth_states WHERE created_at < ?",
        (int(time.time()) - _STATE_TTL,),
    )
    conn.commit()
    conn.close()


def _consume_state(state: str) -> bool:
    """Return True and delete the state if it is valid, else False."""
    conn = sqlite3.connect(_db_path())
    row = conn.execute(
        "SELECT state FROM oauth_states WHERE state = ? AND created_at > ?",
        (state, int(time.time()) - _STATE_TTL),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
    conn.close()
    return row is not None


def _create_session(email: str, name: str, picture: str) -> str:
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect(_db_path())
    conn.execute(
        "INSERT INTO auth_sessions (token, email, name, picture, created_at) VALUES (?, ?, ?, ?, ?)",
        (token, email, name, picture or "", int(time.time())),
    )
    conn.execute(
        "DELETE FROM auth_sessions WHERE created_at < ?",
        (int(time.time()) - _SESSION_TTL,),
    )
    conn.commit()
    conn.close()
    return token


def _lookup_session(token: str) -> Optional[dict]:
    if not token:
        return None
    conn = sqlite3.connect(_db_path())
    row = conn.execute(
        "SELECT email, name, picture FROM auth_sessions WHERE token = ? AND created_at > ?",
        (token, int(time.time()) - _SESSION_TTL),
    ).fetchone()
    conn.close()
    if row:
        return {"email": row[0], "name": row[1], "picture": row[2]}
    return None


def _delete_session(token: str) -> None:
    conn = sqlite3.connect(_db_path())
    conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------

def _build_flow(redirect_uri: str) -> Flow:
    client_config = {
        "web": {
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)


def _redirect_uri() -> str:
    return os.environ.get("APP_URL", "http://localhost:8501").rstrip("/")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    """Return True when Google OAuth credentials are present in the environment."""
    return bool(os.environ.get("GOOGLE_CLIENT_ID") and os.environ.get("GOOGLE_CLIENT_SECRET"))


def get_user() -> Optional[dict]:
    """Return the signed-in user dict (email, name, picture) or None."""
    return st.session_state.get("_auth_user")


def logout(cookie_manager) -> None:
    """Sign out the current user, delete the server-side session, and rerun."""
    token = cookie_manager.get(_COOKIE_NAME)
    if token:
        _delete_session(token)
        cookie_manager.delete(_COOKIE_NAME)
    st.session_state.pop("_auth_user", None)
    st.rerun()


def require_auth(cookie_manager) -> None:
    """Enforce authentication.  Call once near the top of app.py.

    Flow:
      1. Already authenticated in this Streamlit session → return immediately.
      2. OAuth callback detected (?code=...&state=...) → exchange code, set cookie, rerun.
      3. Valid session cookie found → restore user into session state, return.
      4. No valid auth → display sign-in page and stop execution.

    If GOOGLE_CLIENT_ID is not configured this function is a no-op.
    """
    if not is_configured():
        return

    _init_auth_tables()

    # 1. Already authenticated in this session
    if "_auth_user" in st.session_state:
        return

    params = st.query_params.to_dict()

    # 2. Handle OAuth callback
    if "code" in params and "error" not in params:
        code = params.get("code", "")
        state = params.get("state", "")

        if not _consume_state(state):
            st.error("Authentication state is invalid or expired. Please try signing in again.")
            _render_login_page()
            return

        try:
            flow = _build_flow(_redirect_uri())
            flow.fetch_token(code=code)
            credentials = flow.credentials

            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                os.environ["GOOGLE_CLIENT_ID"],
            )

            email: str = id_info.get("email", "")
            allowed_domain = os.environ.get("GOOGLE_ALLOWED_DOMAIN", "").strip()
            if allowed_domain and not email.lower().endswith(f"@{allowed_domain.lower()}"):
                st.error(
                    f"Access is restricted to **@{allowed_domain}** accounts. "
                    f"You signed in as `{email}`."
                )
                st.stop()

            user = {
                "email": email,
                "name": id_info.get("name", email),
                "picture": id_info.get("picture", ""),
            }
            token = _create_session(user["email"], user["name"], user["picture"])
            cookie_manager.set(_COOKIE_NAME, token, max_age=_SESSION_TTL)
            st.session_state["_auth_user"] = user
            st.query_params.clear()
            st.rerun()
            return

        except Exception as exc:
            st.error(f"Authentication failed: {exc}")
            _render_login_page()
            return

    # 3. Check for existing session cookie
    token = cookie_manager.get(_COOKIE_NAME)
    if token:
        user = _lookup_session(token)
        if user:
            st.session_state["_auth_user"] = user
            return

    # 4. Show sign-in page
    _render_login_page()


def _render_login_page() -> None:
    state = secrets.token_urlsafe(32)
    _store_state(state)

    flow = _build_flow(_redirect_uri())
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=state,
        prompt="select_account",
    )

    allowed_domain = os.environ.get("GOOGLE_ALLOWED_DOMAIN", "").strip()
    domain_note = f"Sign in with your **@{allowed_domain}** Google account." if allowed_domain else "Sign in with your Google account."

    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {max-width: 480px; padding-top: 4rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("AI Image Generator")
    st.markdown("---")
    st.markdown(domain_note)
    st.link_button("Sign in with Google", auth_url, use_container_width=True, type="primary")
    st.stop()
