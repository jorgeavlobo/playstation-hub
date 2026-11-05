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

## Reconciliation architecture (proposed ADR-0005)

[ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md) specifies independent LAN, Remote Play and PSN source snapshots and a pure fact-aware state reducer. PSN online/offline does not assert physical power, successful network send does not assert completed power transitions, and stale observations remain last-known history rather than current state. Source health, reachability, freshness and fact values are independent; the session ledger and Home Assistant projections consume the reconciled stream but have separate contracts still under design.

## Session accounting and reporting (proposed ADR-0006)

[ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md) specifies a separate event/checkpoint/session ledger consuming accepted ADR-0005 observations. It proposes bounded evidence-based console duration, explicit unknown gaps, distinct account/game attribution and independent provider aggregate playtime, with half-open UTC intervals and configurable local calendar reporting. The persistence choice, gap thresholds, exact confidence policy and statistics API remain pending approval and validation; no actual duration data has been acquired in the new project.

## Credential lifecycle proposal (ADR-0007)

[ADR-0007](../decisions/ADR-0007-credentials-and-token-persistence.md) specifies separate per-account Sony NPSSO/OAuth token ownership and per-console Remote Play pairing keys, with no credentials exposed to frontend, entities or diagnostics. It proposes synchronized token refresh, versioned durable writes and safe reauth/unpair/unlink. Exact HA secure storage and backup policy belong to pending ADR-0008. PSN endpoint/client authorization is not yet established.

## Storage architecture (proposed ADR-0008)

[ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md) recommends a **hybrid** persistence architecture: native Config Entries/Options for devices/accounts; Home Assistant Store for bounded JSON settings; independent credential store after security review; application-owned SQLite **candidate** for multi-year event/session evidence; Recorder only for HA native metrics and long-term statistics. The historical database and cache must be outside HACS-managed code. SQLite transactions, WAL backup snapshot strategy, HA OS backup inclusion and recovery remain **unvalidated**. The original provisional ADR-0003 is not yet approved.

## Native Home Assistant integration (proposed ADR-0009)

[ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md) specifies candidate `playstation_hub` config flows, DHCP discovery, physical-console and optional PSN service devices, semantic entities, explicit targeted wake/standby actions, coordinator lifecycle, translations and diagnostics. Physical power is not assumed binary and PSN offline does not imply a console is off. No native integration code or Home Assistant OS tests have yet been run.

## Sidebar panel and backend API (proposed ADR-0010)

[ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md) specifies one HACS-shipped Home Assistant sidebar Web Component, static frontend asset registration and a versioned authorized WebSocket API for source state, commands, games and bounded history. Frontend modules never access Sony credentials, transport sockets or SQLite. Shared snapshot/delta subscriptions prevent per-widget provider polling; backend ACL is required even when panel navigation is admin-only. The exact Home Assistant version compatibility, panel registration lifecycle, API schemas, i18n and mobile behavior require tests.

## Official-source baseline refresh — 2026.11 (research only)

[Current official-source audit](../research/official-source-reaudit-home-assistant-2026-11.md): Home Assistant Core 2026.11.0/Python >=3.14.2 is a verified API research target, subject to minimum-version approval. Home Assistant now includes Marketplace, and the custom integration should use current DeviceInfo dataclasses, single-config-entry device ownership, modern flows/repairs, contextual entity naming and 2026.11 sidebar theme CSS. The proposal remains one HACS/Marketplace integration with one sidebar, native LAN transport and optional, separately gated Remote Play and PSN. No implementation compatibility is claimed.

## WP-00A — Source-pinned HA baseline and LAN foundations

[WP-00A](WP-00A-home-assistant-baseline-and-lan-contracts.md) records Home Assistant Core 2026.11.0/Python >=3.14.2 as an official source-verified development reference, with proposed (not approved) minimum HA support. The first LAN models, fake UDP transport, identity candidates, conservative power observations and 20 synthetic tests are specified, not implemented. The integration's one-sidebar/no-MQTT direction remains unchanged.

## Legacy code reuse boundary — research review (2026-11-05)

The [legacy backend review](../research/legacy-code-review-and-refactoring-blueprint-2026-11.md) separates reusable atomic observation/checkpoint/UTC interval accounting principles from unsupported legacy MQTT, Supervisor App and one-player design. Future native transport, entity and persistence modules require approved contracts, async-safe storage, owner-scoped identity and bounded queries. No implementation code was changed.

## Legacy frontend evidence boundary

[Frontend source availability and proposed panel UX](../research/legacy-frontend-inventory-and-panel-ux-review-2026-11.md) distinguishes the documented new sidebar design from uninspected legacy Lovelace components. The README mentions a private frontend snapshot, but source was not found at expected `develop/frontend` paths. No old UI behavior is considered verified by this research.

## Corrected legacy frontend source inventory — 2026-11-05

The earlier missing-frontend statement was a **tool misuse**, not an absent branch tree. The [authoritative `develop` frontend source audit](../research/legacy-frontend-source-audit-2026-11.md) verifies 21 files and 80 counted test declarations (unexecuted), including the Lovelace card, game library, SVG history chart, live/daily/monthly/36-month history clients, navigation, formatters and styles. The design can reuse safe text handling, request cancellation/correlation, generation filtering and activity navigation, but replaces MQTT and fixed single-console assumptions with an authorized multi-console sidebar API. `develop` remains unmodified.
