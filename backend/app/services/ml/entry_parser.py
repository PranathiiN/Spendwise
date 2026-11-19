"""SW-22: SpendWise's own parser for quick add.

Turns "paid 450 for lunch at Swiggy yesterday on UPI" into fields without any
outside AI: rules for dates, amounts, income vs expense and payment method;
the category comes from the user's own category model. Anything ambiguous is
left blank for the user rather than guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from app.models.enums import PaymentMethod, TransactionType
from app.schemas.transaction import MAX_DATE, MIN_DATE
from app.utils.money import money

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DAYS_AGO_RE = re.compile(r"\b(\d+)\s+days?\s+ago\b", re.I)
DAY_MONTH_RE = re.compile(rf"\b(?:on\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_ALT})\b\.?(?:\s+(\d{{4}}))?", re.I)
MONTH_DAY_RE = re.compile(rf"\b(?:on\s+)?({MONTH_ALT})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?", re.I)
NUMERIC_DATE_RE = re.compile(r"\b(?:on\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
ISO_DATE_RE = re.compile(r"\b(?:on\s+)?(\d{4})-(\d{2})-(\d{2})\b")
RELATIVE_RE = re.compile(
    r"\b(?:day before yesterday|yesterday|today|this morning|this evening|tonight|last night)\b", re.I
)
WEEKDAY_RE = re.compile(rf"\b(?:on\s+)?(last\s+)?({'|'.join(WEEKDAYS)})\b", re.I)

CURRENCY = r"(?:rs\.?|inr|₹|rupees?)"
NUMBER = r"\d[\d,]*(?:\.\d+)?"
AMOUNT_RE = re.compile(rf"(?:{CURRENCY}\s*)?(?<![\w.])({NUMBER})(\s*k\b)?(?:\s*/-)?(?:\s*{CURRENCY})?", re.I)
MARKED_AMOUNT_RE = re.compile(rf"{CURRENCY}\s*({NUMBER})(\s*k\b)?|({NUMBER})(\s*k\b)?\s*(?:/-|{CURRENCY})", re.I)

INCOME_RE = re.compile(
    r"\b(salary|credited|received|receive|got paid|earned|refund(?:ed)?|cashback|dividend|interest|bonus|stipend|"
    r"income|freelance|paid me|sent me|gave me|reimburse(?:d|ment)?|sold)\b",
    re.I,
)

PAYMENT_PATTERNS: list[tuple[re.Pattern[str], PaymentMethod]] = [
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:upi|gpay|google pay|phone ?pe|bhim|paytm upi)\b", re.I), PaymentMethod.UPI),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:credit card|cc)\b", re.I), PaymentMethod.CREDIT_CARD),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:debit card|card)\b", re.I), PaymentMethod.DEBIT_CARD),
    (re.compile(r"\b(?:via|using|by|on|through|with|in)?\s*cash\b", re.I), PaymentMethod.CASH),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:net ?banking)\b", re.I), PaymentMethod.NET_BANKING),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:neft|imps|rtgs|bank transfer)\b", re.I), PaymentMethod.BANK_TRANSFER),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*(?:wallet|paytm wallet|amazon pay)\b", re.I), PaymentMethod.WALLET),
    (re.compile(r"\b(?:via|using|by|on|through|with)?\s*che(?:que|ck)\b", re.I), PaymentMethod.CHEQUE),
]

FILLER_RE = re.compile(
    r"\b(?:i|paid|pay|spent|spend|bought|got|for|of|rs|inr|rupees?|amount|received|credited|was|the)\b|₹|/-", re.I
)
SMALL_WORDS = {"at", "for", "from", "to", "and", "of", "in", "on", "with", "a", "an", "the"}


@dataclass
class ParsedEntry:
    transaction_type: TransactionType
    amount: Decimal | None
    transaction_date: date | None
    payment_method: PaymentMethod | None
    description: str
    spans: list[tuple[int, int]] = field(default_factory=list)


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        result = date(y, m, d)
    except ValueError:
        return None
    return result if MIN_DATE <= result <= MAX_DATE else None


def _year(explicit: str | None, month: int, day: int, today: date) -> int:
    if explicit:
        y = int(explicit)
        return y + 2000 if y < 100 else y
    # No year given: assume the most recent such date (transactions are usually in the past).
    candidate = _safe_date(today.year, month, day)
    return today.year - 1 if candidate and candidate > today else today.year


def find_date(text: str, today: date) -> tuple[date | None, tuple[int, int] | None]:
    """The date mentioned in the text and where it was found."""
    if m := DAYS_AGO_RE.search(text):
        n = int(m.group(1))
        return (today - timedelta(days=n), m.span()) if n <= 366 else (None, None)
    if m := RELATIVE_RE.search(text):
        word = m.group(0).lower()
        if word == "day before yesterday":
            return today - timedelta(days=2), m.span()
        if word in ("yesterday", "last night"):
            return today - timedelta(days=1), m.span()
        return today, m.span()
    if m := ISO_DATE_RE.search(text):
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m.span()
    if m := DAY_MONTH_RE.search(text):
        day, month = int(m.group(1)), MONTHS[m.group(2).lower()]
        return _safe_date(_year(m.group(3), month, day, today), month, day), m.span()
    if m := MONTH_DAY_RE.search(text):
        month, day = MONTHS[m.group(1).lower()], int(m.group(2))
        return _safe_date(_year(m.group(3), month, day, today), month, day), m.span()
    if m := NUMERIC_DATE_RE.search(text):  # Indian order: day/month(/year)
        day, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return _safe_date(_year(m.group(3), month, day, today), month, day), m.span()
    if m := WEEKDAY_RE.search(text):
        back = (today.weekday() - WEEKDAYS.index(m.group(2).lower())) % 7
        if m.group(1) and back == 0:
            back = 7
        return today - timedelta(days=back), m.span()
    return None, None


def _to_amount(raw: str, k: str | None) -> Decimal | None:
    try:
        value = Decimal(raw.replace(",", ""))
    except ArithmeticError:
        return None
    if k:
        value *= 1000
    value = money(value)
    return value if Decimal("0") < value < Decimal("10000000000") else None


def find_amount(text: str) -> tuple[Decimal | None, list[tuple[int, int]]]:
    """The amount, if it's unambiguous: a number marked with Rs/₹/rupees, or the only number."""
    marked = []
    for m in MARKED_AMOUNT_RE.finditer(text):
        value = _to_amount(m.group(1) or m.group(3), m.group(2) or m.group(4))
        if value is not None:
            marked.append((value, m.span()))
    if len({v for v, _ in marked}) == 1:
        return marked[0][0], [s for _, s in marked]

    found = []
    for m in AMOUNT_RE.finditer(text):
        value = _to_amount(m.group(1), m.group(2))
        if value is not None:
            found.append((value, m.span()))
    if len({v for v, _ in found}) == 1:
        return found[0][0], [s for _, s in found]
    return None, []


def find_payment_method(text: str) -> tuple[PaymentMethod | None, tuple[int, int] | None]:
    for pattern, method in PAYMENT_PATTERNS:
        if m := pattern.search(text):
            return method, m.span()
    return None, None


def _blank(text: str, spans: list[tuple[int, int]]) -> str:
    chars = list(text)
    for start, end in spans:
        for i in range(start, end):
            chars[i] = " "
    return "".join(chars)


def _title(text: str) -> str:
    parts = text.split()
    return " ".join(
        p.lower() if i and p.lower() in SMALL_WORDS else (p if any(c.isupper() for c in p[1:]) else p.capitalize())
        for i, p in enumerate(parts)
    )


def parse_entry(text: str, today: date) -> ParsedEntry:
    text = " ".join(text.split())
    tx_date, date_span = find_date(text, today)
    without_date = _blank(text, [date_span]) if date_span else text

    amount, amount_spans = find_amount(without_date)
    method, method_span = find_payment_method(without_date)
    ttype = TransactionType.INCOME if INCOME_RE.search(text) else TransactionType.EXPENSE

    spans = [s for s in [date_span, method_span, *amount_spans] if s]
    rest = FILLER_RE.sub(" ", _blank(text, spans))
    rest = re.sub(r"[^\w&'\- ]+", " ", rest)
    rest = re.sub(r"^(?:\s*(?:at|on|in|to|from|and|via|by)\b)+|(?:\b(?:at|on|in|to|from|and|via|by)\s*)+$", " ", rest.strip(), flags=re.I)
    description = _title(" ".join(rest.split()))[:255]

    return ParsedEntry(ttype, amount, tx_date, method, description, spans)
