"""Mobile pairing, device, and private notification event APIs."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from core.database import ApiToken, MobileDevice, NotificationEvent, get_db_session
from services.mobile_devices import (
    create_mobile_device,
    device_to_dict,
    hash_push_token,
    pairing_tokens,
)
from services.notification_events import event_detail, event_summary, opaque_push_payload
from src.auth_helpers import require_user


def _invalidate_token_cache(request: Request) -> None:
    invalidator = getattr(request.app.state, "invalidate_token_cache", None)
    if invalidator:
        invalidator()


def _mobile_owner(request: Request) -> str:
    if getattr(request.state, "api_token", False):
        owner = getattr(request.state, "api_token_owner", None)
    else:
        owner = getattr(request.state, "current_user", None)
    if not owner:
        raise HTTPException(401, "Not authenticated")
    return owner


def _mobile_token_id(request: Request) -> str | None:
    return getattr(request.state, "api_token_id", None) if getattr(request.state, "api_token", False) else None


def setup_mobile_routes() -> APIRouter:
    router = APIRouter(prefix="/api/mobile", tags=["mobile"])

    @router.post("/pair/start")
    async def start_pairing(request: Request, body: dict | None = None):
        owner = require_user(request)
        server_url = ((body or {}).get("server_url") or str(request.base_url).rstrip("/")).strip()
        record = pairing_tokens.create(owner=owner, server_url=server_url)
        return {
            "pairing_token": record.token,
            "expires_at": record.expires_at.isoformat() + "Z",
            "qr_payload": {
                "type": "odysseus_mobile_pairing",
                "server_url": server_url,
                "pairing_token": record.token,
            },
        }

    @router.post("/pair/complete")
    async def complete_pairing(request: Request, body: dict):
        token = (body.get("pairing_token") or "").strip()
        record = pairing_tokens.consume(token)
        if not record:
            raise HTTPException(400, "Invalid or expired pairing token")

        with get_db_session() as db:
            device, mobile_token = create_mobile_device(
                db,
                owner=record.owner,
                device_name=body.get("device_name"),
                platform=body.get("platform"),
                notification_mode=body.get("notification_mode") or "local",
                notification_privacy_level=body.get("notification_privacy_level", 1),
                push_provider=body.get("push_provider"),
                push_token=body.get("push_token"),
            )
            db.flush()
            response = {
                "device": device_to_dict(device),
                "token": mobile_token,
                "server_url": record.server_url,
                "scopes": [s for s in (device.scopes or "").split(",") if s],
            }
        _invalidate_token_cache(request)
        return response

    @router.get("/status")
    async def mobile_status(request: Request):
        owner = _mobile_owner(request)
        token_id = _mobile_token_id(request)
        device_payload = None
        with get_db_session() as db:
            if token_id:
                device = db.query(MobileDevice).filter(
                    MobileDevice.api_token_id == token_id,
                    MobileDevice.owner == owner,
                ).first()
                if not device or device.revoked_at is not None:
                    raise HTTPException(403, "Mobile device revoked")
                device.last_seen_at = datetime.utcnow()
                device_payload = device_to_dict(device)
        return {"status": "ok", "owner": owner, "device": device_payload}

    @router.get("/devices")
    async def list_devices(request: Request):
        owner = _mobile_owner(request)
        with get_db_session() as db:
            devices = db.query(MobileDevice).filter(MobileDevice.owner == owner).order_by(MobileDevice.created_at.desc()).all()
            return {"devices": [device_to_dict(device) for device in devices]}

    @router.post("/devices/{device_id}/revoke")
    async def revoke_device(request: Request, device_id: str):
        owner = _mobile_owner(request)
        with get_db_session() as db:
            device = db.query(MobileDevice).filter(
                MobileDevice.id == device_id,
                MobileDevice.owner == owner,
            ).first()
            if not device:
                raise HTTPException(404, "Device not found")
            device.revoked_at = device.revoked_at or datetime.utcnow()
            if device.api_token_id:
                db.query(ApiToken).filter(ApiToken.id == device.api_token_id).update({"is_active": False})
        _invalidate_token_cache(request)
        return {"status": "revoked"}

    @router.post("/push/register")
    async def register_push(request: Request, body: dict):
        owner = _mobile_owner(request)
        token_id = _mobile_token_id(request)
        if not token_id:
            raise HTTPException(403, "Mobile token required")
        provider = (body.get("push_provider") or body.get("provider") or "").strip().lower()
        push_token = body.get("push_token")
        if provider not in {"ntfy", "apns", "fcm", "unifiedpush", "local"}:
            raise HTTPException(400, "Unsupported push provider")
        with get_db_session() as db:
            device = db.query(MobileDevice).filter(
                MobileDevice.api_token_id == token_id,
                MobileDevice.owner == owner,
                MobileDevice.revoked_at == None,  # noqa: E711
            ).first()
            if not device:
                raise HTTPException(404, "Device not found")
            device.push_provider = provider
            device.push_token_hash = hash_push_token(push_token)
            device.notification_mode = provider
            device.last_seen_at = datetime.utcnow()
        return {"status": "registered", "push_provider": provider, "push_registered": bool(push_token)}

    @router.post("/push/test")
    async def test_push(request: Request):
        owner = _mobile_owner(request)
        token_id = _mobile_token_id(request)
        with get_db_session() as db:
            device = None
            if token_id:
                device = db.query(MobileDevice).filter(MobileDevice.api_token_id == token_id).first()
            event = NotificationEvent(
                id="evt_test_" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f"),
                owner=owner,
                device_id=device.id if device else None,
                event_type="push_test",
                priority="normal",
                private_payload_json='{"message":"Mobile push test"}',
                delivery_status="created",
            )
            db.add(event)
            db.flush()
            return {"status": "created", "event": event_summary(event), "push_payload": opaque_push_payload(event.id)}

    @router.get("/events")
    async def list_events(request: Request):
        owner = _mobile_owner(request)
        now = datetime.utcnow()
        with get_db_session() as db:
            events = db.query(NotificationEvent).filter(
                NotificationEvent.owner == owner,
                NotificationEvent.consumed_at == None,  # noqa: E711
            ).filter(
                (NotificationEvent.expires_at == None) | (NotificationEvent.expires_at > now)  # noqa: E711
            ).order_by(NotificationEvent.created_at.desc()).limit(100).all()
            return {"events": [event_summary(event) for event in events]}

    @router.get("/events/{event_id}")
    async def get_event(request: Request, event_id: str):
        owner = _mobile_owner(request)
        with get_db_session() as db:
            event = db.query(NotificationEvent).filter(
                NotificationEvent.id == event_id,
                NotificationEvent.owner == owner,
            ).first()
            if not event:
                raise HTTPException(404, "Event not found")
            return event_detail(event)

    @router.post("/events/{event_id}/ack")
    async def ack_event(request: Request, event_id: str):
        owner = _mobile_owner(request)
        with get_db_session() as db:
            event = db.query(NotificationEvent).filter(
                NotificationEvent.id == event_id,
                NotificationEvent.owner == owner,
            ).first()
            if not event:
                raise HTTPException(404, "Event not found")
            event.consumed_at = event.consumed_at or datetime.utcnow()
        return {"status": "acknowledged"}

    return router
