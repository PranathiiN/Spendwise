"""SW-12: suggest a category for a new transaction.

Order of preference:
1. The user's own history - the category they last used for the same description
   (so corrections are learned without calling the AI).
2. Claude, given the user's categories of the right type plus recent examples.

The suggestion is never saved here; the user confirms it in the form.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.ai.client import AIRequestError, AIUnavailableError, structured_call
from app.services.category_service import accessible_categories_filter

Source = Literal["history", "ai", "none"]
Confidence = Literal["low", "medium", "high"]

NONE_ID = "none"
EXAMPLE_LIMIT = 40

SYSTEM_PROMPT = """You categorise personal finance transactions for one user.

You get the user's categories (id and name) and some of their past transactions with the category they chose. Pick the single best category for the new transaction. Follow the user's own past choices when a similar description appears. If no category is a reasonable fit, answer "none".

Confidence: "high" when the description clearly matches, "medium" when it's a sensible guess, "low" when you're unsure."""


def _normalise(description: str) -> str:
    return " ".join(description.lower().split())


def _from_history(db: Session, user_id: uuid.UUID, description: str, ttype: str) -> Category | None:
    """Category of the user's most recent transaction with the same description and type."""
    tx = db.scalar(
        select(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == ttype,
            func.lower(func.trim(Transaction.description)) == _normalise(description),
            accessible_categories_filter(user_id),
        )
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(1)
    )
    return tx.category if tx else None


def _recent_examples(db: Session, user_id: uuid.UUID, ttype: str) -> list[tuple[str, str]]:
    rows = db.execute(
        select(Transaction.description, Category.name)
        .join(Category, Transaction.category_id == Category.id)
        .where(Transaction.user_id == user_id, Transaction.transaction_type == ttype)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(EXAMPLE_LIMIT)
    ).all()
    return [(d, c) for d, c in rows]


def suggest_category(
    db: Session,
    user_id: uuid.UUID,
    *,
    description: str,
    transaction_type: str,
    amount: Decimal | None = None,
    payment_method: str | None = None,
) -> tuple[Category | None, Source, Confidence | None]:
    """Return (category, source, confidence). Category is None when there's no suggestion."""
    description = description.strip()
    if not description:
        return None, "none", None

    remembered = _from_history(db, user_id, description, transaction_type)
    if remembered is not None:
        return remembered, "history", "high"

    categories = db.scalars(
        select(Category)
        .where(accessible_categories_filter(user_id), Category.transaction_type == transaction_type)
        .order_by(Category.name)
    ).all()
    if not categories:
        return None, "none", None
    by_id = {str(c.id): c for c in categories}

    lines = ["Categories:"]
    lines += [f"- {c.id}: {c.name}" for c in categories]
    examples = _recent_examples(db, user_id, transaction_type)
    if examples:
        lines.append("\nPast transactions (description -> category):")
        lines += [f"- {d} -> {c}" for d, c in examples]
    lines.append(f"\nNew {transaction_type} transaction:")
    lines.append(f"- Description: {description}")
    if amount is not None:
        lines.append(f"- Amount: {amount}")
    if payment_method:
        lines.append(f"- Payment method: {payment_method}")

    schema = {
        "type": "object",
        "properties": {
            "category_id": {"type": "string", "enum": [*by_id.keys(), NONE_ID]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["category_id", "confidence"],
        "additionalProperties": False,
    }
    try:
        result = structured_call(system=SYSTEM_PROMPT, content="\n".join(lines), schema=schema)
    except (AIUnavailableError, AIRequestError):
        # Suggestions are optional: the form still works without them.
        return None, "none", None

    category = by_id.get(str(result.get("category_id")))  # rejects "none" and anything unexpected
    if category is None:
        return None, "none", None
    confidence = result.get("confidence")
    return category, "ai", confidence if confidence in ("low", "medium", "high") else "low"
