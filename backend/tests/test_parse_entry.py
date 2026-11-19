"""SW-22 quick add: SpendWise's own parser and category model (no outside AI)."""

from datetime import date
from decimal import Decimal

import pytest

from app.services.ml.entry_parser import find_amount, find_date, parse_entry

TODAY = date(2026, 11, 19)  # a Thursday


def test_parse_fills_the_form_from_a_sentence(client, auth_headers):
    resp = client.post("/api/ai/parse", json={"text": "paid 450 for lunch at Swiggy yesterday on UPI"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transaction_type"] == "expense"
    assert body["amount"] == "450.00"
    assert body["description"] == "Lunch at Swiggy"
    assert body["category"]["name"] == "Food & Dining"
    assert body["payment_method"] == "upi"
    assert body["missing"] == []
    assert client.get("/api/transactions", headers=auth_headers).json()["total"] == 0  # nothing saved


def test_parse_income_and_default_date(client, auth_headers):
    body = client.post("/api/ai/parse", json={"text": "salary 85,000 credited"}, headers=auth_headers).json()
    assert body["transaction_type"] == "income"
    assert body["amount"] == "85000.00"
    assert body["category"]["name"] == "Salary"
    assert body["transaction_date"] == date.today().isoformat()


def test_parse_leaves_ambiguous_amount_blank(client, auth_headers):
    body = client.post("/api/ai/parse", json={"text": "dinner for 2 people 900"}, headers=auth_headers).json()
    assert body["amount"] is None
    assert "amount" in body["missing"]


def test_parse_uses_the_users_history_for_category(client, auth_headers, categories, create_tx):
    create_tx(auth_headers, categories["Travel"]["id"], description="Rapido")
    body = client.post("/api/ai/parse", json={"text": "rapido 80 cash"}, headers=auth_headers).json()
    assert body["category"]["name"] == "Travel"
    assert body["payment_method"] == "cash"


def test_parse_validates_input(client, auth_headers):
    assert client.post("/api/ai/parse", json={"text": "   "}, headers=auth_headers).status_code == 422
    assert client.post("/api/ai/parse", json={"text": "x" * 501}, headers=auth_headers).status_code == 422


@pytest.mark.parametrize(
    "text,amount,when,method,description",
    [
        ("paid 450 for lunch at Swiggy yesterday on UPI", "450.00", date(2026, 11, 18), "upi", "Lunch at Swiggy"),
        ("netflix 649 on 5th nov via credit card", "649.00", date(2026, 11, 5), "credit_card", "Netflix"),
        ("Rs 1200 groceries at DMart 15/11", "1200.00", date(2026, 11, 15), None, "Groceries at DMart"),
        ("bought shoes for ₹2,499 last friday using debit card", "2499.00", date(2026, 11, 13), "debit_card", "Shoes"),
        ("electricity bill 1,850.50", "1850.50", None, None, "Electricity Bill"),
        ("movie 3 days ago 500 gpay", "500.00", date(2026, 11, 16), "upi", "Movie"),
        ("phone 2k emi", "2000.00", None, None, "Phone Emi"),
        ("christmas gifts 3000 on 25 dec", "3000.00", date(2025, 12, 25), None, "Christmas Gifts"),
        ("coffee", None, None, None, "Coffee"),
    ],
)
def test_parser_examples(text, amount, when, method, description):
    p = parse_entry(text, TODAY)
    assert (str(p.amount) if p.amount else None) == amount
    assert p.transaction_date == when
    assert (p.payment_method.value if p.payment_method else None) == method
    assert p.description == description


@pytest.mark.parametrize(
    "text,expected",
    [
        ("lunch yesterday", date(2026, 11, 18)),
        ("day before yesterday cab", date(2026, 11, 17)),
        ("paid rent today", date(2026, 11, 19)),
        ("groceries on monday", date(2026, 11, 16)),
        ("dinner last thursday", date(2026, 11, 12)),
        ("on 2026-10-02", date(2026, 10, 2)),
        ("nov 3rd", date(2026, 11, 3)),
        ("31/02", None),
    ],
)
def test_dates(text, expected):
    assert find_date(text, TODAY)[0] == expected


def test_amount_prefers_the_marked_number():
    assert find_amount("2 coffees for rs 240")[0] == Decimal("240.00")
    assert find_amount("2 coffees 240")[0] is None
