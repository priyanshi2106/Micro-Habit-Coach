"""Google Calendar OAuth helpers (v3.0 — calendar integration).

Responsibilities
----------------
- Fernet encryption / decryption of stored tokens (tokens never reach the DB
  as plaintext).
- State JWT creation and verification (short-lived, purpose-scoped, signed
  with the same SECRET_KEY as auth tokens but distinguishable by purpose claim).
- Google OAuth URL generation.
- Authorization code exchange for access + refresh tokens (async, no blocking).

No DB I/O.  All functions are either pure or explicitly async so they are
straightforward to unit-test.

Raising CalendarNotConfiguredError
-----------------------------------
Any function that requires Google credentials or the encryption key raises
CalendarNotConfiguredError when the required settings are absent.  Callers
(the router) should catch this and return HTTP 503.
"""
from __future__ import annotations

import asyncio
import json
import base64
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from google_auth_oauthlib.flow import Flow
from jose import JWTError, jwt as jose_jwt

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Google Calendar read-only scope.  openid + email added so the consent screen
# shows the account identity and lets us retrieve the email on connection.
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
]

_STATE_TOKEN_PURPOSE = "calendar_oauth"
_STATE_TOKEN_EXPIRE_MINUTES = 10


# ── Custom exception ──────────────────────────────────────────────────────────

class CalendarNotConfiguredError(Exception):
    """Raised when Google OAuth credentials or the encryption key are missing.

    The router converts this to HTTP 503 with a clear message so the client
    knows calendar integration is not enabled on this deployment.
    """


# ── Fernet encryption ─────────────────────────────────────────────────────────

def _get_fernet() -> Fernet:
    key = get_settings().calendar_encryption_key
    if not key:
        raise CalendarNotConfiguredError(
            "CALENDAR_ENCRYPTION_KEY is not configured. "
            "Set it to a Fernet key to enable calendar token storage."
        )
    try:
        return Fernet(key.encode())
    except Exception as exc:
        raise CalendarNotConfiguredError(
            f"CALENDAR_ENCRYPTION_KEY is invalid: {exc}"
        ) from exc


def encrypt_token(plaintext: str) -> str:
    """Encrypt a raw token string for safe storage in the database."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored token string.

    Raises InvalidToken (from cryptography) if the ciphertext has been
    tampered with or the encryption key has changed since storage.
    """
    return _get_fernet().decrypt(ciphertext.encode()).decode()


# ── State JWT ─────────────────────────────────────────────────────────────────

def create_state_token(user_id: UUID) -> str:
    """Create a short-lived signed state token for OAuth callback verification.

    The token is embedded as the `state` parameter in the Google consent URL.
    When Google redirects back to our callback, we verify and decode it to
    identify which user is connecting — without a server-side session.

    Uses the same SECRET_KEY as auth tokens but carries a distinct purpose
    claim so it cannot be accepted in place of an access or refresh token.
    """
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "purpose": _STATE_TOKEN_PURPOSE,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TOKEN_EXPIRE_MINUTES),
    }
    return jose_jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_state_token(token: str) -> Optional[str]:
    """Decode and verify a state token.

    Returns the user_id string if the token is valid, unexpired, and carries
    the correct purpose claim.  Returns None in all error cases — callers
    should treat None as an invalid/tampered callback.
    """
    try:
        settings = get_settings()
        payload = jose_jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("purpose") != _STATE_TOKEN_PURPOSE:
            return None
        return payload.get("sub")
    except JWTError:
        return None


# ── OAuth flow ────────────────────────────────────────────────────────────────

def _get_flow() -> Flow:
    """Build a google-auth-oauthlib Flow from Settings.

    Raises CalendarNotConfiguredError when the Google OAuth credentials are
    absent so callers can convert to HTTP 503 cleanly.
    """
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        raise CalendarNotConfiguredError(
            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must both be set "
            "to enable Google Calendar integration."
        )
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=CALENDAR_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )


def get_google_oauth_url(user_id: UUID) -> str:
    """Return the Google consent page URL for calendar read-only access.

    Embeds a signed, short-lived state JWT so the callback endpoint can
    identify the user without a DB-side session or nonce.
    """
    flow = _get_flow()
    state = create_state_token(user_id)
    auth_url, _ = flow.authorization_url(
        access_type="offline",   # request a refresh token
        prompt="consent",        # always show consent to guarantee refresh token
        include_granted_scopes="true",
        state=state,
    )
    return auth_url


# ── Token info dataclass ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class GoogleTokenInfo:
    """Result of a successful authorization code exchange."""
    access_token: str
    refresh_token: Optional[str]   # None only if Google did not issue one
    token_expiry: datetime          # UTC-aware datetime
    google_email: str              # email of the connected Google account


# ── Code exchange ─────────────────────────────────────────────────────────────

async def exchange_code_for_tokens(code: str) -> GoogleTokenInfo:
    """Exchange a Google authorization code for access + refresh tokens.

    Makes two network calls:
    1. Token endpoint (sync, offloaded to thread pool via asyncio.to_thread)
       — exchanges the code for credentials.
    2. Google userinfo endpoint (async via httpx)
       — fetches the connected account email.

    Raises httpx.HTTPStatusError or google-auth-oauthlib exceptions on failure;
    the router should catch these and return an appropriate error response.
    """
    flow = _get_flow()

    # Sync network call — run in a thread to avoid blocking the event loop.
    # OAUTHLIB_RELAX_TOKEN_SCOPE tells oauthlib to accept the returned scopes
    # even when Google returns them in a different order than requested.
    def _fetch() -> None:
        import os
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"
        flow.fetch_token(code=code)

    await asyncio.to_thread(_fetch)

    creds = flow.credentials

    # Normalize token expiry to UTC-aware datetime.
    expiry = creds.expiry
    if expiry is None:
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    elif expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    # Fetch the connected account email via the userinfo endpoint.
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {creds.token}"},
        )
        resp.raise_for_status()
        email: str = resp.json().get("email", "")

    return GoogleTokenInfo(
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        token_expiry=expiry,
        google_email=email,
    )
