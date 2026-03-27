"""Image storage utilities."""

import os
import uuid
from pathlib import Path


STORAGE_DIR = Path(__file__).parent.parent / "data" / "images"


def get_storage_dir() -> Path:
    path = Path(os.environ.get("STORAGE_DIR", str(STORAGE_DIR)))
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_image_bytes(image_bytes: bytes, extension: str = "png") -> str:
    """Save raw image bytes to storage. Returns the file path."""
    storage_dir = get_storage_dir()
    filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = storage_dir / filename
    file_path.write_bytes(image_bytes)
    return str(file_path)


def save_image_from_url(url: str, extension: str = "png") -> str:
    """Download image from URL and save to storage. Returns the file path."""
    import urllib.request
    storage_dir = get_storage_dir()
    filename = f"{uuid.uuid4().hex}.{extension}"
    file_path = storage_dir / filename
    urllib.request.urlretrieve(url, str(file_path))
    return str(file_path)


def load_image_bytes(file_path: str) -> bytes | None:
    """Load image bytes from storage path."""
    path = Path(file_path)
    if path.exists():
        return path.read_bytes()
    return None
