"""Request/response translation for the Ollama and Claude providers (no network)."""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.services.ai.providers.anthropic import AnthropicProvider
from app.services.ai.providers.base import AIRequestError, AIUnavailableError, Image, ToolCall, ToolResult, ToolSpec
from app.services.ai.providers.ollama import OllamaProvider

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
TOOL = ToolSpec("get_budgets", "Budgets for a month", {"type": "object", "properties": {"month": {"type": "string"}}})


def _ollama(handler) -> tuple[OllamaProvider, list[dict]]:
    seen: list[dict] = []

    def wrapped(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        seen.append({"path": request.url.path, "body": body})
        return handler(request, body)

    return OllamaProvider("http://ollama.test", "text-model", "vision-model", 10, transport=httpx.MockTransport(wrapped)), seen


# --- Ollama --------------------------------------------------------------------------


def test_ollama_structured_sends_schema_and_parses_json():
    provider, seen = _ollama(lambda r, b: httpx.Response(200, json={"message": {"content": '{"a": "x"}'}, "done_reason": "stop"}))
    assert provider.structured(system="sys", prompt="hello", schema=SCHEMA) == {"a": "x"}
    body = seen[0]["body"]
    assert seen[0]["path"] == "/api/chat"
    assert body["model"] == "text-model"
    assert body["format"] == SCHEMA
    assert body["stream"] is False
    assert body["options"]["temperature"] == 0
    assert body["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "hello"}]


def test_ollama_uses_vision_model_for_images_and_rejects_pdfs():
    provider, seen = _ollama(lambda r, b: httpx.Response(200, json={"message": {"content": '{"a": "x"}'}}))
    provider.structured(system="s", prompt="p", schema=SCHEMA, images=[Image("image/png", b"\x89PNG")])
    assert seen[0]["body"]["model"] == "vision-model"
    assert seen[0]["body"]["messages"][1]["images"] == ["iVBORw=="]
    with pytest.raises(AIRequestError):
        provider.structured(system="s", prompt="p", schema=SCHEMA, images=[Image("application/pdf", b"%PDF")])


def test_ollama_errors_are_clear():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    down = OllamaProvider("http://ollama.test", "m", "v", 10, transport=httpx.MockTransport(refuse))
    with pytest.raises(AIUnavailableError, match="isn't running"):
        down.structured(system="s", prompt="p", schema=SCHEMA)

    missing, _ = _ollama(lambda r, b: httpx.Response(404, json={"error": "model not found"}))
    with pytest.raises(AIUnavailableError, match="ollama pull text-model"):
        missing.structured(system="s", prompt="p", schema=SCHEMA)

    cut, _ = _ollama(lambda r, b: httpx.Response(200, json={"message": {"content": '{"a":'}, "done_reason": "length"}))
    with pytest.raises(AIRequestError, match="cut off"):
        cut.structured(system="s", prompt="p", schema=SCHEMA)


def test_ollama_status_checks_models_are_downloaded():
    tags = {"models": [{"name": "text-model"}, {"name": "vision-model"}]}
    ready, _ = _ollama(lambda r, b: httpx.Response(200, json=tags))
    assert ready.status().ready is True

    partial, _ = _ollama(lambda r, b: httpx.Response(200, json={"models": [{"name": "text-model"}]}))
    st = partial.status()
    assert st.ready is True and "ollama pull vision-model" in st.message

    none, _ = _ollama(lambda r, b: httpx.Response(200, json={"models": []}))
    assert none.status().ready is False


def test_ollama_chat_tool_round_trip():
    replies = [
        {"message": {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "get_budgets", "arguments": {"month": "2026-11"}}}]}},
        {"message": {"role": "assistant", "content": "All on track."}, "done_reason": "stop"},
    ]
    provider, seen = _ollama(lambda r, b: httpx.Response(200, json=replies.pop(0)))
    convo = provider.chat_start("system prompt", [{"role": "user", "content": "budgets?"}])
    step = provider.chat_step(convo, [TOOL])
    assert step.tool_calls[0].name == "get_budgets"
    assert step.tool_calls[0].arguments == {"month": "2026-11"}
    assert seen[0]["body"]["tools"][0]["function"]["name"] == "get_budgets"

    provider.chat_add_tool_results(convo, [ToolResult(step.tool_calls[0], '{"budgets": []}')])
    assert convo[-1] == {"role": "tool", "tool_name": "get_budgets", "content": '{"budgets": []}'}
    final = provider.chat_step(convo, [TOOL])
    assert final.text == "All on track." and final.tool_calls == []
    assert seen[1]["body"]["messages"][0] == {"role": "system", "content": "system prompt"}


# --- Claude (optional provider) ------------------------------------------------------


class FakeAnthropic:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **params):
        self.calls.append(params)
        return self.responses.pop(0)


def _text(text, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])


def test_anthropic_structured_and_fallbacks():
    fake = FakeAnthropic([_text('{"a": "x"}')])
    provider = AnthropicProvider(None, "claude-opus-5-5", client=fake)
    result = provider.structured(system="s", prompt="p", schema=SCHEMA, images=[Image("application/pdf", b"%PDF")])
    assert result == {"a": "x"}
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert call["output_config"]["format"]["schema"] == SCHEMA
    assert call["messages"][0]["content"][0]["type"] == "document"


def test_anthropic_refusal_and_missing_key():
    provider = AnthropicProvider(None, "m", client=FakeAnthropic([SimpleNamespace(stop_reason="refusal", content=[])]))
    with pytest.raises(AIRequestError):
        provider.structured(system="s", prompt="p", schema=SCHEMA)
    assert AnthropicProvider(None, "m").status().ready is False
    with pytest.raises(AIUnavailableError):
        AnthropicProvider(None, "m").structured(system="s", prompt="p", schema=SCHEMA)


def test_anthropic_chat_tool_round_trip():
    tool_use = SimpleNamespace(type="tool_use", id="toolu_1", name="get_budgets", input={"month": "2026-11"})
    fake = FakeAnthropic([SimpleNamespace(stop_reason="tool_use", content=[tool_use]), _text("Done.")])
    provider = AnthropicProvider(None, "m", client=fake)
    convo = provider.chat_start("sys", [{"role": "user", "content": "hi"}])
    step = provider.chat_step(convo, [TOOL])
    assert step.tool_calls == [ToolCall("toolu_1", "get_budgets", {"month": "2026-11"})]
    assert fake.calls[0]["system"] == "sys"
    assert fake.calls[0]["tools"][0]["input_schema"] == TOOL.parameters
    provider.chat_add_tool_results(convo, [ToolResult(step.tool_calls[0], "{}")])
    assert provider.chat_step(convo, [TOOL]).text == "Done."
    assert fake.calls[1]["messages"][-1]["content"][0]["tool_use_id"] == "toolu_1"
