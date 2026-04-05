"""Tests for src/auth.py — database helpers and config checks.

Only tests pure logic; skips Streamlit UI rendering.
"""

import time

from src import auth


def test_is_configured_returns_false_without_env_vars(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    assert auth.is_configured() is False


def test_is_configured_returns_true_with_required_vars(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")

    assert auth.is_configured() is True


def test_store_and_consume_state(tmp_db_path):
    auth._init_auth_tables()

    auth._store_state("state123", "verifier456")
    result = auth._consume_state("state123")

    assert result == "verifier456"


def test_consume_state_returns_none_for_unknown(tmp_db_path):
    auth._init_auth_tables()

    assert auth._consume_state("nonexistent") is None


def test_consume_state_deletes_after_use(tmp_db_path):
    auth._init_auth_tables()

    auth._store_state("state_once", "verifier")
    auth._consume_state("state_once")

    assert auth._consume_state("state_once") is None


def test_create_and_lookup_session(tmp_db_path):
    auth._init_auth_tables()

    token = auth._create_session("user@example.com", "Test User", "https://example.com/pic.jpg")
    user = auth._lookup_session(token)

    assert user is not None
    assert user["email"] == "user@example.com"
    assert user["name"] == "Test User"
    assert user["picture"] == "https://example.com/pic.jpg"


def test_lookup_session_returns_none_for_expired(tmp_db_path, monkeypatch):
    auth._init_auth_tables()

    token = auth._create_session("user@example.com", "Test User", "")

    # Simulate time passing beyond the TTL
    far_future = int(time.time()) + auth._SESSION_TTL + 3600
    monkeypatch.setattr(time, "time", lambda: far_future)

    assert auth._lookup_session(token) is None


def test_delete_session(tmp_db_path):
    auth._init_auth_tables()

    token = auth._create_session("user@example.com", "Test User", "")
    auth._delete_session(token)

    assert auth._lookup_session(token) is None


def test_lookup_session_returns_none_for_empty_token(tmp_db_path):
    auth._init_auth_tables()

    assert auth._lookup_session("") is None
    assert auth._lookup_session(None) is None
