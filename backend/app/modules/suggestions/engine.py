from __future__ import annotations

from dataclasses import dataclass, replace as dc_replace
from datetime import time
from typing import Optional, Tuple
from uuid import UUID

from app.modules.common.enums import HabitCategory

MINUTES_PER_DAY = 24 * 60

# Deterministic tie-break: higher-priority categories are considered first.
CATEGORY_PRIORITY: tuple[HabitCategory, ...] = (
    HabitCategory.MINDFULNESS,
    HabitCategory.PRODUCTIVITY,
    HabitCategory.MOVEMENT,
    HabitCategory.HEALTH,
    HabitCategory.LEARNING,
    HabitCategory.FINANCE,
    HabitCategory.SOCIAL,
)

# Preferred local-time buckets as half-open ranges in minutes-from-midnight [start, end).
CATEGORY_BUCKET_MINUTES: dict[HabitCategory, list[tuple[int, int]]] = {
    # mindfulness -> morning
    HabitCategory.MINDFULNESS: [(5 * 60, 12 * 60)],
    # movement -> morning or evening
    HabitCategory.MOVEMENT: [(5 * 60, 12 * 60), (17 * 60, 24 * 60)],
    # learning -> midday or evening
    HabitCategory.LEARNING: [(12 * 60, 16 * 60), (17 * 60, 24 * 60)],
    # productivity -> early day
    HabitCategory.PRODUCTIVITY: [(6 * 60, 11 * 60)],
    # finance -> any quiet slot (treat as full waking day; still constrained by free blocks)
    HabitCategory.FINANCE: [(0 * 60, 24 * 60)],
    # social -> evening
    HabitCategory.SOCIAL: [(17 * 60, 24 * 60)],
    # health -> morning or midday
    HabitCategory.HEALTH: [(6 * 60, 12 * 60), (12 * 60, 14 * 60)]
}


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def minutes_to_time(total: int) -> time:
    total = min(max(total, 0), 23 * 60 + 59)
    hour, minute = divmod(total, 60)
    return time(hour, minute, 0)


def intersect_intervals(a_lo: int, a_hi: int, b_lo: int, b_hi: int) -> Optional[Tuple[int, int]]:
    lo = max(a_lo, b_lo)
    hi = min(a_hi, b_hi)
    if lo >= hi:
        return None
    return lo, hi


@dataclass(frozen=True)
class FreeBlockDTO:
    start: time
    end: time


@dataclass(frozen=True)
class HabitDTO:
    id: UUID
    name: str
    category: str
    duration_mins: int
    # Populated by pick_today_suggestion when a learned pattern exists for this habit.
    # Represents (start_mins, end_mins) in minutes-from-midnight local time.
    learned_bucket: Optional[Tuple[int, int]] = None
    # Set by the service from habits.anchor_event via anchor_to_bucket().
    # Represents the user-defined anchor moment (e.g. "after lunch" → 750–840).
    anchor_bucket: Optional[Tuple[int, int]] = None
    # Display label for the anchor (e.g. "After lunch") — passed through to
    # SuggestionCandidate so the scorer can reference it in the reason copy.
    anchor_name: Optional[str] = None


@dataclass(frozen=True)
class SuggestionCandidate:
    habit_id: UUID
    habit_name: str
    category: HabitCategory
    window_start: time
    window_end: time
    reason: str
    # True when the window came from a learned pattern rather than a category rule.
    used_learned: bool = False
    # True when the window came from the user's anchor moment (highest priority).
    used_anchor: bool = False
    # Anchor display label forwarded from HabitDTO.anchor_name; None if no anchor set.
    anchor_name: Optional[str] = None


def _best_window_in_bucket(
    b_lo: int,
    b_hi: int,
    duration: int,
    free_blocks: list[FreeBlockDTO],
) -> Optional[Tuple[int, int]]:
    """Return the earliest feasible [lo, lo+duration) window within the given bucket.

    Shared by the anchor, learned-pattern, and category-rule layers so there
    is exactly one place that performs the block × bucket intersection logic.
    """
    best: Optional[Tuple[int, int]] = None
    for block in free_blocks:
        fs = time_to_minutes(block.start)
        fe = time_to_minutes(block.end)
        if fe <= fs:
            continue
        hit = intersect_intervals(fs, fe, b_lo, b_hi)
        if hit is None:
            continue
        lo, hi = hit
        if hi - lo < duration:
            continue
        cand = (lo, lo + duration)
        if best is None or cand[0] < best[0]:
            best = cand
    return best


def _best_window_for_habit(
    habit: HabitDTO,
    free_blocks: list[FreeBlockDTO],
) -> Optional[Tuple[int, int]]:
    """Return earliest feasible window across all category buckets for this habit."""
    try:
        cat = HabitCategory(habit.category)
    except ValueError:
        return None

    buckets = CATEGORY_BUCKET_MINUTES.get(cat)
    if not buckets:
        return None

    duration = max(1, habit.duration_mins)
    best: Optional[Tuple[int, int]] = None

    for b_lo, b_hi in buckets:
        cand = _best_window_in_bucket(b_lo, b_hi, duration, free_blocks)
        if cand is not None and (best is None or cand[0] < best[0]):
            best = cand

    return best


def _find_best_window(
    habit: HabitDTO,
    free_blocks: list[FreeBlockDTO],
) -> Tuple[Optional[Tuple[int, int]], bool, bool]:
    """Return (window, used_learned, used_anchor).

    Priority chain (highest → lowest):
    1. Anchor window  — explicit user intent ("I do this after lunch")
    2. Learned window — inferred from past completions (pattern_service)
    3. Category rule  — deterministic fallback

    Each layer falls through cleanly to the next when no free block overlaps.
    This means anchors are respected when possible but never block suggestions.
    """
    duration = max(1, habit.duration_mins)

    # 1. Anchor (explicit user preference)
    if habit.anchor_bucket is not None:
        b_lo, b_hi = habit.anchor_bucket
        win = _best_window_in_bucket(b_lo, b_hi, duration, free_blocks)
        if win is not None:
            return win, False, True

    # 2. Learned pattern
    if habit.learned_bucket is not None:
        b_lo, b_hi = habit.learned_bucket
        win = _best_window_in_bucket(b_lo, b_hi, duration, free_blocks)
        if win is not None:
            return win, True, False

    # 3. Category rule
    return _best_window_for_habit(habit, free_blocks), False, False


def pick_today_suggestion(
    habits: list[HabitDTO],
    free_blocks: list[FreeBlockDTO],
    # Caller passes habit_id → (start_mins, end_mins) derived from pattern_service.
    # When present, the matching habit's learned bucket is tried before the category rule.
    patterns: Optional[dict[UUID, Tuple[int, int]]] = None,
) -> Optional[SuggestionCandidate]:
    if not habits or not free_blocks:
        return None

    priority_index = {c: i for i, c in enumerate(CATEGORY_PRIORITY)}

    def sort_key(h: HabitDTO) -> tuple[int, str]:
        try:
            cat = HabitCategory(h.category)
            pri = priority_index.get(cat, 999)
        except ValueError:
            pri = 999
        return (pri, h.name.lower())

    for habit in sorted(habits, key=sort_key):
        # Augment with the learned bucket when the caller supplied one for this habit.
        if patterns and habit.id in patterns:
            habit = dc_replace(habit, learned_bucket=patterns[habit.id])

        win, used_learned, used_anchor = _find_best_window(habit, free_blocks)
        if win is None:
            continue
        lo, hi = win
        start_t = minutes_to_time(lo)
        end_t = minutes_to_time(hi)
        cat = HabitCategory(habit.category)
        # reason is intentionally empty here — the service calls the scorer
        # (scorer.compute_confidence) to produce the final user-readable copy.
        return SuggestionCandidate(
            habit_id=habit.id,
            habit_name=habit.name,
            category=cat,
            window_start=start_t,
            window_end=end_t,
            reason="",
            used_learned=used_learned,
            used_anchor=used_anchor,
            anchor_name=habit.anchor_name,
        )

    return None
