from datetime import datetime

from pydantic import BaseModel


class ProductCreate(BaseModel):
    sku: str
    name: str
    unit: str = "L"


class ProductUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    is_active: bool | None = None


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    unit: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
