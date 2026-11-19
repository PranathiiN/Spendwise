"""Schemas for the phase 2 AI features (SW-12 to SW-16)."""

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated

from app.models.enums import PaymentMethod, TransactionType
from app.schemas.budget import BudgetStatus
from app.schemas.category import CategoryRead
from app.schemas.common import NonNegativeMoney


class AIStatus(BaseModel):
    # SpendWise's own models (categories, quick add, insights, assistant) - always available.
    enabled: bool
    # Receipt scanning needs an optional LLM provider (AI_PROVIDER=ollama or anthropic).
    receipt_scanning: bool
    provider: Literal["ollama", "anthropic", "off"]
    model: str | None
    message: str | None = None  # why receipt scanning is unavailable, if it is


# --- SW-22 natural-language entry -----------------------------------------------------


class ParseRequest(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ParsedTransaction(BaseModel):
    transaction_type: TransactionType
    amount: Decimal | None  # serialized as a 2-decimal string
    description: str
    transaction_date: date | None
    category: CategoryRead | None
    payment_method: PaymentMethod | None
    missing: list[str]  # fields left blank for the user to fill in


# --- SW-12 categorisation -------------------------------------------------------------


class CategorySuggestionRequest(BaseModel):
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    transaction_type: TransactionType
    amount: NonNegativeMoney | None = None
    payment_method: PaymentMethod | None = None


class CategorySuggestion(BaseModel):
    category: CategoryRead | None
    source: Literal["history", "model", "none"]
    confidence: Literal["low", "medium", "high"] | None


# --- SW-15 forecasting ----------------------------------------------------------------


class CategoryForecast(BaseModel):
    category_id: uuid.UUID
    name: str
    color: str
    spent: Decimal
    projected: Decimal
    budget: Decimal | None
    projected_status: BudgetStatus | None
    will_exceed_budget: bool  # forecast goes over a budget that isn't over yet


class GoalForecast(BaseModel):
    goal_id: uuid.UUID
    name: str
    remaining: Decimal
    monthly_pace: Decimal
    projected_completion: date | None
    target_date: date | None
    on_track: bool | None


class Forecast(BaseModel):
    month: str
    currency: str
    available: bool
    reason: str | None = None
    is_estimate: bool = True
    elapsed_days: int = 0
    days_in_month: int = 0
    spent_so_far: Decimal = Decimal("0.00")
    projected_expense: Decimal = Decimal("0.00")
    categories: list[CategoryForecast] = Field(default_factory=list)
    budget_warnings: list[CategoryForecast] = Field(default_factory=list)
    goals: list[GoalForecast] = Field(default_factory=list)


# --- SW-13 insights -------------------------------------------------------------------


class InsightFact(BaseModel):
    id: str
    label: str
    value: str


class Insight(BaseModel):
    title: str
    body: str
    tone: Literal["positive", "neutral", "warning"]
    facts: list[InsightFact]


class InsightsResponse(BaseModel):
    month: str
    available: bool
    reason: str | None = None
    insights: list[Insight] = Field(default_factory=list)


# --- SW-14 chat -----------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(min_length=1, max_length=4000)]


class ChatRequest(BaseModel):
    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=40)]


class ToolCallSummary(BaseModel):
    tool: str
    description: str


class ChatResponse(BaseModel):
    reply: str
    data_used: list[ToolCallSummary]


# --- SW-16 receipt scanning -----------------------------------------------------------


class ReceiptScan(BaseModel):
    readable: bool
    merchant: str | None
    transaction_date: date | None
    amount: Decimal | None  # serialized as a 2-decimal string
    currency: str | None
    category: CategoryRead | None
    message: str | None = None
    transaction_type: TransactionType = TransactionType.EXPENSE
