"""SW-13: plain-language monthly spending insights.

The backend computes every figure (using the same services as the dashboard and
reports), labels each one as a fact with an id, and asks Claude only to write
short observations that cite those fact ids. The cited facts are attached to
each insight from our own numbers, so what the user sees always matches the
rest of the app.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.ai import Insight, InsightFact, InsightsResponse
from app.services.ai.client import structured_call
from app.services.dashboard_service import build_dashboard, category_breakdown
from app.services.forecast_service import build_forecast
from app.utils.dates import add_months, format_month, month_range
from app.utils.money import money

MIN_TRANSACTIONS = 5
UNUSUAL_MULTIPLIER = Decimal("2")
CACHE_SIZE = 256

SYSTEM_PROMPT = """You write short, friendly observations about one person's monthly finances for a personal finance app.

Rules:
- Write 3 to 5 insights. Each has a short title (under 60 characters) and a body of 1-2 sentences.
- Base every insight only on the facts provided, and list the ids of the facts it relies on in fact_ids.
- When you mention a figure, copy it exactly as written in the facts. Never calculate new numbers, round, or estimate.
- Prefer what is most useful: big changes from last month, unusual transactions, budgets near or over their limit, savings-goal progress, and forecasts.
- tone is "warning" for something that needs attention, "positive" for good news, otherwise "neutral".
- Be concrete and non-judgemental. No generic financial advice."""

_cache: OrderedDict[tuple[uuid.UUID, str, str], InsightsResponse] = OrderedDict()
_cache_lock = Lock()


class _Facts:
    def __init__(self, currency: str) -> None:
        self.currency = currency
        self.items: dict[str, InsightFact] = {}

    def money(self, fid: str, label: str, value: Decimal) -> None:
        self.add(fid, label, f"{self.currency} {money(value):,.2f}")

    def add(self, fid: str, label: str, value: str) -> None:
        self.items[fid] = InsightFact(id=fid, label=label, value=value)


def _pct(value: Decimal | None) -> str:
    return "n/a" if value is None else f"{value:+.1f}%"


def _unusual_transactions(db: Session, user_id: uuid.UUID, month_start: date) -> list[tuple[Transaction, Decimal]]:
    """Expenses this month at least 2x the category's average transaction over the previous 3 months."""
    start, end = month_range(month_start)
    hist_start = add_months(month_start, -3)
    averages = dict(
        db.execute(
            select(Transaction.category_id, func.avg(Transaction.amount))
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE.value,
                Transaction.transaction_date >= hist_start,
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
    unusual = []
    for tx in txs:
        avg = averages.get(tx.category_id)
        if avg and tx.amount >= Decimal(avg) * UNUSUAL_MULTIPLIER:
            unusual.append((tx, money(avg)))
    return unusual[:3]


def build_facts(db: Session, user: User, month_start: date, today: date | None = None) -> tuple[_Facts, int]:
    """Return the labelled facts for the month and the month's transaction count."""
    dash = build_dashboard(db, user, month_start)
    facts = _Facts(dash.currency)
    t, prev = dash.totals, dash.previous_totals
    label = month_start.strftime("%B %Y")
    prev_label = add_months(month_start, -1).strftime("%B %Y")

    facts.money("expense_total", f"Total spending in {label}", t.expense)
    facts.money("income_total", f"Total income in {label}", t.income)
    facts.money("net", f"Net (income minus spending) in {label}", t.net)
    facts.add("savings_rate", f"Savings rate in {label}", f"{t.savings_rate}%")
    facts.money("prev_expense_total", f"Total spending in {prev_label}", prev.expense)
    facts.add("expense_change", f"Change in spending vs {prev_label}", _pct(dash.expense_change_percent))
    facts.add("income_change", f"Change in income vs {prev_label}", _pct(dash.income_change_percent))

    prev_by_cat = {
        c.category_id: c.amount
        for c in category_breakdown(db, user.id, add_months(month_start, -1), TransactionType.EXPENSE)
    }
    for i, c in enumerate(dash.expense_by_category[:5], start=1):
        facts.money(f"cat{i}_amount", f"Spending on {c.name} in {label}", c.amount)
        facts.add(f"cat{i}_share", f"{c.name} share of total spending", f"{c.percent}%")
        before = prev_by_cat.get(c.category_id)
        if before:
            facts.money(f"cat{i}_prev", f"Spending on {c.name} in {prev_label}", before)

    for i, (tx, avg) in enumerate(_unusual_transactions(db, user.id, month_start), start=1):
        facts.money(
            f"unusual{i}",
            f"Unusually large {tx.category.name} expense on {tx.transaction_date:%d %b}: {tx.description}",
            tx.amount,
        )
        facts.money(f"unusual{i}_avg", f"Usual {tx.category.name} expense (3-month average)", avg)

    for i, b in enumerate(dash.budget_alerts[:5], start=1):
        state = "over budget" if b.status == "exceeded" else "near its limit"
        facts.add(
            f"budget{i}",
            f"{b.category.name} budget ({state})",
            f"{facts.currency} {b.spent:,.2f} spent of {facts.currency} {b.amount:,.2f} ({b.percent_used}% used)",
        )

    for i, g in enumerate(dash.goals, start=1):
        facts.add(
            f"goal{i}",
            f"Savings goal '{g.name}' progress",
            f"{facts.currency} {g.current_amount:,.2f} of {facts.currency} {g.target_amount:,.2f} ({g.progress_percent}%)",
        )

    forecast = build_forecast(db, user, month_start, today)
    if forecast.available:
        facts.money("forecast_expense", f"Projected total spending for {label} (estimate)", forecast.projected_expense)
        for i, w in enumerate(forecast.budget_warnings[:3], start=1):
            facts.add(
                f"forecast_budget{i}",
                f"{w.name} forecast vs budget (estimate)",
                f"{facts.currency} {w.projected:,.2f} projected vs {facts.currency} {w.budget:,.2f} budget",
            )

    return facts, t.transaction_count


def _facts_key(facts: _Facts) -> str:
    raw = json.dumps([f.model_dump() for f in facts.items.values()], sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_insights(db: Session, user: User, month_start: date, today: date | None = None) -> InsightsResponse:
    month = format_month(month_start)
    facts, count = build_facts(db, user, month_start, today)
    if count < MIN_TRANSACTIONS:
        return InsightsResponse(
            month=month,
            available=False,
            reason=f"Add at least {MIN_TRANSACTIONS} transactions this month to get insights.",
        )

    key = (user.id, month, _facts_key(facts))
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    fact_lines = "\n".join(f"- [{f.id}] {f.label}: {f.value}" for f in facts.items.values())
    schema = {
        "type": "object",
        "properties": {
            "insights": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "tone": {"type": "string", "enum": ["positive", "neutral", "warning"]},
                        "fact_ids": {"type": "array", "items": {"type": "string", "enum": list(facts.items)}},
                    },
                    "required": ["title", "body", "tone", "fact_ids"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["insights"],
        "additionalProperties": False,
    }
    data = structured_call(
        system=SYSTEM_PROMPT,
        content=f"Facts for {month_start:%B %Y}:\n{fact_lines}",
        schema=schema,
        max_tokens=8000,
        effort="medium",
    )

    insights: list[Insight] = []
    for item in data.get("insights", [])[:5]:
        cited = [facts.items[fid] for fid in dict.fromkeys(item.get("fact_ids", [])) if fid in facts.items]
        title, body = str(item.get("title", "")).strip(), str(item.get("body", "")).strip()
        if not cited or not title or not body:
            continue  # every insight must be backed by our own figures
        tone = item.get("tone") if item.get("tone") in ("positive", "neutral", "warning") else "neutral"
        insights.append(Insight(title=title[:120], body=body[:600], tone=tone, facts=cited))

    result = InsightsResponse(month=month, available=True, insights=insights)
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return result
