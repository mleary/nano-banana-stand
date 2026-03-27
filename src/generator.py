"""Multi-provider image generation.

Providers:
  - google-gemini  : Google Gemini image generation via google-genai SDK
                     (uses chatlas ChatGoogle for prompt enhancement)
  - openai         : DALL-E 3 via chatlas ChatOpenAI
  - fal            : fal.ai Flux models
  - replicate      : Replicate Flux models

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
        "label": "Google Gemini (Imagen / Gemini Flash)",
        "default_model": "imagen-3.0-generate-002",
        "models": [
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
    "fal": {
        "label": "fal.ai (Flux)",
        "default_model": "fal-ai/flux/dev",
        "models": [
            "fal-ai/flux/dev",
            "fal-ai/flux/schnell",
            "fal-ai/flux-pro",
        ],
        "api_key_env": "FAL_KEY",
        "requires": ["fal-client"],
    },
    "replicate": {
        "label": "Replicate (Flux)",
        "default_model": "black-forest-labs/flux-dev",
        "models": [
            "black-forest-labs/flux-dev",
            "black-forest-labs/flux-schnell",
        ],
        "api_key_env": "REPLICATE_API_TOKEN",
        "requires": ["replicate"],
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
    safety_filter = settings.get("safety_filter_level", "BLOCK_SOME")

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


def _generate_fal(
    prompt: str,
    model: str,
    api_key: str,
    settings: dict,
) -> tuple[bytes, str]:
    """Generate image using fal.ai."""
    try:
        import fal_client
    except ImportError as exc:
        raise ImportError(
            "fal-client package is required for fal.ai provider. "
            "Install with: pip install fal-client"
        ) from exc

    os.environ["FAL_KEY"] = api_key
    image_size = settings.get("image_size", "square_hd")
    num_steps = settings.get("num_inference_steps", 28)
    seed = settings.get("seed")

    args: dict[str, Any] = dict(
        prompt=prompt,
        image_size=image_size,
        num_inference_steps=num_steps,
    )
    if seed:
        args["seed"] = seed

    result = fal_client.run(model, arguments=args)
    image_url = result["images"][0]["url"]
    return _fetch_url(image_url), "png"


def _generate_replicate(
    prompt: str,
    model: str,
    api_key: str,
    settings: dict,
) -> tuple[bytes, str]:
    """Generate image using Replicate."""
    try:
        import replicate
    except ImportError as exc:
        raise ImportError(
            "replicate package is required for Replicate provider. "
            "Install with: pip install replicate"
        ) from exc

    os.environ["REPLICATE_API_TOKEN"] = api_key
    width = settings.get("width", 1024)
    height = settings.get("height", 1024)
    steps = settings.get("num_inference_steps", 28)

    output = replicate.run(
        model,
        input=dict(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=steps,
        ),
    )
    image_url = output[0] if isinstance(output, list) else output
    return _fetch_url(str(image_url)), "png"


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
        image_bytes, ext = _generate_google_gemini(
            final_prompt, resolved_model, resolved_key, resolved_settings
        )
    elif provider == "openai":
        image_bytes, ext = _generate_openai(
            final_prompt, resolved_model, resolved_key, resolved_settings
        )
    elif provider == "fal":
        image_bytes, ext = _generate_fal(
            final_prompt, resolved_model, resolved_key, resolved_settings
        )
    elif provider == "replicate":
        image_bytes, ext = _generate_replicate(
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
