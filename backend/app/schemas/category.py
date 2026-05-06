from datetime import datetime

from pydantic import BaseModel, field_validator


class CategoryCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        return v.strip()


class CategoryUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
