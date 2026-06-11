"""Tests for the anchor catalog (anchors.py) and schema validation (schemas.py).

Pure Python — no DB, no async.  Covers:
  - Catalog structural integrity (keys, windows, ordering).
  - anchor_to_bucket: happy path, unknown key.
  - VALID_ANCHOR_KEYS completeness.
  - HabitCreate.anchor_event: valid key, None, unknown key.
  - HabitUpdate.anchor_event: valid key, None (clear), omitted (no-op via exclude_unset).
"""
from __future__ import annotations

import pytest
import pydantic

from app.modules.habits.anchors import (
    ANCHOR_CATALOG,
    VALID_ANCHOR_KEYS,
    AnchorDef,
    anchor_to_bucket,
)
from app.modules.habits.schemas import HabitCreate, HabitUpdate


# ── Catalog structural integrity ─────────────────────────────────────────────

class TestAnchorCatalog:
    def test_catalog_is_non_empty(self) -> None:
        assert len(ANCHOR_CATALOG) > 0

    def test_all_keys_match_their_anchor_def_key(self) -> None:
        for k, v in ANCHOR_CATALOG.items():
            assert k == v.key, f"Dict key {k!r} != AnchorDef.key {v.key!r}"

    def test_all_windows_are_valid_minute_ranges(self) -> None:
        for anchor in ANCHOR_CATALOG.values():
            assert 0 <= anchor.start_mins < 24 * 60, f"{anchor.key}: start_mins out of range"
            assert 0 < anchor.end_mins <= 24 * 60, f"{anchor.key}: end_mins out of range"
            assert anchor.start_mins < anchor.end_mins, (
                f"{anchor.key}: start_mins ({anchor.start_mins}) >= end_mins ({anchor.end_mins})"
            )

    def test_all_windows_are_at_least_30_minutes(self) -> None:
        for anchor in ANCHOR_CATALOG.values():
            width = anchor.end_mins - anchor.start_mins
            assert width >= 30, f"{anchor.key}: window too narrow ({width} min)"

    def test_all_display_labels_are_non_empty(self) -> None:
        for anchor in ANCHOR_CATALOG.values():
            assert isinstance(anchor.display, str) and anchor.display.strip(), (
                f"{anchor.key} has empty display label"
            )

    def test_all_keys_are_lowercase_snake_case(self) -> None:
        import re
        for k in ANCHOR_CATALOG:
            assert re.match(r"^[a-z][a-z_]*[a-z]$", k), (
                f"{k!r} is not lowercase snake_case"
            )

    def test_valid_anchor_keys_matches_catalog(self) -> None:
        assert VALID_ANCHOR_KEYS == frozenset(ANCHOR_CATALOG)

    # Spot-check a few specific catalog entries
    def test_after_lunch_window(self) -> None:
        a = ANCHOR_CATALOG["after_lunch"]
        assert a.start_mins == 12 * 60 + 30   # 12:30
        assert a.end_mins == 14 * 60           # 14:00
        assert a.display == "After lunch"

    def test_before_bed_window(self) -> None:
        a = ANCHOR_CATALOG["before_bed"]
        assert a.start_mins == 21 * 60
        assert a.end_mins == 23 * 60

    def test_catalog_is_ordered_chronologically(self) -> None:
        starts = [a.start_mins for a in ANCHOR_CATALOG.values()]
        assert starts == sorted(starts), "Catalog should be ordered by start_mins"


# ── anchor_to_bucket ──────────────────────────────────────────────────────────

class TestAnchorToBucket:
    def test_known_key_returns_correct_tuple(self) -> None:
        bucket = anchor_to_bucket("after_lunch")
        assert bucket == (12 * 60 + 30, 14 * 60)

    def test_unknown_key_returns_none(self) -> None:
        assert anchor_to_bucket("after_brunch") is None

    def test_empty_string_returns_none(self) -> None:
        assert anchor_to_bucket("") is None

    def test_all_catalog_keys_produce_non_none_bucket(self) -> None:
        for key in ANCHOR_CATALOG:
            bucket = anchor_to_bucket(key)
            assert bucket is not None, f"anchor_to_bucket({key!r}) returned None"
            assert len(bucket) == 2

    def test_bucket_matches_catalog_definition(self) -> None:
        for key, anchor in ANCHOR_CATALOG.items():
            bucket = anchor_to_bucket(key)
            assert bucket == (anchor.start_mins, anchor.end_mins)


# ── Schema validation ─────────────────────────────────────────────────────────

class TestHabitCreateAnchorValidation:
    def test_valid_anchor_key_accepted(self) -> None:
        h = HabitCreate(name="Morning run", category="movement", anchor_event="after_waking")
        assert h.anchor_event == "after_waking"

    def test_none_anchor_accepted(self) -> None:
        h = HabitCreate(name="Morning run", category="movement", anchor_event=None)
        assert h.anchor_event is None

    def test_omitted_anchor_defaults_to_none(self) -> None:
        h = HabitCreate(name="Morning run", category="movement")
        assert h.anchor_event is None

    def test_invalid_anchor_key_raises_validation_error(self) -> None:
        with pytest.raises(pydantic.ValidationError) as exc_info:
            HabitCreate(name="Morning run", category="movement", anchor_event="after_brunch")
        errors = exc_info.value.errors()
        assert any("anchor_event" in str(e) or "Unknown anchor" in str(e) for e in errors)

    def test_every_valid_anchor_key_passes(self) -> None:
        for key in VALID_ANCHOR_KEYS:
            h = HabitCreate(name="Test", category="mindfulness", anchor_event=key)
            assert h.anchor_event == key


class TestHabitUpdateAnchorValidation:
    def test_valid_anchor_key_accepted(self) -> None:
        u = HabitUpdate(anchor_event="before_bed")
        assert u.anchor_event == "before_bed"

    def test_none_clears_anchor(self) -> None:
        u = HabitUpdate(anchor_event=None)
        assert u.anchor_event is None

    def test_invalid_anchor_key_raises_validation_error(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            HabitUpdate(anchor_event="during_commute")

    def test_omitted_anchor_excluded_from_model_dump(self) -> None:
        """When anchor_event is omitted, it must not appear in exclude_unset dump."""
        u = HabitUpdate(name="Renamed")
        dumped = u.model_dump(exclude_unset=True)
        assert "anchor_event" not in dumped

    def test_explicit_none_included_in_model_dump(self) -> None:
        """Explicit null must appear in the dump so the service can clear the DB column."""
        u = HabitUpdate(anchor_event=None)
        dumped = u.model_dump(exclude_unset=True)
        assert "anchor_event" in dumped
        assert dumped["anchor_event"] is None
