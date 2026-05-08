from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user_or_esp32, verify_esp32_key
from app.logging_config import get_logger
from app.models.operator import Operator
from app.models.user import WebUser
from app.schemas.operator import OperatorCreate, OperatorRead, OperatorUpdate, PinVerifyRequest
from app.services.auth_service import hash_password, verify_password

router = APIRouter(prefix="/api/v1/operators", tags=["operators"])
_log = get_logger("admin")


@router.get("", response_model=list[OperatorRead])
async def list_operators(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_user_or_esp32),
):
    result = await db.execute(
        select(Operator).where(Operator.is_active == True).order_by(Operator.name)
    )
    return result.scalars().all()


@router.post("", response_model=OperatorRead, status_code=status.HTTP_201_CREATED)
async def create_operator(
    data: OperatorCreate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    exists = await db.execute(select(Operator).where(Operator.badge_code == data.badge_code))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Código de crachá já cadastrado")
    op = Operator(
        name=data.name,
        badge_code=data.badge_code,
        pin_hash=hash_password(data.pin) if data.pin else None,
    )
    db.add(op)
    await db.commit()
    await db.refresh(op)
    _log.info("operator_created", extra={"operator_id": op.id, "name": op.name, "admin_id": _.id})
    return op


@router.put("/{op_id}", response_model=OperatorRead)
async def update_operator(
    op_id: int,
    data: OperatorUpdate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(Operator).where(Operator.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operador não encontrado")
    if data.name is not None:
        op.name = data.name
    if data.badge_code is not None:
        op.badge_code = data.badge_code
    if data.pin is not None:
        op.pin_hash = hash_password(data.pin)
    if data.is_active is not None:
        op.is_active = data.is_active
    db.add(op)
    await db.commit()
    await db.refresh(op)
    _log.info("operator_updated", extra={"operator_id": op.id, "admin_id": _.id})
    return op


@router.delete("/{op_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_operator(
    op_id: int,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(Operator).where(Operator.id == op_id))
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operador não encontrado")
    op.is_active = False
    db.add(op)
    await db.commit()
    _log.info("operator_deactivated", extra={"operator_id": op_id, "admin_id": _.id})


@router.post("/{op_id}/verify-pin", status_code=status.HTTP_200_OK)
async def verify_operator_pin(
    op_id: int,
    data: PinVerifyRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_esp32_key),
):
    result = await db.execute(
        select(Operator).where(Operator.id == op_id, Operator.is_active == True)
    )
    op = result.scalar_one_or_none()
    if not op:
        raise HTTPException(status_code=404, detail="Operador não encontrado")
    if not op.pin_hash:
        raise HTTPException(status_code=400, detail="PIN não cadastrado")
    if not verify_password(data.pin, op.pin_hash):
        raise HTTPException(status_code=401, detail="PIN incorreto")
    return {"valid": True, "operator_id": op.id, "name": op.name}
