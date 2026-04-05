from unittest.mock import patch

import pytest

from src.generator import REFERENCE_GENERATION_MODEL, generate_image


@patch("src.generator.save_image_bytes", return_value="/tmp/generated.png")
@patch("src.generator._generate_gemini_with_reference", return_value=(b"img", "png"))
def test_reference_guided_generation_reports_actual_model(mock_generate, mock_save):
    result = generate_image(
        base_prompt="A product shot",
        provider="google-gemini",
        api_key="test-key",
        reference_images=[b"ref"],
    )

    assert result.model == REFERENCE_GENERATION_MODEL
    assert result.output_path == "/tmp/generated.png"
    mock_generate.assert_called_once()
    mock_save.assert_called_once_with(b"img", "png")


def test_google_multi_image_requests_fail_fast():
    with pytest.raises(ValueError, match="single-image generations"):
        generate_image(
            base_prompt="A product shot",
            provider="google-gemini",
            api_key="test-key",
            settings={"num_images": 2},
        )
