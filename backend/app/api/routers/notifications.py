"""Notifications router.

Endpoints:
  GET  /notifications/preferences   — return current preferences or defaults
  PUT  /notifications/preferences   — upsert preferences
  GET  /notifications/pending       — check whether to notify now (read-only)
  POST /notifications/acknowledge   — record that a notification was shown
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser
from app.core.database import get_db
from app.modules.habit_logs.models import HabitLog
from app.modules.notifications.logic import should_send_notification
from app.modules.notifications.models import NotificationPreference
from app.modules.notifications.schemas import (
    DEFAULT_PREFERENCES,
    NotificationPendingResponse,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
)
from app.modules.suggestions.models import HabitSuggestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/preferences", response_model=NotificationPreferenceRead)
async def get_preferences(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    """Return the user's notification preferences.

    If the user has never saved preferences, returns the default values
    (enabled=False) without creating a DB row.  This allows the frontend
    to always render the preferences UI with a valid state.
    """
    pref = await _get_pref(session, current_user.id)
    if pref is None:
        return DEFAULT_PREFERENCES
    return NotificationPreferenceRead.model_validate(pref)


@router.put("/preferences", response_model=NotificationPreferenceRead)
async def upsert_preferences(
    payload: NotificationPreferenceUpdate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> NotificationPreferenceRead:
    """Create or update the user's notification preferences.

    Validates notify_minutes_before ∈ {5, 10, 15, 30} and
    confidence_threshold ∈ {0.45, 0.65, 0.80}.  Any other value returns 422.
    """
    pref = await _get_pref(session, current_user.id)

    if pref is None:
        pref = NotificationPreference(user_id=current_user.id)
        session.add(pref)
        logger.info("Created notification preferences for user %s", current_user.id)

    pref.enabled = payload.enabled
    pref.notify_minutes_before = payload.notify_minutes_before
    pref.confidence_threshold = payload.confidence_threshold

    await session.commit()
    await session.refresh(pref)
    return NotificationPreferenceRead.model_validate(pref)


@router.get("/pending", response_model=NotificationPendingResponse)
async def get_pending_notification(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> NotificationPendingResponse:
    """Check whether the user should be shown a habit notification right now.

    This endpoint is read-only and idempotent — safe to poll every 5 minutes.
    It does NOT set last_acknowledged_at; that is done by POST /acknowledge.

    Returns should_notify=True when:
    - notifications are enabled with confidence_threshold met,
    - the habit has not been logged as done/skipped today,
    - a notification has not been acknowledged today (local date),
    - and the current local time is within the notification window.
    """
    _no = NotificationPendingResponse(should_notify=False)

    pref = await _get_pref(session, current_user.id)
    if pref is None or not pref.enabled:
        return _no

    # Resolve the user's current local time.
    try:
        tz = ZoneInfo(current_user.timezone)
    except (ZoneInfoNotFoundError, KeyError):
        tz = ZoneInfo("UTC")

    now_local = datetime.now(tz)
    today_local = now_local.date()
    now_local_mins = now_local.hour * 60 + now_local.minute

    # Fetch today's suggestion (read-only; does not create one if absent).
    suggestion_res = await session.execute(
        select(HabitSuggestion)
        .options(selectinload(HabitSuggestion.habit))
        .where(
            HabitSuggestion.user_id == current_user.id,
            HabitSuggestion.calendar_date == today_local,
        )
    )
    suggestion = suggestion_res.scalar_one_or_none()
    if suggestion is None:
        return _no

    # Fetch today's most recent log status.
    log_res = await session.execute(
        select(HabitLog.status)
        .where(
            HabitLog.user_id == current_user.id,
            HabitLog.calendar_date == today_local,
        )
        .order_by(HabitLog.created_at.desc())
        .limit(1)
    )
    log_status: Optional[str] = log_res.scalar_one_or_none()

    # Convert suggestion window times to minutes-from-midnight.
    w_start = suggestion.suggested_window_start
    w_end = suggestion.suggested_window_end
    window_start_mins = w_start.hour * 60 + w_start.minute
    window_end_mins = w_end.hour * 60 + w_end.minute

    if not should_send_notification(
        enabled=pref.enabled,
        confidence_score=float(suggestion.confidence_score),
        confidence_threshold=pref.confidence_threshold,
        log_status=log_status,
        last_acknowledged_at=pref.last_acknowledged_at,
        today_local=today_local,
        user_timezone=current_user.timezone,
        now_local_mins=now_local_mins,
        window_start_mins=window_start_mins,
        window_end_mins=window_end_mins,
        notify_minutes_before=pref.notify_minutes_before,
    ):
        return _no

    # Format window times as "HH:MM" strings for the frontend.
    w_start_str = f"{w_start.hour:02d}:{w_start.minute:02d}"
    w_end_str = f"{w_end.hour:02d}:{w_end.minute:02d}"

    return NotificationPendingResponse(
        should_notify=True,
        habit_name=suggestion.habit.name if suggestion.habit else None,
        habit_duration_mins=suggestion.habit.duration_mins if suggestion.habit else None,
        window_start=w_start_str,
        window_end=w_end_str,
        suggestion_reason=suggestion.suggestion_reason,
        confidence_score=float(suggestion.confidence_score),
    )


@router.post("/acknowledge", status_code=204)
async def acknowledge_notification(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Record that the user's browser successfully displayed a notification.

    Sets last_acknowledged_at = now(UTC) on the NotificationPreference row.
    This is the ONLY place last_acknowledged_at is written — it represents the
    last successfully acknowledged notification, not a speculative delivery.

    If no preference row exists yet (edge case: user somehow bypassed PUT
    preferences), creates one with defaults.
    """
    pref = await _get_pref(session, current_user.id)
    if pref is None:
        pref = NotificationPreference(user_id=current_user.id)
        session.add(pref)

    pref.last_acknowledged_at = datetime.now(timezone.utc)
    await session.commit()
    logger.info(
        "Notification acknowledged for user %s at %s",
        current_user.id, pref.last_acknowledged_at,
    )
    return Response(status_code=204)


# ── Internal helper ───────────────────────────────────────────────────────────

async def _get_pref(
    session: AsyncSession, user_id: object
) -> Optional[NotificationPreference]:
    result = await session.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    return result.scalar_one_or_none()
