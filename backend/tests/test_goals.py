from datetime import date, timedelta


def _create_goal(client, headers, **overrides):
    body = {"name": "Emergency fund", "target_amount": "100000.00"}
    body.update(overrides)
    return client.post("/api/goals", json=body, headers=headers)


def test_create_goal_with_progress(client, auth_headers):
    target_date = (date.today() + timedelta(days=200)).isoformat()
    resp = _create_goal(client, auth_headers, current_amount="25000.00", target_date=target_date)
    assert resp.status_code == 201
    goal = resp.json()
    assert goal["progress_percent"] == "25.0"
    assert goal["remaining_amount"] == "75000.00"
    assert goal["status"] == "active"
    assert goal["monthly_required"] is not None


def test_goal_validation(client, auth_headers):
    assert _create_goal(client, auth_headers, target_amount="0").status_code == 422
    assert _create_goal(client, auth_headers, current_amount="-1").status_code == 422
    assert _create_goal(client, auth_headers, name="").status_code == 422


def test_contribute_and_withdraw(client, auth_headers):
    goal = _create_goal(client, auth_headers, target_amount="1000.00").json()
    url = f"/api/goals/{goal['id']}/contribute"

    resp = client.post(url, json={"amount": "400.50"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["current_amount"] == "400.50"

    resp = client.post(url, json={"amount": "500.00", "action": "withdraw"}, headers=auth_headers)
    assert resp.status_code == 400

    resp = client.post(url, json={"amount": "100.50", "action": "withdraw"}, headers=auth_headers)
    assert resp.json()["current_amount"] == "300.00"

    resp = client.post(url, json={"amount": "700.00"}, headers=auth_headers)
    assert resp.json()["is_completed"] is True
    assert resp.json()["status"] == "completed"
    assert resp.json()["progress_percent"] == "100.0"


def test_overdue_goal(client, auth_headers):
    past = (date.today() - timedelta(days=5)).isoformat()
    goal = _create_goal(client, auth_headers, target_date=past).json()
    assert goal["status"] == "overdue"


def test_update_and_delete_goal(client, auth_headers):
    goal = _create_goal(client, auth_headers).json()
    resp = client.patch(f"/api/goals/{goal['id']}", json={"name": "Rainy day", "target_amount": "50000"},
                        headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Rainy day"
    assert resp.json()["target_amount"] == "50000.00"
    assert client.delete(f"/api/goals/{goal['id']}", headers=auth_headers).status_code == 204
    assert client.get("/api/goals", headers=auth_headers).json() == []


def test_goals_isolated(client, auth_headers, other_headers):
    goal = _create_goal(client, auth_headers).json()
    assert client.get(f"/api/goals/{goal['id']}", headers=other_headers).status_code == 404
    assert client.post(f"/api/goals/{goal['id']}/contribute", json={"amount": "1"},
                       headers=other_headers).status_code == 404
    assert client.delete(f"/api/goals/{goal['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/goals", headers=other_headers).json() == []
