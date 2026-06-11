"""Onboarding router — v2.0 AI-assisted habit suggestions."""
from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.modules.ai.schemas import GoalSuggestionRequest, GoalSuggestionResponse
from app.modules.ai.service import get_ai_suggestions
from app.modules.analytics.logger import log_event

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/goal-suggestions", response_model=GoalSuggestionResponse)
async def get_goal_suggestions(
    body: GoalSuggestionRequest,
    user: CurrentUser,
) -> GoalSuggestionResponse:
    """Return AI-generated starter habit suggestions for a given goal.

    Source is "ai" when OpenAI returned valid output, "fallback" otherwise.
    The endpoint never returns a 500 — all failures produce fallback suggestions.
    """
    suggestions, source = await get_ai_suggestions(body.goal)

    try:
        log_event("goal_suggestions_requested", {
            "user_id": str(user.id),
            "goal": body.goal,
            "source": source,
            "suggestions_returned": len(suggestions),
        })
    except Exception:
        pass

    return GoalSuggestionResponse(
        suggestions=suggestions,
        source=source,
        goal=body.goal,
        user_id=user.id,
    )
