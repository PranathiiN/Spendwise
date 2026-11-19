from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession, MonthParam
from app.schemas.ai import Forecast
from app.services.forecast_service import build_forecast

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("", response_model=Forecast)
def get_forecast(month: MonthParam, current_user: CurrentUser, db: DbSession) -> Forecast:
    """SW-15: end-of-month spending and savings-goal estimates (current month only)."""
    return build_forecast(db, current_user, month)
