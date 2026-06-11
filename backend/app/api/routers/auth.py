"""Auth endpoints: register, login, refresh, logout."""
from __future__ import annotations

from fastapi import APIRouter, Cookie, HTTPException, Response, status
from typing import Optional

from app.api.deps import DbSession
from app.core.security import create_access_token, decode_refresh_token
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.auth.service import login, register
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# Cookie name for the HTTP-only refresh token.
_REFRESH_COOKIE = "refresh_token"
# 7 days in seconds.
_REFRESH_MAX_AGE = 7 * 24 * 60 * 60


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,       # JS cannot read this cookie
        secure=False,        # set True in production (requires HTTPS)
        samesite="lax",      # CSRF protection for same-origin requests
        max_age=_REFRESH_MAX_AGE,
        path="/auth",        # cookie is only sent to /auth/* routes
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    body: RegisterRequest,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    user, access_token, refresh_token = await register(session, body)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
async def login_user(
    body: LoginRequest,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    _, access_token, refresh_token = await login(session, body)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> TokenResponse:
    """Issue a new access token using the HTTP-only refresh cookie.

    The frontend calls this silently on app load to restore the session.
    """
    if refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token",
        )
    user_id = decode_refresh_token(refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    new_access = create_access_token(user_id)
    return TokenResponse(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Clear the refresh cookie. The client should discard its access token."""
    response.delete_cookie(key=_REFRESH_COOKIE, path="/auth")
