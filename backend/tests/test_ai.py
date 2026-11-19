"""Phase 2 AI features (SW-12, SW-13, SW-14, SW-16) with the Claude API mocked."""

import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.ai import client as ai_client
from app.services.ai import insights as insights_module

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


class FakeClaude:
    """Stands in for anthropic.Anthropic: returns queued responses and records every request."""

    def __init__(self) -> None:
        self.queue: list[SimpleNamespace] = []
        self.calls: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **params):
        self.calls.append(params)
        assert self.queue, "unexpected AI call"
        return self.queue.pop(0)

    def reply_json(self, data: dict) -> None:
        self.queue.append(SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(data))]))

    def reply_text(self, text: str) -> None:
        self.queue.append(SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)]))

    def reply_tool(self, name: str, tool_input: dict, tool_id: str = "toolu_1") -> None:
        block = SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)
        self.queue.append(SimpleNamespace(stop_reason="tool_use", content=[block]))


@pytest.fixture
def fake_ai(monkeypatch) -> FakeClaude:
    fake = FakeClaude()
    monkeypatch.setattr(ai_client, "get_client", lambda: fake)
    insights_module._cache.clear()
    return fake


# --- status and switched-off behaviour -----------------------------------------------


def test_status_reports_ai_on_and_off(client, auth_headers, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", None)
    assert client.get("/api/ai/status", headers=auth_headers).json() == {"enabled": False, "model": None}
    monkeypatch.setattr(settings, "anthropic_api_key", "CHANGE_ME")
    assert client.get("/api/ai/status", headers=auth_headers).json()["enabled"] is False
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test")
    assert client.get("/api/ai/status", headers=auth_headers).json() == {"enabled": True, "model": settings.ai_model}


def test_ai_endpoints_return_503_when_ai_is_off(client, auth_headers, categories, create_tx):
    for i in range(5):
        create_tx(auth_headers, categories["Shopping"]["id"], description=f"Item {i}")
    assert client.get("/api/ai/insights?month=2026-11", headers=auth_headers).status_code == 503
    chat = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "hi"}]}, headers=auth_headers)
    assert chat.status_code == 503
    assert "ANTHROPIC_API_KEY" in chat.json()["detail"]
    files = {"file": ("r.png", PNG, "image/png")}
    assert client.post("/api/ai/receipt", files=files, headers=auth_headers).status_code == 503


def test_ai_endpoints_require_login(client):
    assert client.post("/api/ai/categorize", json={"description": "x", "transaction_type": "expense"}).status_code == 401
    assert client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401


# --- SW-12 categorisation ------------------------------------------------------------


def test_categorize_uses_history_without_calling_ai(client, auth_headers, categories, create_tx, fake_ai):
    create_tx(auth_headers, categories["Food & Dining"]["id"], description="Swiggy order")
    resp = client.post(
        "/api/ai/categorize", json={"description": "  swiggy   ORDER ", "transaction_type": "expense"}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "history"
    assert body["category"]["name"] == "Food & Dining"
    assert fake_ai.calls == []


def test_categorize_asks_ai_with_only_the_users_categories(client, auth_headers, other_headers, categories, fake_ai):
    bob_cat = client.post(
        "/api/categories", json={"name": "Bob Secret", "transaction_type": "expense"}, headers=other_headers
    ).json()
    fake_ai.reply_json({"category_id": categories["Shopping"]["id"], "confidence": "medium"})
    resp = client.post(
        "/api/ai/categorize",
        json={"description": "Amazon headphones", "transaction_type": "expense", "amount": "2499.00"},
        headers=auth_headers,
    )
    body = resp.json()
    assert body["source"] == "ai"
    assert body["confidence"] == "medium"
    assert body["category"]["name"] == "Shopping"

    prompt = fake_ai.calls[0]["messages"][0]["content"]
    assert "Shopping" in prompt
    assert "Salary" not in prompt  # income categories aren't offered for an expense
    assert "Bob Secret" not in prompt
    allowed = fake_ai.calls[0]["output_config"]["format"]["schema"]["properties"]["category_id"]["enum"]
    assert bob_cat["id"] not in allowed


def test_categorize_ignores_a_category_the_user_cannot_use(client, auth_headers, other_headers, fake_ai):
    bob_cat = client.post(
        "/api/categories", json={"name": "Bob Secret", "transaction_type": "expense"}, headers=other_headers
    ).json()
    fake_ai.reply_json({"category_id": bob_cat["id"], "confidence": "high"})
    body = client.post(
        "/api/ai/categorize", json={"description": "Mystery", "transaction_type": "expense"}, headers=auth_headers
    ).json()
    assert body == {"category": None, "source": "none", "confidence": None}


def test_categorize_returns_no_suggestion_when_ai_is_off(client, auth_headers):
    resp = client.post("/api/ai/categorize", json={"description": "Coffee", "transaction_type": "expense"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["category"] is None


# --- SW-13 insights ------------------------------------------------------------------


def test_insights_need_enough_transactions(client, auth_headers, categories, create_tx, fake_ai):
    create_tx(auth_headers, categories["Shopping"]["id"])
    body = client.get("/api/ai/insights?month=2026-11", headers=auth_headers).json()
    assert body["available"] is False
    assert body["insights"] == []
    assert fake_ai.calls == []


def test_insights_cite_figures_that_match_the_dashboard(client, auth_headers, categories, create_tx, fake_ai):
    for amount in ["100.00", "250.50", "75.25", "30.00", "44.25"]:
        create_tx(auth_headers, categories["Food & Dining"]["id"], amount=amount, transaction_date="2026-11-03")
    fake_ai.reply_json(
        {
            "insights": [
                {"title": "Food is your top spend", "body": "You spent INR 500.00.", "tone": "neutral",
                 "fact_ids": ["expense_total", "cat1_amount", "made_up_id"]},
                {"title": "Unbacked", "body": "No real facts.", "tone": "warning", "fact_ids": ["made_up_id"]},
            ]
        }
    )
    resp = client.get("/api/ai/insights?month=2026-11", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert len(body["insights"]) == 1  # the insight with no real facts is dropped
    facts = {f["id"]: f["value"] for f in body["insights"][0]["facts"]}
    assert set(facts) == {"expense_total", "cat1_amount"}

    dashboard = client.get("/api/dashboard?month=2026-11", headers=auth_headers).json()
    assert dashboard["totals"]["expense"] == "500.00"
    assert facts["expense_total"] == "INR 500.00"

    # Same data -> served from cache, no second AI call.
    client.get("/api/ai/insights?month=2026-11", headers=auth_headers)
    assert len(fake_ai.calls) == 1


def test_insights_ai_failure_returns_502(client, auth_headers, categories, create_tx, fake_ai):
    for _ in range(5):
        create_tx(auth_headers, categories["Shopping"]["id"])
    fake_ai.queue.append(SimpleNamespace(stop_reason="refusal", content=[]))
    resp = client.get("/api/ai/insights?month=2026-11", headers=auth_headers)
    assert resp.status_code == 502


# --- SW-14 chat ----------------------------------------------------------------------


def test_chat_answers_from_the_users_own_data(client, auth_headers, other_headers, categories, create_tx, fake_ai):
    food = categories["Food & Dining"]["id"]
    create_tx(auth_headers, food, amount="500.00", transaction_date="2026-10-12", description="Dinner")
    create_tx(other_headers, food, amount="999.00", transaction_date="2026-10-12", description="Bob dinner")

    fake_ai.reply_tool(
        "search_transactions",
        {"start_date": "2026-10-01", "end_date": "2026-10-31", "category": "food & dining", "transaction_type": "expense"},
    )
    fake_ai.reply_text("You spent INR 500.00 on Food & Dining in October 2026.")

    resp = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "How much did I spend on food last month?"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "500.00" in body["reply"]
    assert body["data_used"][0]["tool"] == "search_transactions"
    assert "category food & dining" in body["data_used"][0]["description"]

    tool_result = fake_ai.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is False
    data = json.loads(tool_result["content"])
    assert data["total_expense"] == "500.00"
    assert data["matching_count"] == 1
    assert "Bob" not in tool_result["content"]


def test_chat_reports_bad_tool_input_back_to_the_model(client, auth_headers, fake_ai):
    fake_ai.reply_tool("get_budgets", {"month": "October"})
    fake_ai.reply_text("I need a month like 2026-10.")
    resp = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "budgets?"}]}, headers=auth_headers)
    assert resp.status_code == 200
    tool_result = fake_ai.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True
    assert resp.json()["data_used"] == []


def test_chat_has_no_tools_that_change_data():
    from app.services.ai.chat import TOOLS

    names = {t["name"] for t in TOOLS}
    assert names == {"get_month_summary", "search_transactions", "get_budgets", "get_savings_goals", "get_monthly_trend"}


def test_chat_last_message_must_be_from_user(client, auth_headers, fake_ai):
    resp = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 502
    assert fake_ai.calls == []


# --- SW-16 receipts ------------------------------------------------------------------


def test_receipt_rejects_unsupported_and_large_files(client, auth_headers, fake_ai):
    bad = client.post("/api/ai/receipt", files={"file": ("x.txt", b"hello", "text/plain")}, headers=auth_headers)
    assert bad.status_code == 400
    big = client.post("/api/ai/receipt", files={"file": ("x.png", PNG + b"0" * (5 * 1024 * 1024), "image/png")}, headers=auth_headers)
    assert big.status_code == 400
    assert fake_ai.calls == []


def test_receipt_prefills_an_expense_with_decimal_amount(client, auth_headers, categories, fake_ai):
    fake_ai.reply_json(
        {"readable": True, "merchant": "Fresh Mart", "date": "2026-11-15", "total": "1,249.5",
         "currency": "INR", "category_id": categories["Groceries"]["id"] if "Groceries" in categories else "none"}
    )
    resp = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["readable"] is True
    assert body["merchant"] == "Fresh Mart"
    assert body["amount"] == "1249.50"
    assert body["transaction_date"] == "2026-11-15"
    assert body["message"] is None
    sent = fake_ai.calls[0]["messages"][0]["content"][0]
    assert sent["type"] == "image" and sent["source"]["media_type"] == "image/png"
    # Nothing was saved.
    assert client.get("/api/transactions", headers=auth_headers).json()["total"] == 0


def test_receipt_unreadable_returns_clear_message(client, auth_headers, fake_ai):
    fake_ai.reply_json({"readable": False, "merchant": "", "date": "", "total": "", "currency": "", "category_id": "none"})
    body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
    assert body["readable"] is False
    assert body["amount"] is None
    assert "Couldn't read" in body["message"]


def test_receipt_rejects_a_total_that_is_not_a_valid_amount(client, auth_headers, fake_ai):
    fake_ai.reply_json({"readable": True, "merchant": "Shop", "date": "", "total": "12.345", "currency": "", "category_id": "none"})
    body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
    assert body["readable"] is False


def test_receipt_warns_about_a_different_currency(client, auth_headers, fake_ai):
    fake_ai.reply_json({"readable": True, "merchant": "Cafe", "date": "", "total": "12.00", "currency": "usd", "category_id": "none"})
    body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
    assert body["readable"] is True
    assert body["currency"] == "USD"
    assert "USD" in body["message"]
    assert Decimal(body["amount"]) == Decimal("12.00")
