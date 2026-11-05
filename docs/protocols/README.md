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
- [PSN authentication](08-psn-authentication.md) — Detailed source-derived NPSSO/token lifecycle specification; provider authorization and permitted client use remain blocked release gates.
- [PSN presence](09-psn-presence.md) — Detailed source-derived account presence, game activity, polling, privacy, physical-console attribution and reconciliation specification; Sony client/endpoint permission remains unresolved.
- [Game metadata and artwork](10-game-metadata.md) — Detailed source-derived PSN game identity, played/recent/digital libraries, localized metadata, artwork rights, caching, security and tests.

**Documentation progress (2026-11-05):** Protocols 01–07 and 08 contain detailed research specifications; Protocol 09 now has detailed source research; Protocol 10 now has a detailed source-derived research specification. Research maturity is not a live validation or ship-readiness claim.

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

**Protocol 08 research checkpoint (2026-11-05):** Added dedicated reviews of Sony browser-login limitations, authorization-callback eligibility, PSNAWP PyPI versus development APIs, official HA and Emkraan token persistence, refresh-token concurrency, crash/backup recovery and a synthetic test matrix. See [Protocol 08](08-psn-authentication.md), sections 12–16. This does not establish a Sony-approved OAuth client or live protocol compatibility.

**Official Home Assistant Core reference:** A detailed audit of `playstation_network` and its automatic DHCP discovery, config flows, PSNAWP account data, platforms/entities, test coverage and multi-console limitations is maintained at [Core PlayStation Network deep reference audit](../research/home-assistant-core-playstation-network-audit.md). This reference informs Protocols 01, 02, 08, 09 and 10; it does not validate our own integration.

## Cross-protocol architecture review

Before implementation, consult [Cross-protocol architecture review (Protocols 01–10)](../architecture/cross-protocol-review-01-10.md): 22 findings and prioritized ADR/spec prerequisites address device/account identity, source authority and freshness, conservative history, Remote Play byte contracts, Sony API permission, persistence and backups, Home Assistant discovery/entity/action/sidepanel lifecycles and release acceptance. **Detailed protocol documents are not equivalent to an approved or working integration.**

**Cross-source state contract:** The proposed [ADR-0005 Observation Envelope and State Reconciliation](../decisions/ADR-0005-observation-and-state-reconciliation.md) unifies observation identity, ordering, freshness, fact-specific authority and command confirmation across protocols. It remains proposed; no source is declared live validated.

**Session and usage accounting:** The proposed [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md) defines how accepted source observations may contribute to bounded duration, unknown gaps, player attribution, multi-console historical statistics and recovery. A successful status poll is a point observation, not proof of uninterrupted activity or exact game transition time.
