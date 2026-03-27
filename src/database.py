"""SQLite persistence for generations and style presets."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "db.sqlite3"


def get_db_path() -> Path:
    import os
    return Path(os.environ.get("DB_PATH", str(DB_PATH)))


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            project_name TEXT,
            tags TEXT,
            base_prompt TEXT NOT NULL,
            style_prompt TEXT,
            final_prompt TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            settings TEXT,
            output_path TEXT,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def save_generation(
    base_prompt: str,
    final_prompt: str,
    provider: str,
    output_path: str,
    title: str = None,
    project_name: str = None,
    tags: str = None,
    style_prompt: str = None,
    model: str = None,
    settings: dict = None,
) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO generations
           (title, project_name, tags, base_prompt, style_prompt,
            final_prompt, provider, model, settings, output_path, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            title,
            project_name,
            tags,
            base_prompt,
            style_prompt,
            final_prompt,
            provider,
            model,
            json.dumps(settings or {}),
            output_path,
            datetime.utcnow().isoformat(),
        ),
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def get_generations(project_name: str = None, search: str = None) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM generations WHERE 1=1"
    params = []
    if project_name:
        query += " AND project_name = ?"
        params.append(project_name)
    if search:
        query += " AND (title LIKE ? OR base_prompt LIKE ? OR tags LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_generation(gen_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM generations WHERE id = ?", (gen_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_projects() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT project_name FROM generations WHERE project_name IS NOT NULL ORDER BY project_name"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


