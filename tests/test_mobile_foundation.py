from types import SimpleNamespace

from services.mobile_devices import PairingTokenStore, create_mobile_device, device_to_dict
from services.notification_events import opaque_push_payload


class _FakeDb:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


class _Record:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, _name):
        return None


def test_pairing_tokens_are_short_lived_and_single_use():
    store = PairingTokenStore(ttl_seconds=60)
    record = store.create(owner="alice", server_url="https://odysseus.example.com")

    assert record.token.startswith("ody_pair_")
    assert store.consume(record.token).owner == "alice"
    assert store.consume(record.token) is None


def test_mobile_device_creation_uses_device_specific_scoped_token(monkeypatch):
    import services.mobile_devices as mobile_devices

    monkeypatch.setattr(mobile_devices, "ApiToken", _Record)
    monkeypatch.setattr(mobile_devices, "MobileDevice", _Record)

    db = _FakeDb()
    device, token = mobile_devices.create_mobile_device(
        db,
        owner="alice",
        device_name="Alice iPhone",
        platform="ios",
        push_provider="apns",
        push_token="sensitive-provider-token",
    )

    assert token.startswith("ody_")
    assert device.owner == "alice"
    assert device.platform == "ios"
    assert "agent:approve" in device.scopes
    assert device.push_token_hash
    assert "sensitive-provider-token" not in repr(mobile_devices.device_to_dict(device))
    assert len(db.added) == 2


def test_push_payload_is_opaque():
    payload = opaque_push_payload("evt_abc")

    assert payload == {"event_id": "evt_abc", "type": "odysseus_event"}
    assert "subject" not in payload
    assert "summary" not in payload
    assert "message" not in payload


def test_device_to_dict_hides_token_material():
    device = SimpleNamespace(
        id="mob_1",
        device_name="Phone",
        platform="android",
        created_at=None,
        last_seen_at=None,
        revoked_at=None,
        notification_mode="fcm",
        notification_privacy_level=1,
        scopes="notifications:receive,agent:approve",
        push_provider="fcm",
        push_token_hash="abc123",
    )

    payload = device_to_dict(device)

    assert payload["push_registered"] is True
    assert "push_token_hash" not in payload
    assert "abc123" not in repr(payload)
