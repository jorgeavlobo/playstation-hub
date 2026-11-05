# Compliance matrix

**Status:** Planning, no implementation claims — 2026-11-05.

| Requirement | Origin | Status | Evidence |
| --- | --- | --- | --- |
| One HACS integration | Project decision | Approved, unimplemented | Architecture guide |
| One multilingual sidebar panel | Project decision | Approved, unimplemented | Architecture guide |
| No required PS5-MQTT/Mosquitto | Project decision | Approved, unimplemented | Communication architecture |
| LAN discovery/status | Upstream reference | Research documented | Protocols 01–02 |
| Remote Play wake/pairing/standby | Upstream reference | Research documented | Protocols 03–07 |
| Optional PSN presence | Upstream reference | Research documented | Protocols 08–10 |
| Safe SQLite backup/restore | Architecture proposal | Not approved | Architecture guide |
| HACS and Hassfest validation | Official HA/HACS | Not implemented | Architecture guide |
| Gold/Platinum internal targets | Voluntary project policy | Not verified | Architecture guide |

## Cross-protocol architecture gate (2026-11-05)

| Gate | Priority | Status | Reference |
| --- | --- | --- | --- |
| Physical-console/account identity + entry ownership | P0 | ADR-0004 proposed, not approved; hardware identity unverified | [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md) |
| Source authority / freshness / reconciliation | P0 | ADR-0005 proposed, not approved; TTL and device behavior unverified | [ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md) |
| Session ledger and uncertainty policy | P0 | ADR-0006 proposed, not approved; gap thresholds unverified | [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md) |
| Remote Play credential / crypto verification | P0 | SPEC-002 documented; twelve gates unpassed | [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md) |
| Sony PSN client/API entitlement | P0 for PSN | Blocked, optional LAN scope remains | Review X-005 |
| SQLite/credential storage and backups | P0 | ADR-0007/0008 proposed, not approved; consistent HA backup unverified | [ADR-0007](../decisions/ADR-0007-credentials-and-token-persistence.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md) |
| Multi-console DHCP onboarding | P0 | SPEC-001 acceptance matrix documented; implementation and live validation pending | [SPEC-001](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md) |
| HA runtime, entities, frontend and release baseline | P1 | ADR-0009/0010 proposed; target HA baseline, APIs and tests open | [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md), [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md) |
| Exact supported/released capability set | P1 | Undefined pending gates | Review section 16 |

**Audit:** [Protocols 01–10 cross-protocol review](../architecture/cross-protocol-review-01-10.md) (22 findings; seven P0, ten P1 and five P2; this is documentation assessment, not tested code). The proposed ADR/spec backlog is not approved by inclusion here.

No official Home Assistant quality-scale tier is claimed for this custom integration.

## SPEC-005 release evidence checkpoint

[SPEC-005](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md) defines twelve release gates, separate LAN/Remote Play/PSN scopes, reproducible test evidence and CI/CD requirements. **Status: documented, no test evidence or release approval.** Sony PSN authorization remains blocked; HACS/Hassfest and HA OS backup/restore remain untested.

## SPEC-006 security checkpoint

[SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md) defines thirty threats and twelve security gates. **Status: research/proposed; no controls or tests verified.** Sony permission remains blocked and all common security release requirements are pending.

## SPEC-007 compatibility checkpoint

[SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md) documents model/firmware/network compatibility evidence requirements. All twelve compatibility gates remain NOT_TESTED, BLOCKED or NOT_APPROVED. Source-observed PS5/PS4 protocol constants do not prove support.

## Formal architecture review checkpoint

[Formal ADR-0004–0010 review](../architecture/formal-architecture-review-adr-0004-0010.md) records 18 consistency findings and implementation dependencies. All seven ADRs remain proposed pending explicit approval and relevant evidence. WP-00–WP-08 are recommendations, not authorized implementation. PSN permission and Remote Play wire gaps remain separately blocked.
