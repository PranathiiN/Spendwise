"""SW-12: suggest a category for a new transaction - with SpendWise's own model.

Order of preference:
1. The user's own history - the category they last used for the same description.
2. SpendWise's own category model (naive Bayes trained on the user's transactions
   plus starter examples; see app/services/ml/category_model.py).

No outside AI is involved. The suggestion is never saved here; the user confirms it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.transaction import Transaction
from app.services.category_service import accessible_categories_filter
from app.services.ml.category_model import predict_category

Source = Literal["history", "model", "none"]
Confidence = Literal["low", "medium", "high"]


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


def suggest_category(
    db: Session,
    user_id: uuid.UUID,
    *,
    description: str,
    transaction_type: str,
    amount: Decimal | None = None,  # kept for the API; the model doesn't use it yet
    payment_method: str | None = None,
) -> tuple[Category | None, Source, Confidence | None]:
    """Return (category, source, confidence). Category is None when there's no suggestion."""
    description = description.strip()
    if not description:
        return None, "none", None

    remembered = _from_history(db, user_id, description, transaction_type)
    if remembered is not None:
        return remembered, "history", "high"

    prediction = predict_category(db, user_id, description, transaction_type, payment_method)
    if prediction is None:
        return None, "none", None
    return prediction.category, "model", prediction.confidence  # type: ignore[return-value]
