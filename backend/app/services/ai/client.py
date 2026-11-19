"""Entry point for SpendWise's AI features: picks the LLM provider from settings.

AI_PROVIDER=ollama (default) runs free models locally with Ollama;
AI_PROVIDER=anthropic uses the paid Claude API; AI_PROVIDER=off disables AI.
Features call ``get_provider()`` / ``structured_call()`` and never talk to a
provider directly, so tests can swap in a fake.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.services.ai.providers.base import (
    AIRequestError,
    AIUnavailableError,
    Image,
    Provider,
    ProviderStatus,
)

__all__ = [
    "AIRequestError",
    "AIUnavailableError",
    "Image",
    "get_provider",
    "provider_status",
    "structured_call",
]


@lru_cache
def _build(provider: str, key: str | None, model: str, ollama: tuple[str, str, str, float]) -> Provider:
    if provider == "anthropic":
        from app.services.ai.providers.anthropic import AnthropicProvider

        return AnthropicProvider(key, model)
    from app.services.ai.providers.ollama import OllamaProvider

    url, text_model, vision_model, timeout = ollama
    return OllamaProvider(url, text_model, vision_model, timeout)


def get_provider() -> Provider | None:
    """The configured provider, or None when AI is switched off."""
    if settings.ai_provider == "off":
        return None
    key = settings.anthropic_api_key.strip() if settings.anthropic_key_set else None  # type: ignore[union-attr]
    return _build(
        settings.ai_provider,
        key,
        settings.ai_model,
        (settings.ollama_url, settings.ollama_model, settings.ollama_vision_model, settings.ollama_timeout_seconds),
    )


def require_provider() -> Provider:
    provider = get_provider()
    if provider is None:
        raise AIUnavailableError("AI features are switched off (AI_PROVIDER=off in backend/.env).")
    return provider


def provider_status() -> tuple[str, ProviderStatus]:
    provider = get_provider()
    if provider is None:
        return "off", ProviderStatus(False, None, "AI features are switched off (AI_PROVIDER=off in backend/.env).")
    return provider.name, provider.status()


def structured_call(
    *,
    system: str,
    prompt: str,
    schema: dict[str, Any],
    images: list[Image] | None = None,
    max_tokens: int = 4000,
    effort: str = "low",
) -> dict[str, Any]:
    """One request whose reply is a JSON object matching ``schema``."""
    return require_provider().structured(
        system=system, prompt=prompt, schema=schema, images=images, max_tokens=max_tokens, effort=effort
    )
