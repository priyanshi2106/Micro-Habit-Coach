"""Unit tests for app/modules/suggestions/engine.py — Pattern Learning + Anchors.

These are pure-Python tests: no database, no HTTP, no async.
They verify the precedence chain introduced in v2.1 (learned) and v2.3 (anchors):
  anchor → learned bucket → category rule (fallback).
"""
from __future__ import annotations

from datetime import time
from uuid import uuid4

import pytest

from app.modules.suggestions.engine import (
    FreeBlockDTO,
    HabitDTO,
    SuggestionCandidate,
    _best_window_for_habit,
    _find_best_window,
    pick_today_suggestion,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _block(start_h: int, end_h: int) -> FreeBlockDTO:
    return FreeBlockDTO(start=time(start_h, 0), end=time(end_h, 0))


def _habit(category: str = "mindfulness", duration_mins: int = 10) -> HabitDTO:
    return HabitDTO(id=uuid4(), name="Test Habit", category=category, duration_mins=duration_mins)


# ── _best_window_for_habit (category rule, unchanged) ────────────────────────

class TestBestWindowForHabit:
    def test_returns_none_when_no_blocks(self) -> None:
        habit = _habit("mindfulness")
        assert _best_window_for_habit(habit, []) is None

    def test_returns_none_when_block_outside_category_bucket(self) -> None:
        # mindfulness bucket = morning (05:00–12:00), block is evening
        habit = _habit("mindfulness")
        assert _best_window_for_habit(habit, [_block(18, 20)]) is None

    def test_returns_window_when_block_overlaps_bucket(self) -> None:
        habit = _habit("mindfulness", duration_mins=10)
        win = _best_window_for_habit(habit, [_block(6, 9)])
        assert win is not None
        lo, hi = win
        assert hi - lo == 10  # exact duration

    def test_unknown_category_returns_none(self) -> None:
        habit = _habit("unknown_category")
        assert _best_window_for_habit(habit, [_block(0, 23)]) is None

    def test_block_too_short_for_duration(self) -> None:
        habit = _habit("mindfulness", duration_mins=30)
        # Morning bucket ends at 12:00 (720 min). Block is 11:50–12:30 → only 10 min
        # overlap with the morning bucket, which is shorter than the 30-min duration.
        short_block = FreeBlockDTO(start=time(11, 50), end=time(12, 30))
        assert _best_window_for_habit(habit, [short_block]) is None


# ── _find_best_window — learned bucket precedence ────────────────────────────

class TestFindBestWindow:
    def test_no_learned_bucket_uses_category_rule(self) -> None:
        habit = _habit("mindfulness", duration_mins=10)
        win, used_learned, used_anchor = _find_best_window(habit, [_block(6, 9)])
        assert win is not None
        assert used_learned is False
        assert used_anchor is False

    def test_learned_bucket_used_when_free_block_overlaps(self) -> None:
        h_id = uuid4()
        # Category rule: mindfulness → morning (05–12). Learned: evening (17–24).
        habit = HabitDTO(id=h_id, name="Med", category="mindfulness", duration_mins=10,
                         learned_bucket=(17 * 60, 24 * 60))
        blocks = [_block(6, 9), _block(18, 20)]  # both morning and evening available
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        assert win is not None
        lo, _ = win
        # Should pick the evening window, not morning
        assert lo >= 17 * 60
        assert used_learned is True
        assert used_anchor is False

    def test_learned_bucket_no_overlap_falls_back_to_category(self) -> None:
        h_id = uuid4()
        # Learned: evening, but only a morning block is free
        habit = HabitDTO(id=h_id, name="Med", category="mindfulness", duration_mins=10,
                         learned_bucket=(17 * 60, 24 * 60))
        blocks = [_block(6, 9)]
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        # Falls back to category rule → morning block is used
        assert win is not None
        lo, _ = win
        assert lo < 12 * 60
        assert used_learned is False
        assert used_anchor is False

    def test_learned_bucket_no_free_blocks_at_all(self) -> None:
        h_id = uuid4()
        habit = HabitDTO(id=h_id, name="Med", category="mindfulness", duration_mins=10,
                         learned_bucket=(17 * 60, 24 * 60))
        win, used_learned, used_anchor = _find_best_window(habit, [])
        assert win is None
        assert used_learned is False
        assert used_anchor is False

    def test_learned_bucket_block_too_short(self) -> None:
        """Learned bucket overlaps but duration doesn't fit → falls back."""
        h_id = uuid4()
        habit = HabitDTO(id=h_id, name="Med", category="mindfulness", duration_mins=30,
                         learned_bucket=(18 * 60, 19 * 60))  # 1-hour bucket
        # Block inside learned bucket but only 10 min wide
        blocks = [FreeBlockDTO(start=time(18, 0), end=time(18, 10)), _block(6, 9)]
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        # Learned window doesn't fit (10 < 30) → falls back to morning
        assert win is not None
        assert used_learned is False
        assert used_anchor is False

    # ── Anchor tests ─────────────────────────────────────────────────────────

    def test_anchor_beats_learned_and_rule_when_block_available(self) -> None:
        """Anchor window (highest priority) is chosen when a free block overlaps it."""
        h_id = uuid4()
        # Anchor: lunch (12:30–14:00). Learned: evening (17–24). Rule: morning.
        habit = HabitDTO(
            id=h_id, name="Med", category="mindfulness", duration_mins=10,
            anchor_bucket=(12 * 60 + 30, 14 * 60),
            anchor_name="After lunch",
            learned_bucket=(17 * 60, 24 * 60),
        )
        blocks = [_block(6, 9), _block(12, 15), _block(18, 20)]
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        assert win is not None
        lo, _ = win
        # Anchor window starts at 750 (12:30); any lo in that range wins.
        assert lo >= 12 * 60 + 30
        assert lo < 14 * 60
        assert used_anchor is True
        assert used_learned is False

    def test_anchor_falls_back_to_learned_when_no_overlap(self) -> None:
        """Anchor slot is busy → fall through to learned pattern."""
        h_id = uuid4()
        # Anchor: lunch (12:30–14:00), no block overlaps it.
        # Learned: evening → block available.
        habit = HabitDTO(
            id=h_id, name="Med", category="mindfulness", duration_mins=10,
            anchor_bucket=(12 * 60 + 30, 14 * 60),
            anchor_name="After lunch",
            learned_bucket=(17 * 60, 24 * 60),
        )
        blocks = [_block(18, 20)]  # only evening free
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        assert win is not None
        lo, _ = win
        assert lo >= 17 * 60
        assert used_learned is True
        assert used_anchor is False

    def test_anchor_falls_back_to_rule_when_no_learned(self) -> None:
        """Anchor slot busy, no learned pattern → falls back to category rule."""
        h_id = uuid4()
        habit = HabitDTO(
            id=h_id, name="Med", category="mindfulness", duration_mins=10,
            anchor_bucket=(12 * 60 + 30, 14 * 60),
            anchor_name="After lunch",
        )
        blocks = [_block(6, 9)]  # only morning free
        win, used_learned, used_anchor = _find_best_window(habit, blocks)
        assert win is not None
        lo, _ = win
        assert lo < 12 * 60   # morning rule bucket
        assert used_anchor is False
        assert used_learned is False

    def test_anchor_name_forwarded_to_candidate(self) -> None:
        """anchor_name set on HabitDTO is passed through in SuggestionCandidate."""
        h_id = uuid4()
        habit = HabitDTO(
            id=h_id, name="Med", category="mindfulness", duration_mins=5,
            anchor_bucket=(12 * 60 + 30, 14 * 60),
            anchor_name="After lunch",
        )
        candidate = pick_today_suggestion([habit], [_block(12, 15)])
        assert candidate is not None
        assert candidate.used_anchor is True
        assert candidate.anchor_name == "After lunch"

    def test_no_anchor_means_anchor_name_is_none(self) -> None:
        habit = _habit("mindfulness")
        candidate = pick_today_suggestion([habit], [_block(6, 9)])
        assert candidate is not None
        assert candidate.used_anchor is False
        assert candidate.anchor_name is None


# ── pick_today_suggestion — full function ────────────────────────────────────

class TestPickTodaySuggestion:
    def test_returns_none_when_no_habits(self) -> None:
        assert pick_today_suggestion([], [_block(6, 9)]) is None

    def test_returns_none_when_no_blocks(self) -> None:
        assert pick_today_suggestion([_habit()], []) is None

    def test_category_rule_result(self) -> None:
        candidate = pick_today_suggestion([_habit("mindfulness")], [_block(6, 9)])
        assert candidate is not None
        assert candidate.used_learned is False

    def test_learned_pattern_overrides_category(self) -> None:
        h_id = uuid4()
        habit = HabitDTO(id=h_id, name="Walk", category="movement", duration_mins=10)
        # Movement category rule: morning or evening. Learned: midday.
        patterns = {h_id: (12 * 60, 17 * 60)}
        blocks = [_block(6, 9), _block(12, 15)]  # both morning and midday free
        candidate = pick_today_suggestion([habit], blocks, patterns=patterns)
        assert candidate is not None
        assert candidate.used_learned is True
        assert candidate.window_start.hour >= 12

    def test_empty_patterns_dict_treated_as_no_patterns(self) -> None:
        habit = _habit("mindfulness")
        candidate = pick_today_suggestion([habit], [_block(6, 9)], patterns={})
        assert candidate is not None
        assert candidate.used_learned is False

    def test_patterns_none_equivalent_to_empty(self) -> None:
        habit = _habit("mindfulness")
        c1 = pick_today_suggestion([habit], [_block(6, 9)], patterns=None)
        c2 = pick_today_suggestion([habit], [_block(6, 9)])
        assert c1 is not None and c2 is not None
        assert c1.window_start == c2.window_start

    def test_adaptive_reason_is_empty_placeholder(self) -> None:
        """Engine sets reason="" — the scorer in service.py generates the copy."""
        h_id = uuid4()
        habit = HabitDTO(id=h_id, name="Journal", category="mindfulness", duration_mins=5)
        candidate_rule = pick_today_suggestion([habit], [_block(6, 9)])
        patterns = {h_id: (6 * 60, 12 * 60)}
        candidate_adaptive = pick_today_suggestion([habit], [_block(6, 9)], patterns=patterns)
        assert candidate_rule is not None
        assert candidate_adaptive is not None
        # Engine no longer generates user-facing copy — both reasons are empty.
        assert candidate_rule.reason == ""
        assert candidate_adaptive.reason == ""

    def test_pattern_not_matching_habit_id_is_ignored(self) -> None:
        """Patterns keyed by a different habit id must not affect other habits."""
        habit = _habit("mindfulness")
        unrelated_id = uuid4()
        patterns = {unrelated_id: (17 * 60, 24 * 60)}
        candidate = pick_today_suggestion([habit], [_block(6, 9)], patterns=patterns)
        assert candidate is not None
        assert candidate.used_learned is False

    def test_category_priority_order_respected(self) -> None:
        """Mindfulness should be picked over movement when both fit."""
        h_mindfulness = _habit("mindfulness")
        h_movement = _habit("movement")
        candidate = pick_today_suggestion([h_movement, h_mindfulness], [_block(6, 9)])
        assert candidate is not None
        assert candidate.category.value == "mindfulness"
