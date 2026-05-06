from datetime import datetime

from pydantic import BaseModel


class OperatorCreate(BaseModel):
    name: str
    badge_code: str


class OperatorUpdate(BaseModel):
    name: str | None = None
    badge_code: str | None = None
    is_active: bool | None = None


class OperatorRead(BaseModel):
    id: int
    name: str
    badge_code: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
