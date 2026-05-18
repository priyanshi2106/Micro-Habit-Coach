from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HabitSnippet(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str


class SuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    habit_id: UUID
    habit: HabitSnippet
    suggested_window_start: time
    suggested_window_end: time
    source: str
    confidence_score: float
    suggestion_reason: Optional[str]
    calendar_date: date = Field(serialization_alias="date")
    created_at: datetime


class TodaySuggestionResponse(BaseModel):
    date: date
    suggestion: Optional[SuggestionRead]
    # Status of the most recent log for today's suggestion, if any.
    # Used by the frontend to restore resolved state across navigation.
    today_log_status: Optional[str] = None
