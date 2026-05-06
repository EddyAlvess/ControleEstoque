from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_user
from app.models.user import WebUser
from app.schemas.movement import ReportSummaryItem
from app.services import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/summary", response_model=list[ReportSummaryItem])
async def get_summary(
    movement_type: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    shift: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_user),
):
    return await report_service.get_summary(db, movement_type, date_from, date_to, shift)


@router.get("/export")
async def export_csv(
    movement_type: str | None = Query(None),
    operator_id: int | None = Query(None),
    product_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    shift: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_user),
):
    csv_content = await report_service.export_csv(
        db, movement_type, operator_id, product_id, date_from, date_to, shift
    )
    return StreamingResponse(
        iter([csv_content.encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio.csv"},
    )
