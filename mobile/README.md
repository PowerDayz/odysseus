# Odysseus Mobile

Initial Flutter client for the Odysseus mobile API.

## Setup

Install Flutter, then from this directory run:

```bash
flutter create . --platforms=android,ios,web
flutter pub get
flutter analyze
flutter test
flutter run
```

The first screen pairs with an existing Odysseus server using the server-generated pairing token from `/api/mobile/pair/start`. After pairing, the app stores the returned mobile API token in platform secure storage and calls:

- `GET /api/mobile/status`
- `GET /api/mobile/events`
- `POST /api/mobile/events/{event_id}/ack`

## Visual direction

The app mirrors the existing web UI palette and feel: dark `#282c34` background, black panel cards, cyan foreground text, red Odysseus accent, thin borders, monospace typography, compact rounded controls, and simple terminal-style copy.
