# Communication architecture

**Status:** Planning — 2026-11-05.

## Data flow

PS5 LAN → discovery/status adapter → normalized console observation.

Optional Remote Play pairing/control → authenticated command adapter → fresh LAN confirmation.

Optional PSN presence → account observation → game metadata and player association with explicit confidence.

Normalized observations → state fusion → session tracker → SQLite / native HA entities → sidebar panel.

## Rules

- No third-party runtime bridge service.
- LAN monitoring must remain useful without PSN.
- Each transport has its own timeouts, credentials, lifecycle and failure status.
- No optimistic success on sending a command.
- Avoid mixing PS4 Second Screen and PS5 Remote Play wire formats.
- Keep the event loop non-blocking and allow multiple consoles.

See [protocol index](../protocols/README.md).
