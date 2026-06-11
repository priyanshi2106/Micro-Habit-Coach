"""Pattern learning service for v2.1.

Analyses a user's habit log history to identify each habit's preferred
time-of-day window.  This learned preference is passed into the suggestion
engine so it can override the default category-level time bucket once
enough behavioral evidence has accumulated.

Key design decisions
--------------------
- Patterns are computed on-demand at suggestion time from existing
  habit_log rows.  No new DB table is needed for v2.1.
- completed_at is stored in UTC.  We convert to the user's local timezone
  before bucketing so that a habit done at 7 AM local time is not
  mis-classified as "midday" due to a UTC offset.
- Minimum sample threshold is 5 qualifying done logs.  Below this the
  function returns None and the caller uses the category rule instead.
- Tie-breaking: when two buckets have equal counts, the earlier bucket wins
  (morning > midday > evening).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habit_logs.models import HabitLog
from app.modules.habits.models import Habit
from app.modules.users.models import User

_log = logging.getLogger(__name__)

# ── Time bucket definitions (minutes from midnight, half-open [start, end)) ──
# These match the naming and spirit of the category buckets in engine.py.
BUCKET_MORNING = (5 * 60, 12 * 60)    # 05:00 – 12:00
BUCKET_MIDDAY  = (12 * 60, 17 * 60)   # 12:00 – 17:00
BUCKET_EVENING = (17 * 60, 24 * 60)   # 17:00 – 24:00

_BUCKETS: list[tuple[int, int]] = [BUCKET_MORNING, BUCKET_MIDDAY, BUCKET_EVENING]

MIN_SAMPLES = 5       # minimum done logs required before a learned pattern is used
LOOKBACK_DAYS = 30    # logs older than this are excluded from pattern computation


@dataclass(frozen=True)
class HabitPattern:
    """A learned time-of-day preference for one habit.

    start_mins and end_mins are minutes from midnight in the user's local
    timezone, matching the convention used throughout engine.py.

    dominant_fraction:
        Fraction of qualifying completions that fell in the winning bucket.
        1.0 = always in this bucket. 0.5 = evenly split with another bucket.

    recency_score:
        Recency-weighted version of dominant_fraction.  Completions in the
        last 7 days get weight 1.0; days 8-14 get 0.7; days 15-30 get 0.4.
        A score lower than dominant_fraction signals that the user's behavior
        is shifting away from the learned bucket.
    """
    start_mins: int
    end_mins: int
    sample_count: int
    dominant_fraction: float
    recency_score: float


def _classify_minute(minute_of_day: int) -> Optional[tuple[int, int]]:
    """Return the bucket (start, end) that contains the given minute, or None."""
    for bucket in _BUCKETS:
        if bucket[0] <= minute_of_day < bucket[1]:
            return bucket
    return None


def _recency_weight(ts: datetime, now_utc: datetime) -> float:
    """Return a recency weight for a completion timestamp.

    More recent completions carry more weight when computing recency_score.
    Completions older than LOOKBACK_DAYS are excluded by the SQL query and
    should not appear here, but get 0.0 as a safety net.
    """
    age_days = (now_utc - ts.astimezone(timezone.utc)).days
    if age_days <= 7:
        return 1.0
    if age_days <= 14:
        return 0.7
    if age_days <= 30:
        return 0.4
    return 0.0


async def compute_habit_pattern(
    habit_id: UUID,
    user_id: UUID,
    session: AsyncSession,
    *,
    timezone_str: str = "UTC",
) -> Optional[HabitPattern]:
    """Return the learned time-of-day preference for a single habit.

    Returns None if fewer than MIN_SAMPLES qualifying done logs exist within
    the LOOKBACK_DAYS window.

    Parameters
    ----------
    timezone_str:
        IANA timezone name (e.g. "America/New_York").  completed_at values
        are converted from UTC to this timezone before bucketing.
    """
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=LOOKBACK_DAYS)
    result = await session.execute(
        select(HabitLog.completed_at)
        .where(
            HabitLog.habit_id == habit_id,
            HabitLog.user_id == user_id,
            HabitLog.status == "done",
            HabitLog.completed_at.is_not(None),
            HabitLog.completed_at >= cutoff,
        )
    )
    timestamps = [row[0] for row in result]

    if len(timestamps) < MIN_SAMPLES:
        return None

    # Resolve timezone — fall back to UTC if the string is unrecognised.
    try:
        tz = ZoneInfo(timezone_str)
    except (ZoneInfoNotFoundError, Exception):
        _log.warning("pattern_service: unknown timezone %r, falling back to UTC", timezone_str)
        tz = ZoneInfo("UTC")

    # Count completions per bucket and accumulate recency weights.
    bucket_counts: dict[tuple[int, int], int] = {b: 0 for b in _BUCKETS}
    bucket_weights: dict[tuple[int, int], float] = {b: 0.0 for b in _BUCKETS}
    total_weight: float = 0.0

    for ts in timestamps:
        local_ts = ts.astimezone(tz)
        minute_of_day = local_ts.hour * 60 + local_ts.minute
        bucket = _classify_minute(minute_of_day)
        w = _recency_weight(ts, now_utc)
        total_weight += w
        if bucket is not None:
            bucket_counts[bucket] += 1
            bucket_weights[bucket] += w

    # Pick the majority bucket; tie-break by earlier start time.
    best_bucket = max(_BUCKETS, key=lambda b: (bucket_counts[b], -b[0]))

    if bucket_counts[best_bucket] == 0:
        # All completions were outside waking hours — no reliable signal.
        return None

    dominant_fraction = bucket_counts[best_bucket] / len(timestamps)
    recency_score = (
        bucket_weights[best_bucket] / total_weight if total_weight > 0 else 0.0
    )

    return HabitPattern(
        start_mins=best_bucket[0],
        end_mins=best_bucket[1],
        sample_count=len(timestamps),
        dominant_fraction=dominant_fraction,
        recency_score=recency_score,
    )


async def get_patterns_for_user(
    user_id: UUID,
    session: AsyncSession,
) -> dict[UUID, HabitPattern]:
    """Return a mapping of habit_id → HabitPattern for all active habits
    that have accumulated enough done logs.

    Habits below the MIN_SAMPLES threshold are omitted so the engine knows
    to use the category rule for them.
    """
    # Fetch the user's timezone once.
    user_result = await session.execute(
        select(User.timezone).where(User.id == user_id)
    )
    row = user_result.one_or_none()
    timezone_str = row[0] if row else "UTC"

    # Fetch all active habit IDs for this user.
    habits_result = await session.execute(
        select(Habit.id).where(Habit.user_id == user_id, Habit.active.is_(True))
    )
    habit_ids = [row[0] for row in habits_result]

    patterns: dict[UUID, HabitPattern] = {}
    for habit_id in habit_ids:
        pattern = await compute_habit_pattern(
            habit_id, user_id, session, timezone_str=timezone_str
        )
        if pattern is not None:
            patterns[habit_id] = pattern

    return patterns
