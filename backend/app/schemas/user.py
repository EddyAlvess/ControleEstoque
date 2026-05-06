from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    full_name: str
    email: str | None = None
    password: str
    role: Literal["admin", "user"] = "user"


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: int
    username: str
    full_name: str
    email: str | None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
