"""Password hashing and JWT utilities for auth (v3 — real auth milestone).

Design decisions:
- bcrypt via passlib: intentionally slow to resist offline brute-force.
- HS256 JWT: stateless access tokens, verified without a DB round-trip.
- Refresh tokens are opaque UUIDs stored in the DB (see auth service);
  this file only handles the short-lived access token.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
# Claim key that holds the user's UUID as a string.
_SUBJECT_CLAIM = "sub"


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


# ── JWT helpers ───────────────────────────────────────────────────────────────

_REFRESH_TOKEN_EXPIRE_DAYS = 7
_TOKEN_TYPE_CLAIM = "typ"


def create_access_token(user_id: UUID) -> str:
    """Return a signed JWT encoding the user's UUID.

    Expiry is driven by settings.access_token_expire_minutes so it can be
    overridden via env var without a code change.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {_SUBJECT_CLAIM: str(user_id), "exp": expire, _TOKEN_TYPE_CLAIM: "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """Return a long-lived signed JWT used only to issue new access tokens.

    Stored in an HTTP-only cookie so JS cannot read it.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {_SUBJECT_CLAIM: str(user_id), "exp": expire, _TOKEN_TYPE_CLAIM: "refresh"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[UUID]:
    """Decode and verify an access JWT.  Returns the user UUID or None if invalid/expired."""
    return _decode_token(token, expected_type="access")


def decode_refresh_token(token: str) -> Optional[UUID]:
    """Decode and verify a refresh JWT.  Returns the user UUID or None if invalid/expired."""
    return _decode_token(token, expected_type="refresh")


def _decode_token(token: str, *, expected_type: str) -> Optional[UUID]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get(_TOKEN_TYPE_CLAIM) != expected_type:
            return None
        sub: Optional[str] = payload.get(_SUBJECT_CLAIM)
        if sub is None:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None
