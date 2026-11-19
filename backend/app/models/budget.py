import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.category import Category
from app.models.mixins import MONEY_PRECISION, MONEY_SCALE, TimestampMixin, UUIDPrimaryKeyMixin


class Budget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A monthly spending limit for one expense category."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("alert_threshold BETWEEN 1 AND 100", name="alert_threshold_range"),
        CheckConstraint("EXTRACT(DAY FROM month) = 1", name="month_first_day"),
        UniqueConstraint("user_id", "category_id", "month"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    # Always the first day of the budget month, e.g. 2026-11-01.
    month: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True), nullable=False
    )
    # Percentage of the limit at which a warning is shown.
    alert_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=80, server_default="80"
    )

    category: Mapped[Category] = relationship(lazy="joined")
