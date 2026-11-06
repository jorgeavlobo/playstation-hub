# PlayStation Hub — Greenfield SQLite v1 schema and query-model source audit

**Date:** 2026-11-06
**Status:** OFFICIAL_SOURCE_RESEARCH / PROPOSED_LOGICAL_SCHEMA / NO_SQL_DDL / NO_TESTS / NO_IMPLEMENTATION
**Sources:** Home Assistant Core 2026.11.0; official SQLite foreign keys, STRICT tables, CHECK, partial indexes, UPSERT, transaction, WAL, PRAGMA, backup and query planner guidance.
**Accepted product scope:** Greenfield native PlayStation Hub; legacy develop prototype was NEVER deployed and every old database record was fabricated. No legacy importer, old schema v1–v3 compatibility, old MQTT cutover or old data migration.
**Related:** [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md), [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md), [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md), [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md), [Protocol 10](../protocols/10-game-metadata.md).
**Branch:** main documentation only; develop untouched.

> Classification: SQLITE_OFFICIAL = upstream documented fact, CORE_PINNED = inspected Core source, PROJECT_PROPOSAL = unapproved PlayStation Hub design, OPEN_HA_OS = installed runtime unverified. No table below exists. This is a detailed LOGICAL schema proposal, not final CREATE TABLE DDL.

## 1. Summary and decisions to preserve

One private application-owned SQLite database for all physical PlayStations and optional PSN accounts, with one serialized writer and bounded readers. HA Config Entries, device registry, Recorder entities and Sony credentials remain distinct owners. A canonical source observation is not automatically a game session, PSN account presence is not proof of local physical-console activity, and provider-reported lifetime playtime is never summed into locally recorded session seconds.

**Core rules:** typed identities; durable idempotent observation IDs; append-only evidence; versioned derived segments; half-open UTC intervals; explicitly UNKNOWN coverage; stable ledger UUID and transactional cursor; future schema upgrades only of THIS new application's own live data. Do not store duplicate daily/monthly totals as independently authoritative rows. The exact v1 SQL layout awaits approval and future tests.

## 2. External-source evidence matrix

| ID | Evidence | Official fact | Application consequence |
| --- | --- | --- | --- |
| GS-01 | SQLite foreignkeys.html | Foreign key enforcement must be switched ON per connection | Verify on writer, reader and restore-inspection connections |
| GS-02 | SQLite lang_createtable.html | FK parent must use named PK/UNIQUE; CHECK result NULL does not violate | All public identity columns NOT NULL; complete CHECK predicates |
| GS-03 | SQLite lang_createindex.html | UNIQUE permits multiple NULLs | Do not use nullable tuples to guarantee one active association |
| GS-04 | SQLite stricttables.html | STRICT requires SQLite >= 3.37.0 and native INTEGER/TEXT/REAL/BLOB/ANY/INT types | Prefer strict typing only after checking linked C library and compatibility |
| GS-05 | SQLite partialindex.html | Partial unique indexes constrain selected rows | Candidate for one open exclusive console-awake segment |
| GS-06 | SQLite lang_upsert.html | UPSERT handles uniqueness conflicts but not FK or CHECK failures | Check duplicate payload digest and return receipt, not silent replacement |
| GS-07 | SQLite wal.html | WAL readers can coexist with single writer; WAL has local filesystem/version limits | One process-wide writer and version/locality gate |
| GS-08 | SQLite backup/pragma | Online backup yields internally consistent snapshot when completed; integrity_check differs from FK check | Validate both database and domain metadata on restore |
| GS-09 | SQLite lang_analyze.html | PRAGMA optimize supports query planning, version-specific behavior | Measure 36-month plans before adding excessive indexes |
| GS-10 | Core 2026.11 recorder/db_schema.py | Recorder and statistics have their own tables and lifecycles | Never write our private game/session history into Recorder tables |
| GS-11 | Project ADR-0004/0006 | Console/account/title identities and bounded session evidence are separate domains | Preserve source/attribution confidence and time coverage |
| GS-12 | Project ADR-0018 | First ledger genesis is separately authorized from Hub Config Entry | New v1 tables created only inside explicit new generation |

## 3. Ownership model and privacy

**A. HA configuration**: Hub/console/PSN Config Entries, options, entity registry and user-managed display labels. HA entry_id and entity_id are NOT historical primary keys and may change after restore.
**B. Secrets**: Sony OAuth/NPSSO/session/Remote Play pairing material remains in separate protected storage under ADR-0007; never enter history rows or generic exports.
**C. History ledger**: immutable console/account/title keys, evidence observations, revisioned derived sessions, unknown coverage, provider aggregate snapshots and provenance/checkpoints.
**D. Game metadata/cache**: mutable title names, artwork references, locales, metadata source, retrieval freshness and rights. Optional game artwork binaries live in evictable cache.
**E. HA entities/Recorder**: operational projections only, not authoritative multi-year session ledger.
**F. Recovery**: versioned snapshot, manifest, generation pointer and journal operate outside logical table schema.

Source attribution principles:
- LAN facts are physical-console observations only after canonical identity validation.
- PSN account presence is account-scoped, not proof that a particular physical PS5 ran the game.
- A user-declared console-account link is a relationship, not proof of each gaming interval.
- Title identity uses provider+namespace+external ID+platform, not localized name.
- Provider lifetime seconds and entitlements are not local observed seconds or title installation.

## 4. Core v1 tables — precise conceptual columns

Types: TEXT opaque IDs/enums, INTEGER integer UTC microseconds and durations, BLOB only if a separate reviewed nonsecret format is justified. No cumulative REAL seconds. Every ID is NOT NULL. An optional field uses NULL to mean unknown, NOT zero, offline or an empty string.

| Table | Fields (candidate) | Constraints and meaning |
| --- | --- | --- |
| ledger_meta | ledger_uuid, schema_version, min_readable_schema_version, genesis_op_uuid, generation_uuid, lineage_epoch, parent_snapshot_uuid nullable, accounting_policy_version, committed_cursor, created_utc_us | Exactly one logical ledger identity, immutable ledger UUID, cursor advanced in the ingestion transaction |
| schema_revisions | migration_id, from_version, to_version, applied_utc_us, app_version, expected_schema_digest, status | Unique migration id, strictly monotonic; future NEW-app upgrades only |
| runtime_epochs | run_uuid, generation, started_utc_us, ended_utc_us nullable, close_reason, selected_ledger_generation_uuid | One row per process generation where useful; monotonic clocks never persisted across runs |
| console_owners | console_key, console_kind, identity_format_version, canonical_fingerprint, identity_validation_level, first_seen_utc_us, retired_utc_us nullable, label nullable | Stable canonical console key, not IP/MAC/hostname; old key remains after console removal |
| psn_account_refs | account_key, provider_namespace, provider_key, link_status, linked_utc_us, unlinked_utc_us nullable | Unique provider-scoped stable account key; no token or auth cookie |
| console_account_links | association_uuid, console_key FK, account_key FK, relation_kind, provenance, confidence, valid_from_utc_us, valid_to_utc_us nullable, revision | Many-to-many temporal link; NOT a proof of player gameplay on any specific device |
| game_titles | game_key, provider_namespace, title_namespace, external_title_id, platform_scope, title_kind, created_utc_us | Unique nonnullable provider/namespace/id/platform tuple; display name not key |
| observations | observation_uuid, run_uuid FK, source_kind, console_key FK nullable, account_key FK nullable, source_generation, sequence, observed_utc_us, accepted_utc_us, evidence_kind, evidence_confidence, source_precision_us nullable, canonical_digest | Unique idempotency key; validated source owner; no raw Sony token or provider body |
| domain_events | event_uuid, observation_uuid FK, event_kind, effective_utc_us, console_key FK nullable, account_key FK nullable, game_key FK nullable, provenance, interpretation_policy_version, revision | Immutable/revision-audited normalized interpretation, not exact transition time by assumption |
| session_segments | segment_uuid, console_key FK nullable, account_key FK nullable, game_key FK nullable, kind, start_utc_us, end_utc_us nullable, last_checkpoint_utc_us, start_boundary_kind, end_boundary_kind, attribution, start_observation_uuid FK, policy_version, revision, close_reason nullable | Half-open interval; start <= checkpoint <= end when end exists; nullable end only for open segment with current checkpoint |
| unknown_intervals | gap_uuid, console_key FK nullable, account_key FK nullable, start_utc_us, end_utc_us nullable, reason, preceding_observation_uuid FK nullable, following_observation_uuid FK nullable, policy_version | Unknown coverage is NOT OFF and never game time |
| source_checkpoints | source_kind, source_key, run_uuid FK, last_sequence, last_observation_uuid FK, accepted_utc_us, committed_cursor | Unique typed source key; updated in SAME SQL transaction as observation/event/segments |

**Do not make external keys into an unrestricted polymorphic foreign key.** Either use explicit nullable console_key/account_key columns with complete kind-dependent CHECK predicates and named FK references, or split source-specific tables if the SQL design proves cleaner. An observation targeting both hardware and account must represent separate source facts plus reviewed correlation, not an invalid ambiguous owner row.

## 5. Optional v1+ tables — expand only if actual source authorization/features justify

| Table | Candidate fields | Rules |
| --- | --- | --- |
| game_metadata_locales | game_key FK, locale, localized_name, publisher nullable, source, fetched_utc_us, expiry_utc_us nullable, artwork_ref nullable, rights_status | Unique (game,locale,source), names mutable, artwork cached separately; deletion cannot alter sessions |
| game_title_crosswalk | relation_uuid, from_game_key FK, to_game_key FK, match_type, source, confidence, last_verified_utc_us | Edition/concept/trophy aliases are not automatically equivalent game identities |
| provider_entitlement_snapshots | snapshot_uuid, account_key FK, game_key FK, observed_utc_us, entitlement_type, relation_status, provenance | Account library != local installation/permanent ownership |
| provider_playtime_snapshots | snapshot_uuid, account_key FK, game_key FK, observed_utc_us, raw_duration_integer, verified_duration_unit nullable, provider_scope, provenance | Provider totals separate; unspecified units remain unknown |
| evidence_corrections | correction_uuid, referenced_observation_uuid FK, referenced_segment_uuid nullable, old_revision, new_revision, reason, applied_utc_us, provenance | Explicit audit revision; never rewrite original source fact silently |
| retention_tombstones | tombstone_uuid, owner_kind, owner_key, action, authorized_utc_us, provenance | Optional only if approved privacy purge/export requires durable audit; no implicit cascade |

**V1 boundary recommendation:** create the 12 core tables first; add provider and metadata/correction modules only when their API/privacy/authorization are independently validated. Conceptual metadata must not introduce an automatic Sony API dependency to LAN-only monitoring.

## 6. Uniqueness, foreign keys and temporal integrity

Database constraints (subject to actual DDL tests):
- Explicit PK/NOT NULL on all owner UUIDs, observation/event IDs and schema revisions.
- UNIQUE observation_uuid; duplicates with identical content yield existing durable receipt, same ID/different digest is a hard conflict, not DO UPDATE.
- FK to console/account/title/observation rows and mandatory PRAGMA foreign_keys=ON on **each** SQLite connection. No ON DELETE CASCADE for durable session evidence when a Config Entry is removed; retirement/unlink is a status/temporal change.
- CHECK values and nonnegative integer boundaries; CHECK can evaluate NULL as permitted so optional value predicates need explicit null handling.
- Active console-awake exclusivity candidate: PARTIAL UNIQUE(console_key) for kind=console_awake AND end IS NULL. Do not apply the same simplistic key to player/title segments where multiple uncertain associations may exist.
- Active association uniqueness candidate: PARTIAL UNIQUE(console_key,account_key) for valid_to IS NULL, under reviewed link-version semantics. A UNIQUE tuple with nullable columns is insufficient as NULL entries are distinct in SQLite.
- End cannot precede start; an open segment has no asserted end and a bounded last durable checkpoint. Domain logic must enforce more than row-local CHECK.

Not fully enforceable via simple row CHECK:
- Two *closed* exclusive awake segments overlapping in time, or derived gaming segment not genuinely supported by physical/source intervals.
- Identity and confidence validity, overlapping account mappings, correct provider semantics, source time credibility and no double-count after a lost commit acknowledgment.
- A cross-system transaction spanning ledger pointer, HA Config Entries and SQLite schema.
- No silent duplicate time across owner-scoped corrections and replay after a restore fork.

## 7. One atomic ingestion contract

1. Check current HubController writer lease and generation, canonical source key and source sequence.
2. Check observation_uuid in persisted accepted evidence. If same ID/digest exists, return its prior commit receipt; if conflicting payload, reject.
3. Insert accepted observation and derived domain event(s) inside one SQL transaction.
4. Apply bounded reducer transitions: session start/extend/close, last supported checkpoint and unknown coverage gap; do not infer OFF or a game for missed polls.
5. Advance source_checkpoint and global ledger_meta committed_cursor in that SAME transaction.
6. COMMIT before displaying DURABLE history. The writer may have committed even when the awaiting coroutine was cancelled; retry/reconcile by stable observation ID, never add cumulative elapsed time twice.
7. On disk/full/busy/IO errors, do not fabricate a successful cursor; live current state may be marked UNSAVED and missing time UNKNOWN. Do not open a second writer or create a blank DB.
8. All entity getters, front-end requests and transport callbacks use bounded repository queries/messages, never direct DB writes.

An unchanged compatible source heartbeat may advance bounded evidence/checkpoint without creating a new session count. Any source observation processed before durable commit is not a persisted historical fact.

## 8. Temporal and report projections

Use INTEGER UTC epoch microseconds for persisted boundaries, with explicit source timestamp precision/quality separately. Use half-open [start,end) intervals and no negative durations. Process-monotonic timestamps are for within-run scheduling only, never persisted as comparable timestamps across restarts.

- Per-console bounded awake seconds: union compatible covered awake intervals within the requested UTC range; exclude UNKNOWN gaps.
- All-console total: SUM per-console hours; can exceed one wall-clock day across several concurrent consoles. Separate optional wall-clock union metric.
- Game/player attribution: only source-supported and confidence-labelled activity. Provider account presence is not proof of local console gaming.
- PSN reported lifetime duration: store source value/unit/scope, never silently add to locally measured game/console seconds.
- Day/week/month/year/rolling windows: derive requested IANA local calendar boundaries then convert to UTC for clipped intersection; DST 23/25-hour local days and leap years are normal.
- Open segments: report only through last committed checkpoint, not current wall clock. Provisional live timers are not durable history.
- Unknown intervals, coverage flags, interpretation policy version and data_as_of_cursor accompany statistics.
- Reproduce same report at same commit cursor, same policy and timezone; query-time caching must invalidate on new commits, corrections and restored generation.
- Do not persist independent cumulative daily/monthly aggregates in core v1. Optional cache is disposable with version+ledger+cursor+timezone in key.

## 9. Index and volume review (proposals, not benchmarks)

Candidate indexes: UNIQUE observation ID; (source_kind,source_key,source_sequence) with run generation if source sequence resets; (console_key,observed_utc_us); (console_key,start_utc_us), (account_key,start_utc_us), (game_key,start_utc_us) for report filters; partial UNIQUE for open exclusive segments; (account_key,game_key,observed_utc_us DESC) only if provider snapshots are actually used. Verify each with EXPLAIN QUERY PLAN and realistic query workload before creating all indexes.

**Illustrative volume** (not measured): one accepted heartbeat every 30 seconds yields 2,880 observations/day/console and 1,051,200 per non-leap year/console, or approximately 3.15 million rows in 3 years if ALL heartbeats are stored. Prefer storing state changes and enough evidentiary checkpoints to reproduce bounded durations; pruning may not destroy the only evidence underpinning retained sessions. Actual sampling policy, payload size, write rates, WAL growth, backup/snapshot sizes and latency limits remain OPEN.

Use SQLite PRAGMA optimize only under verified actual version and tested resource budgets. A single serialized writer with optional WAL remains subject to the documented 2026 WAL reset fix/backport runtime gate and local filesystem requirement from ADR-0008/SPEC-010.

## 10. Greenfield schema genesis and future schema upgrades

- NEW application starts at schema version v1. The old develop App schema v1–v3 is discarded research-only test data, not an input or migration baseline.
- The native logical Hub Config Entry may exist without initialized history. Per ADR-0018, a separate admin CREATE_NEW_HISTORY action reserves a durable CREATE_INTENT and exclusive staged SQLite generation. Schema genesis and ledger UUID/cursor are written transactionally before closing/verifying/promoting one active generation pointer.
- Normal startup opens an existing selected generation in non-creating mode; never silently recreate absent/corrupt history.
- Intra-ledger schema_meta and schema_revisions are the source for schema migration history. PRAGMA user_version/application_id are optional additional metadata, NOT standalone proof of a safe upgrade or a valid ledger.
- Future upgrades of THIS new product, after it records real data, use reviewed version transitions with immutable pre-upgrade snapshot, transactional/recoverable migration and preserved old generation; no automatic destructive downgrade.
- A restored future-schema DB read by older integration code must enter guarded read-only/RECOVERY_HOLD rather than being reset.
- HA Config Entry updates, recovery journal/active pointer and SQLite SQL transactions do NOT form a single atomic transaction; reconciliation remains necessary.

## 11. Privacy, retention and boundaries

No OAuth/NPSSO, Remote Play pairing material, raw request/response payloads or private Sony credentials in history tables. Console/account provider keys are personal data and never appear raw in generic diagnostics; title metadata/artwork must respect licensing and privacy. Removing a console entry retires it, preserving historical FK parent rows and segments. Account unlink revokes credentials independently of retention of historical evidence.

Explicit user purge requires separate authorization and backup/snapshot/recovery impact review; deletion of DB rows does not automatically wipe historical bytes from WAL or prior backups. No claims of secure erasure unless the design proves them. Default diagnostics and exports omit raw secrets and personal history, unless separately authorized and scoped.

## 12. Outstanding technical gates

| Open choice | Candidate preference | State |
| --- | --- | --- |
| 12 core tables vs further split/merge | Normalize identities/evidence/segments/checkpoints | PROPOSED |
| Timestamp representation | INTEGER UTC microseconds | PROPOSED |
| STRICT typing | Prefer if linked runtime >=3.37 with compatibility | OPEN_HA_OS |
| Foreign-key enforcement | ON and verify per connection | SOURCE_CONFIRMED, APP_NOT_RUN |
| WAL vs rollback | Single writer; final choice needs patched SQLite+FS tests | OPEN_HA_OS |
| Nonoverlap/exclusive session semantics | Partial unique open segments plus serialized reducer checks | PROPOSED |
| PSN snapshots/metadata | Optional, separate from local usage, gated on provider authorization | PROPOSED |
| Retention and derived rollups | Reproducible evidence first, disposable caches later | OPEN |
| UTC vs local timezone reports | UTC instants, convert local calendar boundaries | PROPOSED |
| Idempotent observation+checkpoint transaction | Mandatory correctness target | PROPOSED/NOT_RUN |
| Privacy retention/purge | No cascading loss on entry removal | PROPOSED/NOT_RUN |
| Genesis / future migrations | New v1 from scratch, later only NEW-app upgrades | GREENFIELD_CONFIRMED, DDL_UNAPPROVED |
| Acceptance evidence | SPEC-020 96 planned scenarios and 24 gates | ALL_NOT_RUN |

## 13. Official sources

SQLite:
- https://www.sqlite.org/foreignkeys.html
- https://www.sqlite.org/lang_createtable.html
- https://www.sqlite.org/stricttables.html
- https://www.sqlite.org/partialindex.html
- https://www.sqlite.org/lang_createindex.html
- https://www.sqlite.org/lang_upsert.html
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/lang_analyze.html

Home Assistant pinned:
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/db_schema.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/statistics.py

Project:
- [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md)
- [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md)
- [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [Protocol 10](../protocols/10-game-metadata.md)
- [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md)

**Outcome:** Detailed logical schema/source research only; no executable SQL DDL, code, database, migration, user data, simulator or tests created.
