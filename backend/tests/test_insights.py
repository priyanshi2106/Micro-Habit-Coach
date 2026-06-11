"""Tests for the Weekly Insight feature (v2.2).

Covers:
- WeeklyStats aggregation (stats.py)
- Fallback insight generator (fallback.py)
- No-data threshold rule (service.py / fallback.py)
- Endpoint response shape (service.py)

All tests use mocked sessions — no DB or network required.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as _utc
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.modules.insights.fallback import MIN_LOGS_FOR_INSIGHT, generate_fallback_insight
from app.modules.insights.schemas import WeeklyStats
from app.modules.insights.service import get_weekly_insight


# ── Helpers ──────────────────────────────────────────────────────────────────

def _today() -> date:
    # Match compute_weekly_stats default: UTC date, not local-machine date.
    return datetime.now(_utc.utc).date()


def _days_ago(n: int) -> date:
    return _today() - timedelta(days=n)


def _rows(*entries: tuple) -> MagicMock:
    """Return a mock CursorResult whose .all() returns the given tuples."""
    mock = MagicMock()
    mock.all.return_value = list(entries)
    return mock


def _mock_session(query_result: MagicMock) -> AsyncMock:
    session = AsyncMock()
    session.execute.return_value = query_result
    return session


def _stats(**kwargs) -> WeeklyStats:
    defaults = dict(
        total=7, done=5, snoozed=1, skipped=1,
        completion_rate=0.71,
        best_day="Monday", worst_day="Friday",
        best_habit="Box breathing", most_skipped_habit="Evening walk",
    )
    defaults.update(kwargs)
    return WeeklyStats(**defaults)


# ── Stats aggregation ─────────────────────────────────────────────────────────

class TestComputeWeeklyStats:
    @pytest.mark.asyncio
    async def test_normal_week(self) -> None:
        from app.modules.insights.stats import compute_weekly_stats

        today = _today()
        rows = _rows(
            ("done",    today,             "Box breathing"),
            ("done",    today,             "Box breathing"),
            ("done",    _days_ago(1),      "Morning walk"),
            ("snoozed", _days_ago(2),      "Morning walk"),
            ("skipped", _days_ago(3),      "Evening walk"),
            ("done",    _days_ago(3),      "Box breathing"),
            ("skipped", _days_ago(4),      "Evening walk"),
        )
        session = _mock_session(rows)
        stats, week_start, week_end = await compute_weekly_stats(uuid4(), session)

        assert stats.total == 7
        assert stats.done == 4
        assert stats.snoozed == 1
        assert stats.skipped == 2
        assert round(stats.completion_rate, 2) == round(4 / 7, 2)
        assert stats.best_habit == "Box breathing"
        assert stats.most_skipped_habit == "Evening walk"
        assert week_end == today
        assert week_start == today - timedelta(days=6)

    @pytest.mark.asyncio
    async def test_no_logs_returns_zeroes(self) -> None:
        from app.modules.insights.stats import compute_weekly_stats

        session = _mock_session(_rows())
        stats, _, _ = await compute_weekly_stats(uuid4(), session)

        assert stats.total == 0
        assert stats.done == 0
        assert stats.completion_rate == 0.0
        assert stats.best_day is None
        assert stats.worst_day is None
        assert stats.best_habit is None
        assert stats.most_skipped_habit is None

    @pytest.mark.asyncio
    async def test_all_done_no_most_skipped(self) -> None:
        from app.modules.insights.stats import compute_weekly_stats

        today = _today()
        rows = _rows(
            ("done", today,         "Meditation"),
            ("done", _days_ago(1),  "Meditation"),
            ("done", _days_ago(2),  "Meditation"),
        )
        session = _mock_session(rows)
        stats, _, _ = await compute_weekly_stats(uuid4(), session)

        assert stats.completion_rate == 1.0
        assert stats.most_skipped_habit is None
        assert stats.worst_day is None

    @pytest.mark.asyncio
    async def test_completion_rate_rounds_to_two_decimals(self) -> None:
        from app.modules.insights.stats import compute_weekly_stats

        today = _today()
        rows = _rows(
            ("done",    today,        "H"),
            ("done",    today,        "H"),
            ("skipped", today,        "H"),
        )
        session = _mock_session(rows)
        stats, _, _ = await compute_weekly_stats(uuid4(), session)

        assert stats.completion_rate == round(2 / 3, 2)


# ── Fallback generator ────────────────────────────────────────────────────────

class TestGenerateFallbackInsight:
    def test_below_threshold_returns_early_stage_message(self) -> None:
        s = WeeklyStats(total=2, done=2, snoozed=0, skipped=0, completion_rate=1.0)
        result = generate_fallback_insight(s)
        assert "getting started" in result.lower() or "history" in result.lower()

    def test_zero_logs_returns_early_stage_message(self) -> None:
        s = WeeklyStats(total=0, done=0, snoozed=0, skipped=0, completion_rate=0.0)
        result = generate_fallback_insight(s)
        assert len(result) > 0

    def test_normal_stats_returns_non_empty_string(self) -> None:
        result = generate_fallback_insight(_stats())
        assert isinstance(result, str)
        assert len(result) > 20

    def test_high_completion_has_positive_opener(self) -> None:
        s = _stats(total=5, done=5, snoozed=0, skipped=0, completion_rate=1.0)
        result = generate_fallback_insight(s)
        assert "strong" in result.lower() or "100%" in result or "5 out of 5" in result.lower() or "completed 100" in result

    def test_low_completion_has_gentle_opener(self) -> None:
        s = _stats(total=7, done=2, snoozed=2, skipped=3, completion_rate=0.29,
                   best_habit=None, most_skipped_habit="Evening walk")
        result = generate_fallback_insight(s)
        # Should not open with "Strong week"
        assert not result.startswith("Strong week")

    def test_best_habit_mentioned_when_present(self) -> None:
        result = generate_fallback_insight(_stats(best_habit="Box breathing"))
        assert "Box breathing" in result

    def test_most_skipped_mentioned_when_present(self) -> None:
        result = generate_fallback_insight(_stats(most_skipped_habit="Evening walk"))
        assert "Evening walk" in result

    def test_output_is_4_sentences_or_fewer(self) -> None:
        result = generate_fallback_insight(_stats())
        # Split on sentence-ending punctuation as a rough proxy.
        sentences = [s.strip() for s in result.split(".") if s.strip()]
        assert len(sentences) <= 5  # allow slight tolerance for edge punctuation


# ── No-data threshold in service ─────────────────────────────────────────────

class TestNoDataThreshold:
    @pytest.mark.asyncio
    async def test_below_threshold_returns_fallback_without_ai(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When total < MIN_LOGS_FOR_INSIGHT, source must be 'fallback' and
        no OpenAI call should be attempted."""
        from app.modules.insights import service as svc

        ai_called = []

        async def fake_get_insight_text(stats: WeeklyStats):
            ai_called.append(True)
            return "AI text", "ai"

        monkeypatch.setattr(svc, "_get_insight_text", fake_get_insight_text)

        # Only 1 log — below threshold of MIN_LOGS_FOR_INSIGHT (3).
        today = _today()
        session = _mock_session(_rows(("done", today, "Habit A")))
        result = await get_weekly_insight(uuid4(), session)

        assert result.source == "fallback"
        assert result.has_enough_data is False
        assert len(result.insight) > 0
        assert ai_called == []  # AI must NOT have been called

    @pytest.mark.asyncio
    async def test_at_threshold_calls_ai_path(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.insights import service as svc

        async def fake_get_insight_text(stats: WeeklyStats):
            return "Great job this week.", "ai"

        monkeypatch.setattr(svc, "_get_insight_text", fake_get_insight_text)

        today = _today()
        # Exactly MIN_LOGS_FOR_INSIGHT logs.
        rows = _rows(*[("done", today, "H") for _ in range(MIN_LOGS_FOR_INSIGHT)])
        session = _mock_session(rows)
        result = await get_weekly_insight(uuid4(), session)

        assert result.source == "ai"
        assert result.has_enough_data is True
        assert result.insight == "Great job this week."


# ── Response shape ────────────────────────────────────────────────────────────

class TestResponseShape:
    @pytest.mark.asyncio
    async def test_response_has_all_required_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.insights import service as svc

        async def fake_get_insight_text(stats: WeeklyStats):
            return "You did well this week.", "fallback"

        monkeypatch.setattr(svc, "_get_insight_text", fake_get_insight_text)

        today = _today()
        rows = _rows(*[("done", today, "Meditation") for _ in range(5)])
        session = _mock_session(rows)
        result = await get_weekly_insight(uuid4(), session)

        assert hasattr(result, "week_start")
        assert hasattr(result, "week_end")
        assert hasattr(result, "stats")
        assert hasattr(result, "insight")
        assert hasattr(result, "source")
        assert hasattr(result, "has_enough_data")
        assert result.week_start <= result.week_end
        assert result.source in ("ai", "fallback")
        assert isinstance(result.insight, str) and len(result.insight) > 0
        assert isinstance(result.has_enough_data, bool)

    @pytest.mark.asyncio
    async def test_stats_fields_present_in_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.insights import service as svc

        async def fake_get_insight_text(stats: WeeklyStats):
            return "Some insight.", "fallback"

        monkeypatch.setattr(svc, "_get_insight_text", fake_get_insight_text)

        today = _today()
        rows = _rows(
            ("done", today, "Box breathing"),
            ("done", today, "Box breathing"),
            ("skipped", _days_ago(1), "Evening walk"),
            ("done", _days_ago(2), "Box breathing"),
        )
        session = _mock_session(rows)
        result = await get_weekly_insight(uuid4(), session)

        assert result.stats.total == 4
        assert result.stats.done == 3
        assert result.stats.skipped == 1
        assert result.stats.best_habit == "Box breathing"
        assert result.stats.most_skipped_habit == "Evening walk"
