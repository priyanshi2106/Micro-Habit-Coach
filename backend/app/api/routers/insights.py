from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.modules.analytics.logger import log_event
from app.modules.insights.schemas import WeeklyInsightResponse
from app.modules.insights.service import get_weekly_insight

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/weekly", response_model=WeeklyInsightResponse)
async def weekly_insight(
    session: DbSession,
    user: CurrentUser,
) -> WeeklyInsightResponse:
    result = await get_weekly_insight(user.id, session, timezone_str=user.timezone)
    try:
        log_event(
            "insight_viewed",
            {
                "user_id": str(user.id),
                "source": result.source,
                "week_start": str(result.week_start),
            },
        )
    except Exception:
        pass
    return result
