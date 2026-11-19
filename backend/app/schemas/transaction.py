import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.models.enums import PaymentMethod, TransactionType
from app.schemas.category import CategoryRead
from app.schemas.common import Money

MIN_DATE = date(1970, 1, 1)
MAX_DATE = date(2100, 12, 31)


def _check_date(value: date) -> date:
    if not (MIN_DATE <= value <= MAX_DATE):
        raise ValueError("Date must be between 1970-01-01 and 2100-12-31")
    return value


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
TxDate = Annotated[date, AfterValidator(_check_date)]
OptionalNotes = Annotated[
    Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None,
    BeforeValidator(_blank_to_none),
]
OptionalPaymentMethod = Annotated[PaymentMethod | None, BeforeValidator(_blank_to_none)]


class TransactionCreate(BaseModel):
    category_id: uuid.UUID
    description: Description
    amount: Money
    transaction_type: TransactionType
    transaction_date: TxDate
    payment_method: OptionalPaymentMethod = None
    notes: OptionalNotes = None


class TransactionUpdate(BaseModel):
    """Partial update. Only fields present in the request body are changed."""

    category_id: uuid.UUID | None = None
    description: Description | None = None
    amount: Money | None = None
    transaction_type: TransactionType | None = None
    transaction_date: TxDate | None = None
    payment_method: OptionalPaymentMethod = None
    notes: OptionalNotes = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    category: CategoryRead
    description: str
    amount: Decimal
    transaction_type: TransactionType
    transaction_date: date
    payment_method: PaymentMethod | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionRead]
    total: int
    page: int
    page_size: int
    total_pages: int
    # Totals across ALL rows matching the filters (not just this page).
    total_income: Decimal = Field(default=Decimal("0.00"))
    total_expense: Decimal = Field(default=Decimal("0.00"))
