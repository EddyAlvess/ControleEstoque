from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user, require_user_or_esp32, verify_esp32_key
from app.models.operator import Operator
from app.models.user import WebUser
from app.schemas.operator import OperatorCreate, OperatorRead, OperatorUpdate

router = APIRouter(prefix="/api/v1/operators", tags=["operators"])


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
    op = Operator(name=data.name, badge_code=data.badge_code)
    db.add(op)
    await db.commit()
    await db.refresh(op)
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
    if data.is_active is not None:
        op.is_active = data.is_active
    db.add(op)
    await db.commit()
    await db.refresh(op)
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
