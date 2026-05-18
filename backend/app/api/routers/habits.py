from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentUser, DbSession
from app.modules.habits.schemas import HabitCreate, HabitRead, HabitUpdate
from app.modules.habits.service import create_habit, delete_habit, list_habits, update_habit

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitRead])
async def list_habits_route(
    session: DbSession,
    user: CurrentUser,
    active_only: bool = True,
) -> list[HabitRead]:
    rows = await list_habits(session, user_id=user.id, active_only=active_only)
    return [HabitRead.model_validate(r) for r in rows]


@router.post("", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
async def create_habit_route(
    session: DbSession,
    user: CurrentUser,
    body: HabitCreate,
) -> HabitRead:
    habit = await create_habit(session, user_id=user.id, payload=body)
    return HabitRead.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitRead)
async def update_habit_route(
    session: DbSession,
    user: CurrentUser,
    habit_id: UUID,
    body: HabitUpdate,
) -> HabitRead:
    habit = await update_habit(session, user_id=user.id, habit_id=habit_id, payload=body)
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    return HabitRead.model_validate(habit)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit_route(
    session: DbSession,
    user: CurrentUser,
    habit_id: UUID,
) -> Response:
    deleted = await delete_habit(session, user_id=user.id, habit_id=habit_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
