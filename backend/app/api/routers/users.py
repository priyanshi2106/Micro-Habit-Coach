from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.modules.users.schemas import UserCreate, UserRead
from app.modules.users.service import create_user, get_user_by_email

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(session: DbSession, body: UserCreate) -> UserRead:
    if await get_user_by_email(session, str(body.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    user = await create_user(session, body)
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)
