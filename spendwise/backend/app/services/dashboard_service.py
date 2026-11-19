import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.dashboard import (
    BudgetSummary,
    CategoryBreakdownItem,
    DashboardResponse,
    GoalsSummary,
    MonthTotals,
    TrendPoint,
)
from app.schemas.transaction import TransactionRead
from app.services.budget_service import list_budgets_with_status
from app.services.goal_service import goal_to_read
from app.utils.dates import add_months, format_month, month_range
from app.utils.money import ZERO, money, percent, percent_change


def month_totals(db: Session, user_id: uuid.UUID, month_start: date) -> MonthTotals:
    start, end = month_range(month_start)
    rows = db.execute(
        select(Transaction.transaction_type, func.sum(Transaction.amount), func.count(Transaction.id))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .group_by(Transaction.transaction_type)
    ).all()
    income = expense = ZERO
    count = 0
    for ttype, total, n in rows:
        count += n
        if ttype == TransactionType.INCOME.value:
            income = money(total)
        else:
            expense = money(total)
    net = money(income - expense)
    return MonthTotals(
        income=income,
        expense=expense,
        net=net,
        savings_rate=percent(net, income) if income > 0 else Decimal("0.0"),
        transaction_count=count,
    )


def category_breakdown(
    db: Session, user_id: uuid.UUID, month_start: date, transaction_type: TransactionType
) -> list[CategoryBreakdownItem]:
    start, end = month_range(month_start)
    total_col = func.sum(Transaction.amount)
    rows = db.execute(
        select(
            Category.id,
            Category.name,
            Category.color,
            Category.icon_name,
            total_col,
            func.count(Transaction.id),
        )
        .select_from(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type.value,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .group_by(Category.id, Category.name, Category.color, Category.icon_name)
        .order_by(total_col.desc())
    ).all()
    grand_total = sum((money(r[4]) for r in rows), ZERO)
    return [
        CategoryBreakdownItem(
            category_id=cid,
            name=name,
            color=color,
            icon_name=icon,
            amount=money(total),
            percent=percent(money(total), grand_total),
            transaction_count=n,
        )
        for cid, name, color, icon, total, n in rows
    ]


def monthly_trend(db: Session, user_id: uuid.UUID, end_month: date, months: int = 6) -> list[TrendPoint]:
    first = add_months(end_month, -(months - 1))
    _, end = month_range(end_month)
    year_col = extract("year", Transaction.transaction_date)
    month_col = extract("month", Transaction.transaction_date)
    rows = db.execute(
        select(year_col, month_col, Transaction.transaction_type, func.sum(Transaction.amount))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= first,
            Transaction.transaction_date < end,
        )
        .group_by(year_col, month_col, Transaction.transaction_type)
    ).all()
    buckets: dict[tuple[int, int], dict[str, Decimal]] = {}
    for y, m, ttype, total in rows:
        buckets.setdefault((int(y), int(m)), {})[ttype] = money(total)

    points: list[TrendPoint] = []
    for i in range(months):
        m_start = add_months(first, i)
        data = buckets.get((m_start.year, m_start.month), {})
        income = data.get(TransactionType.INCOME.value, ZERO)
        expense = data.get(TransactionType.EXPENSE.value, ZERO)
        points.append(
            TrendPoint(
                month=format_month(m_start),
                label=m_start.strftime("%b %Y"),
                income=income,
                expense=expense,
                net=money(income - expense),
            )
        )
    return points


def recent_transactions(db: Session, user_id: uuid.UUID, limit: int = 5) -> list[TransactionRead]:
    txs = db.scalars(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(limit)
    ).all()
    return [TransactionRead.model_validate(t) for t in txs]


def build_dashboard(db: Session, user: User, month_start: date) -> DashboardResponse:
    totals = month_totals(db, user.id, month_start)
    previous = month_totals(db, user.id, add_months(month_start, -1))

    budgets = list_budgets_with_status(db, user.id, month_start)
    alerts = [b for b in budgets if b.status != "ok"]

    goals = [goal_to_read(g) for g in db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == user.id)).all()]
    active_goals = [g for g in goals if not g.is_completed]
    active_goals.sort(key=lambda g: (g.target_date is None, g.target_date or date.max, g.name.lower()))

    return DashboardResponse(
        month=format_month(month_start),
        currency=user.preferred_currency,
        totals=totals,
        previous_totals=previous,
        income_change_percent=percent_change(totals.income, previous.income),
        expense_change_percent=percent_change(totals.expense, previous.expense),
        expense_by_category=category_breakdown(db, user.id, month_start, TransactionType.EXPENSE),
        monthly_trend=monthly_trend(db, user.id, month_start, 6),
        recent_transactions=recent_transactions(db, user.id),
        budget_alerts=alerts,
        budget_summary=BudgetSummary(
            total_budgeted=money(sum((b.amount for b in budgets), ZERO)),
            total_spent=money(sum((b.spent for b in budgets), ZERO)),
            budget_count=len(budgets),
            warning_count=sum(1 for b in budgets if b.status == "warning"),
            exceeded_count=sum(1 for b in budgets if b.status == "exceeded"),
        ),
        goals=active_goals[:3],
        goals_summary=GoalsSummary(
            active_count=len(active_goals),
            completed_count=len(goals) - len(active_goals),
            total_saved=money(sum((g.current_amount for g in goals), ZERO)),
            total_target=money(sum((g.target_amount for g in goals), ZERO)),
        ),
    )
