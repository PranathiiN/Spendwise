def test_create_transaction_preserves_decimal_precision(client, auth_headers, categories, create_tx):
    tx = create_tx(auth_headers, categories["Food & Dining"]["id"], amount="1234.56", payment_method="upi")
    assert tx["amount"] == "1234.56"
    assert tx["category"]["name"] == "Food & Dining"
    assert tx["payment_method"] == "upi"


def test_amount_must_be_positive_with_two_decimals(client, auth_headers, categories):
    base = {
        "category_id": categories["Shopping"]["id"],
        "description": "Bad",
        "transaction_type": "expense",
        "transaction_date": "2026-11-05",
    }
    for amount in ["0", "-5", "10.555", "abc"]:
        resp = client.post("/api/transactions", json={**base, "amount": amount}, headers=auth_headers)
        assert resp.status_code == 422, amount


def test_category_type_must_match(client, auth_headers, categories):
    resp = client.post(
        "/api/transactions",
        json={
            "category_id": categories["Salary"]["id"],
            "description": "Wrong",
            "amount": "10",
            "transaction_type": "expense",
            "transaction_date": "2026-11-05",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "income" in resp.json()["detail"]


def test_cannot_use_another_users_category(client, auth_headers, other_headers):
    bob_cat = client.post(
        "/api/categories", json={"name": "Bob Only", "transaction_type": "expense"}, headers=other_headers
    ).json()
    resp = client.post(
        "/api/transactions",
        json={
            "category_id": bob_cat["id"],
            "description": "Sneaky",
            "amount": "10",
            "transaction_type": "expense",
            "transaction_date": "2026-11-05",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_transactions_are_isolated_between_users(client, auth_headers, other_headers, categories, create_tx):
    tx = create_tx(auth_headers, categories["Travel"]["id"])
    assert client.get(f"/api/transactions/{tx['id']}", headers=other_headers).status_code == 404
    assert client.patch(f"/api/transactions/{tx['id']}", json={"amount": "1"}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/transactions/{tx['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/transactions", headers=other_headers).json()["total"] == 0
    # Still intact for the owner
    assert client.get(f"/api/transactions/{tx['id']}", headers=auth_headers).json()["amount"] == "100.00"


def test_update_and_delete_transaction(client, auth_headers, categories, create_tx):
    tx = create_tx(auth_headers, categories["Travel"]["id"])
    resp = client.patch(
        f"/api/transactions/{tx['id']}",
        json={"amount": "250.75", "description": "Train tickets", "notes": "Holiday"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == "250.75"
    assert resp.json()["description"] == "Train tickets"

    # Switching to income without an income category must fail
    resp = client.patch(f"/api/transactions/{tx['id']}", json={"transaction_type": "income"}, headers=auth_headers)
    assert resp.status_code == 400

    resp = client.patch(
        f"/api/transactions/{tx['id']}",
        json={"transaction_type": "income", "category_id": categories["Refund"]["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["category"]["name"] == "Refund"

    assert client.patch(f"/api/transactions/{tx['id']}", json={"amount": None}, headers=auth_headers).status_code == 422

    assert client.delete(f"/api/transactions/{tx['id']}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/transactions/{tx['id']}", headers=auth_headers).status_code == 404


def test_list_filters_search_and_pagination(client, auth_headers, categories, create_tx):
    food = categories["Food & Dining"]["id"]
    salary = categories["Salary"]["id"]
    create_tx(auth_headers, food, description="Pizza night", amount="500.00", transaction_date="2026-11-01")
    create_tx(auth_headers, food, description="Groceries", amount="1200.50", transaction_date="2026-11-10",
              notes="weekly pizza dough")
    create_tx(auth_headers, food, description="Coffee", amount="150.00", transaction_date="2026-10-20")
    create_tx(auth_headers, salary, description="November salary", amount="50000", transaction_type="income",
              transaction_date="2026-11-01")

    def get(**params):
        resp = client.get("/api/transactions", params=params, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()

    assert get()["total"] == 4
    assert get(transaction_type="income")["total"] == 1
    assert get(search="pizza")["total"] == 2  # matches description or notes
    assert get(search="100%")["total"] == 0  # wildcard characters are escaped
    assert get(category_id=food)["total"] == 3
    assert get(start_date="2026-11-01", end_date="2026-11-30")["total"] == 3
    assert get(min_amount="200", max_amount="2000")["total"] == 2

    page = get(page=1, page_size=2, sort_by="amount", sort_order="desc")
    assert page["total"] == 4 and page["total_pages"] == 2 and len(page["items"]) == 2
    assert page["items"][0]["amount"] == "50000.00"
    assert page["total_income"] == "50000.00"
    assert page["total_expense"] == "1850.50"

    assert client.get("/api/transactions", params={"start_date": "2026-12-01", "end_date": "2026-11-01"},
                      headers=auth_headers).status_code == 400


def test_requires_authentication(client):
    assert client.get("/api/transactions").status_code == 401
