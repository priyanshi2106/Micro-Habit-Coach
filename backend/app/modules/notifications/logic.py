"""Pure notification-timing logic (no I/O, no DB, no async).

All functions take plain Python values and return plain Python values.
This design makes every condition independently unit-testable without any
database or network infrastructure.

Coordinate system
-----------------
Times are passed as minutes-from-midnight (int), matching the convention
used throughout suggestions/engine.py.  Callers are responsible for
converting datetime/time objects before calling these functions.

Notification window
-------------------
A notification is eligible when the current local time is in the half-open
interval:

    [window_start - notify_minutes_before, window_end)

- Before this interval: too early, user doesn't need a nudge yet.
- After window_end: the habit window has closed; do not notify.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_in_notification_window(
    now_local_mins: int,
    window_start_mins: int,
    window_end_mins: int,
    notify_minutes_before: int,
) -> bool:
    """Return True when now_local_mins is within the notification window.

    Window: [window_start_mins - notify_minutes_before, window_end_mins)
    """
    notify_start = window_start_mins - notify_minutes_before
    return notify_start <= now_local_mins < window_end_mins


def _local_date_of(ts_utc: datetime, user_timezone: str) -> date:
    """Convert a UTC timestamp to the user's local date."""
    try:
        tz = ZoneInfo(user_timezone)
    except (ZoneInfoNotFoundError, KeyError):
        tz = ZoneInfo("UTC")
    return ts_utc.astimezone(tz).date()


def should_send_notification(
    *,
    enabled: bool,
    confidence_score: float,
    confidence_threshold: float,
    log_status: Optional[str],
    last_acknowledged_at: Optional[datetime],
    today_local: date,
    user_timezone: str,
    now_local_mins: int,
    window_start_mins: int,
    window_end_mins: int,
    notify_minutes_before: int,
) -> bool:
    """Return True when all conditions for sending a notification are met.

    Conditions are checked in order of cheapness (no I/O — all are O(1)):

    1. notifications enabled
    2. suggestion confidence meets threshold
    3. habit not already done or skipped today
    4. notification not already acknowledged today
    5. current time is within the notification window

    Parameters
    ----------
    enabled:
        Value of NotificationPreference.enabled.
    confidence_score:
        confidence_score from the HabitSuggestion row.
    confidence_threshold:
        Minimum score required (from NotificationPreference).
    log_status:
        Today's HabitLog status ("done", "skipped", "snoozed") or None.
    last_acknowledged_at:
        UTC datetime of the last acknowledged notification, or None.
    today_local:
        The user's current local date.
    user_timezone:
        IANA timezone string (e.g. "America/New_York").
    now_local_mins:
        Current local time in minutes-from-midnight.
    window_start_mins:
        suggested_window_start in minutes-from-midnight.
    window_end_mins:
        suggested_window_end in minutes-from-midnight.
    notify_minutes_before:
        How early to start the notification window (from NotificationPreference).
    """
    # 1. Master toggle
    if not enabled:
        return False

    # 2. Confidence filter
    if confidence_score < confidence_threshold:
        return False

    # 3. Habit already resolved for today — no need to prompt
    if log_status in ("done", "skipped"):
        return False

    # 4. Already acknowledged a notification today (local date comparison)
    if last_acknowledged_at is not None:
        last_ack_local = _local_date_of(last_acknowledged_at, user_timezone)
        if last_ack_local >= today_local:
            return False

    # 5. Timing window check
    if not is_in_notification_window(
        now_local_mins, window_start_mins, window_end_mins, notify_minutes_before
    ):
        return False

    return True
