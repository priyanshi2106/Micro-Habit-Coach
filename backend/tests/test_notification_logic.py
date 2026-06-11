"""Unit tests for notifications/logic.py — pure notification-timing functions.

All tests are pure Python: no database, no network, no async.
The logic functions are the core of the notification feature — these tests
verify every condition independently before the endpoints use them.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

import pytest

from app.modules.notifications.logic import (
    _local_date_of,
    is_in_notification_window,
    should_send_notification,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mins(h: int, m: int = 0) -> int:
    return h * 60 + m


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# Default values for should_send_notification that produce True.
# Override individual fields to test each condition.
_BASE = dict(
    enabled=True,
    confidence_score=0.75,
    confidence_threshold=0.65,
    log_status=None,
    last_acknowledged_at=None,
    today_local=date(2026, 6, 6),
    user_timezone="UTC",
    now_local_mins=_mins(8, 45),    # 8:45 local
    window_start_mins=_mins(9, 0),  # window 09:00–09:30
    window_end_mins=_mins(9, 30),
    notify_minutes_before=15,       # notification window: 8:45–9:30
)


# ── is_in_notification_window ─────────────────────────────────────────────────

class TestIsInNotificationWindow:
    # Window: start=09:00 (540), end=09:30 (570), notify_before=15
    # → notification window [08:45, 09:30)

    def test_exactly_at_notify_start_is_true(self) -> None:
        assert is_in_notification_window(_mins(8, 45), _mins(9), _mins(9, 30), 15) is True

    def test_one_minute_before_notify_start_is_false(self) -> None:
        assert is_in_notification_window(_mins(8, 44), _mins(9), _mins(9, 30), 15) is False

    def test_mid_window_is_true(self) -> None:
        assert is_in_notification_window(_mins(9, 10), _mins(9), _mins(9, 30), 15) is True

    def test_one_minute_before_window_end_is_true(self) -> None:
        assert is_in_notification_window(_mins(9, 29), _mins(9), _mins(9, 30), 15) is True

    def test_exactly_at_window_end_is_false(self) -> None:
        # Upper bound is exclusive: now == window_end → False
        assert is_in_notification_window(_mins(9, 30), _mins(9), _mins(9, 30), 15) is False

    def test_after_window_end_is_false(self) -> None:
        assert is_in_notification_window(_mins(10), _mins(9), _mins(9, 30), 15) is False

    def test_zero_notify_before_fires_at_window_start(self) -> None:
        assert is_in_notification_window(_mins(9), _mins(9), _mins(9, 30), 0) is True

    def test_zero_notify_before_before_window_start_is_false(self) -> None:
        assert is_in_notification_window(_mins(8, 59), _mins(9), _mins(9, 30), 0) is False

    def test_large_notify_before_extends_window(self) -> None:
        # notify_before=30: window starts at 08:30
        assert is_in_notification_window(_mins(8, 30), _mins(9), _mins(9, 30), 30) is True
        assert is_in_notification_window(_mins(8, 29), _mins(9), _mins(9, 30), 30) is False

    def test_window_start_equals_end_never_triggers(self) -> None:
        # Degenerate window — no valid notification time
        assert is_in_notification_window(_mins(9), _mins(9), _mins(9), 15) is False


# ── should_send_notification ──────────────────────────────────────────────────

class TestShouldSendAllTrue:
    def test_all_conditions_met_returns_true(self) -> None:
        assert should_send_notification(**_BASE) is True


class TestConditionEnabled:
    def test_disabled_returns_false(self) -> None:
        assert should_send_notification(**{**_BASE, "enabled": False}) is False

    def test_enabled_with_all_other_conditions_met_returns_true(self) -> None:
        assert should_send_notification(**{**_BASE, "enabled": True}) is True


class TestConditionConfidence:
    def test_below_threshold_returns_false(self) -> None:
        # score=0.64 < threshold=0.65
        assert should_send_notification(**{**_BASE, "confidence_score": 0.64}) is False

    def test_exactly_at_threshold_returns_true(self) -> None:
        assert should_send_notification(**{**_BASE, "confidence_score": 0.65}) is True

    def test_above_threshold_returns_true(self) -> None:
        assert should_send_notification(**{**_BASE, "confidence_score": 0.99}) is True

    def test_zero_threshold_any_score_passes(self) -> None:
        assert should_send_notification(**{**_BASE, "confidence_score": 0.0, "confidence_threshold": 0.0}) is True


class TestConditionLogStatus:
    def test_done_returns_false(self) -> None:
        assert should_send_notification(**{**_BASE, "log_status": "done"}) is False

    def test_skipped_returns_false(self) -> None:
        assert should_send_notification(**{**_BASE, "log_status": "skipped"}) is False

    def test_snoozed_does_not_block(self) -> None:
        # Snoozed ≠ done or skipped; user might still want a reminder
        assert should_send_notification(**{**_BASE, "log_status": "snoozed"}) is True

    def test_none_status_does_not_block(self) -> None:
        assert should_send_notification(**{**_BASE, "log_status": None}) is True


class TestConditionAlreadyAcknowledged:
    def test_acknowledged_same_local_date_returns_false(self) -> None:
        # Acknowledged at noon UTC on the same local day
        ack_utc = _utc(2026, 6, 6, 12, 0)
        assert should_send_notification(**{**_BASE, "last_acknowledged_at": ack_utc}) is False

    def test_acknowledged_yesterday_local_returns_true(self) -> None:
        # Acknowledged at 23:59 UTC yesterday (still yesterday in UTC)
        ack_utc = _utc(2026, 6, 5, 23, 59)
        assert should_send_notification(**{**_BASE, "last_acknowledged_at": ack_utc}) is True

    def test_none_means_never_acknowledged(self) -> None:
        assert should_send_notification(**{**_BASE, "last_acknowledged_at": None}) is True

    def test_timezone_aware_comparison_blocks_when_ack_is_today_local(self) -> None:
        """UTC timestamp that looks like yesterday in UTC but is *today* in the user's
        timezone must still block re-notification.

        2026-06-05 23:00 UTC = 2026-06-06 01:00 CEST (UTC+2) → acknowledged_local = 2026-06-06.
        today_local = 2026-06-06 → already acknowledged today → should return False.
        """
        ack_utc = _utc(2026, 6, 5, 23, 0)   # yesterday in UTC
        result = should_send_notification(
            **{
                **_BASE,
                "last_acknowledged_at": ack_utc,
                "today_local": date(2026, 6, 6),
                "user_timezone": "Europe/Berlin",   # UTC+2 → local date = 2026-06-06
            }
        )
        assert result is False

    def test_timezone_aware_comparison_allows_when_ack_is_yesterday_local(self) -> None:
        """UTC timestamp that converts to yesterday in the user's timezone must not block.

        2026-06-05 20:00 UTC = 2026-06-05 22:00 CEST (UTC+2) → acknowledged_local = 2026-06-05.
        today_local = 2026-06-06 → acknowledged yesterday → should return True.
        """
        ack_utc = _utc(2026, 6, 5, 20, 0)   # yesterday evening UTC
        result = should_send_notification(
            **{
                **_BASE,
                "last_acknowledged_at": ack_utc,
                "today_local": date(2026, 6, 6),
                "user_timezone": "Europe/Berlin",   # UTC+2 → local date = 2026-06-05
            }
        )
        assert result is True


class TestConditionTimingWindow:
    def test_too_early_returns_false(self) -> None:
        # 8:44 is before 8:45 notification start
        assert should_send_notification(**{**_BASE, "now_local_mins": _mins(8, 44)}) is False

    def test_exactly_at_notify_start_returns_true(self) -> None:
        assert should_send_notification(**{**_BASE, "now_local_mins": _mins(8, 45)}) is True

    def test_at_window_end_returns_false(self) -> None:
        assert should_send_notification(**{**_BASE, "now_local_mins": _mins(9, 30)}) is False

    def test_after_window_end_returns_false(self) -> None:
        assert should_send_notification(**{**_BASE, "now_local_mins": _mins(22, 0)}) is False


# ── _local_date_of ────────────────────────────────────────────────────────────

class TestLocalDateOf:
    def test_utc_date_preserved(self) -> None:
        ts = _utc(2026, 6, 6, 12, 0)
        assert _local_date_of(ts, "UTC") == date(2026, 6, 6)

    def test_positive_offset_can_advance_date(self) -> None:
        # 2026-06-06 23:00 UTC = 2026-06-07 01:00 Europe/Berlin (CEST, UTC+2)
        ts = _utc(2026, 6, 6, 23, 0)
        assert _local_date_of(ts, "Europe/Berlin") == date(2026, 6, 7)

    def test_negative_offset_can_retreat_date(self) -> None:
        # 2026-06-06 01:00 UTC = 2026-06-05 20:00 America/New_York (EDT, UTC-4)
        ts = _utc(2026, 6, 6, 1, 0)
        assert _local_date_of(ts, "America/New_York") == date(2026, 6, 5)

    def test_unknown_timezone_falls_back_to_utc(self) -> None:
        ts = _utc(2026, 6, 6, 12, 0)
        assert _local_date_of(ts, "Invalid/Timezone") == date(2026, 6, 6)
