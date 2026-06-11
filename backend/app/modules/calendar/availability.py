"""Interval subtraction for calendar-aware free-block computation.

Given the user's manual free blocks and a list of busy windows from Google
Calendar, this module produces the effective free time the suggestion engine
should use.

Design
------
- Pure function (subtract_busy_windows) — no I/O, no side effects.
- Calendar busy windows are subtracted from manual free blocks.
  Manual blocks remain the authoritative source; calendar only constrains
  within them.
- Fragments narrower than MIN_FRAGMENT_MINS are dropped — there is no point
  suggesting a habit in a 2-minute sliver between meetings.
- All times are in minutes-from-midnight in the user's local timezone,
  matching the convention used throughout engine.py.

Example
-------
    free_blocks:  [06:00–09:00, 12:00–18:00]  →  [(360, 540), (720, 1080)]
    busy_windows: [08:00–10:00, 14:00–15:00]  →  [(480, 600), (840, 900)]
    result:       [06:00–08:00, 12:00–14:00, 15:00–18:00]
                   (600-480=120 ≥ MIN → keep; 480+120=600; 720–840 gap kept; etc.)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from app.modules.suggestions.engine import FreeBlockDTO, time_to_minutes, minutes_to_time

# Drop fragments narrower than this (minutes) after subtracting busy windows.
MIN_FRAGMENT_MINS: int = 5


@dataclass(frozen=True)
class BusyWindow:
    """A busy interval in minutes-from-midnight, local time."""
    start_mins: int
    end_mins: int


def subtract_busy_windows(
    free_blocks: list[FreeBlockDTO],
    busy_windows: list[BusyWindow],
) -> list[FreeBlockDTO]:
    """Return free blocks with all busy windows punched out.

    If busy_windows is empty the input list is returned unchanged (no copy).
    Busy windows that fall entirely outside every free block have no effect.

    The algorithm for each free block:
      1. Sort and clip the busy windows to the free block's range.
      2. Walk from the block start to end, emitting sub-intervals that are
         not covered by any busy window and are wide enough to be useful.
    """
    if not busy_windows:
        return free_blocks

    # Sort busy windows once, outside the per-block loop.
    sorted_busy = sorted(busy_windows, key=lambda b: b.start_mins)

    result: list[FreeBlockDTO] = []

    for block in free_blocks:
        f_lo = time_to_minutes(block.start)
        f_hi = time_to_minutes(block.end)
        if f_hi <= f_lo:
            continue

        cursor = f_lo

        for busy in sorted_busy:
            b_lo = busy.start_mins
            b_hi = busy.end_mins

            # Busy window entirely after this free block — stop early.
            if b_lo >= f_hi:
                break

            # Busy window entirely before the cursor — skip.
            if b_hi <= cursor:
                continue

            # Emit the gap between cursor and the start of this busy window.
            gap_lo = cursor
            gap_hi = min(b_lo, f_hi)
            if gap_hi - gap_lo >= MIN_FRAGMENT_MINS:
                result.append(FreeBlockDTO(
                    start=minutes_to_time(gap_lo),
                    end=minutes_to_time(gap_hi),
                ))

            # Advance cursor past the busy window.
            cursor = max(cursor, b_hi)
            if cursor >= f_hi:
                break

        # Emit the remainder of the free block after all busy windows.
        if f_hi - cursor >= MIN_FRAGMENT_MINS:
            result.append(FreeBlockDTO(
                start=minutes_to_time(cursor),
                end=minutes_to_time(f_hi),
            ))

    return result
