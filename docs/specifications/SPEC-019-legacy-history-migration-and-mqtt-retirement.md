# SPEC-019 — Legacy SQLite history migration, provenance and MQTT entity retirement

**Date:** 2026-11-06
**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_EXECUTABLE_CODE
**Primary source audit:** [Develop legacy migration research](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md)
**Technical ADR:** [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) PROPOSED
**Source branch:** develop read-only (App v0.5.0, Lovelace card v1.1.2).
**Documentation branch:** main. No source changes on develop.
**Dependencies:** ADR-0004/0006/0008/0009/0011/0015/0018, SPEC-008–018. Source inspection is not a real user backup or deployment proof.

> Legacy data may have sensitive player names/title/time. Only synthetic or explicitly sanitized consented snapshots can be used in future tests. No production SQLite, options.json, MQTT broker, HA registry, automations or live consoles were touched in this research.

## 1. Objective

Define a safe optional transition from the old single-console App + PS5-MQTT + Mosquitto + standalone SQLite to the accepted native integration architecture with one logical Hub/Archive Config Entry and independent physical-console/PSN account entries.

Migrate only historical evidence whose semantics are verifiable. No legacy physical-console ID is present in the source table schemas, so the initial physical-owner classification MUST be LEGACY_UNATTRIBUTED. Never import or infer Sony token authorization, bind sessions to a newly configured PS5 based on matching player_name/MQTT topic, or silently remove old HA entities.

## 2. Invariants

| ID | Proposed acceptance contract |
| --- | --- |
| LM-I01 | Legacy source access requires a validated, coherent copied SQLite snapshot; no direct modification of active old App /data. |
| LM-I02 | Importer uses non-creating read-only SQLite opens; never invokes the legacy Database constructor which initializes/migrates. |
| LM-I03 | Legacy source version 1, 2 or 3 is accepted only if exact required schema and integrity match; newer/unknown versions fail closed. |
| LM-I04 | Source sha256, size and source manifest are preserved, never mistaken for physical attribution/authenticity. |
| LM-I05 | Exact source table/local row IDs are namespaced by legacy_source_uuid; two sources with id=1 must not collide. |
| LM-I06 | Imported original rows/events/checkpoints remain auditable without unauthorized raw data exposure. |
| LM-I07 | Sessions import with immutable original UTC timestamps and half-open interval semantics. |
| LM-I08 | Open legacy session effective endpoint cannot exceed last valid checkpoint, or start when checkpoint absent. |
| LM-I09 | No missing/inaccessible checkpoints or gaps are padded with restart time or a new native polling assumption. |
| LM-I10 | Legacy runtime continuity threshold 30 seconds is recorded as historical policy, not recomputed with 90-second helper defaults. |
| LM-I11 | Legacy state_update events are sparse change records, never synthesized into a complete periodic observation sequence. |
| LM-I12 | monitoring_state singleton is last-known historical source data, not current native LAN or physical identity. |
| LM-I13 | No source row yields a verified canonical physical PS5 identity or current PSN account authorization from old schema alone. |
| LM-I14 | Default imported physical owner is NULL / LEGACY_UNATTRIBUTED with explicit provenance and confidence. |
| LM-I15 | Legacy player_name is a private historical label, not a PSN auth key, OAuth token or cross-console owner. |
| LM-I16 | Old game title metadata may be preserved as untrusted historical text, without automatic URL artwork fetch. |
| LM-I17 | Old stats and DST comparisons use Europe/Lisbon and source-session semantics; 36-month display is not retention. |
| LM-I18 | Historical import does not overwrite already confirmed new-native ledger observations or controller generations. |
| LM-I19 | Reimport of same validated source/batch is idempotent, including after unknown admin acknowledgment. |
| LM-I20 | Later snapshot of same legacy DB requires overlap/ancestor review, not unconditional full append. |
| LM-I21 | One bounded, administrator-owned migration job staged into a separate, tested target ledger generation. |
| LM-I22 | Original source remains immutable and independently recoverable after target promotion. |
| LM-I23 | Any rollback after new native writes requires explicit newer-data preservation; no blind old-pointer rollback. |
| LM-I24 | Old App options.json and MQTT credentials NEVER enter new historical ledger, UI, diagnostics or source export. |
| LM-I25 | No native Hub/console/PSN Config Entry is fabricated from old MQTT entity ID or player_name. |
| LM-I26 | Exact legacy monitor retained MQTT Discovery topics must be inventoried before user-authorized cleanup. |
| LM-I27 | PS5-MQTT control/power entities and unrelated broker topics are outside this monitor migration cleanup. |
| LM-I28 | Old registered Lovelace card and user automations are mapped/retired in a separately authorized UI cutover. |
| LM-I29 | Source test declarations are not proof tests pass; new fixture and real backup validation still required. |
| LM-I30 | Native monitoring starts at a new evidence boundary, with gap UNKNOWN and no imported/live double counting. |
| LM-I31 | HA OS App /data, backup, entity registry and broker availability must be actually checked before migration. |
| LM-I32 | Migration is optional and fail-closed: an unattributed archive may remain read-only indefinitely. |

## 3. Source schema mapping

| Source table and columns | Target conceptual fields | Mandatory notes |
| --- | --- | --- |
| schema_version.version | original_schema_version | No implicit source migrations |
| events.id, event_type, occurred_at, payload_json | source-event id/type/UTC/audit payload | sparse events, untrusted JSON and personal data |
| sessions.id, session_type, started_at, ended_at | legacy session id/type/start/end | id namespaced; source interval not re-derived from state events |
| sessions.player_name | private legacy_player_label | not verified account key |
| sessions.title_id, title_name, title_image | source game metadata with data classification | image URL not auto-fetched |
| checkpoints.session_id, observed_at, updated_at | source checkpoint and bounded effective end | FK must validate; no fabricated elapsed |
| monitoring_state.id=1, last_observation_at, last_power, last_activity, last_player, last_title_id, updated_at | optional last-source audit record | not fresh current PlayStation |
| Old config mqtt_topic/player_name | optional restricted migration source details | not immutable console/PSN identity |
| Old config mqtt host/user/password, options.json | NO TARGET | secrets strictly excluded |
| Old 10 Discovery MQTT unique IDs | migration entity mapping metadata only | not native console unique ID |
| Old Lovelace history clients/card | future sidebar presentation/DTO design | transport retired, not historical source |

## 4. Proposed non-destructive migration job

1. Admin verifies actual old App installation and finds an authorized source export; do not assert template /data path is user's current file.
2. Obtain WAL-consistent snapshot/backup of old App DB, ideally after stable ingestion stop or SQLite Online Backup. No copy of active main DB alone, no sidecar deletion.
3. Keep original App data and export immutable; record digest, source App/schema version and private provenance. All credentials omitted from history.
4. Read exported SQLite via mode=ro (existing only) and verify SQLite integrity, foreign keys, schema, supported versions, timestamp ranges, session/checkpoint consistency and payload limits.
5. Classify source records as supported, bounded-open, invalid/quarantined, unsupported and LEGACY_UNATTRIBUTED. Do not infer PS5 hardware key from one MQTT subscription.
6. Produce administrator preview with rows/session time per source type, game/title counts, Lisbon UTC/DST report comparisons, confidence and anomalies. Never dump sensitive raw rows to public logs.
7. Require explicit approval of import-as-legacy-archive, not automatic hardware/PSN linking.
8. Stage target independent generation, storing source-record namespace and migration_batch_uuid for idempotency. Preserve raw original source evidence and original policy version.
9. Validate imported totals, audit evidence, unknown gaps, no duplicate sessions and source/target digest manifest under target code. Only then use ADR-0015 controlled active generation promotion with positive SQL worker closure.
10. Begin independent new native history from newly validated source evidence without backfill or implicit overlap merge. Keep imported legacy scope separate unless future proof/consent resolves attribution.
11. Decommission old App/MQTT/card only after validated reporting, backup, automation/entity mapping and explicit owner decision. Never remove third-party PS5-MQTT control entities as part of old monitor sensor cleanup.

**Two-phase cutover:** A. data preserved and independently imported; B. operational services/entities retired. Do not combine them in one unreviewed transaction and do not claim rollback across App, broker, HA registry and SQLite is atomic.

## 5. Test catalogue — 80 planned, ALL NOT_RUN

### 5.1 Legacy acquisition, schema and consistency — 20

| ID | Synthetic scenario | Expected outcome |
| --- | --- | --- |
| LM-SRC01 | Legacy v1 DB with required tables | Recognize schema and preserve missing checkpoint semantics |
| LM-SRC02 | Legacy v2 DB with checkpoints | Read without auto migration |
| LM-SRC03 | Legacy v3 DB with singleton state | Exact schema validated |
| LM-SRC04 | Legacy version >3 | Fail closed, never downgrade |
| LM-SRC05 | Missing legacy DB /data | Report not found, no auto-creation |
| LM-SRC06 | SQLite original active WAL | Consistent source export required |
| LM-SRC07 | Main file copied without hot WAL | Reject untrusted source |
| LM-SRC08 | Legacy Database constructor would auto-migrate | Importer never instantiates constructor |
| LM-SRC09 | Corrupt SQLite / integrity_check fails | Quarantine, originals preserved |
| LM-SRC10 | Foreign key missing checkpoint relationship | Reject/flag, never invent |
| LM-SRC11 | Options contain MQTT credentials | Exclude from target and diagnostics |
| LM-SRC12 | Actual installed path differs from sample | Runtime inventory, no template assumption |
| LM-SRC13 | Source SQLite open with non-create mode | No new source created |
| LM-SRC14 | Locked App still writing during read | Controlled consistent backup required |
| LM-SRC15 | Two different snapshots have same SQLite row IDs | Distinct source namespaces |
| LM-SRC16 | Snapshot SHA altered | Detect, do not trust digest as authentication |
| LM-SRC17 | Malformed event payload JSON | Bounded audit quarantine |
| LM-SRC18 | Timestamp outside representable UTC range | Reject/quarantine row |
| LM-SRC19 | Source file includes symlink/untrusted path | Reject path escape |
| LM-SRC20 | Source backup encrypted or missing | Admin recovery guidance, no claim import succeeded |

### 5.2 Historical semantics, provenance and attribution — 20

| ID | Synthetic scenario | Expected outcome |
| --- | --- | --- |
| LM-HIST01 | Closed console session valid time | Archive exact interval, no physical ID claim |
| LM-HIST02 | Closed gaming session with player label | Preserve private label only |
| LM-HIST03 | Open session with valid checkpoint | Bound effective end to checkpoint |
| LM-HIST04 | Open session without checkpoint | No time beyond start |
| LM-HIST05 | Checkpoint before start | Quarantine as invalid |
| LM-HIST06 | 31-second source gap | Respect legacy 30-second policy |
| LM-HIST07 | Two accepted heartbeats same state, one sparse event | Do not infer only one periodic observation |
| LM-HIST08 | Old monitoring_state AWAKE but import months later | Not current power state |
| LM-HIST09 | Old title_id/name/image | Preserve text; no auto URL fetching |
| LM-HIST10 | Same old player display name on two consoles | No new verified PSN/physical binding |
| LM-HIST11 | Old MQTT topic points to changed device | Historical physical identity unresolved |
| LM-HIST12 | Session with nullable title metadata | Preserve unknown fields |
| LM-HIST13 | UTC session crosses Lisbon DST shift | Source-calendar comparisons correct |
| LM-HIST14 | Half-open session ends local midnight | No next-day phantom activity |
| LM-HIST15 | Session older than 36-month UI index | Preserve row beyond display window |
| LM-HIST16 | Recompute game ranking with exact source sessions | Reconcile totals with policy version |
| LM-HIST17 | Overlapping console/game intervals | No accidental new multi-console duplication |
| LM-HIST18 | User selects a physical PS5 after import | No automatic historic reattribution |
| LM-HIST19 | Two players with same title in separate new accounts | No unauthorized merge with old player_name |
| LM-HIST20 | Native new observations start during migration gap | Gap UNKNOWN, no backfill |

### 5.3 Idempotency, target generation and rollback — 20

| ID | Synthetic scenario | Expected outcome |
| --- | --- | --- |
| LM-IMP01 | Preview without confirmation | No target writes |
| LM-IMP02 | Non-admin requests import | Denied |
| LM-IMP03 | Valid source manifest, batch UUID created | One owner-scoped job |
| LM-IMP04 | Two concurrent admins import same source | One idempotent batch |
| LM-IMP05 | Same batch retried 100 times | No duplicate rows/durations |
| LM-IMP06 | Browser disconnect during import | Backend job survives/fails safely |
| LM-IMP07 | Crash during target staging | Old source and old target preserved |
| LM-IMP08 | Crash after SQL import before pointer | Staged candidate only |
| LM-IMP09 | Crash after pointer but before ACK | Reconcile same selected generation |
| LM-IMP10 | New target already contains native history | No in-place overwrite or blind rollback |
| LM-IMP11 | Same legacy_source_uuid but changed snapshot | Common ancestor/overlap check |
| LM-IMP12 | Two unrelated sources with id=1 | Namespaced row IDs |
| LM-IMP13 | Imported rows intentionally quarantined | Manifest records exact counts/reasons |
| LM-IMP14 | Original private snapshot not preserved | Import blocked or retention warning |
| LM-IMP15 | Source evidence differs during confirmation | Stale preview rejected |
| LM-IMP16 | Worker not closed before pointer | FAILED_UNSAFE_TO_REOPEN |
| LM-IMP17 | Source corrupt mid import | Fail closed, preserve target |
| LM-IMP18 | Failed import then admin restores prior target | No newer native history lost |
| LM-IMP19 | Double count current native and legacy scope | Explicit report-level union policy required |
| LM-IMP20 | Storage quota insufficiency | Preserve original/target and fail safely |

### 5.4 MQTT Discovery, frontend and operational cutover — 20

| ID | Future scenario | Expected outcome |
| --- | --- | --- |
| LM-CUT01 | Inspect ten old monitor Discovery keys | Exact list and synthetic device ID |
| LM-CUT02 | Retained old discovery after App stopped | Old entities may reappear |
| LM-CUT03 | User renamed old entity IDs | Use live registry inventory, not hardcoded JS |
| LM-CUT04 | Old MQTT unique ID collisions with native | Prevent duplicate/overwrite |
| LM-CUT05 | Old monitor sensors + PS5-MQTT external power switch | Cleanup only old monitor topics |
| LM-CUT06 | Wildcard MQTT retain cleanup proposed | Prohibit broad deletes |
| LM-CUT07 | Exact single-component discovery retired with consent | Empty retained payload only to owned topics |
| LM-CUT08 | Old App restarts and republishes discovery | Detect, no false completed retirement |
| LM-CUT09 | HA automation references old monitoring sensor | Warn/map before retirement |
| LM-CUT10 | HA automation references third-party PS5-MQTT switch | Preserve external integration until separately authorized |
| LM-CUT11 | Lovelace card still installed after native panel | Explicit UI retirement plan, no duplicate UI promise |
| LM-CUT12 | Old card calls mqtt/subscribe | Not imported into native history backend |
| LM-CUT13 | Old history request correlation and timeout | Port behavioral tests only |
| LM-CUT14 | Old live retained state after App stopped | Do not show as fresh native status |
| LM-CUT15 | New panel report for legacy unassigned data | Clear provenance, no physical control |
| LM-CUT16 | New physical-console entities created | New canonical IDs, no synthetic old monitor identity reuse |
| LM-CUT17 | Retained old discovery cleanup fails partly | Visible incomplete/rollback-ready status |
| LM-CUT18 | Removing App before source export | Block recommended cutover, data-at-risk warning |
| LM-CUT19 | Native monitoring and old App running concurrently | Prevent duplicate ingestion and timestamp overlap |
| LM-CUT20 | Post-cutover backup and rollback rehearsal | Preserve old source and new committed sessions |

**SPEC-019 total: 80 planned scenarios** (20 SRC +20 HIST +20 IMP +20 CUT); all NOT_RUN. Earlier SPEC-008–018 tests overlap intentionally and do not establish successful migration.

## 6. Sign-off gates — 20 OPEN

| Gate | Required evidence | Status |
| --- | --- | --- |
| LM-G01 | Source app/SQLite actual installation and backup inventory | BLOCKED_USER_DATA / NOT_RUN |
| LM-G02 | WAL-consistent private old App export | NOT_RUN |
| LM-G03 | Exact schema v1/v2/v3 read-only validation | SOURCE_REVIEWED / NOT_RUN |
| LM-G04 | No old Database constructor migration of source | PROPOSED / NOT_RUN |
| LM-G05 | Physical owner default LEGACY_UNATTRIBUTED accepted | OPEN_PRODUCT_DECISION |
| LM-G06 | Player_label/PSN token separation and ACL | NOT_RUN |
| LM-G07 | Legacy 30s policy and checkpoint correctness | SOURCE_REVIEWED / NOT_RUN |
| LM-G08 | UTC/Lisbon DST/36-month window data retention | NOT_RUN |
| LM-G09 | Event sparsity and honest coverage | NOT_RUN |
| LM-G10 | Import namespace, manifest, row and batch idempotency | NOT_RUN |
| LM-G11 | Immutable original and target generation rollback | NOT_RUN |
| LM-G12 | Crash/cancellation and worker-terminal safety | NOT_RUN |
| LM-G13 | Source v3 fields and real record anomalies validated | BLOCKED_USER_DATA |
| LM-G14 | Existing new-native history conflict/no double count | NOT_RUN |
| LM-G15 | Live HA registry and automations dependency review | BLOCKED_HA_OS |
| LM-G16 | Exact old monitor MQTT Discovery retirement only | NOT_RUN |
| LM-G17 | External PS5-MQTT power/activity entities unaffected | NOT_RUN |
| LM-G18 | Lovelace card -> native panel UX/WS transition | NOT_RUN |
| LM-G19 | HA OS App /data backup restore and deinstall safety | BLOCKED_HA_OS |
| LM-G20 | Maintainer-approved data cutover and rollback policy | OPEN |

## 7. Documentation-only boundary

- The source is code on develop, not a live installed database.
- No source export/migration, HA registry scan, broker message, App stop, worker, test or input/output artifact has been created.
- No original historical row count, date interval, player identity, physical PS5 attribution or current HA entity name has been verified in a real deployment.
- ADR-0019 remains PROPOSED even if the user has approved ADR-0011's product architecture and ongoing research.
- Runtime migration requires separate explicit implementation authorization, backups and review of live data.

## 8. Sources

- [New source audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md)
- [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md)
- [Earlier legacy code review](../research/legacy-code-review-and-refactoring-blueprint-2026-11.md)
- [Earlier legacy frontend review](../research/legacy-frontend-source-audit-2026-11.md)
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/main.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/mqtt_publisher.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js
- https://www.home-assistant.io/integrations/mqtt/
- https://www.sqlite.org/backup.html

**Outcome:** 80 NOT_RUN, 20 OPEN. Documentation only.
