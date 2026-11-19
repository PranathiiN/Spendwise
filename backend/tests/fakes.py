"""Test doubles for the LLM provider."""

from app.services.ai.providers.base import ChatStep, ProviderStatus


class FakeProvider:
    """Stands in for Ollama/Claude: returns queued replies and records every request."""

    name = "ollama"
    supports_pdf = True

    def __init__(self) -> None:
        self.replies: list = []
        self.steps: list[ChatStep] = []
        self.calls: list[dict] = []

    def status(self) -> ProviderStatus:
        return ProviderStatus(True, "fake-model", None)

    def reply(self, data) -> None:
        self.replies.append(data)

    def structured(self, **kwargs):
        self.calls.append({"kind": "structured", **kwargs})
        assert self.replies, "unexpected AI call"
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def chat_start(self, system, history):
        return [{"role": "system", "content": system}, *history]

    def chat_step(self, convo, tools):
        self.calls.append({"kind": "chat", "convo": list(convo), "tools": tools})
        assert self.steps, "unexpected AI call"
        return self.steps.pop(0)

    def chat_add_tool_results(self, convo, results):
        convo.append({"role": "tool", "results": results})
