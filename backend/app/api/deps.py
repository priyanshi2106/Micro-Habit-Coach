from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.modules.users.models import User

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def require_bearer_token(
    authorization: Annotated[Optional[str], Header()] = None,
) -> UUID:
    """Extract and verify the JWT from the Authorization: Bearer <token> header.

    Returns the user UUID encoded in the token.
    Raises 401 if the header is missing, malformed, or the token is invalid/expired.
    """
    if authorization is None or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[len("bearer "):]
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


UserId = Annotated[UUID, Depends(require_bearer_token)]


async def require_user(
    session: DbSession,
    user_id: UserId,
) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


CurrentUser = Annotated[User, Depends(require_user)]
