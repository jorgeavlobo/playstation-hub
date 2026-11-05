# PlayStation Hub — Protocol specifications

**Status:** Research and planning. **Last reviewed:** 2026-11-05.

These documents describe the first-party PlayStation connectivity architecture before implementation. No protocol is declared validated on a live console. External repositories are references, not runtime requirements.

## Protocol index

- [LAN discovery](01-lan-discovery.md) — Find PS5 consoles on local IPv4 networks without an external service.
- [Console status](02-console-status.md) — Normalize LAN console observations into reliable state.
- [Console wake-up](03-console-wakeup.md) — Wake a paired PS5 without PS5-MQTT.
- [Remote Play registration](04-remote-play-registration.md) — Pair a console using a user-authorized Remote Play flow.
- [Remote Play cryptography](05-remote-play-cryptography.md) — Describe cryptographic primitives and validation evidence without embedding real secrets.
- [Remote Play session](06-remote-play-session.md) — Establish and maintain an authenticated control session.
- [Remote Play commands](07-remote-play-commands.md) — Execute user-authorized console commands with observed confirmation.
- [PSN authentication](08-psn-authentication.md) — Obtain optional PSN account authorization for enriched activity data.
- [PSN presence](09-psn-presence.md) — Associate PSN account presence with observed game activity.
- [Game metadata and artwork](10-game-metadata.md) — Obtain game identifiers, names and cover art without coupling to the dashboard.

## Evidence labels

- **SOURCE-CONFIRMED:** Directly visible in an identified upstream source file.
- **DESIGN DECISION:** Our proposed implementation policy, not a Sony protocol guarantee.
- **UNVERIFIED:** Requires further protocol review or future real-device testing.
- **BLOCKED:** Cannot be shipped without resolving a security, legal or compatibility constraint.

## Common contract

Each specification includes scope, observed upstream behavior, planned Python boundary, safety and failure behavior, sources, and unresolved questions. Preserve source URLs and pinned revision references. Use English for code, comments and protocol documents; user-visible UI is multilingual.

**Pinned reference trees (2026-11-05):** PS5-MQTT `7ab3075d276f3eeecd81a3322c72231af8cd51bd`; playactor `93ee087445db368acaba9ad50099bce56ca9141d`; psn-api `1e9d9a806fcd884a4ddee8086bfe92594611da9f`.

## First-party integration principle

One HACS custom integration with Python protocol adapters, native HA entities, independent session storage and a single multilingual sidebar panel. No required PS5-MQTT add-on, Mosquitto broker, Node.js or standalone container. Reusing vetted Python dependencies remains possible after license/security review.
