"""Read schemas for the calendar_connections table.

Only the display-safe fields are exposed — encrypted tokens never leave the backend.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    provider: str
    google_account_email: str
    is_active: bool
    connected_at: datetime
    last_synced_at: Optional[datetime]


class CalendarStatusResponse(BaseModel):
    """Returned by GET /calendar/connection."""
    connected: bool
    connection: Optional[CalendarConnectionRead] = None
