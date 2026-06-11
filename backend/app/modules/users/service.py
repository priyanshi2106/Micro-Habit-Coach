from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate

if TYPE_CHECKING:
    from app.modules.auth.schemas import RegisterRequest


async def create_user_with_password(
    session: AsyncSession,
    payload: "RegisterRequest",
) -> User:
    """Create a user from a RegisterRequest (includes password hashing)."""
    user = User(
        name=payload.name,
        email=str(payload.email),
        timezone=payload.timezone,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    """Legacy: creates user with empty password_hash. Used only in tests."""
    user = User(
        name=payload.name,
        email=str(payload.email),
        timezone=payload.timezone,
        password_hash="",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    res = await session.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    res = await session.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()
