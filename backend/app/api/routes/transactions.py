import math
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.utils import not_found, reject_nulls
from app.core.dependencies import CurrentUser, DbSession
from app.models.category import Category
from app.models.enums import PaymentMethod, TransactionType
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionRead,
    TransactionUpdate,
)
from app.services.category_service import get_accessible_category
from app.utils.money import ZERO, money

router = APIRouter(prefix="/transactions", tags=["transactions"])

SORT_COLUMNS = {
    "transaction_date": Transaction.transaction_date,
    "amount": Transaction.amount,
    "description": Transaction.description,
    "created_at": Transaction.created_at,
}


def _validate_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID, ttype: str) -> Category:
    category = get_accessible_category(db, user_id, category_id)
    if category is None:
        # Same message whether it doesn't exist or belongs to someone else.
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Category not found")
    if category.transaction_type != ttype:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Category '{category.name}' is for {category.transaction_type} transactions, "
            f"not {ttype}",
        )
    return category


def _get_owned_transaction(db: Session, user_id: uuid.UUID, transaction_id: uuid.UUID) -> Transaction:
    tx = db.scalar(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
    )
    if tx is None:
        raise not_found("Transaction")
    return tx


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: CurrentUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    transaction_type: TransactionType | None = None,
    category_id: uuid.UUID | None = None,
    payment_method: PaymentMethod | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    min_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    max_amount: Annotated[Decimal | None, Query(ge=0)] = None,
    sort_by: Literal["transaction_date", "amount", "description", "created_at"] = "transaction_date",
    sort_order: Literal["asc", "desc"] = "desc",
) -> TransactionListResponse:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "start_date must be on or before end_date")
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "min_amount must be <= max_amount")

    conditions = [Transaction.user_id == current_user.id]
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        conditions.append(
            or_(
                Transaction.description.ilike(pattern, escape="\\"),
                Transaction.notes.ilike(pattern, escape="\\"),
            )
        )
    if transaction_type is not None:
        conditions.append(Transaction.transaction_type == transaction_type.value)
    if category_id is not None:
        conditions.append(Transaction.category_id == category_id)
    if payment_method is not None:
        conditions.append(Transaction.payment_method == payment_method.value)
    if start_date is not None:
        conditions.append(Transaction.transaction_date >= start_date)
    if end_date is not None:
        conditions.append(Transaction.transaction_date <= end_date)
    if min_amount is not None:
        conditions.append(Transaction.amount >= min_amount)
    if max_amount is not None:
        conditions.append(Transaction.amount <= max_amount)

    total = db.scalar(select(func.count(Transaction.id)).where(*conditions)) or 0

    total_income = total_expense = ZERO
    for ttype, amount in db.execute(
        select(Transaction.transaction_type, func.sum(Transaction.amount))
        .where(*conditions)
        .group_by(Transaction.transaction_type)
    ).all():
        if ttype == TransactionType.INCOME.value:
            total_income = money(amount)
        else:
            total_expense = money(amount)

    sort_col = SORT_COLUMNS[sort_by]
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()
    items = db.scalars(
        select(Transaction)
        .where(*conditions)
        .order_by(order, Transaction.created_at.desc(), Transaction.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return TransactionListResponse(
        items=[TransactionRead.model_validate(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
        total_income=total_income,
        total_expense=total_expense,
    )


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(payload: TransactionCreate, current_user: CurrentUser, db: DbSession) -> TransactionRead:
    _validate_category(db, current_user.id, payload.category_id, payload.transaction_type.value)
    tx = Transaction(
        user_id=current_user.id,
        category_id=payload.category_id,
        description=payload.description,
        amount=payload.amount,
        transaction_type=payload.transaction_type.value,
        transaction_date=payload.transaction_date,
        payment_method=payload.payment_method.value if payload.payment_method else None,
        notes=payload.notes,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return TransactionRead.model_validate(tx)


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(transaction_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> TransactionRead:
    return TransactionRead.model_validate(_get_owned_transaction(db, current_user.id, transaction_id))


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: uuid.UUID, payload: TransactionUpdate, current_user: CurrentUser, db: DbSession
) -> TransactionRead:
    tx = _get_owned_transaction(db, current_user.id, transaction_id)
    data = payload.model_dump(exclude_unset=True)
    reject_nulls(data, ["category_id", "description", "amount", "transaction_type", "transaction_date"])

    new_type = data["transaction_type"].value if "transaction_type" in data else tx.transaction_type
    new_category_id = data.get("category_id", tx.category_id)
    new_category = None
    if "transaction_type" in data or "category_id" in data:
        new_category = _validate_category(db, current_user.id, new_category_id, new_type)

    for key, value in data.items():
        if key in ("transaction_type", "payment_method") and value is not None:
            value = value.value
        setattr(tx, key, value)
    if new_category is not None:
        tx.category = new_category  # keep the relationship in sync with category_id
    db.commit()
    db.refresh(tx)
    return TransactionRead.model_validate(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    tx = _get_owned_transaction(db, current_user.id, transaction_id)
    db.delete(tx)
    db.commit()
