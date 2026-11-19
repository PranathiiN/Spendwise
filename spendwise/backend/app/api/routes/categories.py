import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.utils import not_found
from app.core.dependencies import CurrentUser, DbSession
from app.models.category import Category
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.category_service import accessible_categories_filter, get_owned_category

router = APIRouter(prefix="/categories", tags=["categories"])


def _name_taken(
    db: Session, user_id: uuid.UUID, name: str, ttype: str, exclude_id: uuid.UUID | None = None
) -> bool:
    """A name must be unique (case-insensitive) among system + the user's own categories of a type."""
    stmt = select(Category.id).where(
        accessible_categories_filter(user_id),
        Category.transaction_type == ttype,
        func.lower(Category.name) == name.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    return db.scalar(stmt) is not None


@router.get("", response_model=list[CategoryRead])
def list_categories(
    current_user: CurrentUser,
    db: DbSession,
    transaction_type: TransactionType | None = Query(default=None),
) -> list[Category]:
    stmt = select(Category).where(accessible_categories_filter(current_user.id))
    if transaction_type is not None:
        stmt = stmt.where(Category.transaction_type == transaction_type.value)
    stmt = stmt.order_by(Category.transaction_type, Category.is_system.desc(), Category.name)
    return list(db.scalars(stmt).all())


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, current_user: CurrentUser, db: DbSession) -> Category:
    if _name_taken(db, current_user.id, payload.name, payload.transaction_type.value):
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    category = Category(
        user_id=current_user.id,
        name=payload.name,
        transaction_type=payload.transaction_type.value,
        color=payload.color,
        icon_name=payload.icon_name,
        is_system=False,
    )
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: uuid.UUID, payload: CategoryUpdate, current_user: CurrentUser, db: DbSession
) -> Category:
    category = get_owned_category(db, current_user.id, category_id)
    if category is None:
        # System categories and other users' categories are not editable.
        raise not_found("Category")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in data and _name_taken(
        db, current_user.id, data["name"], category.transaction_type, exclude_id=category.id
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "A category with this name already exists")
    for key, value in data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    category = get_owned_category(db, current_user.id, category_id)
    if category is None:
        raise not_found("Category")
    in_use = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.category_id == category.id)
    )
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This category is used by {in_use} transaction(s). Re-categorize them before deleting.",
        )
    db.delete(category)
    db.commit()
