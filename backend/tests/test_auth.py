"""Tests for auth security helpers and auth service logic (v3 auth milestone).

All tests are pure Python — no DB, no HTTP.  The service-level tests mock the
DB session following the same pattern used in test_insights.py.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)


# ── Password hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        assert hash_password("secret") != "secret"

    def test_correct_password_verifies(self) -> None:
        h = hash_password("correct-horse-battery")
        assert verify_password("correct-horse-battery", h) is True

    def test_wrong_password_fails(self) -> None:
        h = hash_password("correct-horse-battery")
        assert verify_password("wrong", h) is False

    def test_same_password_produces_different_hashes(self) -> None:
        # bcrypt salts each hash — two hashes of the same password differ.
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


# ── JWT — access tokens ───────────────────────────────────────────────────────

class TestAccessToken:
    def test_round_trip(self) -> None:
        uid = uuid4()
        token = create_access_token(uid)
        assert decode_access_token(token) == uid

    def test_tampered_token_returns_none(self) -> None:
        token = create_access_token(uuid4())
        tampered = token[:-4] + "XXXX"
        assert decode_access_token(tampered) is None

    def test_empty_string_returns_none(self) -> None:
        assert decode_access_token("") is None

    def test_refresh_token_rejected_as_access(self) -> None:
        """A refresh token must not be accepted as an access token."""
        uid = uuid4()
        refresh = create_refresh_token(uid)
        # Passing a refresh token to decode_access_token must return None.
        assert decode_access_token(refresh) is None


# ── JWT — refresh tokens ──────────────────────────────────────────────────────

class TestRefreshToken:
    def test_round_trip(self) -> None:
        uid = uuid4()
        token = create_refresh_token(uid)
        assert decode_refresh_token(token) == uid

    def test_access_token_rejected_as_refresh(self) -> None:
        """An access token must not be accepted as a refresh token."""
        uid = uuid4()
        access = create_access_token(uid)
        assert decode_refresh_token(access) is None

    def test_tampered_token_returns_none(self) -> None:
        token = create_refresh_token(uuid4())
        tampered = token[:-4] + "XXXX"
        assert decode_refresh_token(tampered) is None


# ── Auth service — register ───────────────────────────────────────────────────

class TestRegisterService:
    def _make_session(self, existing_user=None) -> AsyncMock:
        """Mock session where get_user_by_email returns existing_user."""
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing_user
        # First execute call = get_user_by_email lookup.
        # Second execute call = session.refresh (called in create_user_with_password).
        session.execute.return_value = result_mock
        return session

    @pytest.mark.asyncio
    async def test_register_returns_tokens(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.modules.auth import service as svc
        from app.modules.auth.schemas import RegisterRequest

        created_user = MagicMock()
        created_user.id = uuid4()
        created_user.password_hash = hash_password("testpass1")

        async def fake_get_by_email(session, email):
            return None  # no existing user

        async def fake_create(session, payload):
            return created_user

        monkeypatch.setattr(svc, "get_user_by_email", fake_get_by_email)
        monkeypatch.setattr(svc, "create_user_with_password", fake_create)

        session = AsyncMock()
        payload = RegisterRequest(
            name="Alex", email="alex@example.com",
            password="testpass1", timezone="UTC"
        )
        user, access, refresh = await svc.register(session, payload)

        assert user is created_user
        assert decode_access_token(access) == created_user.id
        assert decode_refresh_token(refresh) == created_user.id

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises_409(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException
        from app.modules.auth import service as svc
        from app.modules.auth.schemas import RegisterRequest

        existing = MagicMock()

        async def fake_get_by_email(session, email):
            return existing  # email already taken

        monkeypatch.setattr(svc, "get_user_by_email", fake_get_by_email)

        session = AsyncMock()
        payload = RegisterRequest(
            name="Alex", email="taken@example.com",
            password="testpass1", timezone="UTC"
        )
        with pytest.raises(HTTPException) as exc_info:
            await svc.register(session, payload)

        assert exc_info.value.status_code == 409


# ── Auth service — login ──────────────────────────────────────────────────────

class TestLoginService:
    @pytest.mark.asyncio
    async def test_login_correct_credentials(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.modules.auth import service as svc
        from app.modules.auth.schemas import LoginRequest

        uid = uuid4()
        user = MagicMock()
        user.id = uid
        user.password_hash = hash_password("correctpass")

        async def fake_get_by_email(session, email):
            return user

        monkeypatch.setattr(svc, "get_user_by_email", fake_get_by_email)

        session = AsyncMock()
        payload = LoginRequest(email="alex@example.com", password="correctpass")
        result_user, access, refresh = await svc.login(session, payload)

        assert result_user is user
        assert decode_access_token(access) == uid
        assert decode_refresh_token(refresh) == uid

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException
        from app.modules.auth import service as svc
        from app.modules.auth.schemas import LoginRequest

        user = MagicMock()
        user.id = uuid4()
        user.password_hash = hash_password("correctpass")

        async def fake_get_by_email(session, email):
            return user

        monkeypatch.setattr(svc, "get_user_by_email", fake_get_by_email)

        session = AsyncMock()
        payload = LoginRequest(email="alex@example.com", password="wrongpass")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login(session, payload)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_raises_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException
        from app.modules.auth import service as svc
        from app.modules.auth.schemas import LoginRequest

        async def fake_get_by_email(session, email):
            return None  # user not found

        monkeypatch.setattr(svc, "get_user_by_email", fake_get_by_email)

        session = AsyncMock()
        payload = LoginRequest(email="ghost@example.com", password="anything")
        with pytest.raises(HTTPException) as exc_info:
            await svc.login(session, payload)

        assert exc_info.value.status_code == 401
