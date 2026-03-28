"""Permanent reference image library stored in data/references/."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

REFERENCES_DIR = Path(__file__).parent.parent / "data" / "references"


def get_references_dir() -> Path:
    path = Path(os.environ.get("REFERENCES_DIR", str(REFERENCES_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_references() -> list[Path]:
    """Return sorted list of reference image paths."""
    ref_dir = get_references_dir()
    return sorted(
        p for p in ref_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def save_reference(name: str, image_bytes: bytes, extension: str = "jpg") -> Path:
    """Save image bytes as a named reference. Raises if name already exists."""
    ref_dir = get_references_dir()
    stem = name.strip().replace(" ", "_")
    dest = ref_dir / f"{stem}.{extension.lstrip('.')}"
    if dest.exists():
        raise ValueError(f"A reference named '{dest.name}' already exists.")
    dest.write_bytes(image_bytes)
    return dest


def delete_reference(name: str) -> None:
    ref_dir = get_references_dir()
    for ext in SUPPORTED_EXTENSIONS:
        candidate = ref_dir / f"{name}{ext}"
        if candidate.exists():
            candidate.unlink()
            return


def parse_reference_tokens(prompt: str) -> list[str]:
    """Extract names from [bracket] tokens in a prompt string."""
    return re.findall(r'\[([^\[\]]+)\]', prompt)


def resolve_references(names: list[str]) -> tuple[list[bytes], list[str]]:
    """Resolve reference names to bytes from the reference library.

    Returns (found_bytes, missing_names).
    """
    ref_dir = get_references_dir()
    found: list[bytes] = []
    missing: list[str] = []
    for name in names:
        stem = name.strip().replace(" ", "_")
        match = None
        for ext in SUPPORTED_EXTENSIONS:
            candidate = ref_dir / f"{stem}{ext}"
            if candidate.exists():
                match = candidate
                break
        if match:
            found.append(match.read_bytes())
        else:
            missing.append(name)
    return found, missing
