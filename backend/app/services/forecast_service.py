"""SW-15: end-of-month spending and savings-goal forecasts.

Plain arithmetic, no AI, so every figure can be checked:

- Daily spending rate per category = (spent this month + spent in the previous
  3 months that have data) / (days elapsed this month + days in those months).
  Blending in history stops a single big purchase early in the month from
  dominating the projection.
- Projected month total = spent so far + already-recorded future-dated
  transactions + daily rate x days left.
- Goal pace = amount saved / time since the goal was created (at least 30 days).
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai import CategoryForecast, Forecast, GoalForecast
from app.services.budget_service import compute_status, list_budgets_with_status
from app.utils.dates import add_months, days_in_month, first_day_of_month, format_month, month_range
from app.utils.money import ZERO, money

HISTORY_MONTHS = 3
MIN_DATA_MONTHS = 2
MIN_GOAL_DAYS = 30
DAYS_PER_MONTH = Decimal("30.44")


def _months_with_data(db: Session, user_id: uuid.UUID, before: date) -> set[tuple[int, int]]:
    y = extract("year", Transaction.transaction_date)
    m = extract("month", Transaction.transaction_date)
    rows = db.execute(
        select(y, m).where(Transaction.user_id == user_id, Transaction.transaction_date < before).distinct()
    ).all()
    return {(int(a), int(b)) for a, b in rows}


def _expense_by_category(db: Session, user_id: uuid.UUID, start: date, end: date) -> dict[uuid.UUID, Decimal]:
    rows = db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE.value,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .group_by(Transaction.category_id)
    ).all()
    return {cid: money(total) for cid, total in rows}


def _goal_forecasts(db: Session, user_id: uuid.UUID, today: date) -> list[GoalForecast]:
    result: list[GoalForecast] = []
    goals = db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user_id).order_by(SavingsGoal.name)).all()
    for g in goals:
        target, current = money(g.target_amount), money(g.current_amount)
        remaining = money(target - current)
        if remaining <= 0:
            continue
        days_active = max(MIN_GOAL_DAYS, (today - g.created_at.date()).days)
        daily_pace = current / Decimal(days_active)
        projected: date | None = None
        if daily_pace > 0:
            days_needed = math.ceil(remaining / daily_pace)
            if days_needed <= 365 * 100:
                projected = today + timedelta(days=days_needed)
        on_track = None if g.target_date is None or projected is None else projected <= g.target_date
        if g.target_date is not None and projected is None:
            on_track = False
        result.append(
            GoalForecast(
                goal_id=g.id,
                name=g.name,
                remaining=remaining,
                monthly_pace=money(daily_pace * DAYS_PER_MONTH),
                projected_completion=projected,
                target_date=g.target_date,
                on_track=on_track,
            )
        )
    return result


def build_forecast(db: Session, user: User, month_start: date, today: date | None = None) -> Forecast:
    today = today or date.today()
    current = first_day_of_month(today)
    base = Forecast(month=format_month(month_start), currency=user.preferred_currency, available=False)

    if month_start != current:
        base.reason = "Forecasts are only available for the current month."
        return base

    month_end = add_months(current, 1)
    data_months = _months_with_data(db, user.id, month_end)
    if len(data_months) < MIN_DATA_MONTHS:
        base.reason = (
            f"Forecasts need at least {MIN_DATA_MONTHS} months of transactions. "
            "Keep adding them and check back next month."
        )
        return base

    elapsed = today.day
    dim = days_in_month(current)
    remaining_days = dim - elapsed
    tomorrow = today + timedelta(days=1)

    spent = _expense_by_category(db, user.id, current, tomorrow)
    scheduled = _expense_by_category(db, user.id, tomorrow, month_end)

    history: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO)
    history_days = 0
    for i in range(1, HISTORY_MONTHS + 1):
        m = add_months(current, -i)
        if (m.year, m.month) not in data_months:
            continue
        history_days += days_in_month(m)
        start, end = month_range(m)
        for cid, total in _expense_by_category(db, user.id, start, end).items():
            history[cid] += total

    budgets = {b.category.id: b for b in list_budgets_with_status(db, user.id, current)}
    category_ids = set(spent) | set(scheduled) | set(history) | set(budgets)
    categories = {c.id: c for c in db.scalars(select(Category).where(Category.id.in_(category_ids))).all()}

    forecasts: list[CategoryForecast] = []
    total_days = Decimal(elapsed + history_days)
    for cid in category_ids:
        cat = categories.get(cid)
        if cat is None:
            continue
        so_far = spent.get(cid, ZERO)
        rate = (so_far + history.get(cid, ZERO)) / total_days
        projected = money(so_far + scheduled.get(cid, ZERO) + rate * remaining_days)
        budget = budgets.get(cid)
        status = None
        will_exceed = False
        if budget is not None:
            _, _, status = compute_status(budget.amount, projected, budget.alert_threshold)
            will_exceed = projected > budget.amount and budget.status != "exceeded"
        if projected <= 0 and budget is None:
            continue
        forecasts.append(
            CategoryForecast(
                category_id=cid,
                name=cat.name,
                color=cat.color,
                spent=money(so_far),
                projected=projected,
                budget=money(budget.amount) if budget else None,
                projected_status=status,
                will_exceed_budget=will_exceed,
            )
        )
    forecasts.sort(key=lambda f: (-f.projected, f.name.lower()))

    return Forecast(
        month=format_month(current),
        currency=user.preferred_currency,
        available=True,
        elapsed_days=elapsed,
        days_in_month=dim,
        spent_so_far=money(sum(spent.values(), ZERO)),
        projected_expense=money(sum((f.projected for f in forecasts), ZERO)),
        categories=forecasts,
        budget_warnings=[f for f in forecasts if f.will_exceed_budget],
        goals=_goal_forecasts(db, user.id, today),
    )
