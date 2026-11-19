import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.utils import not_found, reject_nulls
from app.core.dependencies import CurrentUser, DbSession, MonthParam
from app.models.budget import Budget
from app.models.enums import TransactionType
from app.schemas.budget import (
    BudgetCopyResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetRead,
    BudgetUpdate,
)
from app.services.budget_service import (
    budget_to_read,
    build_budget_list_response,
    copy_budgets_from_previous_month,
    expense_spending_by_category,
    list_budgets_with_status,
)
from app.services.category_service import get_accessible_category
from app.utils.dates import format_month, parse_month
from app.utils.money import ZERO

router = APIRouter(prefix="/budgets", tags=["budgets"])


def _get_owned_budget(db, user_id: uuid.UUID, budget_id: uuid.UUID) -> Budget:
    budget = db.scalar(select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id))
    if budget is None:
        raise not_found("Budget")
    return budget


def _read_with_spending(db, budget: Budget) -> BudgetRead:
    spending = expense_spending_by_category(db, budget.user_id, budget.month)
    return budget_to_read(budget, spending.get(budget.category_id, ZERO))


@router.get("", response_model=BudgetListResponse)
def list_budgets(month: MonthParam, current_user: CurrentUser, db: DbSession) -> BudgetListResponse:
    budgets = list_budgets_with_status(db, current_user.id, month)
    return build_budget_list_response(month, budgets)


@router.post("", response_model=BudgetRead, status_code=status.HTTP_201_CREATED)
def create_budget(payload: BudgetCreate, current_user: CurrentUser, db: DbSession) -> BudgetRead:
    category = get_accessible_category(db, current_user.id, payload.category_id)
    if category is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category not found")
    if category.transaction_type != TransactionType.EXPENSE.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Budgets can only be set for expense categories")

    month_start = parse_month(payload.month)
    duplicate = db.scalar(
        select(Budget.id).where(
            Budget.user_id == current_user.id,
            Budget.category_id == category.id,
            Budget.month == month_start,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A budget for '{category.name}' already exists for {format_month(month_start)}",
        )

    budget = Budget(
        user_id=current_user.id,
        category_id=category.id,
        month=month_start,
        amount=payload.amount,
        alert_threshold=payload.alert_threshold,
    )
    db.add(budget)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A budget for this category and month already exists")
    db.refresh(budget)
    return _read_with_spending(db, budget)


@router.post("/copy-previous", response_model=BudgetCopyResponse)
def copy_previous_month(month: MonthParam, current_user: CurrentUser, db: DbSession) -> BudgetCopyResponse:
    created = copy_budgets_from_previous_month(db, current_user.id, month)
    return BudgetCopyResponse(month=format_month(month), created=created)


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget(budget_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> BudgetRead:
    return _read_with_spending(db, _get_owned_budget(db, current_user.id, budget_id))


@router.patch("/{budget_id}", response_model=BudgetRead)
def update_budget(
    budget_id: uuid.UUID, payload: BudgetUpdate, current_user: CurrentUser, db: DbSession
) -> BudgetRead:
    budget = _get_owned_budget(db, current_user.id, budget_id)
    data = payload.model_dump(exclude_unset=True)
    reject_nulls(data, ["amount", "alert_threshold"])
    for key, value in data.items():
        setattr(budget, key, value)
    db.commit()
    db.refresh(budget)
    return _read_with_spending(db, budget)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(budget_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    budget = _get_owned_budget(db, current_user.id, budget_id)
    db.delete(budget)
    db.commit()
