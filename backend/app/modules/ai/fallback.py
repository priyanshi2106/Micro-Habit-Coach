"""Keyword-based fallback suggestion engine.

Called whenever the AI service is unavailable, times out, returns unusable
output, or the OPENAI_API_KEY is absent.  Returns 3–5 HabitSuggestionDraft
objects derived from a hardcoded candidate list — no external dependency.

Matching is intentionally simple: if any keyword from a candidate's list
appears anywhere in the (lowercased) goal string, the candidate is included.
If nothing matches, the first 3 candidates are returned as a safe default.
"""
from __future__ import annotations

from app.modules.ai.schemas import HabitSuggestionDraft

# ---------------------------------------------------------------------------
# Candidate pool
# Each entry must satisfy HabitSuggestionDraft validation:
#   - duration_mins in ALLOWED_DURATIONS [5, 10, 15, 20, 30]
#   - category in HabitCategory enum
# "keywords" is used only for matching; it is stripped before Pydantic parse.
# ---------------------------------------------------------------------------
_CANDIDATES: list[dict] = [
    # ── Mindfulness ──────────────────────────────────────────────────────────
    {
        "name": "Box breathing",
        "category": "mindfulness",
        "duration_mins": 5,
        "reason": "Four counts in, hold, out — resets the nervous system in under five minutes.",
        "keywords": ["stress", "anxiety", "calm", "breath", "breathe", "overwhelm", "relax", "sleep", "rest"],
    },
    {
        "name": "Morning meditation",
        "category": "mindfulness",
        "duration_mins": 10,
        "reason": "Ten minutes of stillness before screens sets a calmer tone for the day.",
        "keywords": ["stress", "anxiety", "calm", "focus", "mindful", "present", "sleep", "morning"],
    },
    {
        "name": "Gratitude journal",
        "category": "mindfulness",
        "duration_mins": 5,
        "reason": "Writing three things you're grateful for shifts attention toward the positive.",
        "keywords": ["happy", "happiness", "grateful", "gratitude", "mood", "positive", "mindful"],
    },
    # ── Movement ─────────────────────────────────────────────────────────────
    {
        "name": "10-min walk",
        "category": "movement",
        "duration_mins": 10,
        "reason": "A short walk is one of the highest-leverage micro-habits for energy and mood.",
        "keywords": ["active", "exercise", "fit", "fitness", "energy", "tired", "sluggish", "walk", "move"],
    },
    {
        "name": "Morning stretch",
        "category": "movement",
        "duration_mins": 10,
        "reason": "Loosens overnight stiffness and signals the body it's time to wake up.",
        "keywords": ["stiff", "stretch", "back", "posture", "active", "morning", "wake", "tired", "sleep"],
    },
    {
        "name": "Evening yoga",
        "category": "movement",
        "duration_mins": 20,
        "reason": "A gentle flow before bed lowers cortisol and prepares the body for sleep.",
        "keywords": ["sleep", "rest", "relax", "yoga", "wind down", "evening", "stress", "calm"],
    },
    # ── Health ───────────────────────────────────────────────────────────────
    {
        "name": "Drink 8 glasses of water",
        "category": "health",
        "duration_mins": 5,
        "reason": "Consistent hydration improves energy, skin, and concentration.",
        "keywords": ["health", "hydrat", "water", "energy", "tired", "skin", "diet", "nutrition", "sleep"],
    },
    {
        "name": "Sleep by 10 PM",
        "category": "health",
        "duration_mins": 5,
        "reason": "Anchoring bedtime is the single most reliable way to improve sleep quality.",
        "keywords": ["sleep", "rest", "tired", "fatigue", "insomnia", "bedtime", "night"],
    },
    # ── Productivity ─────────────────────────────────────────────────────────
    {
        "name": "Plan tomorrow",
        "category": "productivity",
        "duration_mins": 5,
        "reason": "A 5-minute end-of-day review means fewer decisions the next morning.",
        "keywords": ["productive", "productivity", "focus", "work", "goal", "plan", "organis", "organiz", "busy"],
    },
    {
        "name": "Review priorities",
        "category": "productivity",
        "duration_mins": 5,
        "reason": "Identifying the one most important task prevents the busy-but-not-productive trap.",
        "keywords": ["productive", "productivity", "focus", "work", "priorit", "overwhelm", "goal", "achieve"],
    },
    # ── Learning ─────────────────────────────────────────────────────────────
    {
        "name": "Read 10 pages",
        "category": "learning",
        "duration_mins": 15,
        "reason": "Ten pages a day compounds to over 10 books a year — with zero pressure.",
        "keywords": ["read", "learn", "study", "book", "knowledge", "grow", "skill", "curious"],
    },
    {
        "name": "Listen to a podcast",
        "category": "learning",
        "duration_mins": 20,
        "reason": "Passive learning during commute or chores adds up quickly.",
        "keywords": ["learn", "study", "podcast", "audio", "knowledge", "skill", "curious", "grow"],
    },
    # ── Finance ──────────────────────────────────────────────────────────────
    {
        "name": "Track daily spending",
        "category": "finance",
        "duration_mins": 5,
        "reason": "Awareness of daily outflows is the foundation of any budgeting habit.",
        "keywords": ["money", "spend", "budget", "finance", "financial", "saving", "save", "debt", "wealth"],
    },
    # ── Social ───────────────────────────────────────────────────────────────
    {
        "name": "Check in with a friend",
        "category": "social",
        "duration_mins": 5,
        "reason": "One short message a day keeps relationships warm without requiring large blocks of time.",
        "keywords": ["social", "friend", "connect", "lonely", "relationship", "people", "network", "community"],
    },
]


def fallback_suggestions(goal: str) -> list[HabitSuggestionDraft]:
    """Return 3–5 HabitSuggestionDraft items matched to the goal by keyword.

    Falls back to the first 3 candidates if no keywords match.
    """
    goal_lower = goal.lower()
    matched: list[dict] = []
    seen_names: set[str] = set()

    for candidate in _CANDIDATES:
        if any(kw in goal_lower for kw in candidate["keywords"]):
            if candidate["name"] not in seen_names:
                # Strip internal-only "keywords" key before Pydantic parse.
                entry = {k: v for k, v in candidate.items() if k != "keywords"}
                matched.append(entry)
                seen_names.add(candidate["name"])

    results = matched[:5] if matched else [
        {k: v for k, v in c.items() if k != "keywords"} for c in _CANDIDATES[:3]
    ]
    return [HabitSuggestionDraft.model_validate(r) for r in results]
