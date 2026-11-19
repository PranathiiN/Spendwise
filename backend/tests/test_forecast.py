"""SW-15 forecasting (plain arithmetic, no AI)."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models import SavingsGoal, User
from app.services.forecast_service import build_forecast

TODAY = date(2026, 11, 10)  # 10 of 30 days elapsed


def _forecast(email: str = "alice@example.com", month: date = date(2026, 11, 1), today: date = TODAY):
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        return build_forecast(db, user, month, today)


def test_forecast_needs_two_months_of_data(client, auth_headers, categories, create_tx):
    create_tx(auth_headers, categories["Shopping"]["id"], transaction_date="2026-11-05")
    f = _forecast()
    assert f.available is False
    assert "2 months" in f.reason
    assert f.categories == []


def test_forecast_only_for_current_month(client, auth_headers):
    f = _forecast(month=date(2026, 10, 1))
    assert f.available is False
    assert "current month" in f.reason


def test_forecast_projects_month_end_and_warns_before_budget_is_exceeded(client, auth_headers, categories, create_tx):
    food = categories["Food & Dining"]["id"]
    # October (31 days): 3100 spent -> 100/day historically.
    create_tx(auth_headers, food, amount="3100.00", transaction_date="2026-10-15")
    # November so far (10 days): 1000 spent.
    create_tx(auth_headers, food, amount="1000.00", transaction_date="2026-11-04")
    # A transaction later this month that's already recorded counts in full.
    create_tx(auth_headers, food, amount="200.00", transaction_date="2026-11-25")
    resp = client.post(
        "/api/budgets", json={"category_id": food, "month": "2026-11", "amount": "4000.00"}, headers=auth_headers
    )
    assert resp.status_code == 201, resp.text

    f = _forecast()
    assert f.available is True and f.is_estimate is True
    assert (f.elapsed_days, f.days_in_month) == (10, 30)
    assert f.spent_so_far == Decimal("1000.00")

    food_fc = next(c for c in f.categories if c.name == "Food & Dining")
    # rate = (1000 + 3100) / (10 + 31) = 100/day; projected = 1000 + 200 + 100 * 20 = 3200
    assert food_fc.projected == Decimal("3200.00")
    assert food_fc.budget == Decimal("4000.00")
    assert food_fc.projected_status == "warning"  # 80% of the budget
    assert food_fc.will_exceed_budget is False
    assert f.projected_expense == Decimal("3200.00")


def test_forecast_flags_budget_that_will_go_over(client, auth_headers, categories, create_tx):
    shop = categories["Shopping"]["id"]
    create_tx(auth_headers, shop, amount="3100.00", transaction_date="2026-10-02")
    create_tx(auth_headers, shop, amount="1000.00", transaction_date="2026-11-02")
    client.post("/api/budgets", json={"category_id": shop, "month": "2026-11", "amount": "2000.00"}, headers=auth_headers)

    f = _forecast()
    assert [w.name for w in f.budget_warnings] == ["Shopping"]
    assert f.budget_warnings[0].projected_status == "exceeded"


def test_forecast_is_per_user(client, auth_headers, other_headers, categories, create_tx):
    shop = categories["Shopping"]["id"]
    create_tx(other_headers, shop, amount="9999.00", transaction_date="2026-10-02")
    create_tx(other_headers, shop, amount="9999.00", transaction_date="2026-11-02")
    create_tx(auth_headers, shop, amount="10.00", transaction_date="2026-10-02")
    create_tx(auth_headers, shop, amount="10.00", transaction_date="2026-11-02")
    f = _forecast()
    assert f.spent_so_far == Decimal("10.00")


def test_goal_completion_is_projected_from_pace(client, auth_headers, categories, create_tx):
    create_tx(auth_headers, categories["Shopping"]["id"], transaction_date="2026-10-02")
    create_tx(auth_headers, categories["Shopping"]["id"], transaction_date="2026-11-02")
    goal = client.post(
        "/api/goals",
        json={"name": "Laptop", "target_amount": "60000.00", "target_date": "2027-12-31"},
        headers=auth_headers,
    ).json()
    client.post(f"/api/goals/{goal['id']}/contribute", json={"amount": "6000.00", "action": "deposit"}, headers=auth_headers)
    with SessionLocal() as db:  # created 60 days before TODAY -> 100/day
        db.execute(
            update(SavingsGoal)
            .where(SavingsGoal.name == "Laptop")
            .values(created_at=datetime(2026, 9, 11, tzinfo=timezone.utc))
        )
        db.commit()

    g = _forecast().goals[0]
    assert g.remaining == Decimal("54000.00")
    assert g.monthly_pace == Decimal("3044.00")
    assert g.projected_completion == date(2028, 5, 3)  # 540 days after 2026-11-10
    assert g.on_track is False
