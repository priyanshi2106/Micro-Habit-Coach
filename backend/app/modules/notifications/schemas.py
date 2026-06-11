"""Pydantic schemas for notification preferences and the pending-notification response."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Allowed values for notify_minutes_before.
ALLOWED_NOTIFY_MINUTES: frozenset[int] = frozenset({5, 10, 15, 30})

# Allowed values for confidence_threshold.
# Mapped to UI labels: 0.45 = Any, 0.65 = Medium, 0.80 = High.
ALLOWED_CONFIDENCE_THRESHOLDS: frozenset[float] = frozenset({0.45, 0.65, 0.80})


class NotificationPreferenceUpdate(BaseModel):
    """Body for PUT /notifications/preferences."""

    enabled: bool
    notify_minutes_before: int = Field(default=15)
    confidence_threshold: float = Field(default=0.65)

    @field_validator("notify_minutes_before")
    @classmethod
    def validate_minutes(cls, v: int) -> int:
        if v not in ALLOWED_NOTIFY_MINUTES:
            raise ValueError(
                f"notify_minutes_before must be one of {sorted(ALLOWED_NOTIFY_MINUTES)}"
            )
        return v

    @field_validator("confidence_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        # Round to 2 dp first to avoid floating-point representation issues
        # (e.g. 0.45000000001 caused by JSON serialisation).
        v = round(v, 2)
        if v not in ALLOWED_CONFIDENCE_THRESHOLDS:
            raise ValueError(
                f"confidence_threshold must be one of {sorted(ALLOWED_CONFIDENCE_THRESHOLDS)}"
            )
        return v


class NotificationPreferenceRead(BaseModel):
    """Response for GET /notifications/preferences and PUT /notifications/preferences."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None        # None when returning the default (no DB row yet)
    user_id: Optional[UUID] = None
    enabled: bool
    notify_minutes_before: int
    confidence_threshold: float
    # UTC timestamp of the last successfully acknowledged notification.
    # None until the user has acknowledged at least one notification.
    last_acknowledged_at: Optional[datetime] = None


class NotificationPendingResponse(BaseModel):
    """Response for GET /notifications/pending."""

    should_notify: bool
    # All fields below are only present when should_notify is True.
    habit_name: Optional[str] = None
    habit_duration_mins: Optional[int] = None
    window_start: Optional[str] = None    # "HH:MM" in user's local time
    window_end: Optional[str] = None      # "HH:MM" in user's local time
    suggestion_reason: Optional[str] = None
    confidence_score: Optional[float] = None


# Default preferences returned when no DB row exists yet.
DEFAULT_PREFERENCES = NotificationPreferenceRead(
    enabled=False,
    notify_minutes_before=15,
    confidence_threshold=0.65,
)
