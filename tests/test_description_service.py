"""Tests for src/services/description_service.py."""

from unittest.mock import MagicMock, patch

from src.services.description_service import generate_short_description


def test_returns_none_when_no_api_key():
    assert generate_short_description("a banana", "") is None


def test_returns_none_when_no_prompt():
    assert generate_short_description("", "key") is None


def test_returns_stripped_text_on_success():
    mock_response = MagicMock()
    mock_response.text = "  Yellow banana on wooden table  "
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    with patch("src.services.description_service.genai", mock_genai):
        result = generate_short_description("A banana", "test-key")

    assert result == "Yellow banana on wooden table"


def test_returns_none_on_api_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API error")
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    with patch("src.services.description_service.genai", mock_genai):
        result = generate_short_description("A banana", "test-key")

    assert result is None


def test_strips_trailing_period():
    mock_response = MagicMock()
    mock_response.text = "Yellow banana on wooden table."
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_genai = MagicMock()
    mock_genai.Client.return_value = mock_client

    with patch("src.services.description_service.genai", mock_genai):
        result = generate_short_description("A banana", "test-key")

    assert result == "Yellow banana on wooden table"
