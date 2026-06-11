"""Unit tests for calendar/oauth.py — Fernet encryption and state JWT.

All tests are pure Python: no network, no database, no async.
The Google OAuth URL generation and code exchange are not tested here because
they require real Google credentials or a mock server — those belong in
integration tests.  This file tests everything that can be tested in isolation.
"""
from __future__ import annotations

import os
import uuid

import pytest
from cryptography.fernet import Fernet, InvalidToken

from app.modules.calendar.oauth import (
    CalendarNotConfiguredError,
    create_state_token,
    decode_state_token,
    decrypt_token,
    encrypt_token,
    get_google_oauth_url,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_settings_cache():
    """Clear the lru_cache on get_settings between tests so env var changes take effect."""
    from app.core.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("CALENDAR_ENCRYPTION_KEY", key)
    return key


@pytest.fixture()
def no_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CALENDAR_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("CALENDAR_ENCRYPTION_KEY", "")


# ── Fernet encrypt / decrypt ──────────────────────────────────────────────────

class TestFernetEncryption:
    def test_round_trip(self, fernet_key: str) -> None:
        plaintext = "ya29.some_google_access_token"
        assert decrypt_token(encrypt_token(plaintext)) == plaintext

    def test_ciphertext_differs_from_plaintext(self, fernet_key: str) -> None:
        plaintext = "access_token_xyz"
        ciphertext = encrypt_token(plaintext)
        assert ciphertext != plaintext

    def test_two_encryptions_of_same_value_differ(self, fernet_key: str) -> None:
        """Fernet uses a random IV — same plaintext → different ciphertext each time."""
        plaintext = "same_token"
        assert encrypt_token(plaintext) != encrypt_token(plaintext)

    def test_tampered_ciphertext_raises(self, fernet_key: str) -> None:
        ciphertext = encrypt_token("token")
        tampered = ciphertext[:-4] + "XXXX"
        with pytest.raises((InvalidToken, Exception)):
            decrypt_token(tampered)

    def test_decrypt_garbage_raises(self, fernet_key: str) -> None:
        with pytest.raises(Exception):
            decrypt_token("not.a.fernet.token")

    def test_no_encryption_key_raises_not_configured(self, no_encryption_key: None) -> None:
        with pytest.raises(CalendarNotConfiguredError):
            encrypt_token("any_token")

    def test_invalid_key_raises_not_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CALENDAR_ENCRYPTION_KEY", "not-a-valid-fernet-key")
        with pytest.raises(CalendarNotConfiguredError):
            encrypt_token("any_token")

    def test_encrypts_refresh_token_successfully(self, fernet_key: str) -> None:
        refresh = "1//0gRefreshTokenFromGoogle"
        assert decrypt_token(encrypt_token(refresh)) == refresh


# ── State JWT ─────────────────────────────────────────────────────────────────

class TestStateToken:
    def test_round_trip(self) -> None:
        user_id = uuid.uuid4()
        token = create_state_token(user_id)
        decoded = decode_state_token(token)
        assert decoded == str(user_id)

    def test_random_string_returns_none(self) -> None:
        assert decode_state_token("garbage.token.here") is None

    def test_empty_string_returns_none(self) -> None:
        assert decode_state_token("") is None

    def test_different_user_ids_produce_different_tokens(self) -> None:
        a = create_state_token(uuid.uuid4())
        b = create_state_token(uuid.uuid4())
        assert a != b

    def test_auth_access_token_rejected_as_state_token(self) -> None:
        """An auth access token must not be accepted as a calendar state token."""
        from app.core.security import create_access_token
        auth_token = create_access_token(uuid.uuid4())
        # decode_state_token checks for purpose="calendar_oauth" claim
        result = decode_state_token(auth_token)
        assert result is None

    def test_state_token_rejected_as_auth_token(self) -> None:
        """A calendar state token must not be accepted as an auth access token."""
        from app.core.security import decode_access_token
        state_token = create_state_token(uuid.uuid4())
        result = decode_access_token(state_token)
        assert result is None

    def test_token_is_a_non_empty_string(self) -> None:
        token = create_state_token(uuid.uuid4())
        assert isinstance(token, str) and len(token) > 0


# ── OAuth URL generation ──────────────────────────────────────────────────────

class TestOAuthUrl:
    def test_raises_when_client_id_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
        with pytest.raises(CalendarNotConfiguredError):
            get_google_oauth_url(uuid.uuid4())

    def test_raises_when_only_client_id_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
        with pytest.raises(CalendarNotConfiguredError):
            get_google_oauth_url(uuid.uuid4())

    def test_url_contains_expected_components(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        url = get_google_oauth_url(uuid.uuid4())
        assert "accounts.google.com" in url
        assert "calendar.readonly" in url
        assert "state=" in url
        assert "access_type=offline" in url

    def test_url_contains_unique_state_per_user(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        url1 = get_google_oauth_url(uuid.uuid4())
        url2 = get_google_oauth_url(uuid.uuid4())
        # State param should differ for different users.
        state1 = [p for p in url1.split("&") if p.startswith("state=")][0]
        state2 = [p for p in url2.split("&") if p.startswith("state=")][0]
        assert state1 != state2

    def test_state_in_url_decodes_to_user_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from urllib.parse import urlparse, parse_qs
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
        user_id = uuid.uuid4()
        url = get_google_oauth_url(user_id)
        params = parse_qs(urlparse(url).query)
        state_jwt = params["state"][0]
        decoded_uid = decode_state_token(state_jwt)
        assert decoded_uid == str(user_id)
