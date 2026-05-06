from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator


class MovementCreate(BaseModel):
    movement_type: Literal["ENTRY", "EXIT"]
    operator_id: int
    product_id: int
    quantity: float
    shift: Literal["MORNING", "AFTERNOON", "NIGHT"] | None = None
    device_id: str | None = None
    notes: str | None = None
    recorded_at: datetime

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


class MovementRead(BaseModel):
    id: int
    movement_type: str
    operator_id: int
    product_id: int
    quantity: float
    shift: str | None
    device_id: str | None
    notes: str | None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MovementReadFull(MovementRead):
    operator_name: str
    product_name: str
    product_unit: str


class ReportSummaryItem(BaseModel):
    product_id: int
    product_name: str
    product_unit: str
    movement_type: str
    total_quantity: float
    count: int
