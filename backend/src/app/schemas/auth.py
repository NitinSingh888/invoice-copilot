from __future__ import annotations

from pydantic import BaseModel, EmailStr


class SignupIn(BaseModel):
    email: EmailStr
    password: str
    org_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class VerifyIn(BaseModel):
    token: str


class VerifyUserIn(BaseModel):
    user_id: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    email: str
    is_verified: bool
    org_id: str | None = None
    org_name: str | None = None
    role: str | None = None


class MemberOut(BaseModel):
    id: str
    email: str
    role: str
    is_verified: bool


class SignupOut(BaseModel):
    message: str
    status: str  # "active" | "pending"
