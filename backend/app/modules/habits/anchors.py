"""Anchor catalog for habit stacking (v3 — anchor feature).

An anchor is a named moment in the user's day (e.g. "after lunch") that the
suggestion engine uses as a high-priority timing signal.  Anchors are explicit
user intent — the user says "I want to do this after lunch", not inferred from
behavior.

Design
------
- The catalog is a dict so lookup is O(1) everywhere.
- Keys are snake_case strings stored in the habits.anchor_event column.
- start_mins / end_mins are in minutes-from-midnight in the user's LOCAL
  timezone, matching the convention used throughout engine.py and
  pattern_service.py.
- Windows are intentionally narrow (90–120 min) so they represent a specific
  moment, not a vague time-of-day preference (which is what category buckets
  handle).
- Anchors are ordered chronologically so the API returns them in a natural
  order for the UI picker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AnchorDef:
    key: str
    display: str
    start_mins: int   # minutes from midnight, inclusive, local time
    end_mins: int     # minutes from midnight, exclusive, local time


# Ordered chronologically so the UI picker lists them in a natural sequence.
ANCHOR_CATALOG: dict[str, AnchorDef] = {
    "after_waking":    AnchorDef("after_waking",    "After waking up",      6 * 60,       8 * 60),
    "after_coffee":    AnchorDef("after_coffee",    "After morning coffee", 7 * 60,       9 * 60),
    "after_breakfast": AnchorDef("after_breakfast", "After breakfast",      7 * 60 + 30,  9 * 60 + 30),
    "before_work":     AnchorDef("before_work",     "Before work starts",   8 * 60,      10 * 60),
    "at_lunch":        AnchorDef("at_lunch",        "At lunch",            12 * 60,      13 * 60),
    "after_lunch":     AnchorDef("after_lunch",     "After lunch",         12 * 60 + 30, 14 * 60),
    "after_work":      AnchorDef("after_work",      "After work",          17 * 60,      19 * 60),
    "after_dinner":    AnchorDef("after_dinner",    "After dinner",        19 * 60,      21 * 60),
    "before_bed":      AnchorDef("before_bed",      "Before bed",          21 * 60,      23 * 60),
}


def anchor_to_bucket(key: str) -> Optional[tuple[int, int]]:
    """Translate an anchor key to a (start_mins, end_mins) engine bucket.

    Returns None if the key is not in the catalog.  Callers should treat
    an unknown anchor the same as no anchor — fall through to pattern/rule.
    """
    anchor = ANCHOR_CATALOG.get(key)
    if anchor is None:
        return None
    return (anchor.start_mins, anchor.end_mins)


VALID_ANCHOR_KEYS: frozenset[str] = frozenset(ANCHOR_CATALOG)
