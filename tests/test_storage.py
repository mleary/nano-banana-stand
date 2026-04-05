"""Tests for src/storage.py — image file I/O."""

from unittest.mock import patch

from src import storage


def test_get_storage_dir_creates_directory(tmp_storage_dir):
    result = storage.get_storage_dir()

    assert result.exists()
    assert result.is_dir()


def test_save_image_bytes_writes_file(tmp_storage_dir):
    path = storage.save_image_bytes(b"fake-png-data")

    assert open(path, "rb").read() == b"fake-png-data"
    assert path.endswith(".png")


def test_save_image_bytes_custom_extension(tmp_storage_dir):
    path = storage.save_image_bytes(b"fake-jpg-data", extension="jpg")

    assert path.endswith(".jpg")
    assert open(path, "rb").read() == b"fake-jpg-data"


@patch("urllib.request.urlretrieve")
def test_save_image_from_url_downloads_and_saves(mock_urlretrieve, tmp_storage_dir):
    path = storage.save_image_from_url("https://example.com/image.png")

    assert path.endswith(".png")
    mock_urlretrieve.assert_called_once()
    call_args = mock_urlretrieve.call_args
    assert call_args[0][0] == "https://example.com/image.png"


def test_load_image_bytes_reads_file(tmp_storage_dir):
    path = storage.save_image_bytes(b"round-trip-data")

    loaded = storage.load_image_bytes(path)

    assert loaded == b"round-trip-data"


def test_load_image_bytes_returns_none_for_missing(tmp_storage_dir):
    assert storage.load_image_bytes("/nonexistent/path.png") is None
