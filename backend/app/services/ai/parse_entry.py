"""SW-22: natural-language transaction entry - with SpendWise's own parser and model.

"paid 450 for lunch at Swiggy yesterday on UPI" -> a pre-filled add-transaction form.

- Amount, date, income/expense and payment method: our own rules
  (app/services/ml/entry_parser.py). An ambiguous amount is left blank.
- Category: the user's history for the same description, else our own
  category model trained on their transactions.
- No date mentioned -> today. Nothing is saved; the user reviews the form.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.ai import ParsedTransaction
from app.schemas.category import CategoryRead
from app.services.ai.categorize import suggest_category
from app.services.ml.entry_parser import parse_entry


def parse_transaction(db: Session, user: User, text: str, today: date | None = None) -> ParsedTransaction:
    today = today or date.today()
    entry = parse_entry(text, today)
    description = entry.description or " ".join(text.split())[:255]

    category, _, _ = suggest_category(
        db,
        user.id,
        description=description,
        transaction_type=entry.transaction_type.value,
        payment_method=entry.payment_method.value if entry.payment_method else None,
    )
    missing = [name for name, value in (("amount", entry.amount), ("category", category)) if value is None]
    return ParsedTransaction(
        transaction_type=entry.transaction_type,
        amount=entry.amount,
        description=description,
        transaction_date=entry.transaction_date or today,
        category=CategoryRead.model_validate(category) if category else None,
        payment_method=entry.payment_method,
        missing=missing,
    )
