import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.budget import BudgetListResponse, BudgetRead, BudgetStatus
from app.schemas.category import CategoryRead
from app.utils.dates import add_months, format_month, month_range
from app.utils.money import ZERO, money, percent


def expense_spending_by_category(
    db: Session, user_id: uuid.UUID, month_start: date
) -> dict[uuid.UUID, Decimal]:
    """Total expense per category for the user in the given month."""
    start, end = month_range(month_start)
    rows = db.execute(
        select(Transaction.category_id, func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE.value,
            Transaction.transaction_date >= start,
            Transaction.transaction_date < end,
        )
        .group_by(Transaction.category_id)
    ).all()
    return {category_id: money(total) for category_id, total in rows}


def compute_status(amount: Decimal, spent: Decimal, threshold: int) -> tuple[Decimal, Decimal, BudgetStatus]:
    """Return (remaining, percent_used, status).

    - exceeded: spent is strictly greater than the limit
    - warning:  spent has reached the alert threshold (including exactly at the limit)
    - ok:       otherwise
    """
    remaining = money(amount - spent)
    pct = percent(spent, amount)
    if spent > amount:
        status: BudgetStatus = "exceeded"
    elif pct >= Decimal(threshold):
        status = "warning"
    else:
        status = "ok"
    return remaining, pct, status


def budget_to_read(budget: Budget, spent: Decimal) -> BudgetRead:
    remaining, pct, status = compute_status(budget.amount, spent, budget.alert_threshold)
    return BudgetRead(
        id=budget.id,
        category=CategoryRead.model_validate(budget.category),
        month=format_month(budget.month),
        amount=money(budget.amount),
        alert_threshold=budget.alert_threshold,
        spent=money(spent),
        remaining=remaining,
        percent_used=pct,
        status=status,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def list_budgets_with_status(db: Session, user_id: uuid.UUID, month_start: date) -> list[BudgetRead]:
    budgets = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == month_start)
    ).all()
    spending = expense_spending_by_category(db, user_id, month_start)
    result = [budget_to_read(b, spending.get(b.category_id, ZERO)) for b in budgets]
    # Most urgent first, then by name.
    order = {"exceeded": 0, "warning": 1, "ok": 2}
    result.sort(key=lambda b: (order[b.status], b.category.name.lower()))
    return result


def build_budget_list_response(month_start: date, budgets: list[BudgetRead]) -> BudgetListResponse:
    total_budgeted = money(sum((b.amount for b in budgets), ZERO))
    total_spent = money(sum((b.spent for b in budgets), ZERO))
    return BudgetListResponse(
        month=format_month(month_start),
        budgets=budgets,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=money(total_budgeted - total_spent),
        warning_count=sum(1 for b in budgets if b.status == "warning"),
        exceeded_count=sum(1 for b in budgets if b.status == "exceeded"),
    )


def copy_budgets_from_previous_month(db: Session, user_id: uuid.UUID, month_start: date) -> int:
    """Copy last month's budgets into month_start, skipping categories that already have one."""
    previous = add_months(month_start, -1)
    prev_budgets = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == previous)
    ).all()
    existing = set(
        db.scalars(
            select(Budget.category_id).where(Budget.user_id == user_id, Budget.month == month_start)
        ).all()
    )
    created = 0
    for b in prev_budgets:
        if b.category_id in existing:
            continue
        db.add(
            Budget(
                user_id=user_id,
                category_id=b.category_id,
                month=month_start,
                amount=b.amount,
                alert_threshold=b.alert_threshold,
            )
        )
        created += 1
    db.commit()
    return created
