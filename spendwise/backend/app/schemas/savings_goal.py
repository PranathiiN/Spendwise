import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.common import HexColor, IconName, Money, NonNegativeMoney

GoalName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
GoalNotes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]
GoalStatus = Literal["active", "completed", "overdue"]


class SavingsGoalCreate(BaseModel):
    name: GoalName
    target_amount: Money
    current_amount: NonNegativeMoney = Decimal("0.00")
    target_date: date | None = None
    color: HexColor = "#10b981"
    icon_name: IconName = "piggy-bank"
    notes: GoalNotes | None = None


class SavingsGoalUpdate(BaseModel):
    name: GoalName | None = None
    target_amount: Money | None = None
    target_date: date | None = None
    color: HexColor | None = None
    icon_name: IconName | None = None
    notes: GoalNotes | None = None


class GoalContribution(BaseModel):
    amount: Money
    action: Literal["deposit", "withdraw"] = "deposit"


class SavingsGoalRead(BaseModel):
    id: uuid.UUID
    name: str
    target_amount: Decimal
    current_amount: Decimal
    remaining_amount: Decimal
    progress_percent: Decimal
    target_date: date | None
    days_remaining: int | None
    monthly_required: Decimal | None
    status: GoalStatus
    is_completed: bool
    color: str
    icon_name: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
