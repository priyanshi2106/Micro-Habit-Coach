from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.models import Habit
from app.modules.habits.schemas import HabitCreate, HabitUpdate


async def create_habit(session: AsyncSession, *, user_id: UUID, payload: HabitCreate) -> Habit:
    habit = Habit(
        user_id=user_id,
        name=payload.name,
        category=payload.category.value,
        duration_mins=payload.duration_mins,
        difficulty=payload.difficulty,
        best_time_of_day=payload.best_time_of_day,
        anchor_event=payload.anchor_event,
        is_custom=payload.is_custom,
        active=payload.active,
    )
    session.add(habit)
    await session.commit()
    await session.refresh(habit)
    return habit


async def update_habit(
    session: AsyncSession,
    *,
    user_id: UUID,
    habit_id: UUID,
    payload: HabitUpdate,
) -> Optional[Habit]:
    res = await session.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    )
    habit = res.scalar_one_or_none()
    if habit is None:
        return None

    data = payload.model_dump(exclude_unset=True)
    # Enum values must be stored as plain strings in the DB column.
    if "category" in data and data["category"] is not None:
        data["category"] = data["category"].value

    for field, value in data.items():
        setattr(habit, field, value)

    await session.commit()
    await session.refresh(habit)
    return habit


async def delete_habit(
    session: AsyncSession,
    *,
    user_id: UUID,
    habit_id: UUID,
) -> bool:
    """Permanently delete a habit owned by the user. Returns False if not found."""
    res = await session.execute(
        select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    )
    habit = res.scalar_one_or_none()
    if habit is None:
        return False
    await session.delete(habit)
    await session.commit()
    return True


async def list_habits(
    session: AsyncSession,
    *,
    user_id: UUID,
    active_only: bool,
) -> list[Habit]:
    stmt = select(Habit).where(Habit.user_id == user_id)
    if active_only:
        stmt = stmt.where(Habit.active.is_(True))
    stmt = stmt.order_by(Habit.created_at.asc())
    res = await session.execute(stmt)
    return list(res.scalars().all())
