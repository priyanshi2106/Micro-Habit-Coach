"""Load sample rows for local development.

Run from `backend/`:

  python -m app.seed

Requires PostgreSQL reachable via `DATABASE_URL` / default compose settings.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.core.database import get_session_factory, init_db_schema
from app.modules.common.enums import HabitCategory, ScheduleBlockType
from app.modules.habits.schemas import HabitCreate
from app.modules.habits.service import create_habit
from app.modules.schedules.schemas import ScheduleBlockCreate
from app.modules.schedules.service import create_schedule_block
from app.modules.users.schemas import UserCreate
from app.modules.users.service import create_user, get_user_by_email


async def run() -> None:
    await init_db_schema()
    factory = get_session_factory()
    async with factory() as session:
        if await get_user_by_email(session, "seed@example.com"):
            print("Seed already applied (user seed@example.com exists).")
            return

        user = await create_user(
            session,
            UserCreate(
                name="Seed User",
                email="seed@example.com",
                timezone="America/Los_Angeles",
            ),
        )

        await create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                name="Box breathing",
                category=HabitCategory.MINDFULNESS,
                duration_mins=2,
            ),
        )
        await create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                name="Walk the block",
                category=HabitCategory.MOVEMENT,
                duration_mins=5,
            ),
        )

        tz = ZoneInfo(user.timezone)
        dow = datetime.now(tz).weekday()

        await create_schedule_block(
            session,
            user_id=user.id,
            payload=ScheduleBlockCreate(
                day_of_week=dow,
                start_time=time(6, 0),
                end_time=time(11, 0),
                block_type=ScheduleBlockType.FREE,
            ),
        )

        print(f"Seeded user id (send as X-User-Id header): {user.id}")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
