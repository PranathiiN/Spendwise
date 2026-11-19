import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.category import CategoryRead
from app.schemas.common import Money, MonthStr

BudgetStatus = Literal["ok", "warning", "exceeded"]


class BudgetCreate(BaseModel):
    category_id: uuid.UUID
    month: MonthStr = Field(description="YYYY-MM")
    amount: Money
    alert_threshold: int = Field(default=80, ge=1, le=100)


class BudgetUpdate(BaseModel):
    amount: Money | None = None
    alert_threshold: int | None = Field(default=None, ge=1, le=100)


class BudgetRead(BaseModel):
    id: uuid.UUID
    category: CategoryRead
    month: str
    amount: Decimal
    alert_threshold: int
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
    status: BudgetStatus
    created_at: datetime
    updated_at: datetime


class BudgetListResponse(BaseModel):
    month: str
    budgets: list[BudgetRead]
    total_budgeted: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    warning_count: int
    exceeded_count: int


class BudgetCopyResponse(BaseModel):
    month: str
    created: int
