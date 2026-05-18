from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.schedules.models import ScheduleBlock
from app.modules.schedules.schemas import ScheduleBlockCreate


async def create_schedule_block(
    session: AsyncSession,
    *,
    user_id: UUID,
    payload: ScheduleBlockCreate,
) -> ScheduleBlock:
    block = ScheduleBlock(
        user_id=user_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        block_type=payload.block_type.value,
    )
    session.add(block)
    await session.commit()
    await session.refresh(block)
    return block


async def delete_schedule_block(
    session: AsyncSession,
    *,
    user_id: UUID,
    block_id: UUID,
) -> bool:
    """Delete a schedule block owned by the user. Returns False if not found."""
    res = await session.execute(
        select(ScheduleBlock).where(
            ScheduleBlock.id == block_id,
            ScheduleBlock.user_id == user_id,
        )
    )
    block = res.scalar_one_or_none()
    if block is None:
        return False
    await session.delete(block)
    await session.commit()
    return True


async def list_schedule_blocks(session: AsyncSession, *, user_id: UUID) -> list[ScheduleBlock]:
    stmt = (
        select(ScheduleBlock)
        .where(ScheduleBlock.user_id == user_id)
        .order_by(ScheduleBlock.day_of_week.asc(), ScheduleBlock.start_time.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())
