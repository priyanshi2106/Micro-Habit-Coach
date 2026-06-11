"""Weekly stats aggregation for the Weekly Insight feature (v2.2).

Queries the last 7 calendar days of habit_logs for a user and returns a
WeeklyStats dataclass.  No AI is involved here — this is pure aggregation.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habit_logs.models import HabitLog
from app.modules.habits.models import Habit
from app.modules.insights.schemas import WeeklyStats

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


async def compute_weekly_stats(
    user_id: UUID,
    session: AsyncSession,
    *,
    timezone_str: str = "UTC",
) -> tuple[WeeklyStats, date, date]:
    """Return (WeeklyStats, week_start, week_end) for the last 7 calendar days.

    week_end is today in the user's local timezone; week_start is 6 days prior.
    All fields default to 0 / None so callers never need to handle missing data.
    """
    try:
        tz = ZoneInfo(timezone_str)
    except (ZoneInfoNotFoundError, Exception):
        tz = ZoneInfo("UTC")

    today = datetime.now(tz).date()
    week_start = today - timedelta(days=6)

    # Fetch all logs in the window, joined to habit name.
    result = await session.execute(
        select(HabitLog.status, HabitLog.calendar_date, Habit.name)
        .join(Habit, Habit.id == HabitLog.habit_id)
        .where(
            HabitLog.user_id == user_id,
            HabitLog.calendar_date >= week_start,
            HabitLog.calendar_date <= today,
        )
    )
    rows = result.all()  # list of (status, calendar_date, habit_name)

    total = len(rows)
    done_count = sum(1 for r in rows if r[0] == "done")
    snoozed_count = sum(1 for r in rows if r[0] == "snoozed")
    skipped_count = sum(1 for r in rows if r[0] == "skipped")
    completion_rate = round(done_count / total, 2) if total > 0 else 0.0

    # Best day: day of week with the most done logs.
    done_by_day: Counter[str] = Counter(
        _DAY_NAMES[r[1].weekday()] for r in rows if r[0] == "done"
    )
    best_day = done_by_day.most_common(1)[0][0] if done_by_day else None

    # Worst day: day of week with the most skipped logs.
    skipped_by_day: Counter[str] = Counter(
        _DAY_NAMES[r[1].weekday()] for r in rows if r[0] == "skipped"
    )
    worst_day = skipped_by_day.most_common(1)[0][0] if skipped_by_day else None

    # Best habit: habit name with the most done logs.
    done_by_habit: Counter[str] = Counter(r[2] for r in rows if r[0] == "done")
    best_habit = done_by_habit.most_common(1)[0][0] if done_by_habit else None

    # Most skipped habit: habit name with the most skipped logs.
    skipped_by_habit: Counter[str] = Counter(r[2] for r in rows if r[0] == "skipped")
    most_skipped_habit = skipped_by_habit.most_common(1)[0][0] if skipped_by_habit else None

    stats = WeeklyStats(
        total=total,
        done=done_count,
        snoozed=snoozed_count,
        skipped=skipped_count,
        completion_rate=completion_rate,
        best_day=best_day,
        worst_day=worst_day,
        best_habit=best_habit,
        most_skipped_habit=most_skipped_habit,
    )
    return stats, week_start, today
