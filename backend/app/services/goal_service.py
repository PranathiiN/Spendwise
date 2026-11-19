from datetime import date
from decimal import ROUND_UP, Decimal

from app.models.savings_goal import SavingsGoal
from app.schemas.savings_goal import GoalStatus, SavingsGoalRead
from app.utils.money import CENT, ZERO, money, percent


def goal_to_read(goal: SavingsGoal, today: date | None = None) -> SavingsGoalRead:
    today = today or date.today()
    target = money(goal.target_amount)
    current = money(goal.current_amount)
    remaining = max(money(target - current), ZERO)
    is_completed = current >= target
    progress = min(percent(current, target), Decimal("100.0"))

    days_remaining: int | None = None
    monthly_required: Decimal | None = None
    status: GoalStatus = "completed" if is_completed else "active"

    if goal.target_date is not None:
        days_remaining = (goal.target_date - today).days
        if not is_completed:
            if days_remaining < 0:
                status = "overdue"
            else:
                months_left = max(
                    1,
                    (goal.target_date.year - today.year) * 12 + (goal.target_date.month - today.month),
                )
                monthly_required = (remaining / Decimal(months_left)).quantize(CENT, rounding=ROUND_UP)

    return SavingsGoalRead(
        id=goal.id,
        name=goal.name,
        target_amount=target,
        current_amount=current,
        remaining_amount=remaining,
        progress_percent=progress,
        target_date=goal.target_date,
        days_remaining=days_remaining,
        monthly_required=monthly_required,
        status=status,
        is_completed=is_completed,
        color=goal.color,
        icon_name=goal.icon_name,
        notes=goal.notes,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )
