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

## WP-00 implementation readiness checkpoint

[WP-00](../architecture/WP-00-implementation-readiness-and-decision-closure.md) records pending HA baseline, canonical identity, observation/session contracts, storage, Remote Play, Sony authorization and API security. **Status: PROPOSED/NOT_READY; no ADR acceptance or executable validation.**

## Home Assistant 2026.11 / Marketplace source re-audit

[Official-source Bible re-audit](../research/official-source-reaudit-home-assistant-2026-11.md) records 18 findings and 32 official source references. Core 2026.11.0 with Python >=3.14.2 is a **source-verified research baseline**, not yet approved as the minimum supported version. Future code must account for DeviceInfo dataclasses, per-entry device ownership, flow `step_id`, modern config-entry errors, 2026.11 naming/entity lifecycle, scoped repairs, Marketplace packaging, `media_entertainment.gaming`, complete custom translation files and panel theme changes. The existence of official backup hooks is source-verified; SQLite snapshot/restore remains untested. All implementation/release gates remain unpassed.

## WP-00A technical baseline and initial LAN contracts

[WP-00A](../architecture/WP-00A-home-assistant-baseline-and-lan-contracts.md) fixes the source-reviewed **development reference** at Core `2026.11.0` / Python `>=3.14.2`; the proposed minimum supported Core version is not yet approved or tested. Exact source-tag behavior reviewed: DHCP generic fallback, DeviceInfo dataclass/registry, explicit flow `step_id`, entity ID change hooks, custom panel/WebSocket and Store flags. Twenty deterministic LAN cases are specified, with **zero tests executed**. WP-01 implementation remains NOT_READY pending maintainer approval and chosen toolchain.

## Source-derived legacy code review — documentation only

[Legacy code review and refactoring blueprint](../research/legacy-code-review-and-refactoring-blueprint-2026-11.md) documents 12 findings and 20 planned validation scenarios against five read-only `develop` backend files. No source code was edited and no tests were executed. A proven old transaction/checkpoint model may inform future modular design, but MQTT, Supervisor `/data`, one-player identity, fixed Lisbon timezone, a 30-second gap policy and synchronous sqlite3 must not be copied without explicit design and compatibility review.

## Legacy frontend availability checkpoint

[Frontend source inventory and UX research](../research/legacy-frontend-inventory-and-panel-ux-review-2026-11.md) records blocker UX-001: actual legacy Lovelace frontend code was not available at expected `develop/frontend` paths. The legacy README's claimed 80 local tests have not been independently verified. Native one-panel UX requirements can be documented, but a component-by-component code audit remains NOT_STARTED.

## Corrected legacy frontend source audit — UX-001 resolved

[Source-backed `develop` frontend audit](../research/legacy-frontend-source-audit-2026-11.md) verifies 21 frontend files and exactly 80 test declarations in ten test files, correcting the earlier mistaken “frontend unavailable” result. The initial source access blocker **UX-001 is RESOLVED**; the current automated test state remains **NOT_RUN**. The legacy card is one-console Lovelace over MQTT-via-HA-WebSocket; do not port its fixed entity IDs, source-derived power OFF assumptions, CSS/theme or browser-local calendar without redesign. The approved new UI remains one sidebar panel, with ADR-0010 implementation pending.

## Official Quality Scale / Marketplace re-audit — Batch 02

The [official-source batch 02](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md) records 22 findings and the [54-rule internal quality applicability matrix](internal-quality-scale-applicability.md) separates **voluntary Core Bronze/Silver/Gold/Platinum engineering standards** from **binding Marketplace installation and catalog checks**. Key new gates: HA-native DHCP discovery ownership, typed per-config-entry runtime data, coordinator-based cached entities, explicit PARALLEL_UPDATES, typed action errors, first-failure/first-recovery logs, allowlisted diagnostics, safe user-managed stale device removal, >95% per-Python-module voluntary coverage target, and Marketplace 100 MiB / 50,000-file artifact limit. All requirements are documented, **NOT_IMPLEMENTED/NOT_TESTED** as applicable; no official custom integration quality tier claimed.

## Multi-console runtime and coordinator official source audit (2026-11-05)

The [Core 2026.11 source audit](../research/ha-core-2026-11-multi-console-runtime-source-audit.md) and [SPEC-008](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md) document 46 tests and 12 unpassed MC approval gates. **Critical finding:** Ordinary DataUpdateCoordinator periodic polling ends when its final listener leaves. PlayStation Hub's multi-year history must therefore have an explicit per-console observation owner even with no enabled sensors or open sidebar. Prefer an entry-owned single-probe LanMonitor and push-only coordinator, subject to approval; do not implement a second polling coordinator simultaneously. Per-entry runtime/unload/initial sleeping-PS5 behavior, user disabled-polling, IP rediscovery and shared SQLite/panel lease remain untested. All related ADR statuses remain PROPOSED.


## Crash recovery and restore-provenance gate — 2026-11-06

| Requirement | Priority | Current status | Planned evidence |
| --- | --- | --- | --- |
| Linked SQLite C runtime patched against the 2026 WAL-reset corruption bug | P0 | BLOCKED_HA_OS, NOT_TESTED | [Recovery audit](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md) / [SPEC-010 CR-G01](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md) |
| Atomic observation + segment + commit cursor with stable idempotent receipt | P0 | PROPOSED, NOT_RUN | [SPEC-010 CR-TX01–CR-TX12](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md) |
| No inflated sessions across crash/restore or clock changes | P0 | PROPOSED, NOT_RUN | [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md) and SPEC-010 |
| Consistent HA OS backup archive plus explicit restore provenance | P0 | BLOCKED_HA_OS / RESTORE_POLICY_OPEN | [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md) / SPEC-010 |
| No destructive auto-snapshot promotion on ordinary restart | P0 | PROPOSED, NOT_RUN | SPEC-010 CR-BK12 |
| Archive-only panel and privacy-safe history retention after final Config Entry removal | P1 | OPEN_PRODUCT_DECISION | [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md) / SPEC-010 |
| Custom app data affected by Recorder-only backup exclusion | P1 | SOURCE_VERIFIED, HA_OS_NOT_TESTED | Supervisor pinned source [restore module](https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py) |

**No project implementation, tests, release checks or ADR approval passed.** The historical DOC registers remain for traceability.


## HA OS storage path, archive-only UI and backup-hook failure findings — 2026-11-06

| Requirement | Priority | Status | Evidence |
| --- | --- | --- | --- |
| App-specific SQLite path outside HACS source but inside selected backup scope | P0 | PROPOSED, NOT_TESTED | [Storage audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md) |
| HA config, Recorder, share/media and cache inclusion clearly separated | P0 | SOURCE_RESEARCHED, HA_OS_NOT_TESTED | Core core_config.py, pinned Supervisor restore/module, official HA backup docs |
| No invisible long-held pre-backup freeze on another platform failure | P0 | SOURCE_CONFIRMED_RISK, MITIGATION_OPEN | Source audit §15, [SPEC-011 ST-BK17–20](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) |
| Immutable backup snapshot with self-derived durable cursor and crash-safe manifest publication | P0 | PROPOSED, NOT_RUN | ADR-0011 / SPEC-011 |
| Valid live DB never auto-replaced with older staged snapshot | P0 | PROPOSED, NOT_RUN | SPEC-010 and SPEC-011 |
| Ledger/config identity divergence after selective old-config restore | P0 | PROPOSED, NOT_RUN | SPEC-011 ST-REC01, ST-BK13 |
| One logical user-confirmed Hub/Archive Config Entry for no-console panel | P1 | ADR-0011 PROPOSED; owner approval pending | SPEC-011 ST-HUB01–16 |
| User-owned retention, export, private backups and explicit purge | P1 | PROPOSED, NOT_RUN | ADR-0008/0010/0011 |

**All SPEC-011 64 case definitions are NOT_RUN, all 16 gates OPEN; none are formal custom-integration Gold/Platinum certification.**
