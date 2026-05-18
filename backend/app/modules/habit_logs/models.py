from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HabitLog(Base):
    __tablename__ = "habit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    suggestion_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habit_suggestions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_window_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    scheduled_window_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    calendar_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="habit_logs")
    habit: Mapped[Habit] = relationship("Habit", back_populates="habit_logs")
    suggestion: Mapped[Optional[HabitSuggestion]] = relationship(
        "HabitSuggestion", back_populates="habit_logs"
    )
