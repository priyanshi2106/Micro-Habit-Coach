"""Structured application logger for analytics events.

Emits JSON lines to stdout so they are captured automatically by Render,
Railway, Fly.io, and any other platform that tails stdout.

Usage:
    from app.modules.analytics.logger import log_event

    log_event("goal_suggestions_requested", {
        "user_id": str(user.id),
        "goal": goal,
        "source": "ai",
        "suggestions_returned": 4,
    })

Events are best-effort — a logging failure must never surface to the user or
block the response. Callers should wrap in try/except if needed.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

_log = logging.getLogger("analytics")

# Ensure the analytics logger always reaches the handler even if the root
# logger level is set higher in some environments.
if not _log.handlers:
    _handler = logging.StreamHandler()
    _handler.setLevel(logging.INFO)
    _log.addHandler(_handler)
    _log.setLevel(logging.INFO)


def log_event(name: str, payload: dict[str, Any]) -> None:
    """Emit a single structured analytics event as a JSON line."""
    record = {
        "event": name,
        "ts": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    try:
        _log.info(json.dumps(record))
    except Exception:
        pass
