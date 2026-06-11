"""Auth request / response schemas."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    timezone: str = Field(default="UTC", max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned by /auth/register and /auth/login.

    access_token is a short-lived JWT (15 min by default).
    The refresh token is set as an HTTP-only cookie by the router — it does
    not appear in this body so JS cannot read it.
    """

    access_token: str
    token_type: str = "bearer"
