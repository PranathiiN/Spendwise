"""Claude API provider (optional, paid). Enable with AI_PROVIDER=anthropic and ANTHROPIC_API_KEY."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

import anthropic

from app.services.ai.providers.base import (
    AIRequestError,
    AIUnavailableError,
    ChatStep,
    Image,
    ProviderStatus,
    ToolCall,
    ToolResult,
    ToolSpec,
)

logger = logging.getLogger(__name__)

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicProvider:
    name = "anthropic"
    supports_pdf = True

    def __init__(self, api_key: str | None, model: str, client: Any = None):
        self.model = model
        if client is not None:
            self._client = client
        elif api_key:
            self._client = anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)
        else:
            self._client = None

    def status(self) -> ProviderStatus:
        if self._client is None:
            return ProviderStatus(False, self.model, "AI features are off. Add ANTHROPIC_API_KEY to backend/.env.")
        return ProviderStatus(True, self.model, None)

    def _create(self, **params: Any):
        if self._client is None:
            raise AIUnavailableError("AI features are off. Add ANTHROPIC_API_KEY to backend/.env.")
        try:
            response = self._client.beta.messages.create(
                model=self.model, betas=[FALLBACK_BETA], fallbacks="default", **params
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
        except anthropic.APIConnectionError as exc:
            raise AIRequestError("Couldn't reach the AI service. Check your internet connection.") from exc
        if response.stop_reason == "refusal":
            raise AIRequestError("The AI declined to answer this request.")
        return response

    @staticmethod
    def _text(response: Any) -> str:
        return "".join(b.text for b in response.content if getattr(b, "type", None) == "text")

    def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        images: list[Image] | None = None,
        max_tokens: int = 4000,
        effort: str = "low",
    ) -> dict[str, Any]:
        content: str | list[dict[str, Any]] = prompt
        if images:
            blocks: list[dict[str, Any]] = []
            for img in images:
                kind = "document" if img.media_type == "application/pdf" else "image"
                data = base64.standard_b64encode(img.data).decode("ascii")
                blocks.append({"type": kind, "source": {"type": "base64", "media_type": img.media_type, "data": data}})
            content = [*blocks, {"type": "text", "text": prompt}]
        response = self._create(
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        if response.stop_reason == "max_tokens":
            raise AIRequestError("The AI reply was cut off. Try again.")
        try:
            data = json.loads(self._text(response))
        except json.JSONDecodeError as exc:
            raise AIRequestError("The AI returned an unreadable reply.") from exc
        if not isinstance(data, dict):
            raise AIRequestError("The AI returned an unexpected reply.")
        return data

    def chat_start(self, system: str, history: list[dict[str, str]]) -> list[Any]:
        # The system prompt travels separately; keep it as the first (sentinel) element.
        return [{"__system__": system}, *[dict(m) for m in history]]

    def chat_step(self, convo: list[Any], tools: list[ToolSpec]) -> ChatStep:
        system = convo[0]["__system__"]
        while True:
            response = self._create(
                max_tokens=16000,
                system=system,
                tools=[{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools],
                messages=convo[1:],
                output_config={"effort": "medium"},
            )
            convo.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "pause_turn":
                break
        calls = [
            ToolCall(id=b.id, name=b.name, arguments=b.input)
            for b in response.content
            if getattr(b, "type", None) == "tool_use"
        ]
        return ChatStep(text=self._text(response), tool_calls=calls, truncated=response.stop_reason == "max_tokens")

    def chat_add_tool_results(self, convo: list[Any], results: list[ToolResult]) -> None:
        convo.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": r.call.id, "content": r.content, "is_error": r.is_error}
                    for r in results
                ],
            }
        )
