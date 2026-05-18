from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.common.enums import HabitCategory


class HabitUpdate(BaseModel):
    """Partial update — only supplied fields are written."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[HabitCategory] = None
    duration_mins: Optional[int] = Field(default=None, ge=1, le=180)
    active: Optional[bool] = None

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: HabitCategory
    duration_mins: int = Field(default=5, ge=1, le=180)
    difficulty: str = Field(default="easy", max_length=32)
    best_time_of_day: Optional[str] = Field(default=None, max_length=64)
    anchor_event: Optional[str] = Field(default=None, max_length=255)
    is_custom: bool = True
    active: bool = True

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class HabitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    category: str
    duration_mins: int
    difficulty: str
    best_time_of_day: Optional[str]
    anchor_event: Optional[str]
    is_custom: bool
    active: bool
    created_at: datetime
