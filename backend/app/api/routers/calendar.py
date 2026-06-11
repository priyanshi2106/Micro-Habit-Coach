"""Google Calendar integration router (v3.0 — read-only availability).

Endpoints
---------
GET  /calendar/auth/url       — generate Google consent URL (requires auth)
GET  /calendar/auth/callback  — handle Google redirect (no auth; state JWT carries identity)
GET  /calendar/connection     — current connection status (requires auth)
DELETE /calendar/connection   — disconnect calendar (requires auth)
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.core.config import get_settings
from app.core.database import get_db
from app.modules.calendar.models import CalendarConnection
from app.modules.calendar.oauth import (
    CalendarNotConfiguredError,
    decode_state_token,
    decrypt_token,
    encrypt_token,
    exchange_code_for_tokens,
    get_google_oauth_url,
)
from app.modules.calendar.schemas import CalendarConnectionRead, CalendarStatusResponse
from app.modules.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["calendar"])


# ── Auth flow ─────────────────────────────────────────────────────────────────

@router.get("/auth/url")
async def get_auth_url(current_user: CurrentUser) -> dict[str, str]:
    """Return the Google OAuth consent URL for the current user.

    Returns HTTP 503 when Google Calendar credentials are not configured,
    so the frontend can conditionally show or hide the Connect button.
    """
    try:
        url = get_google_oauth_url(current_user.id)
        return {"url": url}
    except CalendarNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/auth/callback")
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """Handle Google's redirect after the user grants or denies calendar access.

    This endpoint is called by the user's browser (not by our frontend JS),
    so it cannot require an Authorization header.  The user_id is recovered
    from the signed state JWT.

    On success → redirect to {FRONTEND_URL}/settings?connected=true
    On failure → redirect to {FRONTEND_URL}/settings?error=<reason>
    """
    settings = get_settings()
    base = f"{settings.frontend_url}/settings"

    # Google reported an error (user denied access, etc.)
    if error:
        logger.warning("Google OAuth callback error: %s", error)
        return RedirectResponse(f"{base}?error={error}")

    if not code or not state:
        logger.warning("OAuth callback missing code or state")
        return RedirectResponse(f"{base}?error=invalid_callback")

    # Verify the state JWT and extract the user_id.
    user_id_str = decode_state_token(state)
    if user_id_str is None:
        logger.warning("OAuth callback: invalid or expired state token")
        return RedirectResponse(f"{base}?error=invalid_state")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        return RedirectResponse(f"{base}?error=invalid_state")

    # Exchange the authorization code for tokens.
    try:
        token_info = await exchange_code_for_tokens(code)
    except CalendarNotConfiguredError as exc:
        logger.error("Calendar not configured during callback: %s", exc)
        return RedirectResponse(f"{base}?error=not_configured")
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        return RedirectResponse(f"{base}?error=token_exchange_failed")

    # Encrypt tokens before storing.
    try:
        access_encrypted = encrypt_token(token_info.access_token)
        refresh_encrypted = (
            encrypt_token(token_info.refresh_token)
            if token_info.refresh_token
            else None
        )
    except CalendarNotConfiguredError as exc:
        logger.error("Cannot encrypt tokens: %s", exc)
        return RedirectResponse(f"{base}?error=encryption_not_configured")

    # Upsert the CalendarConnection row for this user.
    await _upsert_connection(
        session=session,
        user_id=user_id,
        google_email=token_info.google_email,
        access_encrypted=access_encrypted,
        refresh_encrypted=refresh_encrypted,
        token_expiry=token_info.token_expiry,
    )

    logger.info("Google Calendar connected for user %s (%s)", user_id, token_info.google_email)
    return RedirectResponse(f"{base}?connected=true")


# ── Connection management ─────────────────────────────────────────────────────

@router.get("/connection", response_model=CalendarStatusResponse)
async def get_connection_status(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> CalendarStatusResponse:
    """Return the current user's calendar connection status."""
    conn = await _get_connection(session, current_user.id)
    if conn is None or not conn.is_active:
        return CalendarStatusResponse(connected=False)
    return CalendarStatusResponse(
        connected=True,
        connection=CalendarConnectionRead.model_validate(conn),
    )


@router.delete("/connection", status_code=204)
async def disconnect_calendar(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Remove the user's Google Calendar connection.

    Tokens are deleted from the database immediately.  We do not call the
    Google token revocation endpoint in v1 — add that before production use.
    """
    conn = await _get_connection(session, current_user.id)
    if conn is None:
        raise HTTPException(status_code=404, detail="No calendar connection found.")
    await session.delete(conn)
    await session.commit()
    logger.info("Google Calendar disconnected for user %s", current_user.id)
    return Response(status_code=204)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_connection(
    session: AsyncSession, user_id: UUID
) -> Optional[CalendarConnection]:
    result = await session.execute(
        select(CalendarConnection).where(CalendarConnection.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _upsert_connection(
    *,
    session: AsyncSession,
    user_id: UUID,
    google_email: str,
    access_encrypted: str,
    refresh_encrypted: Optional[str],
    token_expiry: object,
) -> CalendarConnection:
    """Insert or update the CalendarConnection row for the given user."""
    conn = await _get_connection(session, user_id)

    if conn is None:
        conn = CalendarConnection(user_id=user_id)
        session.add(conn)

    conn.google_account_email = google_email
    conn.access_token_encrypted = access_encrypted
    conn.refresh_token_encrypted = refresh_encrypted
    conn.token_expiry = token_expiry
    conn.is_active = True

    await session.commit()
    await session.refresh(conn)
    return conn
