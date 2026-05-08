from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_user, verify_esp32_key
from app.logging_config import get_logger
from app.models.movement import InventoryMovement
from app.models.shift import Shift
from app.models.user import WebUser
from app.schemas.movement import MovementCreate, MovementRead
from app.services import report_service

router = APIRouter(prefix="/api/v1/movements", tags=["movements"])
_log = get_logger("movements")


_SP = ZoneInfo("America/Sao_Paulo")


async def _detect_shift(db: AsyncSession, recorded_at: datetime) -> str | None:
    """Detecta o turno com base no horário (horário de Brasília) de recorded_at."""
    dt_sp = recorded_at.astimezone(_SP) if recorded_at.tzinfo else recorded_at.replace(tzinfo=timezone.utc).astimezone(_SP)
    hour = dt_sp.hour
    result = await db.execute(select(Shift).where(Shift.is_active == True))
    for shift in result.scalars().all():
        if shift.contains_hour(hour):
            return shift.name
    return None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_movement(
    data: MovementCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_esp32_key),
):
    shift = await _detect_shift(db, data.recorded_at)
    mv = InventoryMovement(
        movement_type=data.movement_type,
        operator_id=data.operator_id,
        product_id=data.product_id,
        quantity=data.quantity,
        shift=shift,
        device_id=data.device_id,
        notes=data.notes,
        recorded_at=data.recorded_at,
    )
    db.add(mv)
    await db.commit()
    await db.refresh(mv)
    _log.info("movement_created", extra={
        "movement_id": mv.id,
        "type": data.movement_type,
        "operator_id": data.operator_id,
        "product_id": data.product_id,
        "quantity": data.quantity,
        "shift": shift,
        "device_id": data.device_id,
    })
    return {"id": mv.id, "shift": shift, "message": "Movimento registrado"}


@router.get("")
async def list_movements(
    movement_type: str | None = Query(None),
    operator_id: int | None = Query(None),
    product_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    shift: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_user),
):
    rows, total = await report_service.get_movements_query(
        db, movement_type, operator_id, product_id, date_from, date_to, shift, page, page_size
    )
    return {"total": total, "page": page, "page_size": page_size, "items": rows}
