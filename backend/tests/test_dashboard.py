def _seed(create_tx, headers, categories):
    salary = categories["Salary"]["id"]
    food = categories["Food & Dining"]["id"]
    housing = categories["Housing"]["id"]
    create_tx(headers, salary, description="Salary", amount="60000.00", transaction_type="income",
              transaction_date="2026-11-01")
    create_tx(headers, housing, description="Rent", amount="20000.00", transaction_date="2026-11-02")
    create_tx(headers, food, description="Dinner", amount="3000.00", transaction_date="2026-11-02")
    create_tx(headers, food, description="Lunch", amount="1000.00", transaction_date="2026-11-15")
    # Previous month
    create_tx(headers, salary, description="Salary", amount="50000.00", transaction_type="income",
              transaction_date="2026-10-01")
    create_tx(headers, food, description="October food", amount="5000.00", transaction_date="2026-10-10")


def test_dashboard_totals_and_breakdown(client, auth_headers, categories, create_tx):
    _seed(create_tx, auth_headers, categories)
    client.post("/api/budgets", json={"category_id": categories["Food & Dining"]["id"], "month": "2026-11",
                                      "amount": "4000"}, headers=auth_headers)

    resp = client.get("/api/dashboard", params={"month": "2026-11"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["totals"]["income"] == "60000.00"
    assert data["totals"]["expense"] == "24000.00"
    assert data["totals"]["net"] == "36000.00"
    assert data["totals"]["savings_rate"] == "60.0"
    assert data["totals"]["transaction_count"] == 4
    assert data["previous_totals"]["expense"] == "5000.00"
    assert data["income_change_percent"] == "20.0"

    breakdown = {c["name"]: c for c in data["expense_by_category"]}
    assert breakdown["Housing"]["amount"] == "20000.00"
    assert breakdown["Food & Dining"]["amount"] == "4000.00"
    assert breakdown["Housing"]["percent"] == "83.3"

    assert len(data["monthly_trend"]) == 6
    assert data["monthly_trend"][-1]["month"] == "2026-11"
    assert data["monthly_trend"][-2]["income"] == "50000.00"

    # Food budget is exactly at the limit -> warning
    assert len(data["budget_alerts"]) == 1
    assert data["budget_alerts"][0]["status"] == "warning"
    assert len(data["recent_transactions"]) == 5
    assert data["currency"] == "INR"


def test_dashboard_isolated(client, auth_headers, other_headers, categories, create_tx):
    _seed(create_tx, auth_headers, categories)
    data = client.get("/api/dashboard", params={"month": "2026-11"}, headers=other_headers).json()
    assert data["totals"]["income"] == "0.00"
    assert data["recent_transactions"] == []


def test_dashboard_rejects_bad_month(client, auth_headers):
    assert client.get("/api/dashboard", params={"month": "2026-13"}, headers=auth_headers).status_code == 422


def test_monthly_report(client, auth_headers, categories, create_tx):
    _seed(create_tx, auth_headers, categories)
    resp = client.get("/api/reports/monthly", params={"month": "2026-11"}, headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()
    assert report["label"] == "November 2026"
    assert len(report["daily"]) == 30
    assert report["daily"][1]["expense"] == "23000.00"  # Nov 2
    assert report["daily"][-1]["cumulative_expense"] == "24000.00"
    assert report["highest_expense_day"]["date"] == "2026-11-02"
    assert report["top_expenses"][0]["description"] == "Rent"
    assert report["income_by_category"][0]["name"] == "Salary"


def test_monthly_csv_export(client, auth_headers, categories, create_tx):
    _seed(create_tx, auth_headers, categories)
    create_tx(auth_headers, categories["Shopping"]["id"], description="=HYPERLINK(\"x\")", amount="10",
              transaction_date="2026-11-20")
    resp = client.get("/api/reports/monthly/export", params={"month": "2026-11"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "spendwise-2026-11.csv" in resp.headers["content-disposition"]
    body = resp.text
    assert "Rent" in body and "October food" not in body
    assert "'=HYPERLINK" in body  # formula injection neutralized
