from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.common.enums import ScheduleBlockType


class ScheduleBlockCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday .. 6=Sunday")
    start_time: time
    end_time: time
    block_type: ScheduleBlockType

    @model_validator(mode="after")
    def end_after_start(self) -> "ScheduleBlockCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time on the same calendar day")
        return self


class ScheduleBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    day_of_week: int
    start_time: time
    end_time: time
    block_type: str
