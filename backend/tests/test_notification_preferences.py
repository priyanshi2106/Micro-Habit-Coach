"""Unit tests for notification preference schemas.

Verifies that NotificationPreferenceUpdate:
- accepts every valid combination of notify_minutes_before and confidence_threshold,
- rejects every disallowed value with a clear error message,
- handles floating-point representation noise (0.45000000001 → valid),
- and that DEFAULT_PREFERENCES has the correct opt-in default values.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.notifications.schemas import (
    ALLOWED_CONFIDENCE_THRESHOLDS,
    ALLOWED_NOTIFY_MINUTES,
    DEFAULT_PREFERENCES,
    NotificationPreferenceUpdate,
)


# ── notify_minutes_before ─────────────────────────────────────────────────────

class TestNotifyMinutesBefore:
    @pytest.mark.parametrize("minutes", [5, 10, 15, 30])
    def test_all_allowed_minutes_accepted(self, minutes: int) -> None:
        prefs = NotificationPreferenceUpdate(
            enabled=True,
            notify_minutes_before=minutes,
            confidence_threshold=0.65,
        )
        assert prefs.notify_minutes_before == minutes

    @pytest.mark.parametrize("bad", [0, 1, 7, 20, 60, -5])
    def test_disallowed_minutes_rejected(self, bad: int) -> None:
        with pytest.raises(ValidationError) as exc_info:
            NotificationPreferenceUpdate(
                enabled=True,
                notify_minutes_before=bad,
                confidence_threshold=0.65,
            )
        errors = exc_info.value.errors()
        assert any("notify_minutes_before" in str(e) for e in errors)

    def test_default_minutes_is_valid(self) -> None:
        # Ensure the hardcoded default of 15 is in the allowed set
        assert 15 in ALLOWED_NOTIFY_MINUTES

    def test_error_message_mentions_allowed_values(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            NotificationPreferenceUpdate(
                enabled=True,
                notify_minutes_before=7,
                confidence_threshold=0.65,
            )
        msg = str(exc_info.value)
        assert "5" in msg
        assert "30" in msg


# ── confidence_threshold ──────────────────────────────────────────────────────

class TestConfidenceThreshold:
    @pytest.mark.parametrize("threshold", [0.45, 0.65, 0.80])
    def test_all_allowed_thresholds_accepted(self, threshold: float) -> None:
        prefs = NotificationPreferenceUpdate(
            enabled=True,
            notify_minutes_before=15,
            confidence_threshold=threshold,
        )
        assert prefs.confidence_threshold == threshold

    @pytest.mark.parametrize("bad", [0.0, 0.50, 0.70, 0.75, 1.0, -0.1])
    def test_disallowed_thresholds_rejected(self, bad: float) -> None:
        with pytest.raises(ValidationError) as exc_info:
            NotificationPreferenceUpdate(
                enabled=True,
                notify_minutes_before=15,
                confidence_threshold=bad,
            )
        errors = exc_info.value.errors()
        assert any("confidence_threshold" in str(e) for e in errors)

    def test_floating_point_noise_accepted(self) -> None:
        # Simulate JSON round-trip where 0.45 becomes 0.4500000000000001
        prefs = NotificationPreferenceUpdate(
            enabled=True,
            notify_minutes_before=15,
            confidence_threshold=0.4500000000000001,
        )
        assert prefs.confidence_threshold == 0.45

    def test_default_threshold_is_valid(self) -> None:
        # Ensure the hardcoded default of 0.65 is in the allowed set
        assert 0.65 in ALLOWED_CONFIDENCE_THRESHOLDS

    def test_error_message_mentions_allowed_values(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            NotificationPreferenceUpdate(
                enabled=True,
                notify_minutes_before=15,
                confidence_threshold=0.50,
            )
        msg = str(exc_info.value)
        assert "0.45" in msg or "0.65" in msg


# ── enabled field ─────────────────────────────────────────────────────────────

class TestEnabledField:
    def test_enabled_true_accepted(self) -> None:
        p = NotificationPreferenceUpdate(enabled=True, notify_minutes_before=15, confidence_threshold=0.65)
        assert p.enabled is True

    def test_enabled_false_accepted(self) -> None:
        p = NotificationPreferenceUpdate(enabled=False, notify_minutes_before=15, confidence_threshold=0.65)
        assert p.enabled is False


# ── DEFAULT_PREFERENCES ───────────────────────────────────────────────────────

class TestDefaultPreferences:
    def test_default_enabled_is_false(self) -> None:
        """Notifications must be opt-in by default."""
        assert DEFAULT_PREFERENCES.enabled is False

    def test_default_minutes_is_in_allowed_set(self) -> None:
        assert DEFAULT_PREFERENCES.notify_minutes_before in ALLOWED_NOTIFY_MINUTES

    def test_default_threshold_is_in_allowed_set(self) -> None:
        assert DEFAULT_PREFERENCES.confidence_threshold in ALLOWED_CONFIDENCE_THRESHOLDS

    def test_default_last_acknowledged_at_is_none(self) -> None:
        assert DEFAULT_PREFERENCES.last_acknowledged_at is None

    def test_default_ids_are_none(self) -> None:
        # Defaults are returned before a row exists — both IDs must be None
        assert DEFAULT_PREFERENCES.id is None
        assert DEFAULT_PREFERENCES.user_id is None
