"""Mobile device pairing and registration helpers."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt

from core.database import ApiToken, MobileDevice

DEFAULT_MOBILE_SCOPES = (
    "chat:read",
    "chat:write",
    "agent:read",
    "agent:approve",
    "email:triage_read",
    "calendar:read",
    "tasks:read",
    "notifications:receive",
    "settings:mobile",
)


@dataclass
class PairingToken:
    token: str
    owner: str
    server_url: str
    expires_at: datetime


class PairingTokenStore:
    """Small in-process store for short-lived mobile pairing tokens."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, PairingToken] = {}

    def create(self, owner: str, server_url: str = "") -> PairingToken:
        self.cleanup()
        token = "ody_pair_" + secrets.token_urlsafe(32)
        record = PairingToken(
            token=token,
            owner=owner,
            server_url=server_url,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=self.ttl_seconds),
        )
        self._tokens[token] = record
        return record

    def consume(self, token: str) -> PairingToken | None:
        self.cleanup()
        record = self._tokens.pop(token, None)
        if not record or record.expires_at <= datetime.now(timezone.utc):
            return None
        return record

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        expired = [token for token, record in self._tokens.items() if record.expires_at <= now]
        for token in expired:
            self._tokens.pop(token, None)


pairing_tokens = PairingTokenStore()


def sanitize_device_name(value: str | None) -> str:
    name = (value or "Mobile device").strip()
    return name[:80] or "Mobile device"


def sanitize_platform(value: str | None) -> str:
    platform = (value or "unknown").strip().lower()
    allowed = {"ios", "android", "web", "unknown"}
    return platform if platform in allowed else "unknown"


def normalize_scopes(scopes: list[str] | tuple[str, ...] | None = None) -> list[str]:
    requested = scopes or DEFAULT_MOBILE_SCOPES
    allowed = set(DEFAULT_MOBILE_SCOPES)
    return [scope for scope in requested if scope in allowed]


def hash_push_token(push_token: str | None) -> str | None:
    if not push_token:
        return None
    return hashlib.sha256(push_token.encode("utf-8")).hexdigest()


def create_mobile_device(
    db,
    *,
    owner: str,
    device_name: str,
    platform: str,
    notification_mode: str = "local",
    notification_privacy_level: int = 1,
    push_provider: str | None = None,
    push_token: str | None = None,
    scopes: list[str] | None = None,
) -> tuple[MobileDevice, str]:
    """Create a revocable device plus a device-specific bearer token."""

    token = "ody_" + secrets.token_urlsafe(32)
    token_id = str(uuid.uuid4())[:8]
    device_id = "mob_" + secrets.token_urlsafe(12)
    mobile_scopes = normalize_scopes(scopes)

    api_token = ApiToken(
        id=token_id,
        owner=owner,
        name=f"Mobile: {sanitize_device_name(device_name)}",
        token_hash=bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode(),
        token_prefix=token[:8],
        scopes=",".join(mobile_scopes),
        is_active=True,
    )
    device = MobileDevice(
        id=device_id,
        owner=owner,
        device_name=sanitize_device_name(device_name),
        platform=sanitize_platform(platform),
        api_token_id=token_id,
        notification_mode=(notification_mode or "local")[:32],
        notification_privacy_level=max(0, min(int(notification_privacy_level), 4)),
        scopes=",".join(mobile_scopes),
        push_provider=(push_provider or "")[:32] or None,
        push_token_hash=hash_push_token(push_token),
    )
    db.add(api_token)
    db.add(device)
    return device, token


def device_to_dict(device: MobileDevice) -> dict[str, Any]:
    return {
        "id": device.id,
        "device_name": device.device_name,
        "platform": device.platform,
        "created_at": device.created_at.isoformat() if device.created_at else None,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "revoked_at": device.revoked_at.isoformat() if device.revoked_at else None,
        "notification_mode": device.notification_mode,
        "notification_privacy_level": device.notification_privacy_level,
        "scopes": [s for s in (device.scopes or "").split(",") if s],
        "push_provider": device.push_provider,
        "push_registered": bool(device.push_token_hash),
    }
