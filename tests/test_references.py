import pytest

from src import references


def test_save_reference_rejects_path_traversal_names(tmp_references_dir):
    with pytest.raises(ValueError, match="must contain letters or numbers"):
        references.save_reference("../..", b"image-bytes", "png")


def test_save_reference_normalizes_name_and_extension(tmp_references_dir):
    saved = references.save_reference("Team Logo", b"image-bytes", "PNG")

    assert saved.name == "team_logo.png"
    assert saved.read_bytes() == b"image-bytes"


def test_resolve_references_matches_normalized_name(tmp_references_dir):
    (tmp_references_dir / "Team_Logo.PNG").write_bytes(b"image-bytes")

    found, missing = references.resolve_references(["team logo"])

    assert found == [b"image-bytes"]
    assert missing == []
