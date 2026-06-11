"""Auth business logic: register, login, token refresh."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.modules.users.models import User
from app.modules.users.service import create_user_with_password, get_user_by_email


async def register(
    session: AsyncSession,
    payload: RegisterRequest,
) -> tuple[User, str, str]:
    """Create a new user and return (user, access_token, refresh_token).

    Raises 409 if the email is already registered.
    """
    existing = await get_user_by_email(session, str(payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await create_user_with_password(session, payload)
    return user, create_access_token(user.id), create_refresh_token(user.id)


async def login(
    session: AsyncSession,
    payload: LoginRequest,
) -> tuple[User, str, str]:
    """Verify credentials and return (user, access_token, refresh_token).

    Returns 401 for both wrong email and wrong password — same error message
    intentionally avoids user enumeration.
    """
    user = await get_user_by_email(session, str(payload.email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return user, create_access_token(user.id), create_refresh_token(user.id)
