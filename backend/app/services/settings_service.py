from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import CompanySettings


class _SettingsCache:
    def __init__(self):
        self._data: dict = {
            "company_name": "InventControl",
            "logo_path": None,
            "logo_icon": "bi-box-seam",
        }

    def get(self) -> dict:
        return dict(self._data)

    async def reload(self, db: AsyncSession) -> None:
        row = (await db.execute(select(CompanySettings))).scalar_one_or_none()
        if row:
            self._data = {
                "company_name": row.company_name,
                "logo_path": row.logo_path,
                "logo_icon": row.logo_icon,
            }

    def update(self, company_name: str, logo_path: str | None, logo_icon: str) -> None:
        self._data = {
            "company_name": company_name,
            "logo_path": logo_path,
            "logo_icon": logo_icon,
        }


settings_cache = _SettingsCache()
