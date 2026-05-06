from datetime import datetime

from pydantic import BaseModel


class ProductCreate(BaseModel):
    sku: str
    name: str
    unit: str = "L"
    category_id: int | None = None


class ProductUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    unit: str | None = None
    category_id: int | None = None
    is_active: bool | None = None


class ProductRead(BaseModel):
    id: int
    sku: str
    name: str
    unit: str
    category_id: int | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductReadFull(ProductRead):
    category_name: str | None = None
