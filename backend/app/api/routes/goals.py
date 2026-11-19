import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.utils import not_found, reject_nulls
from app.core.dependencies import CurrentUser, DbSession
from app.models.savings_goal import SavingsGoal
from app.schemas.savings_goal import (
    GoalContribution,
    SavingsGoalCreate,
    SavingsGoalRead,
    SavingsGoalUpdate,
)
from app.services.goal_service import goal_to_read
from app.utils.money import money

router = APIRouter(prefix="/goals", tags=["savings goals"])

MAX_AMOUNT = Decimal("9999999999.99")


def _get_owned_goal(db, user_id: uuid.UUID, goal_id: uuid.UUID) -> SavingsGoal:
    goal = db.scalar(select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id))
    if goal is None:
        raise not_found("Savings goal")
    return goal


@router.get("", response_model=list[SavingsGoalRead])
def list_goals(current_user: CurrentUser, db: DbSession) -> list[SavingsGoalRead]:
    goals = [
        goal_to_read(g)
        for g in db.scalars(select(SavingsGoal).where(SavingsGoal.user_id == current_user.id)).all()
    ]
    status_order = {"overdue": 0, "active": 1, "completed": 2}
    goals.sort(
        key=lambda g: (
            status_order[g.status],
            g.target_date is None,
            g.target_date.toordinal() if g.target_date else 0,
            g.name.lower(),
        )
    )
    return goals


@router.post("", response_model=SavingsGoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(payload: SavingsGoalCreate, current_user: CurrentUser, db: DbSession) -> SavingsGoalRead:
    goal = SavingsGoal(user_id=current_user.id, **payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_to_read(goal)


@router.get("/{goal_id}", response_model=SavingsGoalRead)
def get_goal(goal_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> SavingsGoalRead:
    return goal_to_read(_get_owned_goal(db, current_user.id, goal_id))


@router.patch("/{goal_id}", response_model=SavingsGoalRead)
def update_goal(
    goal_id: uuid.UUID, payload: SavingsGoalUpdate, current_user: CurrentUser, db: DbSession
) -> SavingsGoalRead:
    goal = _get_owned_goal(db, current_user.id, goal_id)
    data = payload.model_dump(exclude_unset=True)
    reject_nulls(data, ["name", "target_amount", "color", "icon_name"])
    for key, value in data.items():
        setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal_to_read(goal)


@router.post("/{goal_id}/contribute", response_model=SavingsGoalRead)
def contribute(
    goal_id: uuid.UUID, payload: GoalContribution, current_user: CurrentUser, db: DbSession
) -> SavingsGoalRead:
    goal = _get_owned_goal(db, current_user.id, goal_id)
    current = money(goal.current_amount)
    if payload.action == "withdraw":
        if payload.amount > current:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Cannot withdraw more than the saved amount ({current})",
            )
        new_amount = money(current - payload.amount)
    else:
        new_amount = money(current + payload.amount)
        if new_amount > MAX_AMOUNT:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Amount is too large")
    goal.current_amount = new_amount
    db.commit()
    db.refresh(goal)
    return goal_to_read(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> None:
    goal = _get_owned_goal(db, current_user.id, goal_id)
    db.delete(goal)
    db.commit()
