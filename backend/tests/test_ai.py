"""Phase 2 features: categories, insights and assistant (SpendWise's own models) and receipts (LLM faked)."""

from datetime import date
from decimal import Decimal

from app.services.ai import client as ai_client

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"\x00" * 64


def _ask(client, headers, question: str) -> dict:
    resp = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": question}]}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --- status --------------------------------------------------------------------------


def test_status_own_models_always_on_receipts_off_by_default(client, auth_headers):
    body = client.get("/api/ai/status", headers=auth_headers).json()
    assert body["enabled"] is True
    assert body["receipt_scanning"] is False
    assert body["provider"] == "off"
    assert "AI_PROVIDER=ollama" in body["message"]


def test_status_with_a_receipt_provider(client, auth_headers, fake_ai):
    body = client.get("/api/ai/status", headers=auth_headers).json()
    assert body == {"enabled": True, "receipt_scanning": True, "provider": "ollama", "model": "fake-model", "message": None}


def test_ai_endpoints_require_login(client):
    assert client.post("/api/ai/categorize", json={"description": "x", "transaction_type": "expense"}).status_code == 401
    assert client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    assert client.post("/api/ai/parse", json={"text": "coffee 120"}).status_code == 401
    assert client.get("/api/ai/insights").status_code == 401


# --- SW-12 categorisation (own model) ------------------------------------------------


def _suggest(client, headers, description, ttype="expense", **extra):
    resp = client.post("/api/ai/categorize", json={"description": description, "transaction_type": ttype, **extra}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_categorize_uses_exact_history_first(client, auth_headers, categories, create_tx):
    create_tx(auth_headers, categories["Travel"]["id"], description="Swiggy order")  # an unusual choice
    body = _suggest(client, auth_headers, "  swiggy   ORDER ")
    assert body["source"] == "history"
    assert body["category"]["name"] == "Travel"


def test_categorize_works_for_new_users_from_starter_examples(client, auth_headers):
    assert _suggest(client, auth_headers, "Zomato dinner")["category"]["name"] == "Food & Dining"
    assert _suggest(client, auth_headers, "Uber to office")["category"]["name"] == "Transportation"
    assert _suggest(client, auth_headers, "Netflix monthly")["category"]["name"] == "Subscriptions"
    assert _suggest(client, auth_headers, "salary credited", "income")["category"]["name"] == "Salary"
    body = _suggest(client, auth_headers, "Electricity bill November")
    assert body["category"]["name"] == "Utilities" and body["source"] == "model"


def test_categorize_tolerates_typos(client, auth_headers):
    assert _suggest(client, auth_headers, "swigy lunch")["category"]["name"] == "Food & Dining"


def test_categorize_learns_from_the_users_own_choices(client, auth_headers, categories, create_tx):
    gym = client.post("/api/categories", json={"name": "Fitness", "transaction_type": "expense"}, headers=auth_headers).json()
    for d in ["Cult fit membership", "Cult fit renewal", "Cultfit class pack"]:
        create_tx(auth_headers, gym["id"], description=d)
    body = _suggest(client, auth_headers, "cult fit quarterly")
    assert body["source"] == "model"
    assert body["category"]["name"] == "Fitness"


def test_categorize_retrains_after_corrections(client, auth_headers, categories, create_tx):
    assert _suggest(client, auth_headers, "Decathlon purchase")["category"]["name"] == "Shopping"
    for d in ["Decathlon cycle", "Decathlon football", "Decathlon tent"]:
        create_tx(auth_headers, categories["Entertainment"]["id"], description=d)
    assert _suggest(client, auth_headers, "Decathlon purchase")["category"]["name"] == "Entertainment"


def test_categorize_never_uses_another_users_category(client, auth_headers, other_headers, create_tx):
    bob = client.post("/api/categories", json={"name": "Bob Secret", "transaction_type": "expense"}, headers=other_headers).json()
    for _ in range(3):
        create_tx(other_headers, bob["id"], description="mystery widget")
    body = _suggest(client, auth_headers, "mystery widget")
    assert body["category"] is None or body["category"]["name"] != "Bob Secret"


def test_categorize_gives_no_suggestion_for_unknown_words(client, auth_headers):
    assert _suggest(client, auth_headers, "qwxz") == {"category": None, "source": "none", "confidence": None}


# --- SW-13 insights (own rules) ------------------------------------------------------


def test_insights_need_enough_transactions(client, auth_headers, categories, create_tx):
    create_tx(auth_headers, categories["Shopping"]["id"])
    body = client.get("/api/ai/insights?month=2026-11", headers=auth_headers).json()
    assert body["available"] is False
    assert body["insights"] == []


def test_insights_point_out_budgets_changes_and_unusual_spending(client, auth_headers, categories, create_tx):
    food, shop = categories["Food & Dining"]["id"], categories["Shopping"]["id"]
    for d in ["03", "10", "20"]:
        create_tx(auth_headers, food, amount="200.00", transaction_date=f"2026-10-{d}")
    create_tx(auth_headers, shop, amount="100.00", transaction_date="2026-10-05")
    for d in ["02", "04", "06", "08"]:
        create_tx(auth_headers, food, amount="250.00", transaction_date=f"2026-11-{d}")
    create_tx(auth_headers, shop, amount="1500.00", description="New phone case", transaction_date="2026-11-09")
    client.post("/api/budgets", json={"category_id": food, "month": "2026-11", "amount": "900.00"}, headers=auth_headers)

    body = client.get("/api/ai/insights?month=2026-11", headers=auth_headers).json()
    assert body["available"] is True
    titles = [i["title"] for i in body["insights"]]
    assert titles[0] == "Food & Dining is over budget"
    assert "Unusually large Shopping expense" in titles
    assert any(t.startswith("Spending is up") for t in titles)
    assert len(body["insights"]) <= 5

    over = body["insights"][0]
    assert over["tone"] == "warning"
    assert {f["value"] for f in over["facts"]} == {"INR 1,000.00", "INR 900.00"}
    # Figures match the dashboard exactly.
    dash = client.get("/api/dashboard?month=2026-11", headers=auth_headers).json()
    up = next(i for i in body["insights"] if i["title"].startswith("Spending is up"))
    assert f"INR {Decimal(dash['totals']['expense']):,.2f}" in up["body"]


def test_insights_are_per_user(client, auth_headers, other_headers, categories, create_tx):
    for _ in range(5):
        create_tx(other_headers, categories["Shopping"]["id"], amount="5000.00")
    body = client.get("/api/ai/insights?month=2026-11", headers=auth_headers).json()
    assert body["available"] is False


# --- SW-14 assistant (own intent model) ----------------------------------------------


def test_assistant_answers_spending_by_category_and_period(client, auth_headers, other_headers, categories, create_tx):
    food = categories["Food & Dining"]["id"]
    create_tx(auth_headers, food, amount="500.00", transaction_date="2026-10-12", description="Dinner")
    create_tx(auth_headers, food, amount="120.00", transaction_date="2026-11-02", description="Lunch")
    create_tx(other_headers, food, amount="999.00", transaction_date="2026-10-12", description="Bob dinner")

    body = _ask(client, auth_headers, "How much did I spend on food in October?")
    assert "INR 500.00" in body["reply"]
    assert "Food & Dining" in body["reply"] and "October 2026" in body["reply"]
    assert "999" not in body["reply"]
    assert body["data_used"][0]["tool"] == "search_transactions"
    assert "category Food & Dining" in body["data_used"][0]["description"]


def test_assistant_merchant_search_and_top_categories(client, auth_headers, categories, create_tx):
    d = date.today().replace(day=1).isoformat()
    create_tx(auth_headers, categories["Food & Dining"]["id"], amount="300.00", description="Swiggy biryani", transaction_date=d)
    create_tx(auth_headers, categories["Shopping"]["id"], amount="2000.00", description="Amazon shoes", transaction_date=d)

    assert "INR 300.00" in _ask(client, auth_headers, "how much did i spend on swiggy this month")["reply"]
    top = _ask(client, auth_headers, "where does my money go?")["reply"]
    assert top.index("Shopping") < top.index("Food & Dining")


def test_assistant_budgets_goals_and_read_only(client, auth_headers, categories, create_tx):
    month = date.today().strftime("%Y-%m")
    client.post("/api/budgets", json={"category_id": categories["Shopping"]["id"], "month": month, "amount": "1000.00"}, headers=auth_headers)
    create_tx(auth_headers, categories["Shopping"]["id"], amount="1500.00", transaction_date=date.today().isoformat())
    budgets = _ask(client, auth_headers, "am I over budget?")["reply"]
    assert "Shopping" in budgets and "over budget" in budgets

    assert "don't have any savings goals" in _ask(client, auth_headers, "how are my savings goals?")["reply"]
    refuse = _ask(client, auth_headers, "add a transaction for 500")
    assert "only read" in refuse["reply"] and refuse["data_used"] == []


def test_assistant_helps_when_it_does_not_understand(client, auth_headers):
    assert "I can answer questions" in _ask(client, auth_headers, "qwerty zxcv")["reply"]
    assert "I can answer questions" in _ask(client, auth_headers, "hello")["reply"]


def test_assistant_last_message_must_be_from_user(client, auth_headers):
    resp = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# --- SW-16 receipts (optional LLM provider, faked) -----------------------------------


def test_receipts_unavailable_without_a_provider(client, auth_headers):
    files = {"file": ("r.png", PNG, "image/png")}
    assert client.post("/api/ai/receipt", files=files, headers=auth_headers).status_code == 503


def test_receipt_rejects_unsupported_and_large_files(client, auth_headers, fake_ai):
    assert client.post("/api/ai/receipt", files={"file": ("x.txt", b"hello", "text/plain")}, headers=auth_headers).status_code == 400
    big = PNG + b"0" * (5 * 1024 * 1024)
    assert client.post("/api/ai/receipt", files={"file": ("x.png", big, "image/png")}, headers=auth_headers).status_code == 400
    assert fake_ai.calls == []


def test_receipt_pdf_rejected_when_provider_cannot_read_pdfs(client, auth_headers, fake_ai):
    fake_ai.supports_pdf = False
    resp = client.post("/api/ai/receipt", files={"file": ("r.pdf", PDF, "application/pdf")}, headers=auth_headers)
    assert resp.status_code == 400 and "PDF" in resp.json()["detail"]


def test_receipt_prefills_an_expense_with_decimal_amount(client, auth_headers, fake_ai):
    fake_ai.reply({"readable": True, "merchant": "Fresh Mart", "date": "2026-11-15", "total": "1,249.5",
                   "currency": "INR", "category": "Shopping"})
    body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
    assert body["readable"] is True
    assert (body["merchant"], body["amount"], body["transaction_date"]) == ("Fresh Mart", "1249.50", "2026-11-15")
    assert body["category"]["name"] == "Shopping"
    assert fake_ai.calls[0]["images"][0].media_type == "image/png"
    assert client.get("/api/transactions", headers=auth_headers).json()["total"] == 0


def test_receipt_unreadable_or_invalid_total(client, auth_headers, fake_ai):
    fake_ai.reply({"readable": False, "merchant": "", "date": "", "total": "", "currency": "", "category": "none"})
    fake_ai.reply({"readable": True, "merchant": "Shop", "date": "", "total": "12.345", "currency": "", "category": "none"})
    for _ in range(2):
        body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
        assert body["readable"] is False and "Couldn't read" in body["message"]


def test_receipt_warns_about_a_different_currency(client, auth_headers, fake_ai):
    fake_ai.reply({"readable": True, "merchant": "Cafe", "date": "", "total": "12.00", "currency": "usd", "category": "none"})
    body = client.post("/api/ai/receipt", files={"file": ("r.png", PNG, "image/png")}, headers=auth_headers).json()
    assert body["currency"] == "USD" and "USD" in body["message"]
    assert ai_client.get_provider() is fake_ai
