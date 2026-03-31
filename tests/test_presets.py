import os
import tempfile
import unittest
from pathlib import Path

from src import presets


class PresetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = os.environ.get("PRESETS_PATH")
        self.presets_path = Path(self.temp_dir.name) / "nested" / "presets.yaml"
        os.environ["PRESETS_PATH"] = str(self.presets_path)

    def tearDown(self):
        if self.previous_path is None:
            os.environ.pop("PRESETS_PATH", None)
        else:
            os.environ["PRESETS_PATH"] = self.previous_path
        self.temp_dir.cleanup()

    def test_save_preset_creates_parent_directory(self):
        presets.save_preset("Clean", "Minimal product shot")

        self.assertTrue(self.presets_path.exists())
        self.assertIn(
            {"name": "Clean", "description": "", "style_prompt": "Minimal product shot"},
            presets.get_presets(),
        )

    def test_update_preset_changes_style_and_description(self):
        presets.save_preset("Clean", "Minimal product shot", description="Old desc")
        presets.update_preset("Clean", "New style prompt", description="New desc")

        updated = next(p for p in presets.get_presets() if p["name"] == "Clean")
        self.assertEqual(updated["style_prompt"], "New style prompt")
        self.assertEqual(updated["description"], "New desc")

    def test_update_preset_raises_for_missing_preset(self):
        presets.save_preset("Clean", "Minimal product shot")
        with self.assertRaises(ValueError):
            presets.update_preset("NonExistent", "style")


if __name__ == "__main__":
    unittest.main()
