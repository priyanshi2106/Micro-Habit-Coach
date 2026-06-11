"""Prompt-building and response-parsing helpers for Weekly Insight (v2.2).

These functions are pure (no I/O, no async) so they are easy to unit-test.
The actual OpenAI call is made in insights/service.py following the same
pattern as modules/ai/service.py.
"""
from __future__ import annotations

from typing import Optional

from app.modules.insights.schemas import WeeklyStats


def build_insight_prompt(stats: WeeklyStats) -> str:
    """Build the user-turn prompt sent to the LLM.

    The prompt is data-driven: every available stat is included so the model
    can produce a specific, non-generic response.
    """
    lines = [
        "You are a supportive micro-habit coach writing a weekly summary for a user.",
        "",
        "Here are their habit stats for the last 7 days:",
        f"- Total logs: {stats.total}",
        f"- Done: {stats.done}",
        f"- Snoozed: {stats.snoozed}",
        f"- Skipped: {stats.skipped}",
        f"- Completion rate: {int(stats.completion_rate * 100)}%",
    ]

    if stats.best_day:
        lines.append(f"- Best day (most done): {stats.best_day}")
    if stats.worst_day:
        lines.append(f"- Worst day (most skipped): {stats.worst_day}")
    if stats.best_habit:
        lines.append(f"- Most completed habit: {stats.best_habit}")
    if stats.most_skipped_habit:
        lines.append(f"- Most skipped habit: {stats.most_skipped_habit}")

    lines += [
        "",
        "Write a weekly insight with exactly these three parts:",
        "1. One positive observation (specific to their data, not generic praise).",
        "2. One pattern or problem observation (specific habit or day if available).",
        "3. One concrete, actionable suggestion for next week.",
        "",
        "Rules:",
        "- Total length: 2 to 4 sentences.",
        "- Tone: warm, direct, and coaching — not corporate or preachy.",
        "- Do not use bullet points, headers, or markdown.",
        "- Do not repeat the stats back verbatim.",
        "- Respond with plain text only.",
    ]

    return "\n".join(lines)


def parse_insight_response(raw: str) -> Optional[str]:
    """Extract a usable insight string from the raw LLM response.

    Returns None if the response is empty or too short to be useful
    (triggers fallback in the caller).
    """
    text = raw.strip()
    if len(text) < 20:
        return None
    # Truncate at a safe character limit to avoid runaway responses.
    return text[:1000]
