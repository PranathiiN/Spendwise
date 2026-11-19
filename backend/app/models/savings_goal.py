import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import MONEY_PRECISION, MONEY_SCALE, TimestampMixin, UUIDPrimaryKeyMixin


class SavingsGoal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="target_positive"),
        CheckConstraint("current_amount >= 0", name="current_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True), nullable=False
    )
    current_amount: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, MONEY_SCALE, asdecimal=True),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#10b981")
    icon_name: Mapped[str] = mapped_column(String(50), nullable=False, default="piggy-bank")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
