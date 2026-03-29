"""YAML-backed style presets."""

from __future__ import annotations

import os
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise ImportError("PyYAML is required. Install with: pip install pyyaml") from exc


def _presets_path() -> Path:
    return Path(os.environ.get("PRESETS_PATH", "data/presets.yaml"))


def get_presets() -> list[dict]:
    path = _presets_path()
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("presets", [])


def _write_presets(path: Path, presets: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {"presets": presets},
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def save_preset(name: str, style_prompt: str, description: str = "") -> None:
    path = _presets_path()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    presets = data.get("presets", [])
    if any(p["name"] == name for p in presets):
        raise ValueError(f"A preset named '{name}' already exists.")
    presets.append({"name": name, "description": description or "", "style_prompt": style_prompt})
    _write_presets(path, presets)


def delete_preset(name: str) -> None:
    path = _presets_path()
    if not path.exists():
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    presets = [p for p in data.get("presets", []) if p["name"] != name]
    _write_presets(path, presets)
