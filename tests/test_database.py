"""Tests for src/database.py — SQLite persistence layer."""

import json
import time

from src import database as db


def test_init_db_creates_table(tmp_db_path):
    db.init_db()

    conn = db.get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='generations'"
    ).fetchone()
    conn.close()
    assert tables is not None


def test_save_and_get_generation(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(
        base_prompt="A banana",
        final_prompt="A ripe banana on a table",
        provider="google-gemini",
        output_path="/tmp/banana.png",
        model="imagen-4.0",
    )

    row = db.get_generation(gen_id)
    assert row is not None
    assert row["base_prompt"] == "A banana"
    assert row["final_prompt"] == "A ripe banana on a table"
    assert row["provider"] == "google-gemini"
    assert row["output_path"] == "/tmp/banana.png"
    assert row["model"] == "imagen-4.0"


def test_save_generation_with_short_description(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(
        base_prompt="A banana",
        final_prompt="A ripe banana on a table",
        provider="google-gemini",
        output_path="/tmp/banana.png",
        short_description="Ripe banana sitting on wooden table",
    )

    row = db.get_generation(gen_id)
    assert row["short_description"] == "Ripe banana sitting on wooden table"


def test_save_generation_stores_settings_as_json(tmp_db_path):
    db.init_db()

    settings = {"aspect_ratio": "16:9", "num_images": 1}
    gen_id = db.save_generation(
        base_prompt="prompt",
        final_prompt="final",
        provider="openai",
        output_path="/tmp/img.png",
        settings=settings,
    )

    row = db.get_generation(gen_id)
    assert json.loads(row["settings"]) == settings


def test_save_generation_stores_empty_dict_when_no_settings(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(
        base_prompt="prompt",
        final_prompt="final",
        provider="openai",
        output_path="/tmp/img.png",
    )

    row = db.get_generation(gen_id)
    assert json.loads(row["settings"]) == {}


def test_get_generations_returns_newest_first(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="first", final_prompt="first", provider="p", output_path="/1")
    time.sleep(0.01)
    db.save_generation(base_prompt="second", final_prompt="second", provider="p", output_path="/2")

    rows = db.get_generations()
    assert rows[0]["base_prompt"] == "second"
    assert rows[1]["base_prompt"] == "first"


def test_get_generations_filters_by_project(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="a", final_prompt="a", provider="p", output_path="/1", project_name="alpha")
    db.save_generation(base_prompt="b", final_prompt="b", provider="p", output_path="/2", project_name="beta")

    rows = db.get_generations(project_name="alpha")
    assert len(rows) == 1
    assert rows[0]["project_name"] == "alpha"


def test_get_generations_filters_by_search(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="banana split", final_prompt="f", provider="p", output_path="/1")
    db.save_generation(base_prompt="apple pie", final_prompt="f", provider="p", output_path="/2")

    rows = db.get_generations(search="banana")
    assert len(rows) == 1
    assert "banana" in rows[0]["base_prompt"]


def test_get_generation_returns_none_for_missing_id(tmp_db_path):
    db.init_db()

    assert db.get_generation(9999) is None


def test_delete_generation(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(base_prompt="x", final_prompt="x", provider="p", output_path="/1")
    db.delete_generation(gen_id)

    assert db.get_generation(gen_id) is None


def test_update_generation_metadata(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(base_prompt="a", final_prompt="a", provider="p", output_path="/1")
    db.update_generation_metadata(gen_id, title="My Title", project_name="Proj", tags="foo,bar")

    row = db.get_generation(gen_id)
    assert row["title"] == "My Title"
    assert row["project_name"] == "Proj"
    assert row["tags"] == "foo,bar"


def test_update_generation_metadata_clears_fields(tmp_db_path):
    db.init_db()

    gen_id = db.save_generation(
        base_prompt="a", final_prompt="a", provider="p", output_path="/1",
        title="Old", project_name="OldProj", tags="old",
    )
    db.update_generation_metadata(gen_id, title=None, project_name=None, tags=None)

    row = db.get_generation(gen_id)
    assert row["title"] is None
    assert row["project_name"] is None
    assert row["tags"] is None


def test_get_generations_sort_oldest_first(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="first", final_prompt="first", provider="p", output_path="/1")
    time.sleep(0.01)
    db.save_generation(base_prompt="second", final_prompt="second", provider="p", output_path="/2")

    rows = db.get_generations(sort_by="oldest")
    assert rows[0]["base_prompt"] == "first"
    assert rows[1]["base_prompt"] == "second"


def test_get_generations_sort_by_title(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="b", final_prompt="b", provider="p", output_path="/2", title="Zebra")
    db.save_generation(base_prompt="a", final_prompt="a", provider="p", output_path="/1", title="Apple")

    rows = db.get_generations(sort_by="title")
    assert rows[0]["title"] == "Apple"
    assert rows[1]["title"] == "Zebra"


def test_get_generations_sort_by_project(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="b", final_prompt="b", provider="p", output_path="/2", project_name="Zoo")
    db.save_generation(base_prompt="a", final_prompt="a", provider="p", output_path="/1", project_name="Alpha")

    rows = db.get_generations(sort_by="project")
    assert rows[0]["project_name"] == "Alpha"
    assert rows[1]["project_name"] == "Zoo"


def test_get_projects_returns_distinct_names(tmp_db_path):
    db.init_db()

    db.save_generation(base_prompt="a", final_prompt="a", provider="p", output_path="/1", project_name="alpha")
    db.save_generation(base_prompt="b", final_prompt="b", provider="p", output_path="/2", project_name="alpha")
    db.save_generation(base_prompt="c", final_prompt="c", provider="p", output_path="/3", project_name="beta")

    projects = db.get_projects()
    assert projects == ["alpha", "beta"]
