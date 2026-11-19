"""Ollama provider: free LLMs running locally (https://ollama.com).

Uses Ollama's REST API (POST /api/chat). Structured replies use the ``format``
JSON-schema option, which constrains the output to the schema. Receipts use a
separate vision model. Financial data never leaves the machine.
"""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

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

NUM_CTX = 8192


def _not_running(url: str) -> AIUnavailableError:
    return AIUnavailableError(f"Ollama isn't running. Start the Ollama app (it listens on {url}) and try again.")


def _not_downloaded(model: str) -> AIUnavailableError:
    return AIUnavailableError(f"The AI model '{model}' isn't downloaded yet. Run: ollama pull {model}")


class OllamaProvider:
    name = "ollama"
    supports_pdf = False  # local models read images, not PDFs

    def __init__(self, url: str, model: str, vision_model: str, timeout: float, transport: httpx.BaseTransport | None = None):
        self.url = url.rstrip("/")
        self.model = model
        self.vision_model = vision_model
        self._client = httpx.Client(base_url=self.url, timeout=timeout, transport=transport)

    # -- helpers ------------------------------------------------------------------------

    def _post_chat(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = self._client.post("/api/chat", json={**body, "stream": False, "keep_alive": "15m"})
        except httpx.ConnectError as exc:
            raise _not_running(self.url) from exc
        except httpx.TimeoutException as exc:
            raise AIRequestError("The local AI model took too long to answer. Try again.") from exc
        except httpx.HTTPError as exc:
            raise AIRequestError("Couldn't talk to Ollama.") from exc
        if resp.status_code == 404:
            raise _not_downloaded(body["model"])
        if resp.status_code >= 400:
            detail = resp.text[:200]
            raise AIRequestError(f"Ollama returned an error: {detail}")
        try:
            return resp.json()
        except ValueError as exc:
            raise AIRequestError("Ollama returned an unreadable reply.") from exc

    @staticmethod
    def _options(max_tokens: int) -> dict[str, Any]:
        # Deterministic output suits extraction and categorisation.
        return {"temperature": 0, "num_predict": max_tokens, "num_ctx": NUM_CTX}

    # -- Provider interface -------------------------------------------------------------

    def status(self) -> ProviderStatus:
        try:
            resp = self._client.get("/api/tags", timeout=3.0)
            resp.raise_for_status()
            names = {m.get("name", "") for m in resp.json().get("models", [])}
        except (httpx.HTTPError, ValueError):
            return ProviderStatus(False, self.model, str(_not_running(self.url)))

        def present(model: str) -> bool:
            return model in names or (":" not in model and f"{model}:latest" in names)

        missing = [m for m in dict.fromkeys([self.model, self.vision_model]) if not present(m)]
        if self.model in missing:
            return ProviderStatus(False, self.model, str(_not_downloaded(self.model)))
        if missing:
            return ProviderStatus(True, self.model, f"Receipt scanning needs another model. Run: ollama pull {missing[0]}")
        return ProviderStatus(True, self.model, None)

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
        user: dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            if any(i.media_type == "application/pdf" for i in images):
                raise AIRequestError("The local AI model can't read PDFs. Upload a photo or screenshot instead.")
            user["images"] = [base64.standard_b64encode(i.data).decode("ascii") for i in images]
        data = self._post_chat(
            {
                "model": self.vision_model if images else self.model,
                "messages": [{"role": "system", "content": system}, user],
                "format": schema,
                "options": self._options(max_tokens),
            }
        )
        if data.get("done_reason") == "length":
            raise AIRequestError("The AI reply was cut off. Try again.")
        content = (data.get("message") or {}).get("content", "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AIRequestError("The AI returned an unreadable reply.") from exc
        if not isinstance(parsed, dict):
            raise AIRequestError("The AI returned an unexpected reply.")
        return parsed

    def chat_start(self, system: str, history: list[dict[str, str]]) -> list[Any]:
        return [{"role": "system", "content": system}, *[dict(m) for m in history]]

    def chat_step(self, convo: list[Any], tools: list[ToolSpec]) -> ChatStep:
        data = self._post_chat(
            {
                "model": self.model,
                "messages": convo,
                "tools": [
                    {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                    for t in tools
                ],
                "options": self._options(2000),
            }
        )
        message = data.get("message") or {}
        convo.append({k: v for k, v in message.items() if k in ("role", "content", "tool_calls")} | {"role": "assistant"})
        calls = []
        for i, tc in enumerate(message.get("tool_calls") or []):
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):  # some models return a JSON string
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    pass
            calls.append(ToolCall(id=tc.get("id") or f"call_{len(convo)}_{i}", name=fn.get("name", ""), arguments=args))
        return ChatStep(text=message.get("content") or "", tool_calls=calls, truncated=data.get("done_reason") == "length")

    def chat_add_tool_results(self, convo: list[Any], results: list[ToolResult]) -> None:
        for r in results:
            convo.append({"role": "tool", "tool_name": r.call.name, "content": r.content})
