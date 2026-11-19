from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession, MonthParam
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import build_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(month: MonthParam, current_user: CurrentUser, db: DbSession) -> DashboardResponse:
    return build_dashboard(db, current_user, month)
