from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.models import User


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def require_user_id(
    x_user_id: Annotated[Optional[UUID], Header(alias="X-User-Id")] = None,
) -> UUID:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header",
        )
    return x_user_id


UserId = Annotated[UUID, Depends(require_user_id)]


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
