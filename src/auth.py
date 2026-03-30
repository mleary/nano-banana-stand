"""Google OAuth2 authentication for the Streamlit app.

Set the following environment variables to enable auth:
  GOOGLE_CLIENT_ID       — OAuth 2.0 client ID
  GOOGLE_CLIENT_SECRET   — OAuth 2.0 client secret
  APP_URL                — Public base URL of the deployed app (no trailing slash)
  GOOGLE_ALLOWED_DOMAIN  — (optional) restrict sign-in to one Google Workspace domain
  GOOGLE_ALLOWED_EMAILS  — (optional) comma-separated list of allowed email addresses

Access is granted when either GOOGLE_ALLOWED_DOMAIN or GOOGLE_ALLOWED_EMAILS matches.
If neither is set, any Google account can sign in.

If GOOGLE_CLIENT_ID is not set the module is a no-op and all users have open access.
"""

import os
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Optional

import streamlit as st

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

def _db_path() -> Path:
    return Path(os.environ.get("DB_PATH", "data/db.sqlite3"))


def _init_auth_tables() -> None:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS oauth_states (
            state         TEXT    PRIMARY KEY,
            created_at    INTEGER NOT NULL,
            code_verifier TEXT
        )
    """)
    # Migrate existing table if code_verifier column is missing
    cols = {row[1] for row in conn.execute("PRAGMA table_info(oauth_states)")}
    if "code_verifier" not in cols:
        conn.execute("ALTER TABLE oauth_states ADD COLUMN code_verifier TEXT")
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


def _store_state(state: str, code_verifier: str) -> None:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        "INSERT OR REPLACE INTO oauth_states (state, created_at, code_verifier) VALUES (?, ?, ?)",
        (state, int(time.time()), code_verifier),
    )
    conn.execute(
        "DELETE FROM oauth_states WHERE created_at < ?",
        (int(time.time()) - _STATE_TTL,),
    )
    conn.commit()
    conn.close()


def _consume_state(state: str) -> Optional[str]:
    """Return the code_verifier and delete the state if valid, else return None."""
    conn = sqlite3.connect(str(_db_path()))
    row = conn.execute(
        "SELECT code_verifier FROM oauth_states WHERE state = ? AND created_at > ?",
        (state, int(time.time()) - _STATE_TTL),
    ).fetchone()
    if row:
        conn.execute("DELETE FROM oauth_states WHERE state = ?", (state,))
        conn.commit()
    conn.close()
    return row[0] if row else None


def _create_session(email: str, name: str, picture: str) -> str:
    token = secrets.token_urlsafe(32)
    conn = sqlite3.connect(str(_db_path()))
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
    conn = sqlite3.connect(str(_db_path()))
    row = conn.execute(
        "SELECT email, name, picture FROM auth_sessions WHERE token = ? AND created_at > ?",
        (token, int(time.time()) - _SESSION_TTL),
    ).fetchone()
    conn.close()
    if row:
        return {"email": row[0], "name": row[1], "picture": row[2]}
    return None


def _delete_session(token: str) -> None:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------

def _build_flow(redirect_uri: str):
    from google_auth_oauthlib.flow import Flow
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

        # Clear params immediately so CookieManager-triggered reruns don't
        # re-enter this branch and fail on the already-consumed state.
        st.query_params.clear()

        code_verifier = _consume_state(state)
        if code_verifier is None:
            st.error("Authentication state is invalid or expired. Please try signing in again.")
            _render_login_page()
            return

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token
            flow = _build_flow(_redirect_uri())
            flow.fetch_token(code=code, code_verifier=code_verifier)
            credentials = flow.credentials

            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                os.environ["GOOGLE_CLIENT_ID"],
            )

            email: str = id_info.get("email", "")
            allowed_domain = os.environ.get("GOOGLE_ALLOWED_DOMAIN", "").strip()
            allowed_emails = {
                e.strip().lower()
                for e in os.environ.get("GOOGLE_ALLOWED_EMAILS", "").split(",")
                if e.strip()
            }

            domain_ok = allowed_domain and email.lower().endswith(f"@{allowed_domain.lower()}")
            email_ok = email.lower() in allowed_emails

            if (allowed_domain or allowed_emails) and not (domain_ok or email_ok):
                parts = []
                if allowed_domain:
                    parts.append(f"**@{allowed_domain}** accounts")
                if allowed_emails:
                    parts.append("specific allowed emails")
                st.error(
                    f"Access is restricted to {' or '.join(parts)}. "
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
    import base64
    import hashlib

    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()
    _store_state(state, code_verifier)

    redirect = _redirect_uri()
    flow = _build_flow(redirect)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        state=state,
        prompt="select_account",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    print(f"[AUTH DEBUG] client_id={os.environ.get('GOOGLE_CLIENT_ID', '')[:20]}... redirect_uri={redirect}", flush=True)
    print(f"[AUTH DEBUG] auth_url={auth_url}", flush=True)

    allowed_domain = os.environ.get("GOOGLE_ALLOWED_DOMAIN", "").strip()
    allowed_emails = {
        e.strip().lower()
        for e in os.environ.get("GOOGLE_ALLOWED_EMAILS", "").split(",")
        if e.strip()
    }
    if allowed_domain:
        domain_note = f"Sign in with your **@{allowed_domain}** Google account."
    elif allowed_emails:
        domain_note = "Sign in with an authorized Google account."
    else:
        domain_note = "Sign in with your Google account."

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
