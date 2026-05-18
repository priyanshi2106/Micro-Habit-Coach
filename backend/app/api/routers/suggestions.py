from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.modules.suggestions.schemas import TodaySuggestionResponse
from app.modules.suggestions.service import get_or_create_today_suggestion

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("/today", response_model=TodaySuggestionResponse)
async def today_suggestion(session: DbSession, user: CurrentUser) -> TodaySuggestionResponse:
    return await get_or_create_today_suggestion(session, user=user)
