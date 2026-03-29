"""Generation workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src import database as db
from src.generator import PROVIDERS, GenerationResult, generate_image
from src.references import resolve_references
from src.storage import load_image_bytes


@dataclass
class GenerationRequest:
    base_prompt: str
    provider: str
    api_key: str
    model: str | None = None
    style_prompt: str = ""
    settings: dict[str, Any] = field(default_factory=dict)
    reference_image: bytes | None = None
    reference_tokens: list[str] = field(default_factory=list)
    title: str = ""
    project_name: str = ""
    tags: str = ""


@dataclass
class GenerationOutcome:
    generation_id: int
    result: GenerationResult
    image_bytes: bytes | None
    missing_references: list[str] = field(default_factory=list)


def _normalize_optional_text(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def validate_generation_request(request: GenerationRequest) -> None:
    if not request.base_prompt.strip():
        raise ValueError("Please enter a prompt.")

    if not request.api_key:
        env_var = PROVIDERS[request.provider]["api_key_env"]
        raise ValueError(f"`{env_var}` environment variable is not set.")

    if request.provider != "google-gemini" and (
        request.reference_image is not None or request.reference_tokens
    ):
        raise ValueError("Reference images and inline `[name]` tokens require Google Gemini.")


def generate_and_store(request: GenerationRequest) -> GenerationOutcome:
    validate_generation_request(request)

    inline_reference_bytes, missing_references = resolve_references(request.reference_tokens)
    result = generate_image(
        base_prompt=request.base_prompt,
        style_prompt=request.style_prompt,
        provider=request.provider,
        model=request.model,
        api_key=request.api_key,
        settings=request.settings,
        reference_image=request.reference_image,
        reference_images=inline_reference_bytes or None,
    )

    generation_id = db.save_generation(
        base_prompt=request.base_prompt,
        final_prompt=result.final_prompt,
        provider=result.provider,
        output_path=result.output_path,
        title=_normalize_optional_text(request.title),
        project_name=_normalize_optional_text(request.project_name),
        tags=_normalize_optional_text(request.tags),
        style_prompt=_normalize_optional_text(request.style_prompt),
        model=result.model,
        settings=result.settings,
    )

    return GenerationOutcome(
        generation_id=generation_id,
        result=result,
        image_bytes=load_image_bytes(result.output_path),
        missing_references=missing_references,
    )
