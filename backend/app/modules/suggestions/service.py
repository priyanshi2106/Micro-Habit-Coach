from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.common.enums import ScheduleBlockType, SuggestionSource
from app.modules.habit_logs.models import HabitLog
from app.modules.habits.models import Habit
from app.modules.schedules.models import ScheduleBlock
from app.modules.suggestions.engine import FreeBlockDTO, HabitDTO, pick_today_suggestion
from app.modules.suggestions.models import HabitSuggestion
from app.modules.suggestions.schemas import SuggestionRead, TodaySuggestionResponse
from app.modules.users.models import User

DEFAULT_CONFIDENCE = 0.5


async def get_or_create_today_suggestion(
    session: AsyncSession,
    *,
    user: User,
) -> TodaySuggestionResponse:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(user.timezone)
    now = datetime.now(tz)
    today = now.date()
    dow = now.weekday()

    # Fetch today's most recent log status upfront — included in every response
    # so the frontend can restore resolved UI state across navigation.
    log_res = await session.execute(
        select(HabitLog.status)
        .where(HabitLog.user_id == user.id, HabitLog.calendar_date == today)
        .order_by(HabitLog.created_at.desc())
        .limit(1)
    )
    today_log_status = log_res.scalar_one_or_none()

    existing = await session.execute(
        select(HabitSuggestion)
        .options(selectinload(HabitSuggestion.habit))
        .where(
            HabitSuggestion.user_id == user.id,
            HabitSuggestion.calendar_date == today,
        )
    )
    current = existing.scalar_one_or_none()
    if current is not None:
        return TodaySuggestionResponse(
            date=today,
            suggestion=SuggestionRead.model_validate(current),
            today_log_status=today_log_status,
        )

    free_res = await session.execute(
        select(ScheduleBlock).where(
            ScheduleBlock.user_id == user.id,
            ScheduleBlock.day_of_week == dow,
            ScheduleBlock.block_type == ScheduleBlockType.FREE.value,
        )
    )
    free_blocks = [
        FreeBlockDTO(start=b.start_time, end=b.end_time)  # type: ignore[arg-type]
        for b in free_res.scalars().all()
    ]

    habits_res = await session.execute(
        select(Habit).where(
            Habit.user_id == user.id,
            Habit.active.is_(True),
        )
    )
    habits = [
        HabitDTO(
            id=h.id,
            name=h.name,
            category=h.category,  # type: ignore[arg-type]
            duration_mins=h.duration_mins,
        )
        for h in habits_res.scalars().all()
    ]

    candidate = pick_today_suggestion(habits, free_blocks)
    if candidate is None:
        return TodaySuggestionResponse(date=today, suggestion=None, today_log_status=today_log_status)

    row = HabitSuggestion(
        user_id=user.id,
        habit_id=candidate.habit_id,
        suggested_window_start=candidate.window_start,
        suggested_window_end=candidate.window_end,
        source=SuggestionSource.RULE_ENGINE.value,
        confidence_score=DEFAULT_CONFIDENCE,
        suggestion_reason=candidate.reason,
        calendar_date=today,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        dup = await session.execute(
            select(HabitSuggestion)
            .options(selectinload(HabitSuggestion.habit))
            .where(
                HabitSuggestion.user_id == user.id,
                HabitSuggestion.calendar_date == today,
            )
        )
        current = dup.scalar_one()
        return TodaySuggestionResponse(
            date=today,
            suggestion=SuggestionRead.model_validate(current),
            today_log_status=today_log_status,
        )

    loaded = await session.execute(
        select(HabitSuggestion)
        .options(selectinload(HabitSuggestion.habit))
        .where(HabitSuggestion.id == row.id)
    )
    fresh = loaded.scalar_one()
    return TodaySuggestionResponse(
        date=today,
        suggestion=SuggestionRead.model_validate(fresh),
        today_log_status=today_log_status,
    )
