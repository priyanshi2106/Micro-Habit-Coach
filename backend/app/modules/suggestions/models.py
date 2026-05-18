from __future__ import annotations

import uuid
from datetime import date as date_type
from datetime import datetime, time
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HabitSuggestion(Base):
    __tablename__ = "habit_suggestions"
    __table_args__ = (UniqueConstraint("user_id", "calendar_date", name="uq_suggestion_user_day"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    suggested_window_start: Mapped[time] = mapped_column(Time, nullable=False)
    suggested_window_end: Mapped[time] = mapped_column(Time, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False)
    suggestion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    calendar_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="suggestions")
    habit: Mapped[Habit] = relationship("Habit", back_populates="suggestions")
    habit_logs: Mapped[list[HabitLog]] = relationship("HabitLog", back_populates="suggestion")
