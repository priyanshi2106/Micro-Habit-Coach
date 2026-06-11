"""CalendarConnection ORM model — stores one OAuth connection per user.

Design notes
------------
- One row per user (enforced by unique=True on user_id).
- Tokens are stored Fernet-encrypted (see oauth.py).  Raw token strings
  never appear in the DB — only ciphertext.
- is_active=False means the connection is broken (refresh token revoked,
  credentials deleted).  The UI shows a "reconnect" prompt.
- last_synced_at is updated each time we successfully hit the FreeBusy API.
  A stale/null value is a hint that the connection may need attention, but
  does not block suggestion generation (graceful fallback is always used).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default="google"
    )
    # Email of the connected Google account — display-only, never used for auth.
    google_account_email: Mapped[str] = mapped_column(String(320), nullable=False)

    # Fernet-encrypted tokens.  Raw token strings never touch the DB.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # UTC datetime when the stored access token expires.
    token_expiry: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # False when the connection is broken (refresh token revoked / user disconnected).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Set to now() after each successful FreeBusy API call; None = never synced.
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="calendar_connection")
