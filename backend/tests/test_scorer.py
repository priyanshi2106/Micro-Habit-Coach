"""Unit tests for app/modules/habits/scorer.py.

All tests are pure Python — no DB, no I/O.
"""
from __future__ import annotations

import pytest

from app.modules.habits.pattern_service import (
    BUCKET_EVENING,
    BUCKET_MIDDAY,
    BUCKET_MORNING,
    HabitPattern,
)
from app.modules.habits.scorer import (
    MAX_BOOST,
    RELIABLE_SAMPLES,
    ConfidenceResult,
    _BASE_ANCHOR,
    _BASE_FALLBACK,
    _BASE_RULE,
    _bucket_label,
    compute_confidence,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pattern(
    *,
    bucket: tuple[int, int] = BUCKET_MORNING,
    sample_count: int = 10,
    dominant_fraction: float = 0.9,
    recency_score: float = 0.95,
) -> HabitPattern:
    return HabitPattern(
        start_mins=bucket[0],
        end_mins=bucket[1],
        sample_count=sample_count,
        dominant_fraction=dominant_fraction,
        recency_score=recency_score,
    )


# ── _bucket_label ─────────────────────────────────────────────────────────────

class TestBucketLabel:
    def test_morning(self) -> None:
        assert _bucket_label(BUCKET_MORNING[0]) == "morning"

    def test_midday(self) -> None:
        assert _bucket_label(BUCKET_MIDDAY[0]) == "midday"

    def test_evening(self) -> None:
        assert _bucket_label(BUCKET_EVENING[0]) == "evening"

    def test_upper_morning_boundary(self) -> None:
        # 11:59 is still morning
        assert _bucket_label(11 * 60 + 59) == "morning"

    def test_noon_is_midday(self) -> None:
        assert _bucket_label(12 * 60) == "midday"


# ── compute_confidence — base scores ─────────────────────────────────────────

class TestBaseScores:
    def test_no_pattern_rule_match(self) -> None:
        """No history → pure rule baseline 0.45."""
        result = compute_confidence(None, False, "mindfulness", "Meditation")
        assert result.score == _BASE_RULE

    def test_pattern_used_learned_base(self) -> None:
        """Pattern with perfect data → base + full boost."""
        p = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        expected = round(min(_BASE_RULE + MAX_BOOST, 1.0), 2)
        assert result.score == expected

    def test_pattern_fallback_base_lower(self) -> None:
        """Pattern present but fell back → base 0.35, still boosted."""
        p = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        fallback_result = compute_confidence(p, False, "mindfulness", "Meditation")
        used_result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert fallback_result.score < used_result.score
        # Base difference should be exactly _BASE_RULE - _BASE_FALLBACK
        assert abs((used_result.score - fallback_result.score) - (_BASE_RULE - _BASE_FALLBACK)) < 0.01

    def test_score_never_exceeds_one(self) -> None:
        p = _pattern(dominant_fraction=1.0, recency_score=1.0, sample_count=100)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert result.score <= 1.0

    def test_score_never_below_zero(self) -> None:
        p = _pattern(dominant_fraction=0.0, recency_score=0.0, sample_count=5)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert result.score >= 0.0


# ── compute_confidence — boost formula ───────────────────────────────────────

class TestBoostFormula:
    def test_zero_recency_means_no_boost(self) -> None:
        """All-old data (recency_score=0) → boost is 0 → score equals base."""
        p = _pattern(dominant_fraction=1.0, recency_score=0.0, sample_count=10)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert result.score == _BASE_RULE

    def test_low_sample_count_reduces_boost(self) -> None:
        """data_reliability = min(n/RELIABLE_SAMPLES, 1.0) shrinks boost."""
        p_few = _pattern(sample_count=5, dominant_fraction=1.0, recency_score=1.0)
        p_many = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        few_result = compute_confidence(p_few, True, "movement", "Run")
        many_result = compute_confidence(p_many, True, "movement", "Run")
        assert few_result.score < many_result.score

    def test_dominant_fraction_scales_boost(self) -> None:
        p_weak = _pattern(dominant_fraction=0.5, recency_score=1.0, sample_count=10)
        p_strong = _pattern(dominant_fraction=1.0, recency_score=1.0, sample_count=10)
        result_weak = compute_confidence(p_weak, True, "movement", "Run")
        result_strong = compute_confidence(p_strong, True, "movement", "Run")
        assert result_weak.score < result_strong.score

    def test_saturated_data_reliability(self) -> None:
        """Beyond RELIABLE_SAMPLES, more samples do not increase the boost."""
        p_10 = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=0.9, recency_score=0.9)
        p_50 = _pattern(sample_count=50, dominant_fraction=0.9, recency_score=0.9)
        assert compute_confidence(p_10, True, "mindfulness", "M").score == \
               compute_confidence(p_50, True, "mindfulness", "M").score

    def test_score_is_rounded_to_2dp(self) -> None:
        p = _pattern(dominant_fraction=0.7, recency_score=0.8, sample_count=7)
        result = compute_confidence(p, True, "health", "Walk")
        # Verify the score has at most 2 decimal places.
        assert result.score == round(result.score, 2)


# ── compute_confidence — reason strings ──────────────────────────────────────

class TestReasonStrings:
    def test_no_pattern_mentions_category(self) -> None:
        result = compute_confidence(None, False, "mindfulness", "Meditation")
        assert "mindfulness" in result.reason

    def test_fallback_mentions_slot_not_free(self) -> None:
        p = _pattern()
        result = compute_confidence(p, False, "mindfulness", "Meditation")
        assert "free" in result.reason.lower() or "slot" in result.reason.lower()

    def test_fallback_mentions_bucket_name(self) -> None:
        p = _pattern(bucket=BUCKET_MORNING)
        result = compute_confidence(p, False, "mindfulness", "Meditation")
        assert "morning" in result.reason

    def test_low_sample_count_mentions_completions(self) -> None:
        p = _pattern(sample_count=5)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert "5" in result.reason

    def test_high_consistency_says_consistently(self) -> None:
        p = _pattern(sample_count=10, dominant_fraction=0.85)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert "consistently" in result.reason

    def test_medium_consistency_mentions_percentage(self) -> None:
        p = _pattern(sample_count=10, dominant_fraction=0.70)
        result = compute_confidence(p, True, "mindfulness", "Meditation")
        assert "70%" in result.reason

    def test_evening_bucket_reason(self) -> None:
        p = _pattern(bucket=BUCKET_EVENING, sample_count=10, dominant_fraction=0.9)
        result = compute_confidence(p, True, "social", "Call family")
        assert "evening" in result.reason

    def test_midday_bucket_reason(self) -> None:
        p = _pattern(bucket=BUCKET_MIDDAY, sample_count=10, dominant_fraction=0.9)
        result = compute_confidence(p, True, "learning", "Read")
        assert "midday" in result.reason

    def test_reason_is_non_empty_string(self) -> None:
        for pattern, used in [(None, False), (_pattern(), True), (_pattern(), False)]:
            result = compute_confidence(pattern, used, "health", "Walk")
            assert isinstance(result.reason, str) and len(result.reason) > 0


# ── Anchor scoring ────────────────────────────────────────────────────────────

class TestAnchorScoring:
    """Verify anchor cases produce the right base scores and reason copy."""

    def test_anchor_used_no_history_base_score(self) -> None:
        """Anchor used, no pattern → base = _BASE_ANCHOR (0.50)."""
        result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        assert result.score == _BASE_ANCHOR

    def test_anchor_used_ranks_above_rule_base(self) -> None:
        """Anchor base (0.50) must exceed rule base (0.45)."""
        anchor_result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        rule_result = compute_confidence(None, False, "mindfulness", "Meditate")
        assert anchor_result.score > rule_result.score

    def test_anchor_with_pattern_boost_stacks(self) -> None:
        """Pattern boost is applied on top of the anchor base."""
        no_pattern = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        p = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        with_pattern = compute_confidence(
            p, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        assert with_pattern.score > no_pattern.score

    def test_anchor_fallback_no_history_uses_rule_base(self) -> None:
        """Anchor set but slot unavailable, no pattern → _BASE_RULE (no pattern → not fallback path)."""
        result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=False, anchor_name="After lunch",
        )
        assert result.score == _BASE_RULE

    def test_anchor_fallback_with_pattern_uses_fallback_base(self) -> None:
        """Anchor set but slot unavailable, pattern exists → _BASE_FALLBACK."""
        p = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        fallback_result = compute_confidence(
            p, False, "mindfulness", "Meditate",
            used_anchor=False, anchor_name="After lunch",
        )
        used_result = compute_confidence(
            p, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        assert fallback_result.score < used_result.score

    def test_anchor_used_reason_mentions_anchor_name(self) -> None:
        result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After lunch",
        )
        assert "after lunch" in result.reason.lower()

    def test_anchor_fallback_reason_mentions_anchor_name(self) -> None:
        result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=False, anchor_name="After lunch",
        )
        assert "after lunch" in result.reason.lower()

    def test_anchor_fallback_reason_mentions_not_free(self) -> None:
        result = compute_confidence(
            None, False, "mindfulness", "Meditate",
            used_anchor=False, anchor_name="Before bed",
        )
        assert "free" in result.reason.lower() or "available" in result.reason.lower()

    def test_no_anchor_no_pattern_uses_category_copy(self) -> None:
        """When no anchor and no pattern, existing rule copy is returned."""
        result = compute_confidence(None, False, "mindfulness", "Meditate")
        assert "mindfulness" in result.reason

    def test_anchor_score_capped_at_one(self) -> None:
        """Anchor base + max boost should never exceed 1.0."""
        p = _pattern(sample_count=RELIABLE_SAMPLES, dominant_fraction=1.0, recency_score=1.0)
        result = compute_confidence(
            p, False, "mindfulness", "Meditate",
            used_anchor=True, anchor_name="After waking",
        )
        assert result.score <= 1.0

    def test_anchor_base_constant_value(self) -> None:
        assert _BASE_ANCHOR == 0.50


# ── ConfidenceResult ──────────────────────────────────────────────────────────

class TestConfidenceResult:
    def test_is_frozen(self) -> None:
        r = ConfidenceResult(score=0.5, reason="test")
        with pytest.raises((AttributeError, TypeError)):
            r.score = 0.9  # type: ignore[misc]
