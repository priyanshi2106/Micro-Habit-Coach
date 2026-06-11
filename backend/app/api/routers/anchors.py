"""Anchor catalog endpoint — returns valid anchor keys and display labels.

This is read-only reference data, so no auth dependency is required.
The engine uses start_mins/end_mins internally; those are not exposed here
since the frontend only needs names to render the picker.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.modules.habits.anchors import ANCHOR_CATALOG

router = APIRouter(prefix="/anchors", tags=["anchors"])


class AnchorItem(BaseModel):
    key: str
    display: str


@router.get("", response_model=list[AnchorItem])
async def list_anchors() -> list[AnchorItem]:
    """Return all valid anchor keys and their display labels, in chronological order."""
    return [AnchorItem(key=a.key, display=a.display) for a in ANCHOR_CATALOG.values()]
