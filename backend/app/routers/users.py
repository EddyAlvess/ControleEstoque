from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, require_user
from app.logging_config import get_logger
from app.models.user import WebUser
from app.schemas.auth import AdminPasswordResetRequest
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.auth_service import hash_password

router = APIRouter(prefix="/api/v1/users", tags=["users"])
_log = get_logger("admin")


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(WebUser).order_by(WebUser.username))
    return result.scalars().all()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    exists = await db.execute(select(WebUser).where(WebUser.username == data.username))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username já existe")
    user = WebUser(
        username=data.username,
        full_name=data.full_name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    _log.info("user_created", extra={"user_id": user.id, "username": user.username, "role": user.role, "admin_id": _.id})
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(WebUser).where(WebUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = data.email
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    _log.info("user_updated", extra={"user_id": user.id, "admin_id": _.id})
    return user


@router.post("/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    data: AdminPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    result = await db.execute(select(WebUser).where(WebUser.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 8 caracteres")
    user.hashed_password = hash_password(data.new_password)
    db.add(user)
    await db.commit()
    _log.info("user_password_reset", extra={"user_id": user.id, "admin_id": _.id})
    return {"message": "Senha redefinida com sucesso"}
