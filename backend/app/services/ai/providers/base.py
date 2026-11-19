"""Provider-neutral interface for the LLM behind SpendWise's AI features.

Features (categorisation, insights, chat, receipts, natural-language entry) only
talk to this interface, so the LLM can be swapped with the AI_PROVIDER setting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class AIUnavailableError(Exception):
    """The AI provider is switched off, not running, or not set up."""


class AIRequestError(Exception):
    """The AI call failed, was declined, or returned something unusable."""


@dataclass(frozen=True)
class Image:
    media_type: str  # image/jpeg, image/png, image/webp, image/gif or application/pdf
    data: bytes


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema of the arguments


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: Any  # usually a dict; validated by the tool itself


@dataclass
class ChatStep:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    truncated: bool = False


@dataclass
class ToolResult:
    call: ToolCall
    content: str
    is_error: bool = False


@dataclass(frozen=True)
class ProviderStatus:
    ready: bool
    model: str | None
    message: str | None = None


class Provider(Protocol):
    name: str
    supports_pdf: bool

    def status(self) -> ProviderStatus: ...

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
        """One request whose reply is a JSON object matching ``schema``."""
        ...

    def chat_start(self, system: str, history: list[dict[str, str]]) -> list[Any]:
        """Build a provider-specific conversation from plain {role, content} messages."""
        ...

    def chat_step(self, convo: list[Any], tools: list[ToolSpec]) -> ChatStep:
        """Run one model turn and append the assistant's reply to ``convo``."""
        ...

    def chat_add_tool_results(self, convo: list[Any], results: list[ToolResult]) -> None:
        """Append tool results so the next ``chat_step`` can use them."""
        ...
