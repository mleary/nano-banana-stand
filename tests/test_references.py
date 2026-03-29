import os
import tempfile
import unittest
from pathlib import Path

from src import references


class ReferenceStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_dir = os.environ.get("REFERENCES_DIR")
        os.environ["REFERENCES_DIR"] = self.temp_dir.name

    def tearDown(self):
        if self.previous_dir is None:
            os.environ.pop("REFERENCES_DIR", None)
        else:
            os.environ["REFERENCES_DIR"] = self.previous_dir
        self.temp_dir.cleanup()

    def test_save_reference_rejects_path_traversal_names(self):
        with self.assertRaisesRegex(ValueError, "must contain letters or numbers"):
            references.save_reference("../..", b"image-bytes", "png")

    def test_save_reference_normalizes_name_and_extension(self):
        saved = references.save_reference("Team Logo", b"image-bytes", "PNG")

        self.assertEqual(saved.name, "team_logo.png")
        self.assertEqual(saved.read_bytes(), b"image-bytes")

    def test_resolve_references_matches_normalized_name(self):
        Path(self.temp_dir.name, "Team_Logo.PNG").write_bytes(b"image-bytes")

        found, missing = references.resolve_references(["team logo"])

        self.assertEqual(found, [b"image-bytes"])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
