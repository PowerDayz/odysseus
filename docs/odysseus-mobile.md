# Odysseus Mobile Flutter App Plan

## Working title

**Odysseus Mobile** is a privacy-first Flutter companion app for Odysseus that lets users securely connect to their own self-hosted Odysseus instance, remotely control local models and agents, and receive mobile notifications without exposing private user data.

## Core principle

Odysseus Mobile must preserve Odysseus' local-first/private-data promise. APNs, FCM, `ntfy`, UnifiedPush, or similar systems may be used only as wake-up transports.

Push payloads should not include email contents, email subjects, sender names by default, AI summaries, prompts, documents, calendar contents, task contents, model outputs, private memory contents, user files, or chat messages.

Default push payloads should be generic and opaque:

```json
{
  "event_id": "evt_random_opaque_id",
  "type": "odysseus_event"
}
```

The phone receives the notification, opens the app, authenticates locally, then fetches private details directly from the user's Odysseus instance.

## High-level architecture

```text
User's Odysseus Instance
  - local models
  - email
  - calendar
  - agents
  - memory
  - notification rules
  - private event queue
        |
        | generic wake-up event only
        v
Notification Transport
  - APNs for iOS
  - FCM for Android
  - self-hosted ntfy
  - UnifiedPush where available
        |
        | opaque push only
        v
Flutter Mobile App
  - receives generic notification
  - unlocks with biometrics/passcode when configured
  - connects directly to Odysseus
  - fetches private event details
```

## Main app functions

### Connect to Odysseus

The app should support manual server URL entry, QR-code pairing from the Odysseus web UI, LAN access, Tailscale/WireGuard/VPN access, HTTPS reverse proxy access, and optional self-signed/local certificate handling for advanced users.

For non-local connections, HTTPS should be strongly recommended or required.

### Secure device pairing

Odysseus should use dedicated mobile pairing instead of normal browser sessions:

```text
1. User opens Odysseus web UI.
2. User goes to Settings -> Mobile Devices.
3. User clicks "Pair New Device".
4. Odysseus displays QR code with short-lived pairing token.
5. Flutter app scans QR code.
6. App exchanges pairing token for a device-specific token.
7. Odysseus stores the device as a revocable mobile client.
```

Device records should include id, user/owner, device name, platform, created time, last seen time, revoked time, notification mode, notification privacy level, scopes, push provider, push token hash, and the backing token id.

### Least-privilege mobile permissions

Suggested default mobile scopes:

```text
chat:read
chat:write
agent:read
agent:approve
email:triage_read
calendar:read
tasks:read
notifications:receive
settings:mobile
```

Dangerous capabilities should be opt-in or unavailable by default:

```text
shell:execute
files:write
mcp:admin
settings:admin
tokens:manage
model:download
server:manage
users:manage
```

Some non-dangerous admin actions, such as restarting services or managing models, may be added later behind explicit scopes.

## Notification design

Push providers should only receive generic wake-up payloads. Private data remains inside Odysseus until the authenticated mobile app fetches it directly.

Notification transports should include:

- local-only/app-open WebSocket or SSE notifications
- self-hosted `ntfy`
- APNs for iOS
- FCM for Android
- UnifiedPush for Android where available

APNs and FCM support should be possible from the start, but app-store credentials and release-specific code must remain private or gated behind build flags until official release builds are ready.

## Notification privacy levels

The default should be private.

```text
0. Silent/badge only
1. Generic alert: "Odysseus needs your attention"
2. Category only: "Urgent email detected"
3. Limited metadata: "Urgent email from Alice"
4. Summary/content preview: "Alice needs the contract reviewed before 5 PM"
```

Levels 3 and 4 must be explicit opt-ins. Level 4 should warn that private content may appear on the lock screen and may be sent to the notification provider.

## Notification event lifecycle

```text
1. Local model/email/calendar/task system creates a private event.
2. Odysseus stores full private event locally.
3. Odysseus creates an opaque event_id.
4. Odysseus sends only event_id/generic alert to the push provider.
5. Phone receives notification.
6. Phone connects directly to Odysseus.
7. Phone fetches private event details after authentication.
```

Notification events should include id, owner, optional device id, event type, priority, creation time, expiration time, consumed time, encrypted private payload JSON, push sent time, and delivery status.

## First version scope

This is not only a tiny MVP. The first solid version should include the core notification system and at least three killer use cases:

- agent approval notifications
- urgent email triage notifications
- long-running task completion notifications

Other target screens include pairing/connection, server status, notifications inbox, chat, agent activity, approval requests, email triage, and settings.

## Backend work

Expected backend modules:

```text
routes/mobile_routes.py
services/mobile_devices.py
services/notification_events.py
services/push_providers/
```

Suggested API endpoints:

```text
POST /api/mobile/pair/start
POST /api/mobile/pair/complete
GET  /api/mobile/devices
POST /api/mobile/devices/{id}/revoke

GET  /api/mobile/events
GET  /api/mobile/events/{event_id}
POST /api/mobile/events/{event_id}/ack

POST /api/mobile/push/register
POST /api/mobile/push/test

GET  /api/mobile/status
GET  /api/mobile/agent/activity
POST /api/mobile/agent/approvals/{id}/approve
POST /api/mobile/agent/approvals/{id}/deny
```

## Security requirements

Must-have:

- device-specific tokens
- short-lived pairing codes
- revocable devices
- scoped mobile permissions
- rate limiting
- push payloads contain no private data by default
- local encrypted storage for the mobile token in the app
- server URL verification during pairing
- audit log for mobile actions
- visible list of connected devices
- remote revoke

Should-have:

- per-device notification privacy level
- per-device scopes
- per-device notification provider
- per-device last seen timestamp
- optional biometric/passcode gate before app open or private details
- option to require re-auth before sensitive approvals

Avoid:

- sending content through APNs/FCM by default
- storing push tokens in logs
- exposing admin tools to mobile by default
- allowing mobile shell access by default
- using one global API token for every device

## Distribution

Early development can live inside this repository under `mobile/`. Later, the Flutter app may move to a separate `odysseus-mobile` repository while backend changes remain here.

Target distribution paths:

- side-load/developer install first
- F-Droid/GitHub releases for Android
- Play Store
- Apple App Store

## Build phases

1. **Foundation**: Flutter scaffold, URL connection, QR pairing, token storage, server status, simple authenticated call, basic chat or notification inbox.
2. **Private notification event system**: event queue, generic wake-up events, event detail fetch after auth, app-open local notifications, WebSocket/SSE while reachable.
3. **Self-hosted `ntfy`**: private topics, test notifications, generic-only payloads, local/VPS/Tailscale docs.
4. **Android push options**: FCM, UnifiedPush where practical, notification channels, optional foreground service for power users.
5. **iOS APNs**: APNs, notification permissions, silent push where appropriate, generic alert fallback, App Store-compatible behavior.
6. **Remote control features**: agent activity, approve/deny agent actions, email triage review, task/calendar reminders, chat continuation, model/server status.
