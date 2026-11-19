"""Initial schema and default system categories.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-17
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Kept inline (not imported from app code) so this migration never changes meaning.
DEFAULT_CATEGORIES = [
    ("Food & Dining", "expense", "#f97316", "utensils"),
    ("Housing", "expense", "#8b5cf6", "home"),
    ("Transportation", "expense", "#0ea5e9", "car"),
    ("Shopping", "expense", "#ec4899", "shopping-bag"),
    ("Utilities", "expense", "#eab308", "zap"),
    ("Entertainment", "expense", "#a855f7", "film"),
    ("Healthcare", "expense", "#ef4444", "heart-pulse"),
    ("Education", "expense", "#3b82f6", "graduation-cap"),
    ("Travel", "expense", "#14b8a6", "plane"),
    ("Subscriptions", "expense", "#6366f1", "repeat"),
    ("Personal Care", "expense", "#f43f5e", "sparkles"),
    ("Other Expense", "expense", "#64748b", "circle-ellipsis"),
    ("Salary", "income", "#16a34a", "briefcase"),
    ("Freelance", "income", "#22c55e", "laptop"),
    ("Business", "income", "#059669", "building"),
    ("Investment Income", "income", "#0d9488", "trending-up"),
    ("Gift", "income", "#84cc16", "gift"),
    ("Refund", "income", "#10b981", "rotate-ccw"),
    ("Other Income", "income", "#65a30d", "circle-plus"),
]


def _timestamps(with_updated: bool = True) -> list[sa.Column]:
    cols = [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    ]
    if with_updated:
        cols.append(
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
        )
    return cols


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("preferred_currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("icon_name", sa.String(50), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false()),
        *_timestamps(with_updated=False),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_categories_user_id_users", ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "transaction_type IN ('income', 'expense')", name="ck_categories_transaction_type"
        ),
        sa.CheckConstraint(
            "(is_system AND user_id IS NULL) OR (NOT is_system AND user_id IS NOT NULL)",
            name="ck_categories_system_owner",
        ),
        sa.UniqueConstraint(
            "user_id", "name", "transaction_type", name="uq_categories_user_id_name_transaction_type"
        ),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])

    op.create_table(
        "transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_transactions_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_transactions_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        sa.CheckConstraint(
            "transaction_type IN ('income', 'expense')", name="ck_transactions_transaction_type"
        ),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"])
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "transaction_date"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("alert_threshold", sa.Integer(), nullable=False, server_default="80"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_budgets"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_budgets_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_budgets_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("amount > 0", name="ck_budgets_amount_positive"),
        sa.CheckConstraint(
            "alert_threshold BETWEEN 1 AND 100", name="ck_budgets_alert_threshold_range"
        ),
        sa.CheckConstraint("EXTRACT(DAY FROM month) = 1", name="ck_budgets_month_first_day"),
        sa.UniqueConstraint(
            "user_id", "category_id", "month", name="uq_budgets_user_id_category_id_month"
        ),
    )
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    op.create_table(
        "savings_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("target_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("icon_name", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_savings_goals"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_savings_goals_user_id_users", ondelete="CASCADE"
        ),
        sa.CheckConstraint("target_amount > 0", name="ck_savings_goals_target_positive"),
        sa.CheckConstraint("current_amount >= 0", name="ck_savings_goals_current_non_negative"),
    )
    op.create_index("ix_savings_goals_user_id", "savings_goals", ["user_id"])

    categories = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("transaction_type", sa.String()),
        sa.column("color", sa.String()),
        sa.column("icon_name", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": uuid.uuid4(),
                "user_id": None,
                "name": name,
                "transaction_type": ttype,
                "color": color,
                "icon_name": icon,
                "is_system": True,
            }
            for name, ttype, color, icon in DEFAULT_CATEGORIES
        ],
    )


def downgrade() -> None:
    op.drop_table("savings_goals")
    op.drop_table("budgets")
    op.drop_table("transactions")
    op.drop_table("categories")
    op.drop_table("users")
