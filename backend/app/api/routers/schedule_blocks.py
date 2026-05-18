from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.modules.schedules.schemas import ScheduleBlockCreate, ScheduleBlockRead
from app.modules.schedules.service import (
    create_schedule_block,
    delete_schedule_block,
    list_schedule_blocks,
)

router = APIRouter(prefix="/schedule-blocks", tags=["schedule-blocks"])


@router.get("", response_model=list[ScheduleBlockRead])
async def list_schedule_blocks_route(
    session: DbSession,
    user: CurrentUser,
) -> list[ScheduleBlockRead]:
    rows = await list_schedule_blocks(session, user_id=user.id)
    return [ScheduleBlockRead.model_validate(r) for r in rows]


@router.post("", response_model=ScheduleBlockRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_block_route(
    session: DbSession,
    user: CurrentUser,
    body: ScheduleBlockCreate,
) -> ScheduleBlockRead:
    try:
        block = await create_schedule_block(session, user_id=user.id, payload=body)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A block with the same day, time range, and type already exists.",
        )
    return ScheduleBlockRead.model_validate(block)


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_block_route(
    session: DbSession,
    user: CurrentUser,
    block_id: UUID,
) -> Response:
    deleted = await delete_schedule_block(session, user_id=user.id, block_id=block_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule block not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
