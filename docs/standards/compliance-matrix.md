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


## User-approved Hub architecture and immutable snapshot gates — 2026-11-06

| Area | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| Product decision | One user-confirmed logical Hub/Archive entry, separate console/account entries, one panel/controller | ACCEPTED_DESIGN, NOT_IMPLEMENTED | [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06) |
| Persistence | Private app-owned configuration-root direction outside HACS source | ACCEPTED_DIRECTION, FINAL_PATH_CONDITIONAL | ADR-0011, ADR-0008 |
| Snapshot correctness | Bounded SQLite Online Backup API copy; destination closure; own cursor; integrity/FK/schema | RESEARCH_PREFERRED, NOT_RUN | [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md), [source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md) |
| Publication | Immutable snapshot+manifest generation, crash-safe marker, safe retention | PROPOSED, NOT_RUN | SPEC-012 |
| HA archive | Core/Supervisor documented pre/post do not expose custom app-owned per-file exclude; live DB/WAL also may be archived | SOURCE_INSPECTED, HA_OS_NOT_TESTED | Pinned Core backup manager/const, Supervisor module |
| Backup liveness | Other platform prehook failure cannot strand app SQLite writer; post hook best-effort | P0, NOT_RUN | SPEC-012 SN-ARC06–08 |
| Restore | No blind selection of potentially copied raw DB or stale snapshot; admin intent/lineage | P0, NOT_APPROVED, NOT_RUN | ADR-0012, SPEC-012 |
| Privacy | Private snapshots, no generic token/export leakage | CONDITIONAL, NOT_RUN | ADR-0007/0008, SPEC-012 |

**Test status:** SPEC-012 has 64 NOT_RUN cases, 16 OPEN gates. No code or acceptance test has been run.


## Restore authority and cross-scope identity safeguards — 2026-11-06

| Evidence gate | Priority | Status | Reference |
| --- | --- | --- | --- |
| One default private ledger direction, no required extra OS mount/SQL server | P0 | ACCEPTED_DIRECTION; final path conditional | [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md) |
| Pinned Core OS bind mounts for config/share/media | P1 | PINNED_SOURCE_VERIFIED, runtime NOT_TESTED | [Research](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md) |
| Recommended automatic backup configuration vs share/media | P0 | OFFICIAL_DOC_VERIFIED, actual backup NOT_TESTED | https://www.home-assistant.io/common-tasks/general/backups/ |
| App backup preparation vs custom source archive exclusion | P0 | NO_PUBLIC_CONTRACT_FOUND_IN_PINNED_API | Core/Supervisor backup source audit, ADR-0013 |
| Config-only restore with newer share ledger, and inverse share-only restore | P0 | PROPOSED, NOT_RUN | [SPEC-013 RA-REST02/03](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md) |
| Equal ledger UUID/cursor but differing event lineage | P0 | PROPOSED, NOT_RUN | SPEC-013 RA-ID01/02 |
| No silent raw DB/WAL or largest-cursor automatic promotion | P0 | PROPOSED, NOT_RUN | [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md) |
| Privileged admin restoration with old file preservation and explicit UNKNOWN gaps | P0 | PROPOSED, NOT_RUN | SPEC-013 RA-UX01–16 |
| Same physical console account identity validated across restored HA Config Entries | P0 | BLOCKED_HARDWARE + NOT_RUN | ADR-0004, SPEC-013 RA-ID09–16 |

**SPEC-013:** 64 case IDs enumerated, 16 OPEN gates. The product-level Hub/Archive architecture is accepted; this operational restore strategy is not approved or implemented.


## Administrator recovery, restore progress and upstream-interface requirements — 2026-11-06

| Gate | Priority | Status | Source |
| --- | --- | --- | --- |
| Single authenticated native administrator recovery UI, no extra service/MQTT | P0 | PROPOSED / NOT_IMPLEMENTED | [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) |
| Hub-only RECOVERY_HOLD when ledger is invalid, with no empty DB creation | P0 | NOT_RUN | [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md), AR-UX02 |
| Global ledger Repairs issue independent of one console Config Entry | P0 | SOURCE_API_VERIFIED, APP_NOT_RUN | Core 2026.11 issue_registry / HA Repairs docs |
| Admin require_admin / expiry/revocation and preview-confirm revalidation | P0 | SOURCE_API_VERIFIED, APP_NOT_RUN | Core websocket_api/decorators.py; SPEC-014 |
| Disconnect cleanup vs durable recovery job ownership | P0 | SOURCE_API_VERIFIED, APP_NOT_RUN | Core websocket_api/connection.py and decorators.py |
| Real Supervisor restore job progress and backup manager event subscription | P0 | PINNED_SOURCE_VERIFIED, APP_HA_OS_NOT_RUN | Core hassio/backup.py, BackupManager, official test; Supervisor docker/homeassistant.py |
| Universal custom restore authority with backup source/SQLite digest | P0 | NOT_ESTABLISHED | [Source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md) |
| Custom app-owned file exclusion from Core/Supervisor config backup via pre/post | P0 | NO_SUPPORTED_CONTRACT_IN_REVIEWED_API | HA backup developer docs and pinned filters |
| Two unfiled upstream extensions, scoped artifacts and durable restore intent | P1 | PROPOSED_RESEARCH, NO_ISSUE_FILED | ADR-0014 §6 |
| Recovery preview/confirm with one job, old bytes preserved, no fork merge | P0 | PROPOSED / NOT_RUN | SPEC-014 72 cases and 18 gates |
| Privacy-safe diagnostics, hostile archive bounds, physical/PSN ACL | P0 | PROPOSED / NOT_RUN | SPEC-006, SPEC-014 |

All 72 SPEC-014 tests remain NOT_RUN, all 18 gates OPEN; the accepted ADR-0011 product architecture does not automatically accept the operational recovery algorithm. No formal official HA Quality Scale certification is claimed.


## Crash-atomic recovery journal and generation promotion compliance — 2026-11-06

| Gate | Priority | Evidence status | Reference |
| --- | --- | --- | --- |
| Never rename/delete an active SQLite DB or manually detach its hot WAL/journal | P0 | OFFICIAL_SQLITE_SOURCE_VERIFIED / NOT_TESTED | [Crash source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md) |
| Distinct SQLite working generations and one active pointer | P0 | DESIGN_PROPOSAL / NOT_RUN | [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md), [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) |
| Application recovery journal distinct from SQLite native rollback/WAL | P0 | PROPOSED / NOT_RUN | SPEC-015 JR-I09 and crash matrix |
| Positive writer/reader/executor closure before any active source selection | P0 | PROPOSED / NOT_RUN | SPEC-015 JR-SQL01–10 |
| One-path atomic os.replace; durable file AND parent-directory sync | P0 | PYTHON/POSIX SOURCE_VERIFIED; HA_OS_NOT_RUN | Official Python os.replace, Linux fsync manual |
| Post-crash pointer/journal mismatch resolved without blind rollback/replay | P0 | NOT_RUN | SPEC-015 JR-PH13–19, JR-BOOT05/06 |
| HA Config Entry / physical PlayStation / PSN mappings revalidated separately | P0 | NOT_RUN / HARDWARE_BLOCKED | ADR-0004, ADR-0015 |
| GC never removes selected current / last known good / in-archive source | P0 | NOT_RUN | SPEC-015 JR-OS07–10 |
| No fabricated historical intervals after old backup or failed commit | P0 | NOT_RUN | ADR-0006 / SPEC-015 JR-BOOT17 |
| Full HA config restore can rewind entire pointer/journal/generation set | P0 | PINNED_SUPERVISOR_SOURCE_VERIFIED; HA_OS_NOT_RUN | ADR-0013/0015, SPEC-015 JR-OS01 |
| Source shutdown race and storage filesystem crash matrix | P0 | NOT_RUN | SPEC-015 80 tests, 20 gates |

**Status:** ADR-0015 is a technical PROPOSAL; ADR-0011 product architecture remains ACCEPTED. No tests or real integration code exist and no formal Home Assistant quality certification is claimed.


## Recovery Hold bootstrap and SQLite worker lifecycle compliance — 2026-11-06

| Requirement | Priority | Source/implementation state | Evidence |
| --- | --- | --- | --- |
| Accepted Hub/Archive control plane can load with internal RECOVERY_HOLD | P0 | PROPOSED, HA_OS_NOT_RUN | [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md), [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md) |
| Distinguish HA LOADED/SETUP_RETRY/SETUP_ERROR/MIGRATION_ERROR from internal history health | P0 | CORE_PINNED, APP_NOT_RUN | Home Assistant 2026.11 Config Entries + setup failures |
| Typed runtime_data before awaited platform forwarding | P0 | SOURCE_VERIFIED, NOT_TESTED | Core config_entries.py, contributor config-entries guide |
| One global controller DENY_WRITE before concurrent Hub/console/account entries | P0 | PROPOSED, NOT_RUN | SPEC-016 BH-I01/02/08/09 |
| Optional SOURCE_ONLY_UNSAVED no persisted history writes | P0 | PROPOSED, MAINTAINER_POLICY_OPEN | ADR-0016 §7 |
| Running ThreadPoolExecutor job cannot be cancelled through Future.cancel/cancel_futures | P0 | PYTHON_SOURCE_VERIFIED, NO_APP_TEST | Python 3.14 concurrent.futures |
| sqlite3.interrupt abort is not proof of closed connection | P0 | PYTHON_SOURCE_VERIFIED, NO_APP_TEST | Python 3.14 sqlite3 reference |
| aiosqlite v0.21.0 queued operation may run after await cancellation | P0 | THIRD_PARTY_SOURCE_VERIFIED, NOT_SELECTED | pinned aiosqlite/core.py, SPEC-016 |
| SQLite connection close, queue drain and worker terminal before generation switch | P0 | PROPOSED, NOT_RUN | SPEC-016 BH-WORK01–20, ADR-0015 |
| Hub global Repairs through physical console removal | P1 | CORE_API_VERIFIED, APP_NOT_RUN | Core issue_registry, SPEC-016 BH-BOOT14 |
| Old-source WAL/journal preservation with FAILED_UNSAFE_TO_REOPEN | P0 | SQLITE_SOURCE_VERIFIED, NOT_TESTED | ADR-0015/0016 |
| HA OS/Container and physical console multi-entry boot tests | P0 | BLOCKED_RUNTIME/HARDWARE | SPEC-016 80 cases and 20 gates |

No formal Home Assistant quality tier is claimed. ADR-0011 accepted only product architecture; ADR-0016 remains a technical proposal.


## Degraded operation capability matrix and SQLite 0.22.x terminal-proof gates — 2026-11-06

| Required safety boundary | Priority | Current evidence/status | Reference |
| --- | --- | --- | --- |
| Backend operation guard independent of HA Entity.available and UI visibility | P0 | CORE_SOURCE_VERIFIED, APP_NOT_RUN | [Source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) |
| One policy shared by Home Assistant service/automation, WS, background probe and device control | P0 | PROPOSED, NOT_RUN | [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) |
| Distinguish current source reading from durable historical writing | P0 | PROPOSED, NOT_RUN | ADR-0006, SPEC-017 |
| Identity conflict always denies power/Remote Play, PSN re-link and attribution | P0 | PROPOSED, HARDWARE_NOT_VERIFIED | ADR-0004, SPEC-017 |
| RECOVERY_HOLD console source-only status and no backfill | P0 | CONDITIONAL_PRODUCT_POLICY, NOT_RUN | SPEC-017 CAP-MODE04/18/19 |
| RECOVERY_HOLD power/Remote Play defaults DENY | P0 | CONSERVATIVE_PROPOSAL, PENDING_OWNER_APPROVAL | ADR-0017 |
| PSN account read/refresh under history Hold | P1 | CONDITIONAL_ACCOUNT_POLICY | ADR-0017 |
| Verified immutable snapshot read while live worker fenced | P1 | PROPOSED, NOT_RUN | SPEC-017 CAP-MODE12 |
| aiosqlite 0.21 Thread inheritance vs 0.22.0/0.22.1 private worker | P0 | THIRD_PARTY_PINNED_SOURCE_VERIFIED | v0.21.0, v0.22.0, v0.22.1 aiosqlite/core.py |
| aiosqlite 0.22.1 stop Future callback vs actual thread terminal | P0 | SOURCE_VERIFIED, WORKER_NOT_TESTED | Source audit §5, SPEC-017 CAP-WORK03/06 |
| Stdlib ThreadPoolExecutor shutdown(wait=True) off event loop | P0 | PYTHON_SOURCE_VERIFIED, APP_NOT_RUN | Python 3.14 concurrent.futures |
| No generation cutover before all connections and worker terminal proved | P0 | PROPOSED, NOT_RUN | ADR-0015/0017, SPEC-017 |
| HA OS packaging, SQLite C version, power-cut/multi-console tests | P0 | BLOCKED_HA_OS | SPEC-017 80 NOT_RUN / 20 OPEN |

**No code and no passed tests.** ADR-0011 product direction remains ACCEPTED; operational degraded permissions and worker selection remain proposed.


## First-boot SQLite history creation and lost-ledger safety gates — 2026-11-06

| Requirement | Priority | Evidence/status | Source |
| --- | --- | --- | --- |
| Existing history opens with SQLite URI mode=rw/ro, never implicit create | P0 | SQLITE_SOURCE_VERIFIED, APP_NOT_TESTED | [First-boot audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) |
| Verify effective SQLite read/write mode after READWRITE fallback | P0 | SQLITE_SOURCE_VERIFIED, APP_NOT_TESTED | sqlite3_open_v2/sqlite3_db_readonly |
| Missing/corrupt/inaccessible/restored ledger classified without empty reset | P0 | PROPOSED, NOT_RUN | [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md) |
| Hub Config Flow creation distinct from user-confirmed history genesis | P0 | PROPOSED_PRODUCT_DETAIL, NOT_RUN | HA Config Flow docs, ADR-0018 |
| Hub unique ID duplicate abort; manifest still supports multiple console/account entries | P0 | CORE_API_VERIFIED, APP_NOT_RUN | HA Config Flow, Config Entries, SPEC-018 FB-FLOW01–07 |
| Durable CREATE_INTENT before exclusive SQLite staging | P0 | PROPOSED, NOT_RUN | SPEC-018 FB-CREATE01–20 |
| Schema genesis, close, integrity and FK validation before pointer | P0 | PROPOSED, NOT_RUN | ADR-0015/0018, SPEC-018 |
| Concurrent admin Create/Import requests serialized and idempotent | P0 | PROPOSED, NOT_RUN | SPEC-018 FB-FLOW08–11 |
| Restored-old Hub/retained history does not silently reinitialize | P0 | PROPOSED, NOT_RUN | SPEC-018 FB-CLASS03–16 |
| Permission/mount/symlink/IO failures not conflated with absence | P0 | PYTHON_SOURCE_VERIFIED, APP_NOT_RUN | Python os, SPEC-018 |
| No true "never had history" proof from empty local directory | P0 | LOGICAL_LIMITATION, UX_NOT_APPROVED | ADR-0018, first-boot source audit |
| Full HA OS restore, Container paths and multi-console boot tests | P0 | BLOCKED_HA_OS | SPEC-018 80 tests/20 gates |

**No implementation, no tests, no first-ledger creation and no formal Home Assistant Quality Scale certification.** ADR-0011 accepted the product structure; ADR-0018 is technical PROPOSED.


## Legacy historical data migration and MQTT retirement compliance gates — 2026-11-06

| Requirement | Priority | State | Evidence |
| --- | --- | --- | --- |
| Read-only audit of develop App v0.5.0 / SQLite v3 structure | P0 | SOURCE_REVIEWED, USER_DB_NOT_INSPECTED | [Legacy audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md) |
| Coherent WAL-safe export of actual installed App /data | P0 | NOT_RUN / USER_CONSENT_REQUIRED | [SPEC-019 LM-SRC01–20](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md) |
| Never instantiate create/migrate-capable legacy Database on source | P0 | SOURCE_RISK_VERIFIED, IMPORT_NOT_RUN | develop/backend/app/database.py |
| No physical PS5 UUID in legacy source historical sessions | P0 | SOURCE_CONFIRMED | develop/backend/app/database.py schema v3 |
| Default import LEGACY_UNATTRIBUTED and no PSN credential graft | P0 | ADR-0019 PROPOSED, NOT_RUN | [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) |
| Preserve 30-second runtime continuity, checkpoint bounded end and Lisbon DST | P0 | SOURCE_REVIEWED, NOT_TESTED | develop/main.py, session_tracker.py, usage_statistics.py |
| Namespaced idempotent import batches and active-generation rollback safety | P0 | PROPOSED, NOT_RUN | SPEC-019 LM-IMP01–20, ADR-0015 |
| 36-month UI history index is not retention cutoff | P1 | SOURCE_REVIEWED, REAL_DB_UNKNOWN | develop/ps5_history_index.py |
| Exact ten old synthetic monitor MQTT Discovery identities | P0 | SOURCE_REVIEWED, USER_REGISTRY_UNKNOWN | develop/mqtt_publisher.py |
| Targeted old monitor discovery cleanup independent of PS5-MQTT power/activity | P0 | OWNER_APPROVAL_PENDING, NOT_RUN | Official HA MQTT docs, SPEC-019 LM-CUT01–20 |
| Old Lovelace references and user automations mapped before retirement | P0 | NOT_RUN / HA_OS_BLOCKED | develop/frontend/ps5-dashboard-card.js |
| Real installed App backup/old SQLite data retained after cutover | P0 | UNKNOWN, NO_USER_DATA_READ | SPEC-019 LM-G01/02/19/20 |

**SPEC-019:** 80 named NOT_RUN cases, 20 OPEN gates, no actual user database or entity registry inspected. ADR-0011 product architecture remains ACCEPTED; ADR-0019 import policy remains PROPOSED. No formal HA quality certification or migration success claim.


## Greenfield scope reset: no deployed legacy application or data — 2026-11-06

**Maintainer-confirmed fact:** The old develop prototype was never deployed and all legacy SQLite records were fabricated for tests. This is a completely new PlayStation Hub. Any legacy data import/DTO mapping, v1-v3 App schema compatibility, prior PS5-MQTT entity cleanup, legacy hardware re-attribution, historical backup extraction, or live App cutover is CLOSED_NOT_APPLICABLE, not a blocker. [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) is SUPERSEDED; [SPEC-019](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md)'s 80 test cases and 20 gates are RETIRED. [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md)'s specifically legacy-only FB-CLASS13, FB-OS18 and FB-G14 are also NOT_APPLICABLE.

Keep new-app first-time ledger genesis, versioned forward migrations AFTER actual real records exist, new-app backups/restores/corruption recovery, independent console/PSN identity and admin controls. No legacy data or MQTT broker is to be imported/cleaned up. Historical source-code analyses remain technical reference, not operational deliverables. No tests or source code executed.


## Greenfield SQLite v1 identity/evidence/time integrity compliance — 2026-11-06

| P0/P1 gate | Priority | Evidence and state | Source |
| --- | --- | --- | --- |
| No legacy App data/schema migration; old develop rows fictional | P0 | MAINTAINER_CONFIRMED_GREENFIELD | [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md) |
| One application-owned ledger with 12 candidate normalized core tables | P0 | PROPOSED, NO_SQL_DDL | [Research](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md) / [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md) |
| Console, PSN account, game title and Hub/HA IDs in distinct namespaces | P0 | PROPOSED, HARDWARE_NOT_VERIFIED | ADR-0004 and SPEC-020 |
| SQLite foreign_keys=ON per writer/reader/backup connection | P0 | SQLITE_SOURCE_VERIFIED, APP_NOT_RUN | SQLite foreignkeys.html |
| STRICT table type enforcement requires SQLite >=3.37 | P0 | SQLITE_SOURCE_VERIFIED, LINKED_VERSION_OPEN | SQLite stricttables.html |
| NOT NULL/UNIQUE/CHECK including NULL and open-exclusive partial indexes | P0 | SQLITE_SOURCE_VERIFIED, APP_NOT_RUN | SQLite create table, create index and partialindex |
| Atomic accepted evidence, event/segment/gap/checkpoint/ledger cursor | P0 | PROPOSED, NOT_RUN | ADR-0006/0020, SPEC-020 |
| Idempotent observation UUID and ambiguous COMMIT receipt | P0 | PROPOSED, NOT_RUN | SPEC-020 GS-TX06/07/11 |
| Half-open UTC microseconds and local DST/leap calendar reports | P0 | PROPOSED, NOT_RUN | SPEC-020 GS-RP01–08 |
| Missing evidence UNKNOWN, no inferred OFF or gameplay | P0 | PROPOSED, NOT_RUN | ADR-0006, SPEC-020 |
| Provider lifetime/PSN entitlement not part of local session total | P0 | PROPOSED, PSN_AUTH_OPEN | Protocol 10, SPEC-020 |
| Game localized metadata/cover never changes durable title identity | P1 | PROPOSED, NOT_RUN | Protocol 10, ADR-0020 |
| No Sony credentials or raw private game history in diagnostics | P0 | SECURITY_DESIGN, NOT_RUN | ADR-0007, ADR-0020 |
| No history deletion on console Config Entry removal/unlink | P0 | PROPOSED, NOT_RUN | ADR-0004/0008/0020 |
| 36-month synthetic index/read/backup/retention benchmark | P0 | NOT_RUN | SPEC-020 GS-OS17–21 |
| New v1 genesis and later NEW-app-only versioned migrations | P0 | PROPOSED, NOT_RUN | ADR-0018/0020, SPEC-020 |

**Status:** SPEC-020 defines 96 NOT_RUN acceptance scenarios and 24 OPEN gates. This does not close earlier ADR-0004/0006/0008, SQLite linked-version/WAL, source/API authorization or HA OS release gates. No executable SQLite model or HA Quality Scale certification.

## First-party implementation / no additional runtime-package compliance — 2026-11-06

**New explicit maintainer requirement accepted:** [Dependency sovereignty policy](../architecture/first-party-dependency-sovereignty-policy.md), with [source-backed technical feasibility audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md) and Architecture Guide v0.61.0. Previous proposals to import or shell-execute any PlayStation package are superseded.

| Requirement | Authority/status | Future evidence |
| --- | --- | --- |
| 100% own PlayStation-specific protocol/data logic | ACCEPTED REQUIREMENT / NOT_IMPLEMENTED | Source code/test and provenance review |
| No PlayStation third-party runtime libraries (playactor/Chiaki/PSNAWP/etc.) | ACCEPTED REQUIREMENT / NOT_TESTED | Static import and vendored/binary scan |
| No additional pip/npm runtime requirements | ACCEPTED TARGET / NOT_TESTED | Manifest \`requirements\` empty + hassfest + dependency audit |
| Use Python standard library and supported HA public helpers | ACCEPTED TARGET / NOT_TESTED | Import review; HA 2026.11 native network/helper tests |
| Native HA network broadcast and per-interface source/target policy | SOURCE-CONFIRMED API / NOT_TESTED ON HA OS | network.async_get_adapters and async_get_ipv4_broadcast_addresses; allowlisted broadcast |
| No Node, CLI subprocess, MQTT broker, App or extra service | ACCEPTED REQUIREMENT / NOT_IMPLEMENTED | Release/install/runtime/CI checks |
| Plain owned JavaScript sidebar without frontend runtime framework | ACCEPTED TARGET / NOT_IMPLEMENTED | Bundle/manifest/asset scan and HA browser/mobile test |
| AES not self-implemented; Remote Play encrypted control gated | REQUIRED SECURITY CONSTRAINT / BLOCKED_CRYPTO_BACKEND | Only explicit trusted backend choice and interop tests unlock |
| Sony PSN access is optional and authorization-gated, no SDK | REQUIRED PRIVACY/AUTH CONSTRAINT / BLOCKED_PROVIDER_AUTHORIZATION | Authorized app credentials, rate/error handling, access tests |

Native HA functions may use transitive platform packages. This is not a claim of literally zero third-party code inside Home Assistant; it is **zero extra runtime installations plus independently owned PlayStation behavior**. All tests NOT_RUN and no dependency/code created by documentation alone.

## PS5 Remote Play cryptographic source-compatibility guard — 2026-11-07

**Source-audit reference:** [PS5 Remote Play derivation/version, rights and safety report](../research/ps5-remote-play-crypto-derivation-versions-and-security-source-audit-2026-11-07.md), Guide v0.66.0. The PlayStation-specific implementation must be ours, with no imported PlayStation client, copied AGPL/GPL tables, unmanaged crypto or new pip runtime dependency. A direct import of HA-preinstalled PyCA still needs **explicit maintainer approval**.

| Requirement | Status / release evidence |
| --- | --- |
| PS5 AES-128-CFB128 (not CFB8/CBC) plus IV HMAC SHA256 full 32-byte digest truncated to 16-byte IV | SOURCE-VERIFIED / NOT_IMPLEMENTED; byte/crypto test required |
| Pairing PIN, 480-byte preface, PS5-specific lookup key tables and lawful reuse rights | SOURCE-VERIFIED PARTIAL / RIGHTS_UNRESOLVED |
| Outbound/inbound per-encrypted-payload counter correctness and zero-payload frame behavior | SOURCE-VERIFIED / TESTS_NOT_RUN |
| RP-Version 1.0 does not represent PS5 firmware version | SOURCE-VERIFIED / firmware matrix NOT_RUN |
| Modern PS5 independent known-answer vectors and real device handshake | BLOCKED_PENDING_APPROVAL_AND_DEVICE |
| Alternative Mbed TLS SHA256 HMAC output sizing | UPSTREAM_STATIC_CONCERN / NOT_COMPILED_OR_EXPLOITED; do not copy |
| HA-preinstalled cryptography PyCA AES primitive exception | UNAPPROVED; must not import before maintainer choice |
| Sony account provisioning and protocol table provenance | BLOCKED_PROVIDER_AND_RIGHTS_REVIEW |

`CRY-01..20` are descriptive future test traces inside existing SPEC-002, **not executed** or a new numbered SPEC. LAN status/title/archiving unaffected.

## Exact PS5 cryptographic table provenance and independent-oracle compliance — 2026-11-07

[Source/rights analysis](../research/ps5-remote-play-lookup-table-provenance-rights-and-independent-oracles-2026-11-07.md) gives a reproducible no-byte-copy finding: Chiaki, Playactor and the Python port carry identical **8192 PS5 lookup bytes**, and historical/authored provenance places Chiaki 2020 → Playactor 2021 (explicit Chiaki credit) → Python 2026 (explicit Playactor generation). This is NOT multiple independent device tests and not an automatic license/permission to redistribute constants.

| Gate | Status | Future evidence before release |
| --- | --- | --- |
| ORIGIN-01 all 8192 bytes full-array equivalence | SOURCE_CONFIRMED | No raw binary keys copied; revisions logged |
| ORIGIN-02 temporal and attribution chain | SOURCE_CONFIRMED | Historical Chiaki/Playactor/Python commits and PR #16 |
| ORIGIN-03 lawful status/rights of numeric table reuse | OPEN | Expert review of source expression/data rights, license notices, Sony terms; Portuguese/EU interoperability limits |
| ORIGIN-05 preinstalled PyCA AES library exception | NOT APPROVED | Explicit user decision; zero new pip requirement does not mean no third-party import |
| ORIGIN-06 public crypto standards tests | NOT_RUN | RFC4231 HMAC plus NIST SP800-38A CFB math, labelled non-Sony |
| ORIGIN-07 own original fake console | NOT_RUN | Byte framing/counter/HTTP tests authored from scratch; no copied fixtures |
| ORIGIN-08 authenticated retail PS5 interop | BLOCKED/NOT_RUN | Legitimate account/console, safety permissions and approved firmware protocol testing |
| ORIGIN-09 no unauthorized copied tables/SDKs | NOT_RUN release check | Source/SBOM/fixture/license scan, no PlayStation runtime dependency |

Conservative policy stays `NO_TABLE_COPY` until explicit lawful provenance and maintainer approval; AES backend, Sony account identity and real device tests independently gate Remote Play. Passive LAN unaffected. No new numbered ADR/SPEC and no shipped source code.

## Sony Account ID self-provisioning and exact 64-bit handling — 2026-11-07

[Source/official Sony account identity audit](../research/first-party-psn-account-id-provisioning-and-pairing-trust-audit-2026-11-07.md) and [proposed provisioning contract](../architecture/first-party-psn-account-identity-and-pairing-provisioning-contract.md) define test and privacy gates without any PlayStation library or new OAuth dependency.

| Gate | Status | Future release evidence |
| --- | --- | --- |
| PSN account `user_id` vs online ID/email/host ID distinction | Sony privacy + upstream code SOURCE_CONFIRMED | Strictly typed separate identities |
| `uint64` → 8-byte little-endian → Base64 12 ASCII chars with one `=` | Upstream multiple source programs SOURCE_CONFIRMED | Own Python pure conversion and canonical roundtrip tests NOT_RUN |
| Manual Account ID and PS5 Pair Device PIN accepted by local registration without client-side OAuth call | PINNED_SOURCE only | Own source/hardware tests NOT_RUN |
| Sony personal-data export acquisition | Official Sony help CONFIRMED; ID field only COMMUNITY_REPORTED | No full Excel import, user-provided scalar only |
| 16–19 digit numeric ID precision | Official Microsoft Excel max 15 digits | Original text and Python int; never JS Number/sheet numeric conversion |
| Sony OAuth client registration for our HA integration | NOT VERIFIED | No borrowed Sony app Client ID/secret, NPSSO or token harvesting |
| User ID format vs Sony account ownership | DISTINCT; no provider assertion | USER_ASSERTED ≠ CONSOLE_ACCEPTED_PAIRING ≠ SONY_VERIFIED |
| Registered wake credential vs Account ID | Upstream source separate credential fields | Wake not available without accepted RP registration |
| Multi-console/account pairing and secret retention | PROPOSED | ACL/secret isolation, failed/revoked/replaced device tests |
| AES primitive and lawful key-table rights | BLOCKED/UNAPPROVED | No encrypted pairing feature release without both gates |

All `IDP-01..24` are source-derived future checks added to existing SPEC-002/003, not executed tests. LAN discovery and source-based history remain standalone and unaffected.
