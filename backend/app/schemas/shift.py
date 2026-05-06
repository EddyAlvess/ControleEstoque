from datetime import datetime

from pydantic import BaseModel, field_validator


class ShiftCreate(BaseModel):
    name: str
    label: str
    start_hour: int
    end_hour: int

    @field_validator("name")
    @classmethod
    def name_upper(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("start_hour", "end_hour")
    @classmethod
    def hour_range(cls, v: int) -> int:
        if not 0 <= v <= 23:
            raise ValueError("hora deve estar entre 0 e 23")
        return v


class ShiftUpdate(BaseModel):
    label: str | None = None
    start_hour: int | None = None
    end_hour: int | None = None
    is_active: bool | None = None

    @field_validator("start_hour", "end_hour")
    @classmethod
    def hour_range(cls, v: int | None) -> int | None:
        if v is not None and not 0 <= v <= 23:
            raise ValueError("hora deve estar entre 0 e 23")
        return v


class ShiftRead(BaseModel):
    id: int
    name: str
    label: str
    start_hour: int
    end_hour: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
