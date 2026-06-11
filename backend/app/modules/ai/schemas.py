from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.modules.common.enums import HabitCategory

# Duration values allowed for AI-suggested habits.
# Keeps suggestions feeling like genuine micro-habits.
ALLOWED_DURATIONS: list[int] = [5, 10, 15, 20, 30]


def round_to_allowed_duration(value: int) -> int:
    """Round an arbitrary integer to the nearest value in ALLOWED_DURATIONS.
    When two values are equidistant the smaller one wins.
    """
    return min(ALLOWED_DURATIONS, key=lambda d: (abs(d - value), d))


class GoalSuggestionRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=200, strip_whitespace=True)


class HabitSuggestionDraft(BaseModel):
    """A single AI-generated habit candidate shown to the user for review.

    Difficulty is intentionally absent — the save layer always sets it to
    "easy" for v2.0 because the field has no functional role in the current
    rule engine or UI.
    """

    name: str = Field(min_length=1, max_length=255)
    category: HabitCategory
    duration_mins: int = Field(ge=1)
    reason: str = Field(max_length=200)

    @field_validator("category", mode="before")
    @classmethod
    def normalise_category(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower().strip()
        return v

    @field_validator("duration_mins", mode="before")
    @classmethod
    def snap_to_preset(cls, v: object) -> object:
        if isinstance(v, (int, float)):
            return round_to_allowed_duration(int(v))
        return v


class GoalSuggestionResponse(BaseModel):
    suggestions: list[HabitSuggestionDraft]
    source: Literal["ai", "fallback"]
    goal: str
    user_id: Optional[UUID] = None
