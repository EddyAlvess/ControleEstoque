from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    user_id: int
    username: str
    role: str


class PasswordResetRequest(BaseModel):
    old_password: str
    new_password: str


class AdminPasswordResetRequest(BaseModel):
    new_password: str
