"""Validate values that come back from an LLM before they reach a form."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.schemas.transaction import MAX_DATE, MIN_DATE
from app.utils.money import money

AMOUNT_RE = re.compile(r"^\d{1,10}(\.\d{1,2})?$")


def parse_amount(value: object) -> Decimal | None:
    """A positive amount with at most 2 decimals ("1,249.5" -> 1249.50), else None. Never a float."""
    text = str(value or "").strip().replace(",", "")
    if not AMOUNT_RE.match(text):
        return None
    try:
        amount = money(Decimal(text))
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def parse_date(value: object) -> date | None:
    try:
        d = date.fromisoformat(str(value or "").strip())
    except ValueError:
        return None
    return d if MIN_DATE <= d <= MAX_DATE else None
