"""Thin wrapper around the Anthropic SDK shared by every AI feature.

- Returns ``None`` from ``get_client()`` when no API key is configured, so callers
  can switch AI features off instead of crashing.
- Turns SDK errors, refusals and truncated replies into two exception types that
  the routes map to clear HTTP errors.
- Enables server-side refusal fallbacks on every request.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AIUnavailableError(Exception):
    """AI features are switched off (no ANTHROPIC_API_KEY)."""


class AIRequestError(Exception):
    """The AI call failed, was declined, or returned something unusable."""


@lru_cache
def _build_client(api_key: str) -> anthropic.Anthropic:
    # Short timeout: these calls sit behind interactive UI.
    return anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)


def get_client() -> anthropic.Anthropic | None:
    if not settings.ai_enabled:
        return None
    return _build_client(settings.anthropic_api_key.strip())  # type: ignore[union-attr]


def create_message(**params: Any):
    """Call the Messages API with the configured model and refusal fallbacks.

    Raises AIUnavailableError when AI is off and AIRequestError on any failure.
    """
    client = get_client()
    if client is None:
        raise AIUnavailableError("AI features are off. Add ANTHROPIC_API_KEY to backend/.env.")
    try:
        response = client.beta.messages.create(
            model=settings.ai_model,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            **params,
        )
    except anthropic.AuthenticationError as exc:
        raise AIRequestError("The AI service rejected the API key. Check ANTHROPIC_API_KEY.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise AIRequestError("The API key isn't allowed to use this AI model.") from exc
    except anthropic.RateLimitError as exc:
        raise AIRequestError("The AI service is busy right now. Try again in a minute.") from exc
    except anthropic.BadRequestError as exc:
        logger.warning("AI bad request: %s", exc)
        raise AIRequestError("The AI service couldn't process this request.") from exc
    except anthropic.APIStatusError as exc:
        logger.warning("AI status error %s: %s", exc.status_code, exc)
        raise AIRequestError("The AI service returned an error. Try again later.") from exc
    except anthropic.APIConnectionError as exc:  # includes timeouts
        raise AIRequestError("Couldn't reach the AI service. Check your internet connection.") from exc

    if response.stop_reason == "refusal":
        raise AIRequestError("The AI declined to answer this request.")
    return response


def response_text(response: Any) -> str:
    return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def structured_call(
    *,
    system: str,
    content: str | list[dict[str, Any]],
    schema: dict[str, Any],
    max_tokens: int = 4000,
    effort: str = "low",
) -> dict[str, Any]:
    """One request whose reply is JSON matching ``schema`` (structured outputs)."""
    response = create_message(
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": content}],
        output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
    )
    if response.stop_reason == "max_tokens":
        raise AIRequestError("The AI reply was cut off. Try again.")
    try:
        data = json.loads(response_text(response))
    except json.JSONDecodeError as exc:
        raise AIRequestError("The AI returned an unreadable reply.") from exc
    if not isinstance(data, dict):
        raise AIRequestError("The AI returned an unexpected reply.")
    return data
