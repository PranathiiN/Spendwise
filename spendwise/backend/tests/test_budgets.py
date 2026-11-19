from decimal import Decimal

from app.services.budget_service import compute_status


def test_compute_status_thresholds():
    assert compute_status(Decimal("1000"), Decimal("500"), 80)[2] == "ok"
    assert compute_status(Decimal("1000"), Decimal("800"), 80)[2] == "warning"
    assert compute_status(Decimal("1000"), Decimal("1000"), 80)[2] == "warning"
    remaining, pct, status = compute_status(Decimal("1000"), Decimal("1200.50"), 80)
    assert status == "exceeded"
    assert remaining == Decimal("-200.50")
    assert pct == Decimal("120.1")


def _create_budget(client, headers, category_id, amount="1000.00", month="2026-11", threshold=80):
    return client.post(
        "/api/budgets",
        json={"category_id": category_id, "month": month, "amount": amount, "alert_threshold": threshold},
        headers=headers,
    )


def test_budget_status_reflects_spending(client, auth_headers, categories, create_tx):
    food = categories["Food & Dining"]["id"]
    resp = _create_budget(client, auth_headers, food)
    assert resp.status_code == 201
    assert resp.json()["status"] == "ok"
    assert resp.json()["spent"] == "0.00"

    create_tx(auth_headers, food, amount="850.00", transaction_date="2026-11-03")
    create_tx(auth_headers, food, amount="999.00", transaction_date="2026-10-31")  # other month, ignored

    data = client.get("/api/budgets", params={"month": "2026-11"}, headers=auth_headers).json()
    budget = data["budgets"][0]
    assert budget["spent"] == "850.00"
    assert budget["remaining"] == "150.00"
    assert budget["percent_used"] == "85.0"
    assert budget["status"] == "warning"
    assert data["warning_count"] == 1

    create_tx(auth_headers, food, amount="200.00", transaction_date="2026-11-04")
    data = client.get("/api/budgets", params={"month": "2026-11"}, headers=auth_headers).json()
    assert data["budgets"][0]["status"] == "exceeded"
    assert data["exceeded_count"] == 1
    assert data["total_spent"] == "1050.00"


def test_duplicate_budget_rejected(client, auth_headers, categories):
    food = categories["Food & Dining"]["id"]
    assert _create_budget(client, auth_headers, food).status_code == 201
    assert _create_budget(client, auth_headers, food).status_code == 409
    assert _create_budget(client, auth_headers, food, month="2026-12").status_code == 201


def test_budget_requires_expense_category(client, auth_headers, categories):
    assert _create_budget(client, auth_headers, categories["Salary"]["id"]).status_code == 400


def test_budget_validation(client, auth_headers, categories):
    food = categories["Food & Dining"]["id"]
    assert _create_budget(client, auth_headers, food, amount="0").status_code == 422
    assert _create_budget(client, auth_headers, food, month="2026-13").status_code == 422
    assert _create_budget(client, auth_headers, food, threshold=150).status_code == 422


def test_update_and_delete_budget(client, auth_headers, categories):
    budget = _create_budget(client, auth_headers, categories["Housing"]["id"]).json()
    resp = client.patch(f"/api/budgets/{budget['id']}", json={"amount": "25000.00", "alert_threshold": 90},
                        headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["amount"] == "25000.00"
    assert resp.json()["alert_threshold"] == 90
    assert client.delete(f"/api/budgets/{budget['id']}", headers=auth_headers).status_code == 204


def test_budgets_isolated(client, auth_headers, other_headers, categories):
    budget = _create_budget(client, auth_headers, categories["Housing"]["id"]).json()
    assert client.get(f"/api/budgets/{budget['id']}", headers=other_headers).status_code == 404
    assert client.patch(f"/api/budgets/{budget['id']}", json={"amount": "1"}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/budgets/{budget['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/budgets", params={"month": "2026-11"}, headers=other_headers).json()["budgets"] == []


def test_copy_previous_month(client, auth_headers, categories):
    _create_budget(client, auth_headers, categories["Housing"]["id"], month="2026-10")
    _create_budget(client, auth_headers, categories["Utilities"]["id"], month="2026-10")
    _create_budget(client, auth_headers, categories["Utilities"]["id"], month="2026-11", amount="300")

    resp = client.post("/api/budgets/copy-previous", params={"month": "2026-11"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["created"] == 1  # Utilities already existed
    data = client.get("/api/budgets", params={"month": "2026-11"}, headers=auth_headers).json()
    assert len(data["budgets"]) == 2
