import csv
import io
import uuid
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.report import DailyPoint, MonthlyReport
from app.schemas.transaction import TransactionRead
from app.services.budget_service import list_budgets_with_status
from app.services.dashboard_service import category_breakdown, month_totals, monthly_trend
from app.utils.dates import add_months, days_in_month, format_month, iter_days, month_range
from app.utils.money import CENT, ZERO, money, percent_change


def daily_series(db: Session, user_id: uuid.UUID, month_start: date) -> list[DailyPoint]:
    start, end = month_range(month_start)
    rows = db.execute(
        select(Transaction.transaction_date, Transaction.transaction_type, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .group_by(Transaction.transaction_date, Transaction.transaction_type)
    ).all()
    by_day: dict[date, dict[str, Decimal]] = {}
    for d, ttype, total in rows:
        by_day.setdefault(d, {})[ttype] = money(total)

    points: list[DailyPoint] = []
    cumulative = ZERO
    for d in iter_days(start, end):
        data = by_day.get(d, {})
        expense = data.get(TransactionType.EXPENSE.value, ZERO)
        cumulative = money(cumulative + expense)
        points.append(
            DailyPoint(
                date=d,
                income=data.get(TransactionType.INCOME.value, ZERO),
                expense=expense,
                cumulative_expense=cumulative,
            )
        )
    return points


def _elapsed_days(month_start: date, today: date) -> int:
    """Days to average over: full month in the past, days so far in the current month."""
    start, end = month_range(month_start)
    if today >= end:
        return days_in_month(month_start)
    if today < start:
        return days_in_month(month_start)
    return (today - start).days + 1


def build_monthly_report(db: Session, user: User, month_start: date, today: date | None = None) -> MonthlyReport:
    today = today or date.today()
    totals = month_totals(db, user.id, month_start)
    previous = month_totals(db, user.id, add_months(month_start, -1))
    daily = daily_series(db, user.id, month_start)

    start, end = month_range(month_start)
    top = db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user.id,
            Transaction.transaction_type == TransactionType.EXPENSE.value,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .order_by(Transaction.amount.desc(), Transaction.transaction_date.desc())
        .limit(5)
    ).all()

    elapsed = _elapsed_days(month_start, today)
    avg_daily = (totals.expense / Decimal(elapsed)).quantize(CENT, rounding=ROUND_HALF_UP) if elapsed else ZERO
    highest = max((p for p in daily if p.expense > 0), key=lambda p: p.expense, default=None)

    return MonthlyReport(
        month=format_month(month_start),
        label=month_start.strftime("%B %Y"),
        currency=user.preferred_currency,
        totals=totals,
        previous_totals=previous,
        income_change_percent=percent_change(totals.income, previous.income),
        expense_change_percent=percent_change(totals.expense, previous.expense),
        income_by_category=category_breakdown(db, user.id, month_start, TransactionType.INCOME),
        expense_by_category=category_breakdown(db, user.id, month_start, TransactionType.EXPENSE),
        daily=daily,
        top_expenses=[TransactionRead.model_validate(t) for t in top],
        budgets=list_budgets_with_status(db, user.id, month_start),
        average_daily_expense=avg_daily,
        highest_expense_day=highest,
        six_month_trend=monthly_trend(db, user.id, month_start, 6),
    )


_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value: str | None) -> str:
    """Prevent CSV/spreadsheet formula injection for user-provided text."""
    if not value:
        return ""
    return "'" + value if value.startswith(_FORMULA_PREFIXES) else value


def export_month_csv(db: Session, user_id: uuid.UUID, month_start: date) -> str:
    start, end = month_range(month_start)
    txs = db.scalars(
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .order_by(Transaction.transaction_date, Transaction.created_at)
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Type", "Category", "Description", "Amount", "Payment Method", "Notes"])
    for t in txs:
        writer.writerow(
            [
                t.transaction_date.isoformat(),
                t.transaction_type,
                _safe_cell(t.category.name),
                _safe_cell(t.description),
                str(money(t.amount)),
                t.payment_method or "",
                _safe_cell(t.notes),
            ]
        )
    return buffer.getvalue()
