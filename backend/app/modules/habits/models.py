from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    duration_mins: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, default="easy")
    best_time_of_day: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    anchor_event: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="habits")
    suggestions: Mapped[list[HabitSuggestion]] = relationship(
        "HabitSuggestion", back_populates="habit"
    )
    habit_logs: Mapped[list[HabitLog]] = relationship("HabitLog", back_populates="habit")
