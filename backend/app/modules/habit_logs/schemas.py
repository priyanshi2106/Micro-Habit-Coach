from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.common.enums import HabitLogStatus


class HabitLogSummary(BaseModel):
    week_total: int
    week_done: int
    week_snoozed: int
    week_skipped: int
    current_streak: int


class HabitLogCreate(BaseModel):
    habit_id: UUID
    suggestion_id: Optional[UUID] = None
    status: HabitLogStatus
    completed_at: Optional[datetime] = None
    scheduled_window_start: Optional[time] = None
    scheduled_window_end: Optional[time] = None
    date: date


class HabitLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    habit_id: UUID
    habit_name: Optional[str] = None
    suggestion_id: Optional[UUID]
    status: str
    completed_at: Optional[datetime]
    scheduled_window_start: Optional[time]
    scheduled_window_end: Optional[time]
    calendar_date: date = Field(serialization_alias="date")
    created_at: datetime
