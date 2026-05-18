from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "day_of_week",
            "start_time",
            "end_time",
            "block_type",
            name="uq_schedule_block_slot",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    block_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    user: Mapped[User] = relationship("User", back_populates="schedule_blocks")
