import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin
from app.logging_config import get_logger
from app.models.settings import CompanySettings
from app.models.user import WebUser
from app.services.settings_service import settings_cache

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])
_log = get_logger("admin")

LOGOS_DIR = Path("app/static/logos")
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}


class SettingsUpdate(BaseModel):
    company_name: str
    logo_icon: str = "bi-snow2"

    @field_validator("company_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nome da empresa não pode estar em branco.")
        return v


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    row = (await db.execute(select(CompanySettings))).scalar_one_or_none()
    if not row:
        return {"company_name": "InventControl", "logo_path": None, "logo_icon": "bi-box-seam"}
    return {"company_name": row.company_name, "logo_path": row.logo_path, "logo_icon": row.logo_icon}


@router.put("")
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _user: WebUser = Depends(require_admin),
):
    row = (await db.execute(select(CompanySettings))).scalar_one_or_none()
    if not row:
        row = CompanySettings(company_name=data.company_name, logo_icon=data.logo_icon)
        db.add(row)
    else:
        row.company_name = data.company_name
        row.logo_icon = data.logo_icon
    await db.commit()
    settings_cache.update(data.company_name, row.logo_path, data.logo_icon)
    _log.info("settings_updated", extra={"company_name": data.company_name, "admin_id": _user.id})
    return {"ok": True}


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: WebUser = Depends(require_admin),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Formato não suportado. Use PNG, JPG, GIF, WebP ou SVG.")

    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "logo.png").suffix or ".png"
    dest = LOGOS_DIR / f"logo{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    logo_path = f"/static/logos/logo{suffix}"
    row = (await db.execute(select(CompanySettings))).scalar_one_or_none()
    if not row:
        row = CompanySettings(logo_path=logo_path)
        db.add(row)
    else:
        row.logo_path = logo_path
    await db.commit()

    cs = settings_cache.get()
    settings_cache.update(cs["company_name"], logo_path, cs["logo_icon"])
    _log.info("logo_uploaded", extra={"logo_path": logo_path, "admin_id": _user.id})
    return {"logo_path": logo_path}


@router.delete("/logo")
async def delete_logo(
    db: AsyncSession = Depends(get_db),
    _user: WebUser = Depends(require_admin),
):
    row = (await db.execute(select(CompanySettings))).scalar_one_or_none()
    if row and row.logo_path:
        path = Path("app") / row.logo_path.lstrip("/")
        if path.exists():
            path.unlink()
        row.logo_path = None
        await db.commit()

    cs = settings_cache.get()
    settings_cache.update(cs["company_name"], None, cs["logo_icon"])
    _log.info("logo_deleted", extra={"admin_id": _user.id})
    return {"ok": True}
