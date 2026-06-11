"""NotificationPreference ORM model — one row per user, created on first opt-in.

Design notes
------------
- Row is never created until the user explicitly saves preferences (PUT).
  GET preferences returns sensible defaults when no row exists.
- enabled defaults to False: this feature is strict opt-in.
- last_acknowledged_at is the UTC timestamp of the last time the user's
  browser called POST /notifications/acknowledge after successfully displaying
  a notification.  It is null until that event occurs — it is NEVER set
  speculatively.  The "already notified today" check converts this UTC value
  to the user's local timezone before comparing dates.
- notify_minutes_before and confidence_threshold are constrained to the
  allowed values by the schema validators, not at the DB level.  This keeps
  the DB simple and lets us change the allowed set without a migration.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Master toggle — False until the user explicitly enables notifications.
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # How many minutes before suggested_window_start to show the notification.
    # Allowed values: 5, 10, 15, 30.
    notify_minutes_before: Mapped[int] = mapped_column(Integer, nullable=False, default=15)

    # Minimum confidence_score required to trigger a notification.
    # Mapped to UI labels: 0.45 = Any, 0.65 = Medium, 0.80 = High.
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.65)

    # UTC timestamp of the last successfully acknowledged notification.
    # Null = the user has never acknowledged a notification.
    # This field is ONLY written by POST /notifications/acknowledge — never speculatively.
    last_acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="notification_preference")
