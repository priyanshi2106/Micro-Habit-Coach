from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.calendar.availability import subtract_busy_windows
from app.modules.calendar.client import get_busy_windows_today
from app.modules.calendar.models import CalendarConnection
from app.modules.common.enums import ScheduleBlockType, SuggestionSource
from app.modules.habit_logs.models import HabitLog
from app.modules.habits.models import Habit
from app.modules.habits.anchors import ANCHOR_CATALOG, anchor_to_bucket
from app.modules.habits.pattern_service import get_patterns_for_user
from app.modules.habits.scorer import compute_confidence
from app.modules.schedules.models import ScheduleBlock
from app.modules.suggestions.engine import FreeBlockDTO, HabitDTO, pick_today_suggestion
from app.modules.suggestions.models import HabitSuggestion
from app.modules.suggestions.schemas import SuggestionRead, TodaySuggestionResponse
from app.modules.users.models import User


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

    # If the user has an active Google Calendar connection, subtract today's
    # busy events from the free blocks so the engine never suggests a habit
    # during a real meeting.  Any failure is caught inside get_busy_windows_today
    # and returns [] — suggestion generation always continues with manual blocks.
    cal_res = await session.execute(
        select(CalendarConnection).where(
            CalendarConnection.user_id == user.id,
            CalendarConnection.is_active.is_(True),
        )
    )
    cal_connection = cal_res.scalar_one_or_none()
    if cal_connection is not None:
        busy_windows = await get_busy_windows_today(cal_connection, session, user.timezone)
        if busy_windows:
            free_blocks = subtract_busy_windows(free_blocks, busy_windows)

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
            anchor_bucket=anchor_to_bucket(h.anchor_event) if h.anchor_event else None,
            anchor_name=(
                ANCHOR_CATALOG[h.anchor_event].display
                if h.anchor_event and h.anchor_event in ANCHOR_CATALOG
                else None
            ),
        )
        for h in habits_res.scalars().all()
    ]

    # Build learned-pattern map: habit_id → (start_mins, end_mins).
    # Only habits with ≥ MIN_SAMPLES done-logs in a dominant bucket produce a pattern.
    raw_patterns = await get_patterns_for_user(user.id, session)
    patterns = {hid: (p.start_mins, p.end_mins) for hid, p in raw_patterns.items()}

    candidate = pick_today_suggestion(habits, free_blocks, patterns=patterns or None)
    if candidate is None:
        return TodaySuggestionResponse(date=today, suggestion=None, today_log_status=today_log_status)

    source = (
        SuggestionSource.ADAPTIVE_ENGINE.value
        if (candidate.used_learned or candidate.used_anchor)
        else SuggestionSource.RULE_ENGINE.value
    )

    # Compute confidence score and user-readable reason via the scorer.
    # raw_patterns holds the HabitPattern (dominant_fraction, recency_score)
    # when enough history exists; None otherwise.
    pattern = raw_patterns.get(candidate.habit_id)
    confidence_result = compute_confidence(
        pattern=pattern,
        used_learned=candidate.used_learned,
        category=str(candidate.category.value),
        habit_name=candidate.habit_name,
        used_anchor=candidate.used_anchor,
        anchor_name=candidate.anchor_name,
    )

    row = HabitSuggestion(
        user_id=user.id,
        habit_id=candidate.habit_id,
        suggested_window_start=candidate.window_start,
        suggested_window_end=candidate.window_end,
        source=source,
        confidence_score=confidence_result.score,
        suggestion_reason=confidence_result.reason,
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
