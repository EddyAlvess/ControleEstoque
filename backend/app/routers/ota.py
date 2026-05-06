import os
import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_admin, verify_esp32_key
from app.models.firmware import FirmwareVersion
from app.models.user import WebUser

router = APIRouter(prefix="/api/v1/ota", tags=["ota"])

UPLOAD_DIR = "/app/uploads/firmware"


@router.get("/version")
async def get_current_version(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_esp32_key),
):
    result = await db.execute(
        select(FirmwareVersion).where(FirmwareVersion.is_current == True)
    )
    fw = result.scalar_one_or_none()
    if not fw:
        return {"version": "0.0.0", "available": False}
    return {"version": fw.version, "available": True}


@router.get("/firmware.bin")
async def download_firmware(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_esp32_key),
):
    result = await db.execute(
        select(FirmwareVersion).where(FirmwareVersion.is_current == True)
    )
    fw = result.scalar_one_or_none()
    if not fw:
        raise HTTPException(status_code=404, detail="Nenhum firmware disponível")
    filepath = os.path.join(UPLOAD_DIR, fw.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Arquivo de firmware não encontrado")
    return FileResponse(filepath, media_type="application/octet-stream", filename=fw.filename)


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_firmware(
    version: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: WebUser = Depends(require_admin),
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"firmware_{version}.bin"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    await db.execute(update(FirmwareVersion).values(is_current=False))
    fw = FirmwareVersion(version=version, filename=filename, is_current=True)
    db.add(fw)
    await db.commit()
    return {"message": f"Firmware {version} enviado e definido como atual"}
