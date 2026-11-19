"""Default (system) categories shared by every user.

The initial Alembic migration inserts these rows. This module is used by the
test suite and can be run manually to (re)insert any missing system categories:

    python -m app.db.seed
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

# (name, transaction_type, color, icon_name)
DEFAULT_CATEGORIES: list[tuple[str, str, str, str]] = [
    # Expense
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
    # Income
    ("Salary", "income", "#16a34a", "briefcase"),
    ("Freelance", "income", "#22c55e", "laptop"),
    ("Business", "income", "#059669", "building"),
    ("Investment Income", "income", "#0d9488", "trending-up"),
    ("Gift", "income", "#84cc16", "gift"),
    ("Refund", "income", "#10b981", "rotate-ccw"),
    ("Other Income", "income", "#65a30d", "circle-plus"),
]


def seed_system_categories(db: Session) -> int:
    """Insert missing system categories. Returns the number of rows inserted."""
    from app.models.category import Category

    existing = {
        (name, ttype)
        for name, ttype in db.execute(
            select(Category.name, Category.transaction_type).where(Category.is_system.is_(True))
        ).all()
    }
    inserted = 0
    for name, ttype, color, icon in DEFAULT_CATEGORIES:
        if (name, ttype) in existing:
            continue
        db.add(
            Category(
                user_id=None,
                name=name,
                transaction_type=ttype,
                color=color,
                icon_name=icon,
                is_system=True,
            )
        )
        inserted += 1
    db.commit()
    return inserted


if __name__ == "__main__":
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        count = seed_system_categories(session)
        print(f"Inserted {count} system categories.")
