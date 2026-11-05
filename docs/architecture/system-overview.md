# System overview

**Status:** Architecture planning — 2026-11-05.

PlayStation Hub is one HACS custom integration and one GitHub Release containing native Home Assistant Python code and a single multilingual custom sidebar panel.

## Logical components

1. LAN discovery/status transport.
2. Optional Remote Play pairing, wake and standby transport.
3. Optional PSN authentication and presence adapter.
4. State fusion with freshness and explicit uncertainty.
5. Multi-console/player domain and session tracking.
6. Dedicated persistence and native HA entities/actions.
7. One responsive sidebar frontend.

No PS5-MQTT, Mosquitto, Node.js or separate App is required by design. External protocol libraries remain subject to licensing and security review.

## Open architectural decisions

- Final storage path, SQLite consistency and backup/restore behavior.
- Multi-console config-entry boundaries and PSN account association.
- Exact Python transport contracts and supported console generations.
- Supported minimum Home Assistant release and frontend registration lifecycle.

See [protocol index](../protocols/README.md) and [architecture guide](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md).

## Cross-protocol review checkpoint

The [Protocols 01–10 architecture audit](cross-protocol-review-01-10.md) identifies the shared contracts required before implementation: identity/config-entry ownership, source observation and reconciliation, session uncertainty, Remote Play credential/cipher interoperability, PSN legal authorization, storage and backup approval, HA native discovery/entities/actions, versioned WebSocket panel API, error policy and release CI. Current designs remain research specifications; see the review's finding register and ADR backlog. **Dedicated SQLite remains provisional.**

## Identity ownership (proposed ADR-0004)

The proposed [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md) distinguishes physical console identity, PSN account identity and game title identity. Its preferred option is a separate HA config entry for each verified physical console and each PSN account, with explicit optional many-to-many links, preserving LAN independence and per-entry lifecycle. This is not approved or live-tested; canonical host IDs, HA flow constraints and storage ownership remain open.
