"""Unit tests for app/modules/habits/pattern_service.py — Pattern Learning (v2.1 + v2.2).

The DB session is mocked so no real database is required.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.habits.pattern_service import (
    BUCKET_EVENING,
    BUCKET_MIDDAY,
    BUCKET_MORNING,
    MIN_SAMPLES,
    HabitPattern,
    _classify_minute,
    _recency_weight,
    compute_habit_pattern,
    get_patterns_for_user,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _utc(hour: int, minute: int = 0, days_ago: int = 3) -> datetime:
    """UTC datetime a few days ago at the given hour:minute.

    Defaults to 3 days ago so all timestamps fall within the 7-day
    high-weight window, giving recency_score = 1.0 for single-bucket tests.
    Use days_ago > 7 to test recency weight decay.
    """
    base = datetime.now(timezone.utc).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return base - timedelta(days=days_ago)


def _execute_returning_rows(rows: list) -> MagicMock:
    """Return a mock that behaves like an SQLAlchemy CursorResult (iterable)."""
    mock = MagicMock()
    mock.__iter__ = MagicMock(return_value=iter(rows))
    return mock


def _execute_returning_one(value) -> MagicMock:
    """Return a mock where .one_or_none() returns a single row tuple."""
    mock = MagicMock()
    mock.one_or_none.return_value = value
    return mock


def _mock_session(*side_effects) -> AsyncMock:
    """Build an AsyncMock session whose .execute() returns the given values in order."""
    session = AsyncMock()
    session.execute.side_effect = list(side_effects)
    return session


# ── _recency_weight ───────────────────────────────────────────────────────────

class TestRecencyWeight:
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def test_within_7_days_is_1(self) -> None:
        now = self._now()
        ts = now - timedelta(days=3)
        assert _recency_weight(ts, now) == 1.0

    def test_boundary_7_days_is_1(self) -> None:
        now = self._now()
        ts = now - timedelta(days=7)
        assert _recency_weight(ts, now) == 1.0

    def test_8_days_is_0_7(self) -> None:
        now = self._now()
        ts = now - timedelta(days=8)
        assert _recency_weight(ts, now) == 0.7

    def test_14_days_is_0_7(self) -> None:
        now = self._now()
        ts = now - timedelta(days=14)
        assert _recency_weight(ts, now) == 0.7

    def test_15_days_is_0_4(self) -> None:
        now = self._now()
        ts = now - timedelta(days=15)
        assert _recency_weight(ts, now) == 0.4

    def test_30_days_is_0_4(self) -> None:
        now = self._now()
        ts = now - timedelta(days=30)
        assert _recency_weight(ts, now) == 0.4

    def test_older_than_30_days_is_0(self) -> None:
        now = self._now()
        ts = now - timedelta(days=31)
        assert _recency_weight(ts, now) == 0.0


# ── _classify_minute ─────────────────────────────────────────────────────────

class TestClassifyMinute:
    def test_early_morning_is_none(self) -> None:
        assert _classify_minute(4 * 60) is None  # 04:00 — before waking hours

    def test_morning_start(self) -> None:
        assert _classify_minute(5 * 60) == BUCKET_MORNING

    def test_morning_mid(self) -> None:
        assert _classify_minute(8 * 60) == BUCKET_MORNING

    def test_morning_end_exclusive(self) -> None:
        assert _classify_minute(12 * 60) == BUCKET_MIDDAY

    def test_midday(self) -> None:
        assert _classify_minute(14 * 60) == BUCKET_MIDDAY

    def test_evening_start(self) -> None:
        assert _classify_minute(17 * 60) == BUCKET_EVENING

    def test_evening_mid(self) -> None:
        assert _classify_minute(20 * 60) == BUCKET_EVENING

    def test_midnight_boundary(self) -> None:
        assert _classify_minute(24 * 60) is None  # outside any bucket


# ── compute_habit_pattern ─────────────────────────────────────────────────────

class TestComputeHabitPattern:
    @pytest.mark.asyncio
    async def test_returns_none_below_min_samples(self) -> None:
        rows = [(_utc(7),) for _ in range(MIN_SAMPLES - 1)]
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_morning_pattern_for_morning_completions(self) -> None:
        # 5 completions all at 07:00, 3 days ago (within high-weight window).
        rows = [(_utc(7),) for _ in range(MIN_SAMPLES)]
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        assert (result.start_mins, result.end_mins) == BUCKET_MORNING
        assert result.sample_count == MIN_SAMPLES
        # All completions in one bucket → dominant_fraction = 1.0.
        assert result.dominant_fraction == 1.0
        # All recent (within 7 days) and all in bucket → recency_score = 1.0.
        assert result.recency_score == 1.0

    @pytest.mark.asyncio
    async def test_returns_evening_pattern_for_evening_completions(self) -> None:
        rows = [(_utc(19),) for _ in range(MIN_SAMPLES)]
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        assert (result.start_mins, result.end_mins) == BUCKET_EVENING
        assert result.dominant_fraction == 1.0

    @pytest.mark.asyncio
    async def test_unknown_timezone_falls_back_to_utc(self) -> None:
        rows = [(_utc(8),) for _ in range(MIN_SAMPLES)]
        session = _mock_session(_execute_returning_rows(rows))
        # Should not raise; uses UTC as fallback.
        result = await compute_habit_pattern(uuid4(), uuid4(), session,
                                             timezone_str="Mars/Olympus_Mons")
        assert result is not None
        assert (result.start_mins, result.end_mins) == BUCKET_MORNING

    @pytest.mark.asyncio
    async def test_all_completions_outside_waking_hours_returns_none(self) -> None:
        # Midnight to 4 AM — none of the three buckets cover this.
        rows = [(_utc(2),) for _ in range(MIN_SAMPLES)]
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is None

    @pytest.mark.asyncio
    async def test_majority_bucket_wins(self) -> None:
        # 2 morning, 5 evening → evening wins.
        morning_rows = [(_utc(7),) for _ in range(2)]
        evening_rows = [(_utc(19),) for _ in range(5)]
        rows = morning_rows + evening_rows
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        assert (result.start_mins, result.end_mins) == BUCKET_EVENING
        # 5 out of 7 completions are in evening.
        assert abs(result.dominant_fraction - 5/7) < 0.01

    @pytest.mark.asyncio
    async def test_tie_break_earlier_bucket_wins(self) -> None:
        # Equal counts in morning and midday → morning wins (earlier bucket).
        morning_rows = [(_utc(7),) for _ in range(3)]
        midday_rows  = [(_utc(13),) for _ in range(3)]
        rows = morning_rows + midday_rows
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        assert (result.start_mins, result.end_mins) == BUCKET_MORNING

    @pytest.mark.asyncio
    async def test_sample_count_reflects_all_qualifying_logs(self) -> None:
        rows = [(_utc(7),) for _ in range(8)]
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        assert result.sample_count == 8

    @pytest.mark.asyncio
    async def test_recency_score_lower_when_behavior_is_shifting(self) -> None:
        """Old completions in evening + new in morning → evening pattern but
        low recency_score because recent behavior differs from historical."""
        # 5 old evening completions (days_ago=20, weight 0.4)
        old_evening = [(_utc(19, days_ago=20),) for _ in range(5)]
        # 2 new morning completions (days_ago=2, weight 1.0) — below the
        # bucket win threshold but they shift the recency signal.
        new_morning = [(_utc(7, days_ago=2),) for _ in range(2)]
        rows = old_evening + new_morning
        session = _mock_session(_execute_returning_rows(rows))
        result = await compute_habit_pattern(uuid4(), uuid4(), session, timezone_str="UTC")
        assert result is not None
        # Evening should still win by count (5 > 2).
        assert (result.start_mins, result.end_mins) == BUCKET_EVENING
        # dominant_fraction = 5/7 ≈ 0.71
        assert abs(result.dominant_fraction - 5/7) < 0.01
        # recency_score should be less than dominant_fraction because recent
        # completions are in morning, not evening.
        assert result.recency_score < result.dominant_fraction


# ── get_patterns_for_user ─────────────────────────────────────────────────────

class TestGetPatternsForUser:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_habits(self) -> None:
        user_id = uuid4()
        session = _mock_session(
            _execute_returning_one(("UTC",)),   # User.timezone
            _execute_returning_rows([]),         # Habit.id — no habits
        )
        result = await get_patterns_for_user(user_id, session)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_pattern_for_habit_above_threshold(self) -> None:
        user_id = uuid4()
        habit_id = uuid4()
        morning_rows = [(_utc(7),) for _ in range(MIN_SAMPLES)]

        session = _mock_session(
            _execute_returning_one(("UTC",)),           # User.timezone
            _execute_returning_rows([(habit_id,)]),     # Habit.id
            _execute_returning_rows(morning_rows),      # HabitLog.completed_at
        )
        result = await get_patterns_for_user(user_id, session)
        assert habit_id in result
        assert isinstance(result[habit_id], HabitPattern)
        assert (result[habit_id].start_mins, result[habit_id].end_mins) == BUCKET_MORNING

    @pytest.mark.asyncio
    async def test_omits_habit_below_threshold(self) -> None:
        user_id = uuid4()
        habit_id = uuid4()
        sparse_rows = [(_utc(7),) for _ in range(MIN_SAMPLES - 1)]

        session = _mock_session(
            _execute_returning_one(("UTC",)),
            _execute_returning_rows([(habit_id,)]),
            _execute_returning_rows(sparse_rows),
        )
        result = await get_patterns_for_user(user_id, session)
        assert habit_id not in result
        assert result == {}

    @pytest.mark.asyncio
    async def test_missing_user_row_defaults_to_utc(self) -> None:
        """If the user row is not found, timezone should default to UTC without crashing."""
        user_id = uuid4()
        session = _mock_session(
            _execute_returning_one(None),   # User not found
            _execute_returning_rows([]),    # No habits
        )
        result = await get_patterns_for_user(user_id, session)
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_habits_independent_patterns(self) -> None:
        user_id = uuid4()
        h1, h2 = uuid4(), uuid4()
        morning_rows = [(_utc(7),) for _ in range(MIN_SAMPLES)]
        evening_rows = [(_utc(19),) for _ in range(MIN_SAMPLES)]

        session = _mock_session(
            _execute_returning_one(("UTC",)),
            _execute_returning_rows([(h1,), (h2,)]),
            _execute_returning_rows(morning_rows),   # h1 logs
            _execute_returning_rows(evening_rows),   # h2 logs
        )
        result = await get_patterns_for_user(user_id, session)
        assert h1 in result and h2 in result
        assert (result[h1].start_mins, result[h1].end_mins) == BUCKET_MORNING
        assert (result[h2].start_mins, result[h2].end_mins) == BUCKET_EVENING
