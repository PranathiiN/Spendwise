"""Category choices offered to the LLM.

Models are given category *names* (small local models pick names far more
reliably than IDs). The structured-output schema limits the answer to these
names, and the name is mapped back to the user's own Category here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.services.category_service import accessible_categories_filter

NONE = "none"


def category_choices(db: Session, user_id: uuid.UUID, transaction_type: str) -> dict[str, Category]:
    """Categories the user may use for this type, keyed by name.

    If a custom category has the same name as a system one, the custom one wins.
    """
    rows = db.scalars(
        select(Category)
        .where(accessible_categories_filter(user_id), Category.transaction_type == transaction_type)
        .order_by(Category.is_system.desc(), Category.name)  # custom last so it overrides
    ).all()
    choices: dict[str, Category] = {}
    for c in rows:
        choices[c.name] = c
    return dict(sorted(choices.items(), key=lambda kv: kv[0].lower()))


def pick(choices: dict[str, Category], answer: object) -> Category | None:
    """Map the model's answer back to a Category (case-insensitive); None for 'none' or unknown."""
    if not isinstance(answer, str):
        return None
    if answer in choices:
        return choices[answer]
    lowered = answer.strip().lower()
    for name, cat in choices.items():
        if name.lower() == lowered:
            return cat
    return None


def enum_of(choices: dict[str, Category]) -> list[str]:
    return [*choices.keys(), NONE]
