from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    # bcrypt hash — never store plaintext. See app/core/security.py.
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    habits: Mapped[list[Habit]] = relationship("Habit", back_populates="user")
    schedule_blocks: Mapped[list[ScheduleBlock]] = relationship(
        "ScheduleBlock", back_populates="user"
    )
    suggestions: Mapped[list[HabitSuggestion]] = relationship(
        "HabitSuggestion", back_populates="user"
    )
    habit_logs: Mapped[list[HabitLog]] = relationship("HabitLog", back_populates="user")
    # One-to-one — None when the user has not connected a calendar.
    calendar_connection: Mapped[Optional[CalendarConnection]] = relationship(
        "CalendarConnection", back_populates="user", uselist=False
    )
    # One-to-one — None until the user explicitly saves notification preferences.
    notification_preference: Mapped[Optional[NotificationPreference]] = relationship(
        "NotificationPreference", back_populates="user", uselist=False
    )
