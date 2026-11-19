from fastapi import APIRouter
from fastapi.responses import Response

from app.core.dependencies import CurrentUser, DbSession, MonthParam
from app.schemas.report import MonthlyReport
from app.services.report_service import build_monthly_report, export_month_csv
from app.utils.dates import format_month

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly", response_model=MonthlyReport)
def monthly_report(month: MonthParam, current_user: CurrentUser, db: DbSession) -> MonthlyReport:
    return build_monthly_report(db, current_user, month)


@router.get("/monthly/export", response_class=Response)
def export_monthly_csv(month: MonthParam, current_user: CurrentUser, db: DbSession) -> Response:
    # UTF-8 BOM so Excel on Windows shows symbols such as ₹ correctly.
    content = "﻿" + export_month_csv(db, current_user.id, month)
    filename = f"spendwise-{format_month(month)}.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
