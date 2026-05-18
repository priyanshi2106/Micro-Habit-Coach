from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class SuggestionCandidate:
    habit_id: UUID
    habit_name: str
    category: HabitCategory
    window_start: time
    window_end: time
    reason: str


def _best_window_for_habit(
    habit: HabitDTO,
    free_blocks: list[FreeBlockDTO],
) -> Optional[Tuple[int, int]]:
    """Return earliest feasible window as minute range [lo, hi) where hi-lo >= duration."""
    try:
        cat = HabitCategory(habit.category)
    except ValueError:
        return None

    buckets = CATEGORY_BUCKET_MINUTES.get(cat)
    if not buckets:
        return None

    best: Optional[Tuple[int, int]] = None
    duration = max(1, habit.duration_mins)

    for block in free_blocks:
        fs = time_to_minutes(block.start)
        fe = time_to_minutes(block.end)
        if fe <= fs:
            continue

        for b_lo, b_hi in buckets:
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


def pick_today_suggestion(
    habits: list[HabitDTO],
    free_blocks: list[FreeBlockDTO],
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
        win = _best_window_for_habit(habit, free_blocks)
        if win is None:
            continue
        lo, hi = win
        start_t = minutes_to_time(lo)
        end_t = minutes_to_time(hi)
        cat = HabitCategory(habit.category)
        reason = (
            f"You have {habit.duration_mins} min free — a good moment for {habit.name}."
        )
        return SuggestionCandidate(
            habit_id=habit.id,
            habit_name=habit.name,
            category=cat,
            window_start=start_t,
            window_end=end_t,
            reason=reason,
        )

    return None
