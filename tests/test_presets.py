import pytest

from src import presets


def test_save_preset_creates_parent_directory(tmp_presets_path):
    presets.save_preset("Clean", "Minimal product shot")

    assert tmp_presets_path.exists()
    assert {"name": "Clean", "description": "", "style_prompt": "Minimal product shot"} in presets.get_presets()


def test_update_preset_changes_style_and_description(tmp_presets_path):
    presets.save_preset("Clean", "Minimal product shot", description="Old desc")
    presets.update_preset("Clean", "New style prompt", description="New desc")

    updated = next(p for p in presets.get_presets() if p["name"] == "Clean")
    assert updated["style_prompt"] == "New style prompt"
    assert updated["description"] == "New desc"


def test_update_preset_raises_for_missing_preset(tmp_presets_path):
    presets.save_preset("Clean", "Minimal product shot")
    with pytest.raises(ValueError):
        presets.update_preset("NonExistent", "style")
