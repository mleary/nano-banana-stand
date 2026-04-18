from unittest.mock import patch

import pytest

from src.generator import GenerationResult
from src.services.generation_service import (
    GenerationRequest,
    generate_and_store,
    validate_generation_request,
)



def test_validate_generation_request_rejects_reference_tokens_for_openai():
    request = GenerationRequest(
        base_prompt="A launch image",
        provider="openai",
        api_key="test-key",
        reference_tokens=["logo"],
    )

    with pytest.raises(ValueError, match="require Google Gemini"):
        validate_generation_request(request)


@patch("src.services.generation_service.load_image_bytes", return_value=b"image-bytes")
@patch("src.services.generation_service.db.save_generation", return_value=42)
@patch(
    "src.services.generation_service.generate_image",
    return_value=GenerationResult(
        output_path="/tmp/generated.png",
        provider="google-gemini",
        model="imagen-4.0-generate-001",
        final_prompt="Better prompt",
        settings={"aspect_ratio": "16:9"},
    ),
)
@patch(
    "src.services.generation_service.resolve_references",
    return_value=([b"inline-ref"], ["missing_logo"]),
)
@patch(
    "src.services.generation_service.generate_short_description",
    return_value="Launch image clean editorial style",
)
def test_generate_and_store_persists_normalized_metadata(
    mock_desc,
    mock_resolve,
    mock_generate,
    mock_save,
    mock_load,
):
    request = GenerationRequest(
        base_prompt="A launch image",
        style_prompt="Clean editorial",
        provider="google-gemini",
        model="imagen-4.0-generate-001",
        api_key="test-key",
        settings={"aspect_ratio": "16:9"},
        reference_tokens=["logo"],
        title="  Hero  ",
        project_name="  Q2 launch  ",
        tags="  marketing,hero  ",
    )

    outcome = generate_and_store(request)

    assert outcome.generation_id == 42
    assert outcome.image_bytes == b"image-bytes"
    assert outcome.missing_references == ["missing_logo"]
    assert outcome.short_description == "Launch image clean editorial style"
    mock_resolve.assert_called_once_with(["logo"])
    mock_generate.assert_called_once()
    mock_desc.assert_called_once_with("A launch image", "test-key")
    mock_save.assert_called_once_with(
        base_prompt="A launch image",
        final_prompt="Better prompt",
        provider="google-gemini",
        output_path="/tmp/generated.png",
        title="Hero",
        project_name="Q2 launch",
        tags="marketing,hero",
        style_prompt="Clean editorial",
        model="imagen-4.0-generate-001",
        settings={"aspect_ratio": "16:9"},
        short_description="Launch image clean editorial style",
    )
    mock_load.assert_called_once_with("/tmp/generated.png")
