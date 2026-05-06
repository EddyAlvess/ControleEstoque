from fastapi import Cookie, Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import WebUser
from app.services.auth_service import decode_access_token

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WebUser | None:
    token = request.cookies.get("access_token")
    if not token:
        return None
    token_data = decode_access_token(token)
    if not token_data:
        return None
    result = await db.execute(
        select(WebUser).where(WebUser.id == token_data.user_id, WebUser.is_active == True)
    )
    return result.scalar_one_or_none()


async def require_user(
    user: WebUser | None = Depends(get_current_user),
) -> WebUser:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado",
        )
    return user


async def require_admin(
    user: WebUser = Depends(require_user),
) -> WebUser:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores",
        )
    return user


async def verify_esp32_key(
    api_key: str | None = Security(api_key_header),
) -> None:
    if not api_key or api_key != settings.ESP32_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida",
        )
