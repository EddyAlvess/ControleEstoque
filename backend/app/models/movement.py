from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    movement_type: Mapped[str] = mapped_column(String(8), nullable=False)  # ENTRY | EXIT
    operator_id: Mapped[int] = mapped_column(ForeignKey("operators.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    shift: Mapped[str | None] = mapped_column(String(16))  # MORNING | AFTERNOON | NIGHT
    device_id: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_mv_type", "movement_type"),
        Index("idx_mv_operator", "operator_id"),
        Index("idx_mv_product", "product_id"),
        Index("idx_mv_recorded", "recorded_at"),
        Index("idx_mv_shift", "shift"),
        Index("idx_mv_type_date", "movement_type", "recorded_at"),
    )
