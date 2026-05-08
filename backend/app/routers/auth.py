from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import require_user
from app.limiter import limiter
from app.logging_config import get_logger
from app.models.user import WebUser
from app.schemas.auth import PasswordResetRequest
from app.services.auth_service import (
    TokenData,
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(tags=["auth"])
_log = get_logger("auth")


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebUser).where(WebUser.username == username, WebUser.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.hashed_password):
        _log.warning("login_failure", extra={"username": username, "ip": request.client.host if request.client else "-"})
        return RedirectResponse(url="/login?error=1", status_code=status.HTTP_302_FOUND)

    token = create_access_token(TokenData(user_id=user.id, username=user.username, role=user.role))
    resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        "access_token", token,
        httponly=True, samesite="lax",
        max_age=86400 * 7,
        secure=settings.SECURE_COOKIES,
    )
    _log.info("login_success", extra={"username": user.username, "role": user.role, "ip": request.client.host if request.client else "-"})
    return resp


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie("access_token")
    return resp


@router.post("/reset-password")
async def reset_password(
    request: Request,
    data: PasswordResetRequest,
    user: WebUser = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nova senha deve ter pelo menos 8 caracteres")
    user.hashed_password = hash_password(data.new_password)
    db.add(user)
    await db.commit()
    _log.info("password_change", extra={"username": user.username, "ip": request.client.host if request.client else "-"})
    return {"message": "Senha alterada com sucesso"}
