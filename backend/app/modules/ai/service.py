"""AI habit suggestion service.

Calls OpenAI to turn a user's goal string into 3–5 structured habit drafts.
Falls back to the keyword engine on any failure — timeout, bad JSON,
validation error, or missing API key — so the endpoint never returns a 500.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.config import get_settings
from app.modules.ai.fallback import fallback_suggestions
from app.modules.ai.schemas import (
    ALLOWED_DURATIONS,
    HabitSuggestionDraft,
    round_to_allowed_duration,
)
from app.modules.common.enums import HabitCategory

_log = logging.getLogger(__name__)

# The model must be good enough to follow a structured JSON schema reliably.
# gpt-4o-mini is fast, cheap, and accurate enough for this narrow task.
_MODEL = "gpt-4o-mini"
_MIN_SUGGESTIONS = 3
_MAX_SUGGESTIONS = 5

_ALLOWED_CATEGORIES = [c.value for c in HabitCategory]
_ALLOWED_DURATIONS_STR = ", ".join(str(d) for d in ALLOWED_DURATIONS)


def _build_prompt(goal: str) -> str:
    return f"""You are a micro-habit coach. A user wants to: "{goal}".

Suggest {_MIN_SUGGESTIONS} to {_MAX_SUGGESTIONS} realistic micro-habits that help with this goal.

Rules:
- Each habit must have a short, specific name (max 8 words).
- category must be one of: {", ".join(_ALLOWED_CATEGORIES)}
- duration_mins must be one of: {_ALLOWED_DURATIONS_STR}
- reason must be one sentence explaining why this habit helps the goal (max 200 characters).
- Do not suggest habits that require equipment, subscriptions, or other people.
- Prefer habits that take 5–15 minutes.

Respond with valid JSON only, in this exact shape:
{{
  "suggestions": [
    {{
      "name": "...",
      "category": "...",
      "duration_mins": 5,
      "reason": "..."
    }}
  ]
}}"""


def _parse_and_validate(raw: str) -> Optional[list[HabitSuggestionDraft]]:
    """Parse raw JSON string from OpenAI and validate each item.

    Returns None if the output is unusable (triggers fallback).
    Invalid individual items are skipped; if fewer than _MIN_SUGGESTIONS
    remain, None is returned.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _log.warning("ai_service: JSON parse failed")
        return None

    raw_list = data.get("suggestions")
    if not isinstance(raw_list, list) or len(raw_list) == 0:
        _log.warning("ai_service: missing or empty suggestions list")
        return None

    valid: list[HabitSuggestionDraft] = []
    for item in raw_list[:_MAX_SUGGESTIONS]:
        try:
            # Snap duration before Pydantic so the validator always sees
            # a clean preset value.
            if isinstance(item.get("duration_mins"), (int, float)):
                item["duration_mins"] = round_to_allowed_duration(int(item["duration_mins"]))
            draft = HabitSuggestionDraft.model_validate(item)
            valid.append(draft)
        except Exception as exc:
            _log.debug("ai_service: skipping invalid item %s — %s", item, exc)

    if len(valid) < _MIN_SUGGESTIONS:
        _log.warning(
            "ai_service: only %d valid suggestions after validation (need %d)",
            len(valid),
            _MIN_SUGGESTIONS,
        )
        return None

    return valid


async def get_ai_suggestions(goal: str) -> tuple[list[HabitSuggestionDraft], str]:
    """Return (suggestions, source) where source is 'ai' or 'fallback'.

    Never raises — all failures produce a fallback result.
    """
    settings = get_settings()

    if not settings.openai_api_key:
        _log.info("ai_service: no API key — using fallback")
        return fallback_suggestions(goal), "fallback"

    try:
        from openai import AsyncOpenAI  # imported lazily so missing key never crashes import

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful micro-habit coach. "
                        "Always respond with valid JSON matching the requested schema."
                    ),
                },
                {"role": "user", "content": _build_prompt(goal)},
            ],
            temperature=0.7,
            max_tokens=600,
            timeout=10,
        )

        raw = response.choices[0].message.content or ""
        suggestions = _parse_and_validate(raw)

        if suggestions is None:
            _log.warning("ai_service: validation failed — using fallback")
            return fallback_suggestions(goal), "fallback"

        return suggestions, "ai"

    except Exception as exc:
        _log.warning("ai_service: OpenAI call failed (%s) — using fallback", exc)
        return fallback_suggestions(goal), "fallback"
