from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(128), nullable=False, default="SorvPel")
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    logo_icon: Mapped[str] = mapped_column(String(64), nullable=False, default="bi-snow2")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
