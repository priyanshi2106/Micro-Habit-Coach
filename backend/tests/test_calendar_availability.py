"""Unit tests for calendar/availability.py — interval subtraction logic.

All tests are pure Python: no database, no network, no async.
The subtract_busy_windows function is the core of the calendar integration —
these tests cover every edge case before the function is wired into the
suggestion service.
"""
from __future__ import annotations

from datetime import time

import pytest

from app.modules.calendar.availability import (
    MIN_FRAGMENT_MINS,
    BusyWindow,
    subtract_busy_windows,
)
from app.modules.suggestions.engine import FreeBlockDTO


# ── Helpers ───────────────────────────────────────────────────────────────────

def block(start_h: int, end_h: int) -> FreeBlockDTO:
    return FreeBlockDTO(start=time(start_h, 0), end=time(end_h, 0))


def block_m(start_h: int, start_m: int, end_h: int, end_m: int) -> FreeBlockDTO:
    return FreeBlockDTO(start=time(start_h, start_m), end=time(end_h, end_m))


def busy(start_h: int, end_h: int) -> BusyWindow:
    return BusyWindow(start_mins=start_h * 60, end_mins=end_h * 60)


def busy_m(start_h: int, start_m: int, end_h: int, end_m: int) -> BusyWindow:
    return BusyWindow(start_mins=start_h * 60 + start_m, end_mins=end_h * 60 + end_m)


# ── Empty inputs ──────────────────────────────────────────────────────────────

class TestEmptyInputs:
    def test_empty_free_blocks_returns_empty(self) -> None:
        assert subtract_busy_windows([], [busy(8, 9)]) == []

    def test_empty_busy_returns_free_blocks_unchanged(self) -> None:
        blocks = [block(6, 9), block(12, 18)]
        result = subtract_busy_windows(blocks, [])
        assert result is blocks   # same object — no copy made

    def test_both_empty_returns_empty(self) -> None:
        assert subtract_busy_windows([], []) == []


# ── Busy entirely outside free block ─────────────────────────────────────────

class TestBusyOutsideFreeBlock:
    def test_busy_before_free_block_has_no_effect(self) -> None:
        result = subtract_busy_windows([block(12, 18)], [busy(9, 11)])
        assert len(result) == 1
        assert result[0].start == time(12, 0)
        assert result[0].end == time(18, 0)

    def test_busy_after_free_block_has_no_effect(self) -> None:
        result = subtract_busy_windows([block(6, 9)], [busy(10, 11)])
        assert len(result) == 1
        assert result[0].start == time(6, 0)

    def test_busy_adjacent_to_end_of_block(self) -> None:
        """Busy starting exactly at block end touches but does not affect the block."""
        result = subtract_busy_windows([block(6, 9)], [busy(9, 10)])
        assert len(result) == 1


# ── Busy overlapping the start of a free block ───────────────────────────────

class TestBusyOverlapsStart:
    def test_busy_clips_start_of_block(self) -> None:
        # Free 06–09, busy 05–07 → effective 07–09
        result = subtract_busy_windows([block(6, 9)], [busy(5, 7)])
        assert len(result) == 1
        assert result[0].start == time(7, 0)
        assert result[0].end == time(9, 0)

    def test_busy_covers_entire_start_leaving_remainder(self) -> None:
        result = subtract_busy_windows([block(8, 18)], [busy(7, 12)])
        assert len(result) == 1
        assert result[0].start == time(12, 0)
        assert result[0].end == time(18, 0)


# ── Busy overlapping the end of a free block ─────────────────────────────────

class TestBusyOverlapsEnd:
    def test_busy_clips_end_of_block(self) -> None:
        # Free 06–09, busy 08–10 → effective 06–08
        result = subtract_busy_windows([block(6, 9)], [busy(8, 10)])
        assert len(result) == 1
        assert result[0].start == time(6, 0)
        assert result[0].end == time(8, 0)


# ── Busy entirely within a free block ────────────────────────────────────────

class TestBusyWithinFreeBlock:
    def test_busy_splits_block_into_two(self) -> None:
        # Free 12–18, busy 14–15 → 12–14 and 15–18
        result = subtract_busy_windows([block(12, 18)], [busy(14, 15)])
        assert len(result) == 2
        assert result[0].start == time(12, 0)
        assert result[0].end == time(14, 0)
        assert result[1].start == time(15, 0)
        assert result[1].end == time(18, 0)

    def test_two_busy_windows_create_three_fragments(self) -> None:
        # Free 6–18, busy 8–9 and 11–12 → 6–8, 9–11, 12–18
        result = subtract_busy_windows([block(6, 18)], [busy(8, 9), busy(11, 12)])
        assert len(result) == 3
        assert result[0].end == time(8, 0)
        assert result[1].start == time(9, 0)
        assert result[1].end == time(11, 0)
        assert result[2].start == time(12, 0)

    def test_adjacent_busy_windows_merge_gap_correctly(self) -> None:
        """Two back-to-back busy windows leave no fragment between them."""
        result = subtract_busy_windows([block(6, 18)], [busy(8, 10), busy(10, 12)])
        # Fragment between 10–10 is zero width → dropped
        assert all(
            b.end.hour * 60 + b.end.minute > b.start.hour * 60 + b.start.minute
            for b in result
        )


# ── Busy covers entire free block ────────────────────────────────────────────

class TestBusyCoversEntireBlock:
    def test_fully_covered_block_removed(self) -> None:
        result = subtract_busy_windows([block(6, 9)], [busy(5, 10)])
        assert result == []

    def test_fully_covered_block_exact_match(self) -> None:
        result = subtract_busy_windows([block(8, 10)], [busy(8, 10)])
        assert result == []


# ── Multiple free blocks ──────────────────────────────────────────────────────

class TestMultipleFreeBlocks:
    def test_busy_in_first_block_only(self) -> None:
        result = subtract_busy_windows([block(6, 9), block(12, 18)], [busy(7, 8)])
        assert len(result) == 3   # 6–7, 8–9, and 12–18 untouched

    def test_busy_in_second_block_only(self) -> None:
        result = subtract_busy_windows([block(6, 9), block(12, 18)], [busy(14, 15)])
        assert len(result) == 3   # 6–9 untouched, 12–14, 15–18

    def test_busy_spanning_both_blocks_clips_each(self) -> None:
        # Busy 8–13 clips end of first block (6–9) and start of second (12–18).
        result = subtract_busy_windows([block(6, 9), block(12, 18)], [busy(8, 13)])
        assert any(b.start == time(6, 0) and b.end == time(8, 0) for b in result)
        assert any(b.start == time(13, 0) and b.end == time(18, 0) for b in result)

    def test_first_block_fully_removed_second_untouched(self) -> None:
        result = subtract_busy_windows([block(6, 9), block(12, 18)], [busy(5, 10)])
        assert len(result) == 1
        assert result[0].start == time(12, 0)

    def test_realistic_day_scenario(self) -> None:
        """Simulate a working day with a morning block, lunch, and afternoon block."""
        free = [block(8, 12), block(13, 18)]
        # Two meetings: 9–10 standup, 15:30–16:30 review
        meetings = [busy_m(9, 0, 10, 0), busy_m(15, 30, 16, 30)]
        result = subtract_busy_windows(free, meetings)
        starts = [f"{b.start.hour}:{b.start.minute:02d}" for b in result]
        ends = [f"{b.end.hour}:{b.end.minute:02d}" for b in result]
        # Expect: 8–9, 10–12, 13–15:30, 16:30–18
        assert "8:00" in starts
        assert "10:00" in starts
        assert "13:00" in starts
        assert "16:30" in starts
        assert len(result) == 4


# ── MIN_FRAGMENT_MINS enforcement ─────────────────────────────────────────────

class TestMinFragmentDropping:
    def test_fragment_shorter_than_minimum_is_dropped(self) -> None:
        """A 3-minute fragment after a busy window should be dropped."""
        # Free 8:00–8:10, busy 8:00–8:07 → 3-min remainder (< 5) → dropped
        free = [block_m(8, 0, 8, 10)]
        meetings = [busy_m(8, 0, 8, 7)]
        result = subtract_busy_windows(free, meetings)
        for b in result:
            width = (b.end.hour * 60 + b.end.minute) - (b.start.hour * 60 + b.start.minute)
            assert width >= MIN_FRAGMENT_MINS, f"Fragment too short: {width} min"

    def test_fragment_exactly_at_minimum_is_kept(self) -> None:
        """A fragment exactly MIN_FRAGMENT_MINS wide should be kept."""
        free = [block_m(8, 0, 9, 0)]
        # Busy 8:00–8:55 → 5-min remainder 8:55–9:00
        meetings = [busy_m(8, 0, 8, 60 - MIN_FRAGMENT_MINS)]
        result = subtract_busy_windows(free, meetings)
        assert len(result) == 1
        width = (result[0].end.hour * 60 + result[0].end.minute) - (
            result[0].start.hour * 60 + result[0].start.minute
        )
        assert width == MIN_FRAGMENT_MINS

    def test_gap_between_two_busy_too_short_is_dropped(self) -> None:
        """A gap between two busy windows that is too narrow is dropped."""
        # Free 8–12. Busy 9–10:58 and 11–12. Gap is 10:58–11:00 = 2 min → dropped.
        free = [block(8, 12)]
        meetings = [busy_m(9, 0, 10, 58), busy(11, 12)]
        result = subtract_busy_windows(free, meetings)
        for b in result:
            width = (b.end.hour * 60 + b.end.minute) - (b.start.hour * 60 + b.start.minute)
            assert width >= MIN_FRAGMENT_MINS


# ── BusyWindow dataclass ──────────────────────────────────────────────────────

class TestBusyWindow:
    def test_is_frozen(self) -> None:
        bw = BusyWindow(start_mins=480, end_mins=540)
        with pytest.raises((AttributeError, TypeError)):
            bw.start_mins = 0  # type: ignore[misc]

    def test_minutes_are_stored_correctly(self) -> None:
        bw = BusyWindow(start_mins=9 * 60, end_mins=10 * 60)
        assert bw.start_mins == 540
        assert bw.end_mins == 600
