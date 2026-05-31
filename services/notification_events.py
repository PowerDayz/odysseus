"""Privacy-preserving mobile notification event helpers."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from core.database import NotificationEvent


def opaque_push_payload(event_id: str) -> dict[str, str]:
    """Return the only payload shape that may be sent to push providers by default."""

    return {"event_id": event_id, "type": "odysseus_event"}


def create_notification_event(
    db,
    *,
    owner: str,
    event_type: str,
    private_payload: dict[str, Any],
    device_id: str | None = None,
    priority: str = "normal",
    ttl_seconds: int = 7 * 24 * 60 * 60,
) -> NotificationEvent:
    event = NotificationEvent(
        id="evt_" + secrets.token_urlsafe(18),
        owner=owner,
        device_id=device_id,
        event_type=(event_type or "generic")[:64],
        priority=(priority or "normal")[:32],
        expires_at=datetime.utcnow() + timedelta(seconds=ttl_seconds),
        private_payload_json=json.dumps(private_payload or {}, separators=(",", ":")),
        delivery_status="created",
    )
    db.add(event)
    return event


def event_summary(event: NotificationEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "priority": event.priority,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "expires_at": event.expires_at.isoformat() if event.expires_at else None,
        "consumed_at": event.consumed_at.isoformat() if event.consumed_at else None,
        "delivery_status": event.delivery_status,
    }


def event_detail(event: NotificationEvent) -> dict[str, Any]:
    detail = event_summary(event)
    try:
        detail["private_payload"] = json.loads(event.private_payload_json or "{}")
    except Exception:
        detail["private_payload"] = {}
    return detail
