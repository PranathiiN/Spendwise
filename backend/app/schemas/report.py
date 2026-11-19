import datetime as dt
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.budget import BudgetRead
from app.schemas.dashboard import CategoryBreakdownItem, MonthTotals, TrendPoint
from app.schemas.transaction import TransactionRead


class DailyPoint(BaseModel):
    date: dt.date
    income: Decimal
    expense: Decimal
    cumulative_expense: Decimal


class MonthlyReport(BaseModel):
    month: str
    label: str
    currency: str
    totals: MonthTotals
    previous_totals: MonthTotals
    income_change_percent: Decimal | None
    expense_change_percent: Decimal | None
    income_by_category: list[CategoryBreakdownItem]
    expense_by_category: list[CategoryBreakdownItem]
    daily: list[DailyPoint]
    top_expenses: list[TransactionRead]
    budgets: list[BudgetRead]
    average_daily_expense: Decimal
    highest_expense_day: DailyPoint | None
    six_month_trend: list[TrendPoint]
