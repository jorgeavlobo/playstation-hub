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
| Physical-console/account identity + entry ownership | P0 | Open | [Cross-protocol review X-001](../architecture/cross-protocol-review-01-10.md) |
| Source authority / freshness / reconciliation | P0 | Open | Review X-002 and X-008 |
| Session ledger and uncertainty policy | P0 | Open | Review X-003 |
| Remote Play credential / crypto verification | P0 | Hardware unverified | Review X-004 |
| Sony PSN client/API entitlement | P0 for PSN | Blocked, optional LAN scope remains | Review X-005 |
| SQLite/credential storage and backups | P0 | Proposed, not approved | ADR-0003; Review X-006 |
| Multi-console DHCP onboarding | P0 | Dedicated flow needed, not implemented | Review X-007 |
| HA runtime, entities, frontend and release baseline | P1 | Open | Review X-012, X-013, X-016 |
| Exact supported/released capability set | P1 | Undefined pending gates | Review section 16 |

**Audit:** [Protocols 01–10 cross-protocol review](../architecture/cross-protocol-review-01-10.md) (22 findings; seven P0, ten P1 and five P2; this is documentation assessment, not tested code). The proposed ADR/spec backlog is not approved by inclusion here.

No official Home Assistant quality-scale tier is claimed for this custom integration.
