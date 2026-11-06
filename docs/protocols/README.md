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

**Credential lifecycle:** The proposed [ADR-0007](../decisions/ADR-0007-credentials-and-token-persistence.md) consolidates security and persistence requirements for PSN OAuth credentials and Remote Play pairing keys spanning Protocols 03–08. Actual secret storage, backup design and provider permission remain unresolved.

**Storage and recoverability:** Proposed [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md) evaluates HA Config Entries, Store, Recorder and an application-owned SQLite candidate for sessions and evidence. SQLite backup consistency, schema lifecycle, private credentials and HA OS restore have explicit verification gates; no database is approved or implemented.

**Home Assistant integration interface:** Proposed [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md) covers native config flows, multi-console discovery, device/entity registries, sensors, buttons, targeted actions, security, lifecycle and translations. Sidebar/WebSocket architecture follows in ADR-0010.

**Frontend and backend API:** Proposed [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md) defines the one-sidebar-panel delivery, Home Assistant WebSocket access, message versions, bounded data queries, state subscriptions, command permission checks, frontend translation and HACS packaging. No frontend/server endpoint is implemented yet.

**Discovery acceptance:** [SPEC-001](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md) specifies parser, DHCP Discovered, multi-console, identity and network reliability acceptance tests. No acceptance gate has passed; live firmware behavior remains unverified.

**Remote Play acceptance:** [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md) consolidates Protocols 03–07 byte contracts, crypto vectors, safe command handling and twelve unpassed release gates. No live interoperability is claimed.

**PSN permission and availability:** [SPEC-003](../specifications/SPEC-003-psn-authorization-and-availability.md) documents OAuth/NPSSO handoff, token lifecycle, privacy and rate budgets, 30 synthetic tests and 12 unpassed release gates. Sony client and endpoint permissions remain unresolved; LAN monitoring is independent.

**PSN DTO mapping:** [SPEC-004](../specifications/SPEC-004-psn-presence-game-metadata-dto-mapping.md) defines source-aware account, presence, current title, played/recent/library, trophy, catalog and artwork contracts with 36 synthetic tests and 12 unpassed gates. Sony API authorization remains a prerequisite.

**End-to-end testing and release:** [SPEC-005](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md) covers CI/CD, HACS/Hassfest, HA OS, real-console verification, security, persistence and twelve release gates. No tests have been executed.

**Security and privacy:** [SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md) covers the cross-protocol threat model, thirty tests and twelve unpassed security gates.

**Console and firmware compatibility:** [SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md) defines the PS5 candidate models, deferred PS4 families, firmware and network test matrix, and twelve unpassed compatibility gates.

**Initial implementation contracts:** [WP-00A](../architecture/WP-00A-home-assistant-baseline-and-lan-contracts.md) pins Home Assistant Core 2026.11.0 / Python >=3.14.2 as a research/test reference and defines the pure LAN discovery/status parser, identity candidate, observation ordering, fake transport and 20 pending tests. No implementation is authorized by the document.

## Pinned upstream repository audit — 2026-11-06

[Deep source-code comparison: playactor, PS5-MQTT, chiaki-ng, HA Core, psn-api, PSNAWP and alternatives](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md) is now the current upstream-specific supplement to Protocols 01–10. Key corrections: Chiaki maps `200`=READY, `620`=STANDBY, unknown codes to UNKNOWN; `playactor` previously classifies any non-620 code as AWAKE; chiaki recognizes optional `running-app-titleid` / `running-app-name` headers, potentially relevant for LAN-only title metadata; PS5-MQTT's PSN-to-device match is heuristic, and its sequential polling can break on a transitioning device; PS5-MQTT also documents multi-interface broadcast/listener pitfalls. No firmware test has confirmed optional LAN title headers on a real PS5. Chiaki-ng's current canonical repository is `chiaki-ng/chiaki-ng` (AGPL-3.0); the latest `playdirector` PyPI 0.4.2 API is a GPL-3.0-only redesign, not an equivalent of earlier 0.3.x/MIT examples.

This targeted source audit is justified as a newly identified capability under WP-00B, but does not open another numbered ADR/SPEC or reauthorize writing implementation code.

## Further deep source triangulation — 2026-11-06

[Second source-level protocol audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) extends the initial upstream survey with commit-pinned `ktnrg45/pyremoteplay`, `iharosi/ps5-remoteplay`, `iharosi/ps5-wake` and `leonanluppi/chiaki-km`, plus deeper PSNAWP/Emkraan/HA Core/psn-api runtime comparison. Key findings: `ps5-remoteplay` was ported from playactor and is **not** an independent protocol oracle; it inherits non-620 => AWAKE and can report standby success after a swallowed close timeout; playactor can truncate colon-bearing LAN title headers and retain CR in identity fields; Chiaki-KM actually consumes optional local app metadata for UI profile choice, without proving every real PS5 reports it; unchanged PS5-MQTT UI events cannot replace durable source heartbeats. Optional PSN should use per-account token refresh serialization and preserve multi-title presence rather than treat HA's first-title UI selection as physical console evidence. These are documentation additions to existing specs, not executable validation or new ADR/SPEC numbering. See also Architecture Guide v0.60.0.

## Runtime dependency sovereignty — maintainer requirement 2026-11-06

**Superseding architecture rule:** [First-party dependency policy](../architecture/first-party-dependency-sovereignty-policy.md) and [native stdlib/HA source audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md). References to playactor/Chiaki/PS5-MQTT/PSNAWP/pyremoteplay throughout Protocols 01–10 are **research-only**; none is an approved runtime library, bundled submodule, CLI command, dependency or source-copy template. The new PlayStation Hub authors every PlayStation protocol adapter itself with Python stdlib and supported native HA APIs, targeting zero extra runtime pip/npm requirements and no MQTT/add-on. Native HA network adapter/broadcast and HTTP session helpers are allowed platform services.

**Important exception:** Remote Play encrypted registration/control cannot be promised with stdlib-only AES (no general AES-CFB/CBC API); cryptography remains a gated capability pending an independently vetted secure primitive and explicit maintainer acceptance. Sony PSN source use likewise requires actual authorization. LAN-only monitoring and optional reported title metadata do **not** depend on those gates.

## Latest first-party LAN wire/temporal contract — 2026-11-06

[DDP wire protocol, source correlation and independent monitoring research](../research/lan-ddp-wire-and-temporal-correlation-audit-2026-11-06.md) now refines Protocols 01/02/03/10, ADR-0005/0021 and SPEC-001/021. Static source-observed SRCH messages have **no demonstrated request ID, nonce or timestamp echo**, so an in-process \`request_generation\` is only a callback/ordering aid and cannot prove a reply came from one exact scan. Python UDP \`sendto\` queues rather than confirms delivery. Chiaki's discovery service updates accepted host last-ping state for unchanged replies but emits visible callbacks only on changes. Thus own PlayStation Hub monitoring requires **accepted repeated source observations** even when HA entities do not change; duration remains bounded inference, not exact measured play. No PlayStation library, MQTT/add-on, code, firmware test or new numbered ADR/SPEC.

## Latest LAN game/title semantics (2026-11-06)

[Detailed app source/foreground research](../research/lan-running-app-identity-foreground-and-provider-boundary-2026-11-06.md) and [first-party title identity contract](../architecture/lan-running-app-evidence-and-title-identity-contract.md) refine Protocols 02/09/10, ADR-0005/0021, SPEC-004/021. Code path from Chiaki-ng response through Chiaki-KM UI/profile shows local \`running-app-name/titleid\` is a practical candidate. It is **not** Sony-confirmed foreground/human gameplay; Sony documentation expressly allows games/apps paused under Home. Missing app header is not proof of home/game closed; system/regional/PS4 backward-compatibility title IDs require namespaced preservation. PS5 on-console ELF focus payloads are out of scope; no extra PlayStation runtime libraries or game-state daemon. All descriptions remain source research, not firmware or code test results.
