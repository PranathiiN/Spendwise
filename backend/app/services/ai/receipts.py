"""SW-16: read a receipt image or PDF and pre-fill a new expense.

Nothing is saved: the extracted fields go back to the form for the user to check.
The receipt file itself is not stored.
"""

from __future__ import annotations

import base64
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.ai import ReceiptScan
from app.schemas.category import CategoryRead
from app.schemas.transaction import MAX_DATE, MIN_DATE
from app.services.ai.client import structured_call
from app.services.category_service import accessible_categories_filter
from app.utils.money import money

MAX_BYTES = 5 * 1024 * 1024
AMOUNT_RE = re.compile(r"^\d{1,10}(\.\d{1,2})?$")
UNREADABLE = "Couldn't read this receipt. Try a clearer photo, or enter the details yourself."

SYSTEM_PROMPT = """You read shop and restaurant receipts and extract details for an expense tracker.

Extract:
- merchant: the shop or business name, short and in title case.
- date: the purchase date as YYYY-MM-DD, or "" if it isn't shown.
- total: the final amount paid (after tax and discounts) using only digits and an optional dot with up to 2 decimals, e.g. "1249.50". No currency symbols or thousands separators. "" if it isn't shown.
- currency: the 3-letter ISO currency code if you can tell, otherwise "".
- category_id: the best matching category from the list, or "none".
- readable: false if the image isn't a receipt or the total can't be read.

Never guess a total you can't read."""


class InvalidReceiptError(ValueError):
    pass


def detect_media_type(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data.startswith(b"%PDF"):
        return "application/pdf"
    raise InvalidReceiptError("Upload a JPEG, PNG, WebP or GIF image, or a PDF.")


def _parse_amount(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(",", "")
    if not AMOUNT_RE.match(text):
        return None
    try:
        amount = money(Decimal(text))
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def _parse_date(value: object) -> date | None:
    try:
        d = date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None
    return d if MIN_DATE <= d <= MAX_DATE else None


def scan_receipt(db: Session, user: User, data: bytes) -> ReceiptScan:
    if not data:
        raise InvalidReceiptError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise InvalidReceiptError("The file is too large. The limit is 5 MB.")
    media_type = detect_media_type(data)

    categories = db.scalars(
        select(Category)
        .where(accessible_categories_filter(user.id), Category.transaction_type == TransactionType.EXPENSE.value)
        .order_by(Category.name)
    ).all()
    by_id: dict[str, Category] = {str(c.id): c for c in categories}

    encoded = base64.standard_b64encode(data).decode("ascii")
    block_type = "document" if media_type == "application/pdf" else "image"
    content = [
        {"type": block_type, "source": {"type": "base64", "media_type": media_type, "data": encoded}},
        {
            "type": "text",
            "text": "Expense categories:\n" + "\n".join(f"- {cid}: {c.name}" for cid, c in by_id.items()),
        },
    ]
    schema = {
        "type": "object",
        "properties": {
            "readable": {"type": "boolean"},
            "merchant": {"type": "string"},
            "date": {"type": "string"},
            "total": {"type": "string"},
            "currency": {"type": "string"},
            "category_id": {"type": "string", "enum": [*by_id.keys(), "none"]},
        },
        "required": ["readable", "merchant", "date", "total", "currency", "category_id"],
        "additionalProperties": False,
    }
    result = structured_call(system=SYSTEM_PROMPT, content=content, schema=schema, max_tokens=4000, effort="low")

    amount = _parse_amount(result.get("total"))
    if not result.get("readable") or amount is None:
        return ReceiptScan(
            readable=False, merchant=None, transaction_date=None, amount=None, currency=None, category=None,
            message=UNREADABLE,
        )

    merchant = str(result.get("merchant") or "").strip()[:255] or None
    currency = str(result.get("currency") or "").strip().upper()[:3] or None
    category = by_id.get(str(result.get("category_id")))
    message = None
    if currency and currency != user.preferred_currency:
        message = (
            f"This receipt looks like it's in {currency}, but your currency is {user.preferred_currency}. "
            "Check the amount before saving."
        )
    return ReceiptScan(
        readable=True,
        merchant=merchant,
        transaction_date=_parse_date(result.get("date")),
        amount=amount,
        currency=currency,
        category=CategoryRead.model_validate(category) if category else None,
        message=message,
    )
