"""Shared pytest fixtures for the test suite."""

import os
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_db_path(tmp_path, monkeypatch):
    """Point DB_PATH to a temporary file and return the path."""
    db_file = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DB_PATH", str(db_file))
    return db_file


@pytest.fixture()
def tmp_storage_dir(tmp_path, monkeypatch):
    """Point STORAGE_DIR to a temporary directory and return the path."""
    storage = tmp_path / "images"
    monkeypatch.setenv("STORAGE_DIR", str(storage))
    return storage


@pytest.fixture()
def tmp_presets_path(tmp_path, monkeypatch):
    """Point PRESETS_PATH to a temporary file and return the path."""
    presets_file = tmp_path / "presets.yaml"
    monkeypatch.setenv("PRESETS_PATH", str(presets_file))
    return presets_file


@pytest.fixture()
def tmp_references_dir(tmp_path, monkeypatch):
    """Point REFERENCES_DIR to a temporary directory and return the path."""
    refs = tmp_path / "references"
    refs.mkdir()
    monkeypatch.setenv("REFERENCES_DIR", str(refs))
    return refs
