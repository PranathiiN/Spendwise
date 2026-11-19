import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("transaction_type IN ('income', 'expense')", name="transaction_type"),
        CheckConstraint(
            "(is_system AND user_id IS NULL) OR (NOT is_system AND user_id IS NOT NULL)",
            name="system_owner",
        ),
        UniqueConstraint("user_id", "name", "transaction_type"),
    )

    # NULL for system (default) categories shared by all users.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(10), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#64748b")
    icon_name: Mapped[str] = mapped_column(String(50), nullable=False, default="tag")
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
