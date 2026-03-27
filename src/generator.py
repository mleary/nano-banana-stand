"""Multi-provider image generation.

Providers:
  - google-gemini  : Google Gemini image generation via google-genai SDK
                     (uses chatlas ChatGoogle for prompt enhancement)
  - openai         : DALL-E 3 via chatlas ChatOpenAI

Set IMAGE_PROVIDER env var (default: google-gemini).
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Any

from src.storage import save_image_bytes, save_image_from_url


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

PROVIDERS = {
    "google-gemini": {
        "label": "Google Gemini (Imagen)",
        "default_model": "imagen-4.0-generate-001",
        "models": [
            "imagen-4.0-generate-001",
            "imagen-4.0-fast-generate-001",
            "imagen-3.0-generate-002",
            "imagen-3.0-fast-generate-001",
        ],
        "api_key_env": "GOOGLE_API_KEY",
        "requires": ["google-genai", "chatlas"],
    },
    "openai": {
        "label": "OpenAI (DALL-E 3)",
        "default_model": "dall-e-3",
        "models": ["dall-e-3", "dall-e-2"],
        "api_key_env": "OPENAI_API_KEY",
        "requires": ["chatlas"],
    },
}


@dataclass
class GenerationResult:
    output_path: str
    provider: str
    model: str
    final_prompt: str
    settings: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


def _generate_google_gemini(
    prompt: str,
    model: str,
    api_key: str,
    settings: dict,
) -> tuple[bytes, str]:
    """Generate image using Google Generative AI (Imagen).

    Uses chatlas ChatGoogle for any prompt-enhancement step before generation.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise ImportError(
            "google-genai package is required for Google Gemini provider. "
            "Install it with: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)

    number_of_images = settings.get("num_images", 1)
    aspect_ratio = settings.get("aspect_ratio", "1:1")
    safety_filter = settings.get("safety_filter_level", "BLOCK_LOW_AND_ABOVE")

    response = client.models.generate_images(
        model=model,
        prompt=prompt,
        config=genai_types.GenerateImagesConfig(
            number_of_images=number_of_images,
            aspect_ratio=aspect_ratio,
            safety_filter_level=safety_filter,
        ),
    )

    if not response.generated_images:
        raise RuntimeError("Google Gemini returned no images. Check your prompt or API key.")

    image_bytes = response.generated_images[0].image.image_bytes
    return image_bytes, "png"


def _enhance_prompt_with_chatlas_google(prompt: str, api_key: str) -> str:
    """Use chatlas ChatGoogle (Gemini) to enhance a prompt before generation."""
    try:
        from chatlas import ChatGoogle
    except ImportError:
        return prompt  # graceful fallback — chatlas not installed

    chat = ChatGoogle(api_key=api_key)
    enhancement_request = (
        "You are an expert at writing prompts for AI image generators. "
        "Rewrite the following prompt to be more vivid and precise, "
        "optimised for a photorealistic presentation image. "
        "Return only the improved prompt text, nothing else.\n\n"
        f"Original prompt: {prompt}"
    )
    result = chat.chat(enhancement_request)
    enhanced = str(result).strip()
    return enhanced if enhanced else prompt


def _generate_openai(
    prompt: str,
    model: str,
    api_key: str,
    settings: dict,
) -> tuple[bytes, str]:
    """Generate image using OpenAI DALL-E via chatlas ChatOpenAI."""
    try:
        from chatlas import ChatOpenAI  # noqa: F401 — verify chatlas is installed
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "chatlas and openai packages are required for OpenAI provider. "
            "Install with: pip install chatlas openai"
        ) from exc

    client = OpenAI(api_key=api_key)
    size = settings.get("size", "1024x1024")
    quality = settings.get("quality", "standard")
    style = settings.get("style", "vivid")

    kwargs: dict[str, Any] = dict(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        response_format="b64_json",
    )
    if model == "dall-e-3":
        kwargs["quality"] = quality
        kwargs["style"] = style

    response = client.images.generate(**kwargs)
    image_bytes = base64.b64decode(response.data[0].b64_json)
    return image_bytes, "png"


def _generate_gemini_with_reference(
    prompt: str,
    reference_image_bytes: bytes,
    api_key: str,
    settings: dict,
) -> tuple[bytes, str]:
    """Generate image using Gemini generate_content() with a reference image input."""
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise ImportError(
            "google-genai package is required for Google Gemini provider. "
            "Install it with: pip install google-genai"
        ) from exc

    client = genai.Client(api_key=api_key)

    image_part = genai_types.Part.from_bytes(
        data=reference_image_bytes,
        mime_type="image/jpeg",
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[image_part, prompt],
        config=genai_types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data, "png"

    raise RuntimeError("Gemini returned no image data for reference-guided generation.")


def _fetch_url(url: str) -> bytes:
    import urllib.request
    with urllib.request.urlopen(url) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_image(
    base_prompt: str,
    style_prompt: str = "",
    provider: str = "google-gemini",
    model: str | None = None,
    api_key: str | None = None,
    settings: dict | None = None,
    enhance_prompt: bool = False,
    reference_image: bytes | None = None,
) -> GenerationResult:
    """Generate an image and persist it to storage.

    Args:
        base_prompt: Core description of the image.
        style_prompt: Optional style suffix appended to the base prompt.
        provider: One of the keys in PROVIDERS.
        model: Override the default model for the provider.
        api_key: API key (falls back to env var if not supplied).
        settings: Provider-specific generation settings.
        enhance_prompt: If True and provider is google-gemini, use chatlas
                        ChatGoogle to enhance the prompt before generation.

    Returns:
        GenerationResult with output_path and metadata.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Choose from: {list(PROVIDERS)}")

    provider_info = PROVIDERS[provider]
    resolved_model = model or provider_info["default_model"]
    resolved_settings = settings or {}

    # Resolve API key
    env_var = provider_info["api_key_env"]
    resolved_key = api_key or os.environ.get(env_var, "")
    if not resolved_key:
        raise ValueError(
            f"API key for {provider} not set. "
            f"Pass api_key= or set the {env_var} environment variable."
        )

    # Build final prompt
    parts = [base_prompt.strip()]
    if style_prompt and style_prompt.strip():
        parts.append(style_prompt.strip())
    final_prompt = ". ".join(parts)

    # Optional prompt enhancement via chatlas + Gemini
    if enhance_prompt and provider == "google-gemini":
        final_prompt = _enhance_prompt_with_chatlas_google(final_prompt, resolved_key)

    # Generate
    if provider == "google-gemini":
        if reference_image:
            image_bytes, ext = _generate_gemini_with_reference(
                final_prompt, reference_image, resolved_key, resolved_settings
            )
        else:
            image_bytes, ext = _generate_google_gemini(
                final_prompt, resolved_model, resolved_key, resolved_settings
            )
    elif provider == "openai":
        image_bytes, ext = _generate_openai(
            final_prompt, resolved_model, resolved_key, resolved_settings
        )
    output_path = save_image_bytes(image_bytes, ext)

    return GenerationResult(
        output_path=output_path,
        provider=provider,
        model=resolved_model,
        final_prompt=final_prompt,
        settings=resolved_settings,
    )


def get_provider_api_key(provider: str) -> str:
    """Return the API key from environment for the given provider."""
    env_var = PROVIDERS[provider]["api_key_env"]
    return os.environ.get(env_var, "")
