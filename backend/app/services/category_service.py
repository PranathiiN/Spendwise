import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.category import Category


def accessible_categories_filter(user_id: uuid.UUID):
    """SQL condition: system categories OR the user's own categories."""
    return or_(Category.is_system.is_(True), Category.user_id == user_id)


def get_accessible_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
    """Return the category only if it is a system category or belongs to this user."""
    return db.scalar(
        select(Category).where(Category.id == category_id, accessible_categories_filter(user_id))
    )


def get_owned_category(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
    """Return the category only if it is a custom category owned by this user."""
    return db.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.is_system.is_(False),
        )
    )
