"""Confidence scorer for habit suggestions (v2.3 — anchor support).

Given the habit's learned pattern (if any), whether the engine used the
learned window, and whether an anchor moment drove the suggestion, this
module computes:

  - confidence_score  — float in [0.0, 1.0] stored with the suggestion row
  - reason            — one user-readable sentence stored as suggestion_reason

Design principles
-----------------
- Deterministic: same inputs always produce the same output.
- No I/O: pure function, easy to unit-test.
- Rule engine is the foundation: base_score is always >= 0.35.  The adaptive
  layer can add up to MAX_BOOST (0.40) on top.
- Anchors rank above rule/pattern base confidence but below a fully-established
  pattern, so they feel meaningful without over-promising precision.
- Transparent: the reason string reflects exactly what drove the score.

Scoring formula
---------------
    confidence_score = clamp(base_score + pattern_boost, 0.0, 1.0)

    pattern_boost = dominant_fraction
                    × recency_score
                    × data_reliability          # saturates at RELIABLE_SAMPLES
                    × MAX_BOOST

Base scores
-----------
    0.50  — anchor used (explicit user preference for this moment)
    0.45  — rule match (no pattern, or learned window successfully used)
    0.35  — pattern existed but engine fell back to rule/anchor (preferred slot
            had no free-block overlap today)

Score examples
--------------
    No history, rule match                                     →  0.45
    Anchor set and used, no history                            →  0.50
    Anchor set and used, 10 samples consistent                 →  ~0.86 (capped 1.0)
    5 samples, 80% in bucket, recent                           →  ~0.61
    10 samples, 90% consistent, recent                         →  ~0.79
    Pattern present but engine fell back (weak)                →  ~0.35
    Pattern present but engine fell back (strong, 10 samp.)    →  ~0.69
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.modules.habits.pattern_service import HabitPattern

# ── Tuning constants ──────────────────────────────────────────────────────────
MAX_BOOST = 0.40          # maximum the adaptive layer can add to the base score
RELIABLE_SAMPLES = 10     # sample count at which data_reliability saturates at 1.0
_SAMPLES_FOR_COPY = 7     # below this, mention sample count in the reason

_BASE_ANCHOR   = 0.50     # user set an explicit anchor and it was used
_BASE_RULE     = 0.45     # confident rule match (no anchor, no pattern fallback)
_BASE_FALLBACK = 0.35     # preferred window unavailable — engine fell back


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ConfidenceResult:
    score: float    # 0.0 – 1.0, rounded to 2 decimal places
    reason: str     # one user-readable sentence


def compute_confidence(
    pattern: Optional[HabitPattern],
    used_learned: bool,
    category: str,
    habit_name: str,
    used_anchor: bool = False,
    anchor_name: Optional[str] = None,
) -> ConfidenceResult:
    """Compute a confidence score and reason for a suggestion.

    Parameters
    ----------
    pattern:
        The habit's learned ``HabitPattern`` (from pattern_service), or None
        if no pattern was available (threshold not met).
    used_learned:
        True when the engine placed the suggestion in the learned-pattern window.
    category:
        The habit's category string (e.g. ``"mindfulness"``).
    habit_name:
        Display name of the habit — used in reason copy.
    used_anchor:
        True when the engine placed the suggestion in the anchor window.
    anchor_name:
        Display label of the anchor (e.g. ``"After lunch"``), or None if no
        anchor is set for this habit.  Should be non-None whenever
        ``anchor_name is not None`` even if ``used_anchor=False`` (anchor was
        set but the slot was unavailable today).
    """
    # ── Base score ────────────────────────────────────────────────────────────
    if used_anchor:
        # Explicit user intent — anchor window was free and was used.
        base = _BASE_ANCHOR
    elif pattern is None or used_learned:
        # No pattern, or learned window was successfully used.
        base = _BASE_RULE
    else:
        # Preferred window (anchor or pattern) was unavailable today.
        base = _BASE_FALLBACK

    # ── Pattern boost (stacks on top of any base, including anchor) ───────────
    boost = 0.0
    if pattern is not None:
        data_reliability = min(pattern.sample_count / RELIABLE_SAMPLES, 1.0)
        boost = (
            pattern.dominant_fraction
            * pattern.recency_score
            * data_reliability
            * MAX_BOOST
        )

    score = round(min(base + boost, 1.0), 2)

    # ── Reason copy ──────────────────────────────────────────────────────────
    reason = _build_reason(
        pattern, used_learned, category, habit_name,
        used_anchor=used_anchor, anchor_name=anchor_name,
    )

    return ConfidenceResult(score=score, reason=reason)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _bucket_label(start_mins: int) -> str:
    """Convert bucket start in minutes-from-midnight to a display label."""
    if start_mins < 12 * 60:
        return "morning"
    if start_mins < 17 * 60:
        return "midday"
    return "evening"


def _build_reason(
    pattern: Optional[HabitPattern],
    used_learned: bool,
    category: str,
    habit_name: str,
    used_anchor: bool = False,
    anchor_name: Optional[str] = None,
) -> str:
    # ── Anchor cases ──────────────────────────────────────────────────────────
    if anchor_name is not None:
        if used_anchor:
            # Anchor window was free and used.
            return f"Scheduled {anchor_name.lower()}, as you prefer."
        else:
            # Anchor was set but the slot was unavailable today.
            return (
                f"Your {anchor_name.lower()} slot wasn't free — "
                f"this is your best available window today."
            )

    # ── No anchor — pattern-based or rule-based copy ──────────────────────────
    if pattern is None:
        return f"Good time for {category} habits in your schedule."

    bucket = _bucket_label(pattern.start_mins)

    if not used_learned:
        return (
            f"Your usual {bucket} slot wasn't free — "
            f"this is your best available window today."
        )

    pct = round(pattern.dominant_fraction * 100)

    if pattern.sample_count < _SAMPLES_FOR_COPY:
        return (
            f"You've done {habit_name} in the {bucket} "
            f"{pattern.sample_count} times — still building your pattern."
        )

    if pct >= 80:
        return f"Your history shows you consistently do {habit_name} in the {bucket}."

    return f"You do {habit_name} in the {bucket} {pct}% of the time."
