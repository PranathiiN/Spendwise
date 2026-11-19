"""SW-13: plain-language monthly spending insights - with SpendWise's own rules.

Every figure comes from the same services as the dashboard and reports. Rules
pick what's worth pointing out (budgets over or heading over, unusual expenses,
big changes from last month, savings rate, goals) and write it up from
templates. Each insight lists the figures it's based on. No outside AI.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai import Insight, InsightFact, InsightsResponse
from app.services.dashboard_service import build_dashboard, category_breakdown
from app.services.forecast_service import build_forecast
from app.utils.dates import add_months, first_day_of_month, format_month, month_range
from app.utils.money import money

MIN_TRANSACTIONS = 5
MAX_INSIGHTS = 5
UNUSUAL_MULTIPLIER = Decimal("2")
CHANGE_THRESHOLD = Decimal("10")  # percent
CATEGORY_CHANGE_THRESHOLD = Decimal("20")  # percent


@dataclass
class _Candidate:
    priority: int
    insight: Insight


def _unusual_transactions(db: Session, user_id: uuid.UUID, month_start: date) -> list[tuple[Transaction, Decimal]]:
    """Expenses this month at least 2x the category's average transaction over the previous 3 months."""
    start, end = month_range(month_start)
    averages = dict(
        db.execute(
            select(Transaction.category_id, func.avg(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE.value,
                Transaction.transaction_date >= add_months(month_start, -3),
                Transaction.transaction_date < start,
            )
            .group_by(Transaction.category_id)
        ).all()
    )
    txs = db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE.value,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .order_by(Transaction.amount.desc())
    ).all()
    result = []
    for tx in txs:
        avg = averages.get(tx.category_id)
        if avg and tx.amount >= Decimal(avg) * UNUSUAL_MULTIPLIER:
            result.append((tx, money(avg)))
    return result[:2]


def generate_insights(db: Session, user: User, month_start: date, today: date | None = None) -> InsightsResponse:
    today = today or date.today()
    month = format_month(month_start)
    dash = build_dashboard(db, user, month_start)
    t, prev = dash.totals, dash.previous_totals
    if t.transaction_count < MIN_TRANSACTIONS:
        return InsightsResponse(
            month=month, available=False, reason=f"Add at least {MIN_TRANSACTIONS} transactions this month to get insights."
        )

    cur = dash.currency
    label = month_start.strftime("%B")
    prev_label = add_months(month_start, -1).strftime("%B")
    counter = iter(range(1, 1000))

    def m(value: Decimal) -> str:
        return f"{cur} {money(value):,.2f}"

    def fact(lbl: str, value: str) -> InsightFact:
        return InsightFact(id=f"f{next(counter)}", label=lbl, value=value)

    out: list[_Candidate] = []

    def add(priority: int, title: str, body: str, tone: str, facts: list[InsightFact]) -> None:
        out.append(_Candidate(priority, Insight(title=title, body=body, tone=tone, facts=facts)))  # type: ignore[arg-type]

    # Budgets over or near their limit.
    for b in dash.budget_alerts[:3]:
        f = [fact(f"{b.category.name} spent", m(b.spent)), fact(f"{b.category.name} budget", m(b.amount))]
        if b.status == "exceeded":
            add(100, f"{b.category.name} is over budget",
                f"You've spent {m(b.spent)} against a budget of {m(b.amount)}, {m(b.spent - b.amount)} over.", "warning", f)
        else:
            add(65, f"{b.category.name} is close to its budget",
                f"{b.percent_used}% used: {m(b.spent)} of {m(b.amount)}, with {m(b.remaining)} left.", "warning", f)

    # Budgets the forecast says will go over (current month only).
    if first_day_of_month(today) == month_start:
        forecast = build_forecast(db, user, month_start, today)
        for w in forecast.budget_warnings[:2]:
            add(90, f"{w.name} is heading over budget",
                f"At your usual pace you'll spend about {m(w.projected)} on {w.name} this month, above the {m(w.budget)} budget (estimate).",
                "warning", [fact(f"{w.name} projected (estimate)", m(w.projected)), fact(f"{w.name} budget", m(w.budget))])

    # Unusually large expenses.
    for tx, avg in _unusual_transactions(db, user.id, month_start):
        add(80, f"Unusually large {tx.category.name} expense",
            f"{tx.description} on {tx.transaction_date:%d %b} cost {m(tx.amount)}, more than double your usual {tx.category.name} expense of {m(avg)}.",
            "warning", [fact(tx.description, m(tx.amount)), fact(f"Usual {tx.category.name} expense (3-month average)", m(avg))])

    # Total spending vs last month.
    change = dash.expense_change_percent
    if change is not None and abs(change) >= CHANGE_THRESHOLD:
        f = [fact(f"Spending in {label}", m(t.expense)), fact(f"Spending in {prev_label}", m(prev.expense))]
        if change > 0:
            add(70, f"Spending is up {change}% on {prev_label}",
                f"You spent {m(t.expense)} in {label}, {m(t.expense - prev.expense)} more than {prev_label}'s {m(prev.expense)}.", "warning", f)
        else:
            add(70, f"Spending is down {abs(change)}% on {prev_label}",
                f"You spent {m(t.expense)} in {label}, {m(prev.expense - t.expense)} less than {prev_label}'s {m(prev.expense)}.", "positive", f)

    # Biggest category change vs last month.
    prev_by_cat = {c.category_id: c for c in category_breakdown(db, user.id, add_months(month_start, -1), TransactionType.EXPENSE)}
    changes = []
    for c in dash.expense_by_category:
        before = prev_by_cat.get(c.category_id)
        if before and before.amount > 0:
            pct = (c.amount - before.amount) / before.amount * 100
            changes.append((c, before, pct))
    if changes:
        c, before, pct = max(changes, key=lambda x: x[0].amount - x[1].amount)
        if pct >= CATEGORY_CHANGE_THRESHOLD:
            add(60, f"{c.name} spending grew the most",
                f"{c.name} went from {m(before.amount)} in {prev_label} to {m(c.amount)} in {label} ({pct.quantize(Decimal('0.1'))}% more).",
                "neutral", [fact(f"{c.name} in {label}", m(c.amount)), fact(f"{c.name} in {prev_label}", m(before.amount))])
        c, before, pct = min(changes, key=lambda x: x[0].amount - x[1].amount)
        if pct <= -CATEGORY_CHANGE_THRESHOLD:
            add(50, f"You cut back on {c.name}",
                f"{c.name} went down from {m(before.amount)} in {prev_label} to {m(c.amount)} in {label}.",
                "positive", [fact(f"{c.name} in {label}", m(c.amount)), fact(f"{c.name} in {prev_label}", m(before.amount))])

    # Savings rate.
    if t.income > 0:
        f = [fact(f"Income in {label}", m(t.income)), fact(f"Spending in {label}", m(t.expense)), fact("Savings rate", f"{t.savings_rate}%")]
        if t.net < 0:
            add(75, "You spent more than you earned",
                f"Spending of {m(t.expense)} was {m(-t.net)} more than your income of {m(t.income)} in {label}.", "warning", f)
        elif t.savings_rate >= 20:
            add(45, f"You saved {t.savings_rate}% of your income",
                f"You kept {m(t.net)} of your {m(t.income)} income in {label}.", "positive", f)

    # Where most money went.
    if dash.expense_by_category:
        top = dash.expense_by_category[0]
        add(40, f"{top.name} was your biggest expense",
            f"{m(top.amount)} went on {top.name}, {top.percent}% of your spending in {label}.",
            "neutral", [fact(f"{top.name} in {label}", m(top.amount)), fact("Share of spending", f"{top.percent}%")])

    # Savings goals close to done.
    for g in dash.goals:
        if g.progress_percent >= 75:
            add(35, f"'{g.name}' is almost there",
                f"You've saved {m(g.current_amount)} of {m(g.target_amount)} ({g.progress_percent}%), {m(g.remaining_amount)} to go.",
                "positive", [fact(f"{g.name} saved", m(g.current_amount)), fact(f"{g.name} target", m(g.target_amount))])
            break

    out.sort(key=lambda c: -c.priority)
    return InsightsResponse(month=month, available=True, insights=[c.insight for c in out[:MAX_INSIGHTS]])
