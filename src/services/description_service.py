"""AI short-description generation for image records."""

from __future__ import annotations

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None
    genai_types = None

DESCRIPTION_MODEL = "gemini-2.0-flash"


def generate_short_description(prompt: str, api_key: str) -> str | None:
    """Generate a 5-8 word description summarizing an image prompt."""
    if not api_key or not prompt or genai is None:
        return None

    client = genai.Client(api_key=api_key)
    instruction = (
        "Write a 5-8 word description summarizing this image prompt. "
        "Use plain descriptive words only. No punctuation at the end. "
        f"Prompt: {prompt}"
    )
    try:
        response = client.models.generate_content(
            model=DESCRIPTION_MODEL,
            contents=instruction,
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=30,
            ),
        )
        text = response.text.strip().rstrip(".")
        return text if text else None
    except Exception:
        return None
