def test_default_categories_are_available(client, auth_headers):
    resp = client.get("/api/categories", headers=auth_headers)
    assert resp.status_code == 200
    names = {(c["name"], c["transaction_type"]) for c in resp.json()}
    assert ("Food & Dining", "expense") in names
    assert ("Salary", "income") in names
    assert len([c for c in resp.json() if c["is_system"]]) == 19


def test_filter_categories_by_type(client, auth_headers):
    resp = client.get("/api/categories", params={"transaction_type": "income"}, headers=auth_headers)
    assert resp.status_code == 200
    assert all(c["transaction_type"] == "income" for c in resp.json())


def test_custom_category_is_private(client, auth_headers, other_headers):
    resp = client.post(
        "/api/categories",
        json={"name": "Pets", "transaction_type": "expense", "color": "#123456", "icon_name": "dog"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    other_names = {c["name"] for c in client.get("/api/categories", headers=other_headers).json()}
    assert "Pets" not in other_names
    assert client.patch(f"/api/categories/{cat_id}", json={"name": "X"}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/categories/{cat_id}", headers=other_headers).status_code == 404


def test_duplicate_category_name_rejected(client, auth_headers):
    resp = client.post(
        "/api/categories", json={"name": "food & dining", "transaction_type": "expense"}, headers=auth_headers
    )
    assert resp.status_code == 409


def test_system_category_cannot_be_modified(client, auth_headers, categories):
    cat_id = categories["Housing"]["id"]
    assert client.patch(f"/api/categories/{cat_id}", json={"name": "Rent"}, headers=auth_headers).status_code == 404
    assert client.delete(f"/api/categories/{cat_id}", headers=auth_headers).status_code == 404


def test_category_in_use_cannot_be_deleted(client, auth_headers, create_tx):
    cat = client.post(
        "/api/categories", json={"name": "Pets", "transaction_type": "expense"}, headers=auth_headers
    ).json()
    create_tx(auth_headers, cat["id"])
    assert client.delete(f"/api/categories/{cat['id']}", headers=auth_headers).status_code == 409


def test_invalid_color_rejected(client, auth_headers):
    resp = client.post(
        "/api/categories", json={"name": "Pets", "transaction_type": "expense", "color": "red"}, headers=auth_headers
    )
    assert resp.status_code == 422
