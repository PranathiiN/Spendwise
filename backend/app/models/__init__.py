"""Import every model here so Base.metadata knows about all tables (used by Alembic and tests)."""

from app.models.budget import Budget
from app.models.category import Category
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.models.user import User

__all__ = ["Budget", "Category", "SavingsGoal", "Transaction", "User"]
