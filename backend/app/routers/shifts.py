from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user_or_esp32
from app.models.shift import Shift
from app.schemas.shift import ShiftCreate, ShiftRead, ShiftUpdate

router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


@router.get("", response_model=list[ShiftRead])
async def list_shifts(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    result = await db.execute(select(Shift).order_by(Shift.start_hour))
    return result.scalars().all()


@router.post("", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
async def create_shift(
    data: ShiftCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    exists = await db.execute(select(Shift).where(Shift.name == data.name))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Turno com esse nome já existe")
    shift = Shift(
        name=data.name,
        label=data.label,
        start_hour=data.start_hour,
        end_hour=data.end_hour,
    )
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.put("/{shift_id}", response_model=ShiftRead)
async def update_shift(
    shift_id: int,
    data: ShiftUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Turno não encontrado")
    if data.label is not None:
        shift.label = data.label
    if data.start_hour is not None:
        shift.start_hour = data.start_hour
    if data.end_hour is not None:
        shift.end_hour = data.end_hour
    if data.is_active is not None:
        shift.is_active = data.is_active
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift(
    shift_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Turno não encontrado")
    await db.delete(shift)
    await db.commit()
