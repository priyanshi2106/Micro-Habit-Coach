from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.modules.habit_logs.schemas import HabitLogCreate, HabitLogRead, HabitLogSummary
from app.modules.habit_logs.service import create_habit_log, get_log_summary, list_habit_logs

router = APIRouter(prefix="/habit-logs", tags=["habit-logs"])


@router.post("", response_model=HabitLogRead, status_code=status.HTTP_201_CREATED)
async def create_habit_log_route(
    session: DbSession,
    user: CurrentUser,
    body: HabitLogCreate,
) -> HabitLogRead:
    log = await create_habit_log(session, user_id=user.id, payload=body)
    return HabitLogRead.model_validate(log)


@router.get("/summary", response_model=HabitLogSummary)
async def get_log_summary_route(
    session: DbSession,
    user: CurrentUser,
) -> HabitLogSummary:
    return await get_log_summary(session, user_id=user.id)


@router.get("", response_model=list[HabitLogRead])
async def list_habit_logs_route(
    session: DbSession,
    user: CurrentUser,
    limit: int = 50,
) -> list[HabitLogRead]:
    logs = await list_habit_logs(session, user_id=user.id, limit=limit)
    return [HabitLogRead(**l.__dict__, habit_name=l.habit.name) for l in logs]