"""Google Calendar API client — FreeBusy queries only (v3.0, read-only).

This module is the only place that makes live HTTP calls to the Google
Calendar API.  It is intentionally thin:

- One public function: get_busy_windows_today()
- All failures are caught and logged; the function always returns a list
  (empty on failure → caller falls back to manual-only free blocks).
- Token refresh is handled here when the stored access token is expired.

No event titles or event details are fetched — only busy/free intervals
via the FreeBusy API.  This is privacy-preserving by design.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.calendar.availability import BusyWindow
from app.modules.calendar.models import CalendarConnection
from app.modules.calendar.oauth import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"
# Refresh the access token if it expires within this many seconds.
_REFRESH_BUFFER_SECS = 300   # 5 minutes


async def get_busy_windows_today(
    connection: CalendarConnection,
    session: AsyncSession,
    user_timezone: str,
) -> list[BusyWindow]:
    """Return today's busy windows from Google Calendar (primary calendar).

    Fetches via the FreeBusy API so no event titles reach our server.
    Times are converted to the user's local timezone and expressed as
    minutes-from-midnight, matching the convention in engine.py.

    Returns an empty list on any failure (network error, expired token that
    can't be refreshed, API error, etc.) so the caller always falls back to
    manual-only schedule blocks gracefully.
    """
    if not connection.is_active:
        return []

    try:
        access_token = await _get_valid_access_token(connection, session)
    except Exception as exc:
        logger.warning("Could not get valid access token for user %s: %s", connection.user_id, exc)
        return []

    if access_token is None:
        return []

    try:
        tz = ZoneInfo(user_timezone)
    except (ZoneInfoNotFoundError, KeyError):
        tz = ZoneInfo("UTC")

    now_local = datetime.now(tz)
    # Start of today (midnight local), end of today (midnight+1 local).
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = now_local.replace(hour=23, minute=59, second=59, microsecond=0)

    body = {
        "timeMin": day_start.isoformat(),
        "timeMax": day_end.isoformat(),
        "items": [{"id": "primary"}],
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _FREEBUSY_URL,
                json=body,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "FreeBusy API returned %s for user %s: %s",
            exc.response.status_code, connection.user_id, exc.response.text,
        )
        return []
    except Exception as exc:
        logger.warning("FreeBusy API call failed for user %s: %s", connection.user_id, exc)
        return []

    # Update last_synced_at.
    connection.last_synced_at = datetime.now(timezone.utc)
    await session.commit()

    # Parse the FreeBusy response into BusyWindow objects.
    busy_intervals = data.get("calendars", {}).get("primary", {}).get("busy", [])
    windows: list[BusyWindow] = []

    for interval in busy_intervals:
        try:
            start_dt = datetime.fromisoformat(interval["start"]).astimezone(tz)
            end_dt = datetime.fromisoformat(interval["end"]).astimezone(tz)
            start_mins = start_dt.hour * 60 + start_dt.minute
            end_mins = end_dt.hour * 60 + end_dt.minute
            if end_mins > start_mins:
                windows.append(BusyWindow(start_mins=start_mins, end_mins=end_mins))
        except (KeyError, ValueError):
            continue

    logger.debug(
        "FreeBusy: %d busy windows for user %s on %s",
        len(windows), connection.user_id, now_local.date(),
    )
    return windows


# ── Token management ──────────────────────────────────────────────────────────

async def _get_valid_access_token(
    connection: CalendarConnection,
    session: AsyncSession,
) -> Optional[str]:
    """Return a valid access token, refreshing it if necessary.

    Returns None (and marks the connection inactive) if the refresh token
    is missing or the refresh call fails unrecoverably.
    """
    now_utc = datetime.now(timezone.utc)
    expiry = connection.token_expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    # Token is still fresh enough — decrypt and return directly.
    if expiry > now_utc + timedelta(seconds=_REFRESH_BUFFER_SECS):
        return decrypt_token(connection.access_token_encrypted)

    # Token is expired or expiring soon — refresh using the stored refresh token.
    if not connection.refresh_token_encrypted:
        logger.warning(
            "No refresh token for user %s — marking connection inactive.", connection.user_id
        )
        connection.is_active = False
        await session.commit()
        return None

    refresh_token = decrypt_token(connection.refresh_token_encrypted)
    settings = get_settings()

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )

    def _do_refresh() -> None:
        creds.refresh(GoogleRequest())

    try:
        await asyncio.to_thread(_do_refresh)
    except RefreshError as exc:
        logger.warning(
            "Refresh token revoked for user %s — marking inactive: %s",
            connection.user_id, exc,
        )
        connection.is_active = False
        await session.commit()
        return None

    # Persist the refreshed tokens.
    connection.access_token_encrypted = encrypt_token(creds.token)
    new_expiry = creds.expiry
    if new_expiry is not None and new_expiry.tzinfo is None:
        new_expiry = new_expiry.replace(tzinfo=timezone.utc)
    connection.token_expiry = new_expiry or (now_utc + timedelta(hours=1))
    await session.commit()

    return creds.token
