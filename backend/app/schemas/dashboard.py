import uuid
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.budget import BudgetRead
from app.schemas.savings_goal import SavingsGoalRead
from app.schemas.transaction import TransactionRead


class MonthTotals(BaseModel):
    income: Decimal
    expense: Decimal
    net: Decimal
    savings_rate: Decimal  # percent of income kept (net / income * 100)
    transaction_count: int


class CategoryBreakdownItem(BaseModel):
    category_id: uuid.UUID
    name: str
    color: str
    icon_name: str
    amount: Decimal
    percent: Decimal
    transaction_count: int


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    label: str  # e.g. "Nov 2026"
    income: Decimal
    expense: Decimal
    net: Decimal


class BudgetSummary(BaseModel):
    total_budgeted: Decimal
    total_spent: Decimal
    budget_count: int
    warning_count: int
    exceeded_count: int


class GoalsSummary(BaseModel):
    active_count: int
    completed_count: int
    total_saved: Decimal
    total_target: Decimal


class DashboardResponse(BaseModel):
    month: str
    currency: str
    totals: MonthTotals
    previous_totals: MonthTotals
    income_change_percent: Decimal | None
    expense_change_percent: Decimal | None
    expense_by_category: list[CategoryBreakdownItem]
    monthly_trend: list[TrendPoint]
    recent_transactions: list[TransactionRead]
    budget_alerts: list[BudgetRead]
    budget_summary: BudgetSummary
    goals: list[SavingsGoalRead]
    goals_summary: GoalsSummary
