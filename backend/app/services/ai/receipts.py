"""SW-16: read a receipt image (or a PDF, where the provider supports it) and pre-fill a new expense.

Nothing is saved: the extracted fields go back to the form for the user to check.
The receipt file itself is not stored.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.user import User
from app.schemas.ai import ReceiptScan
from app.schemas.category import CategoryRead
from app.services.ai.categories import category_choices, enum_of, pick
from app.services.ai.client import Image, require_provider
from app.services.ai.validation import parse_amount, parse_date

MAX_BYTES = 5 * 1024 * 1024
UNREADABLE = "Couldn't read this receipt. Try a clearer photo, or enter the details yourself."

SYSTEM_PROMPT = """You read shop and restaurant receipts and extract details for an expense tracker.

Extract:
- merchant: the shop or business name, short and in title case.
- date: the purchase date as YYYY-MM-DD, or "" if it isn't shown.
- total: the final amount paid (after tax and discounts) using only digits and an optional dot with up to 2 decimals, e.g. "1249.50". No currency symbols or thousands separators. "" if it isn't shown.
- currency: the 3-letter ISO currency code if you can tell, otherwise "".
- category: the best matching category from the list, or "none".
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


def scan_receipt(db: Session, user: User, data: bytes) -> ReceiptScan:
    if not data:
        raise InvalidReceiptError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise InvalidReceiptError("The file is too large. The limit is 5 MB.")
    media_type = detect_media_type(data)

    provider = require_provider()
    if media_type == "application/pdf" and not provider.supports_pdf:
        raise InvalidReceiptError("The local AI model can't read PDFs. Upload a photo or screenshot of the receipt.")

    choices = category_choices(db, user.id, TransactionType.EXPENSE.value)
    schema = {
        "type": "object",
        "properties": {
            "readable": {"type": "boolean"},
            "merchant": {"type": "string"},
            "date": {"type": "string"},
            "total": {"type": "string"},
            "currency": {"type": "string"},
            "category": {"type": "string", "enum": enum_of(choices)},
        },
        "required": ["readable", "merchant", "date", "total", "currency", "category"],
        "additionalProperties": False,
    }
    result = provider.structured(
        system=SYSTEM_PROMPT,
        prompt="Expense categories: " + ", ".join(choices),
        schema=schema,
        images=[Image(media_type, data)],
        max_tokens=1000,
        effort="low",
    )

    amount = parse_amount(result.get("total"))
    if not result.get("readable") or amount is None:
        return ReceiptScan(
            readable=False, merchant=None, transaction_date=None, amount=None, currency=None, category=None,
            message=UNREADABLE,
        )

    merchant = str(result.get("merchant") or "").strip()[:255] or None
    currency = str(result.get("currency") or "").strip().upper()[:3] or None
    category = pick(choices, result.get("category"))
    message = None
    if currency and currency != user.preferred_currency:
        message = (
            f"This receipt looks like it's in {currency}, but your currency is {user.preferred_currency}. "
            "Check the amount before saving."
        )
    return ReceiptScan(
        readable=True,
        merchant=merchant,
        transaction_date=parse_date(result.get("date")),
        amount=amount,
        currency=currency,
        category=CategoryRead.model_validate(category) if category else None,
        message=message,
    )
