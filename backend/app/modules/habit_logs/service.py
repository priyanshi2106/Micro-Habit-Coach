from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.habit_logs.models import HabitLog
from app.modules.habit_logs.schemas import HabitLogCreate, HabitLogSummary
from app.modules.habits.models import Habit
from app.modules.suggestions.models import HabitSuggestion


async def create_habit_log(
    session: AsyncSession,
    *,
    user_id: UUID,
    payload: HabitLogCreate,
) -> HabitLog:
    habit_res = await session.execute(
        select(Habit).where(Habit.id == payload.habit_id, Habit.user_id == user_id)
    )
    habit = habit_res.scalar_one_or_none()
    if habit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Habit not found")

    if payload.suggestion_id is not None:
        sug_res = await session.execute(
            select(HabitSuggestion).where(
                HabitSuggestion.id == payload.suggestion_id,
                HabitSuggestion.user_id == user_id,
            )
        )
        if sug_res.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found",
            )

    # For done logs, ensure completed_at is always populated so pattern
    # learning has a reliable timestamp to work with.
    completed_at = payload.completed_at
    if payload.status.value == "done" and completed_at is None:
        completed_at = datetime.now(timezone.utc)

    log = HabitLog(
        user_id=user_id,
        habit_id=payload.habit_id,
        suggestion_id=payload.suggestion_id,
        status=payload.status.value,
        completed_at=completed_at,
        scheduled_window_start=payload.scheduled_window_start,
        scheduled_window_end=payload.scheduled_window_end,
        calendar_date=payload.date,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log

async def get_log_summary(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> HabitLogSummary:
    today = date.today()
    week_start = today - timedelta(days=6)

    # All distinct dates with at least one done log (no limit — needed for streak).
    done_dates_result = await session.execute(
        select(HabitLog.calendar_date)
        .where(HabitLog.user_id == user_id, HabitLog.status == "done")
        .distinct()
    )
    done_dates: set[date] = {row[0] for row in done_dates_result}

    # Streak rule (v1.2 product decision):
    # A streak is the count of consecutive calendar days with at least one "done" log.
    # If the user has not completed a habit yet today, the streak from prior days is
    # still considered active — it is only broken after a full missed day has passed.
    # This means a streak of N shown today was earned through yesterday at minimum,
    # and today still has a chance to extend it.
    streak = 0
    check = today if today in done_dates else today - timedelta(days=1)
    while check in done_dates:
        streak += 1
        check -= timedelta(days=1)

    # Weekly counts grouped by status.
    weekly_result = await session.execute(
        select(HabitLog.status, func.count())
        .where(HabitLog.user_id == user_id, HabitLog.calendar_date >= week_start)
        .group_by(HabitLog.status)
    )
    counts = {row[0]: row[1] for row in weekly_result}

    week_done = counts.get("done", 0)
    week_snoozed = counts.get("snoozed", 0)
    week_skipped = counts.get("skipped", 0)

    return HabitLogSummary(
        week_total=week_done + week_snoozed + week_skipped,
        week_done=week_done,
        week_snoozed=week_snoozed,
        week_skipped=week_skipped,
        current_streak=streak,
    )


async def list_habit_logs(
    session: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 50,
) -> list[HabitLog]:
    stmt = (
        select(HabitLog)
        .options(selectinload(HabitLog.habit))
        .where(HabitLog.user_id == user_id)
        .order_by(HabitLog.created_at.desc())
        .limit(limit)
    )
    results = await session.execute(stmt)
    return list(results.scalars().all())
