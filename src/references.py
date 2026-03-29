"""Permanent reference image library stored in data/references/."""

from __future__ import annotations

import os
import re
from pathlib import Path

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
_REFERENCE_NAME_RE = re.compile(r"[^a-z0-9_-]+")

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


def _normalize_reference_name(name: str) -> str:
    normalized = name.strip().lower().replace(" ", "_")
    normalized = _REFERENCE_NAME_RE.sub("_", normalized).strip("_")
    if not normalized:
        raise ValueError("Reference names must contain letters or numbers.")
    return normalized


def _normalize_extension(extension: str) -> str:
    normalized = f".{extension.lstrip('.').lower()}"
    if normalized not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Use one of: {supported}.")
    return normalized


def _find_reference_path(name: str) -> Path | None:
    normalized_name = _normalize_reference_name(name)
    for path in list_references():
        if _normalize_reference_name(path.stem) == normalized_name:
            return path
    return None


def reference_exists(name: str) -> bool:
    try:
        return _find_reference_path(name) is not None
    except ValueError:
        return False


def save_reference(name: str, image_bytes: bytes, extension: str = "jpg") -> Path:
    """Save image bytes as a named reference. Raises if name already exists."""
    ref_dir = get_references_dir()
    stem = _normalize_reference_name(name)
    suffix = _normalize_extension(extension)
    existing = _find_reference_path(name)
    if existing:
        raise ValueError(f"A reference named '{existing.name}' already exists.")
    dest = ref_dir / f"{stem}{suffix}"
    dest.write_bytes(image_bytes)
    return dest


def delete_reference(name: str) -> None:
    existing = _find_reference_path(name)
    if existing:
        existing.unlink()


def parse_reference_tokens(prompt: str) -> list[str]:
    """Extract names from [bracket] tokens in a prompt string."""
    return re.findall(r'\[([^\[\]]+)\]', prompt)


def resolve_references(names: list[str]) -> tuple[list[bytes], list[str]]:
    """Resolve reference names to bytes from the reference library.

    Returns (found_bytes, missing_names).
    """
    found: list[bytes] = []
    missing: list[str] = []
    for name in names:
        try:
            match = _find_reference_path(name)
        except ValueError:
            match = None
        if match:
            found.append(match.read_bytes())
        else:
            missing.append(name)
    return found, missing
