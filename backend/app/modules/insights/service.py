"""Weekly Insight service — orchestrates stats, AI, and fallback (v2.2).

Flow:
  1. compute_weekly_stats → WeeklyStats  (uses user's local timezone)
  2. if total < MIN_LOGS_FOR_INSIGHT → return fallback early-stage message
  3. get_insight_text(stats) → (text, source)
     a. no API key → fallback immediately
     b. OpenAI call → parse response
     c. any failure → fallback
  4. log weekly_insight_generated
  5. return WeeklyInsightResponse
"""
from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.analytics.logger import log_event
from app.modules.insights.fallback import MIN_LOGS_FOR_INSIGHT, generate_fallback_insight
from app.modules.insights.prompt import build_insight_prompt, parse_insight_response
from app.modules.insights.schemas import WeeklyInsightResponse, WeeklyStats
from app.modules.insights.stats import compute_weekly_stats

_log = logging.getLogger(__name__)

_MODEL = "gpt-4o-mini"


async def _get_insight_text(stats: WeeklyStats) -> tuple[str, Literal["ai", "fallback"]]:
    """Return (insight_text, source).

    Tries OpenAI first; falls back to the deterministic generator on any failure.
    Never raises.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        _log.info("insights_service: no API key — using fallback")
        return generate_fallback_insight(stats), "fallback"

    try:
        from openai import AsyncOpenAI  # lazy import — same pattern as ai/service.py

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a micro-habit coach. "
                        "Write concise, supportive, plain-text weekly insights. "
                        "No markdown, no bullet points."
                    ),
                },
                {"role": "user", "content": build_insight_prompt(stats)},
            ],
            temperature=0.6,
            max_tokens=200,
            timeout=10,
        )

        raw = response.choices[0].message.content or ""
        text = parse_insight_response(raw)

        if text is None:
            _log.warning("insights_service: AI response unusable — using fallback")
            return generate_fallback_insight(stats), "fallback"

        return text, "ai"

    except Exception as exc:
        _log.warning("insights_service: OpenAI call failed (%s) — using fallback", exc)
        return generate_fallback_insight(stats), "fallback"


async def get_weekly_insight(
    user_id: UUID,
    session: AsyncSession,
    *,
    timezone_str: str = "UTC",
) -> WeeklyInsightResponse:
    """Main entry point for GET /insights/weekly."""
    stats, week_start, week_end = await compute_weekly_stats(
        user_id, session, timezone_str=timezone_str
    )

    has_enough_data = stats.total >= MIN_LOGS_FOR_INSIGHT

    if not has_enough_data:
        insight: str = generate_fallback_insight(stats)
        source: Literal["ai", "fallback"] = "fallback"
    else:
        insight, source = await _get_insight_text(stats)

    try:
        log_event(
            "weekly_insight_generated",
            {
                "user_id": str(user_id),
                "source": source,
                "completion_rate": stats.completion_rate,
                "week_start": str(week_start),
                "has_enough_data": has_enough_data,
            },
        )
    except Exception:
        pass

    return WeeklyInsightResponse(
        week_start=week_start,
        week_end=week_end,
        stats=stats,
        insight=insight,
        source=source,
        has_enough_data=has_enough_data,
    )
