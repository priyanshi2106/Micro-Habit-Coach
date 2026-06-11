"""Deterministic fallback insight generator for the Weekly Insight feature (v2.2).

Produces a coaching-style 2–4 sentence summary from WeeklyStats without
any external API calls.  Used when:
  - OpenAI is unavailable or no API key is configured,
  - the weekly total is below the minimum threshold (< 3 logs), or
  - OpenAI returns an unusable response.
"""
from __future__ import annotations

from app.modules.insights.schemas import WeeklyStats

# Minimum logs required before generating a meaningful insight.
# Below this, return an early-stage encouraging message instead.
MIN_LOGS_FOR_INSIGHT = 3


def generate_fallback_insight(stats: WeeklyStats) -> str:
    """Return a 2–4 sentence coaching-style insight derived purely from stats.

    Never raises.  Always returns a non-empty string.
    """
    if stats.total < MIN_LOGS_FOR_INSIGHT:
        return (
            "You're just getting started — keep logging your habits this week. "
            "Once you have a few more days of history, you'll see a personalised "
            "weekly insight here."
        )

    parts: list[str] = []

    # --- Opening: completion rate framing ---
    pct = int(stats.completion_rate * 100)
    if stats.completion_rate >= 0.8:
        opening = f"Strong week — you completed {pct}% of your habits."
    elif stats.completion_rate >= 0.5:
        opening = f"You completed {pct}% of your habits this week, a solid start."
    else:
        opening = (
            f"You logged {stats.done} habit{'s' if stats.done != 1 else ''} as done "
            f"out of {stats.total} this week."
        )
    parts.append(opening)

    # --- Pattern observation: best habit or best day ---
    if stats.best_habit and stats.best_day:
        parts.append(
            f"{stats.best_habit} was your most consistent habit, "
            f"and {stats.best_day} was your strongest day."
        )
    elif stats.best_habit:
        parts.append(f"{stats.best_habit} was your most consistent habit this week.")
    elif stats.best_day:
        parts.append(f"{stats.best_day} was your strongest day this week.")

    # --- Problem observation: most skipped habit or worst day ---
    if stats.most_skipped_habit:
        parts.append(
            f"{stats.most_skipped_habit} was skipped most often — "
            "consider adjusting its scheduled time or duration."
        )
    elif stats.worst_day and stats.worst_day != stats.best_day:
        parts.append(
            f"{stats.worst_day} had the most skips — "
            "it may help to plan something lighter on that day."
        )

    # --- Closing suggestion if we don't already have 3 parts ---
    if len(parts) < 2:
        if stats.completion_rate < 0.5:
            parts.append(
                "Try picking one habit to focus on next week rather than doing all of them."
            )
        else:
            parts.append("Keep the momentum going into next week.")

    return " ".join(parts)
