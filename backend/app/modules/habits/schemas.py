from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.common.enums import HabitCategory
from app.modules.habits.anchors import VALID_ANCHOR_KEYS


def _validate_anchor(v: object) -> object:
    """Shared anchor_event validator used in both HabitCreate and HabitUpdate.

    Accepts None (clear / not set) or a key that exists in the catalog.
    Rejects unknown strings with a clear error listing valid options.
    """
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("anchor_event must be a string or null")
    if v not in VALID_ANCHOR_KEYS:
        valid = sorted(VALID_ANCHOR_KEYS)
        raise ValueError(f"Unknown anchor '{v}'. Valid anchors: {valid}")
    return v


class HabitUpdate(BaseModel):
    """Partial update — only supplied fields are written.

    anchor_event can be:
    - omitted entirely  → no change to the stored anchor
    - a valid anchor key → updates the anchor
    - null              → clears the anchor
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    category: Optional[HabitCategory] = None
    duration_mins: Optional[int] = Field(default=None, ge=1, le=180)
    active: Optional[bool] = None
    anchor_event: Optional[str] = Field(default=None, max_length=255)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("anchor_event", mode="before")
    @classmethod
    def validate_anchor_event(cls, v: object) -> object:
        return _validate_anchor(v)


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

    @field_validator("anchor_event", mode="before")
    @classmethod
    def validate_anchor_event(cls, v: object) -> object:
        return _validate_anchor(v)


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
