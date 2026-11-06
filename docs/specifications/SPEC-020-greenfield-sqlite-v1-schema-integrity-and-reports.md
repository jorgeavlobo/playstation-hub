# SPEC-020 — Greenfield SQLite v1 schema, integrity, idempotency and usage reports

**Date:** 2026-11-06
**Status:** PROPOSED / NO_DDL / NOT_IMPLEMENTED / ALL_TESTS_NOT_RUN
**Research:** [Source-pinned SQLite v1 schema audit](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md)
**Decision:** [ADR-0020 PROPOSED](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md)
**Input contracts:** ADR-0004 physical identity, ADR-0005 evidence, ADR-0006 sessions/timezones, ADR-0008 persistence, ADR-0011 ACCEPTED Hub product, ADR-0018 new genesis, Protocol 09/10 PSN and game identities.
**Official source versions:** SQLite documentation and pinned HA Core 2026.11.0 Recorder source (source of comparison, NOT our DB).
**Branch:** main documentation only. develop is old fictional prototype reference and is not a migration input.

> A named test below is a planned acceptance scenario, not a test executed or a working SQL migration. The 12 core tables and optional tables are logical, subject to explicit maintainer approval and compatible SQLite runtime tests. No SQL CREATE TABLE source file is authorized.

## 1. Goal

Specify a brand-new multi-console, optional-account SQLite history and metadata model that can be written idempotently, independently verified, backed up/restored, reported over local calendar periods, and extended without importing any legacy develop data. Preserve separate truth categories: physical LAN evidence, PSN account presence, local attributed gameplay and provider lifetime playtime.

The v1 schema must not:
- assume a user account is required for LAN-only sessions;
- identify a console by IP, display label or HA entity/entry ID;
- store Sony authentication/Remote Play credentials;
- interpret network silence as console OFF or gap as gaming;
- sum two consoles as though they are one exclusive physical resource;
- substitute provider lifetime minutes for locally observed duration;
- maintain irreconcilable independent day/month totals;
- delete historical sessions when a console Config Entry is removed.

## 2. Proposed core v1 logical schema

| Family | Candidate tables | Responsibilities |
| --- | --- | --- |
| Version/genesis | ledger_meta, schema_revisions, runtime_epochs | Ledger identity, runtime and migration/lineage authority |
| Identity | console_owners, psn_account_refs, console_account_links | Stable separate physical/account identities and temporal association |
| Game keys | game_titles | Provider/namespace/ID/platform-stable game identity |
| Evidence | observations, domain_events | Immutable accepted source facts, normalization/revision, idempotency |
| Historical intervals | session_segments, unknown_intervals | Bounded awake/game/attributed activity and missing-coverage periods |
| Acceptance cursor | source_checkpoints | Per-source durable checkpoint with global commit cursor |

This is **12 logical core tables**, not 12 runtime tables that already exist. Optional after source/legal/feature approvals: game_metadata_locales, game_title_crosswalk, provider_entitlement_snapshots, provider_playtime_snapshots, evidence_corrections and retention_tombstones.

See ADR-0020 and the research audit for proposed fields and FK/index relationships. The final physical schema may split/merge tables after tests without automatically invalidating these logical invariants.

## 3. Proposed data invariants

| ID | Must eventually prove |
| --- | --- |
| GS-I01 | Greenfield v1 schema has no old develop schema or historical fake data importer. |
| GS-I02 | One ledger UUID and initial genesis identity, schema version and durable cursor are transactionally coherent. |
| GS-I03 | Physical console ID, PSN account ID, title ID, Hub Config Entry ID and HA entity ID are different namespaces. |
| GS-I04 | LAN-only physical console may have sessions with no linked PSN account or verified title. |
| GS-I05 | Game title identity uses provider, title namespace, external ID and platform scope, all explicit and nonnullable where unique. |
| GS-I06 | Foreign-key parent columns are explicitly named PK/UNIQUE, not implicit rowids. |
| GS-I07 | Every SQLite connection that uses relational history explicitly enables and checks foreign-key enforcement. |
| GS-I08 | Every canonical durable key is NOT NULL; SQLite UNIQUE NULL loopholes cannot produce duplicate active owners. |
| GS-I09 | STRICT table mode is gated on actual linked SQLite C library >=3.37 and supported backup/downgrade policy. |
| GS-I10 | Epoch timestamps and durations are integer, not accumulating floating point time. |
| GS-I11 | Source timestamp accuracy/confidence is tracked separately from numeric timestamp precision. |
| GS-I12 | No provider credential, auth token, pairing secret or raw private packet is stored in history. |
| GS-I13 | Original source observations are immutable/auditable and deduplicated by stable UUID and canonical payload digest. |
| GS-I14 | Same observation UUID with different payload is a conflict, not a silent overwrite or duplicate credit. |
| GS-I15 | Accepted observation, derived events, segment revisions/gaps, checkpoints and ledger commit cursor form one atomic SQL transaction. |
| GS-I16 | Lost async COMMIT acknowledgment is reconciled by persisted stable observation ID, not by adding elapsed seconds again. |
| GS-I17 | Source generation, runtime run UUID and per-owner sequence prevent stale callbacks from writing newer generations. |
| GS-I18 | Historical sessions use half-open UTC intervals with explicit last committed evidence checkpoint. |
| GS-I19 | Open console-awake segments have at most one current exclusive segment per verified console, under reviewed domain/index constraints. |
| GS-I20 | No overlapping closed exclusive console-awake coverage can double count in reports. |
| GS-I21 | Unknown gaps remain UNKNOWN, not OFF or inferred gameplay. |
| GS-I22 | PSN account presence cannot prove a game played on this LAN console or a player identity. |
| GS-I23 | Provider lifetime playtime/entitlement snapshots are not summed with local game/awake time. |
| GS-I24 | Game metadata/locale/cover changes never change already committed session identities or durations. |
| GS-I25 | Removing a console Config Entry or unlinking account cannot cascade-delete historical observation/session rows. |
| GS-I26 | Every row-level CHECK handles NULL intentionally and every source type is constrained to valid owner fields. |
| GS-I27 | PARTIAL UNIQUE constraints on open intervals are applied only to correct exclusive resource, not every account/title interpretation. |
| GS-I28 | Daily/weekly/monthly/yearly reports clip [start,end) intervals to IANA timezone-derived UTC windows. |
| GS-I29 | DST, leap days and midnight boundaries never double count or introduce negative duration. |
| GS-I30 | Combined all-console device-hours may exceed wall-clock time; separate union metric must not be silently substituted. |
| GS-I31 | Report totals are deterministic for the same ledger cursor, accounting policy and report timezone. |
| GS-I32 | No independent, non-reproducible durable aggregate counters exist in core schema. |
| GS-I33 | SQLITE_FULL/BUSY/READONLY/IOERR cannot advance durable cursor falsely or reset history. |
| GS-I34 | Backups and recovery snapshots preserve schema, ledger UUID, FK integrity, policy and commit cursor. |
| GS-I35 | New first genesis is explicit and initialized in staged unique generation before active pointer, never generic create-on-open. |
| GS-I36 | Later real-data schema upgrades are versioned NEW-app-only, no old synthetic v1–v3 App compatibility. |
| GS-I37 | Incompatible newer schema is refused in protected mode, not downgraded or overwritten. |
| GS-I38 | Every optional Sony provider feature remains conditional on independently verified permitted API and privacy. |
| GS-I39 | All database access occurs through shared manager and bounded reader/writer leases, not HA entity getters or UI. |
| GS-I40 | Minimal indexes serve verified query patterns, with tested 36-month scale and source-specific access control. |

## 4. Future acceptance test catalogue — 96 NOT_RUN

### 4.1 Schema, types, FKs and identities — 24 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| GS-SC01 | Explicit genesis creates ledger v1 | Exactly one ledger UUID, schema version, valid empty cursor |
| GS-SC02 | Duplicate genesis operation/restart | One ledger identity, idempotent receipt |
| GS-SC03 | Old synthetic develop schema supplied | No legacy importer; unrelated source cannot silently adopt |
| GS-SC04 | Strict tables on patched supported SQLite | Valid native INTEGER/TEXT types, constraints enforced |
| GS-SC05 | STRICT on unsupported SQLite | Feature gate; no destructive fallback |
| GS-SC06 | Foreign keys disabled on new connection | Connection cannot ingest until FK ON verified |
| GS-SC07 | Insert segment referencing unknown console | FK rejects, no orphan segment |
| GS-SC08 | Insert account association referencing absent account | FK rejects, no dangling association |
| GS-SC09 | Remove console Config Entry | Retire runtime/reference, historical rows retained |
| GS-SC10 | Unlink PSN account | Token revoked elsewhere; past physical history unchanged |
| GS-SC11 | Two consoles same friendly name/IP | Distinct stable physical keys, no merge |
| GS-SC12 | Physical console replaced at prior IP | New key, old history retained on prior key |
| GS-SC13 | PSN account linked to two consoles | Valid many-to-many, no invented local play |
| GS-SC14 | Two accounts linked to one console | No automatic same-game/player attribution |
| GS-SC15 | Foreign PSN account key used as console key | Namespace/type guard rejects |
| GS-SC16 | Game title same name, different provider ID | Two distinct title keys |
| GS-SC17 | Game title same external ID, different platform | Distinct where source scope distinguishes |
| GS-SC18 | UNIQUE tuple with NULL title scope attempt | NOT NULL/sentinel policy prevents identity ambiguity |
| GS-SC19 | Invalid CHECK range end < start | Reject |
| GS-SC20 | CHECK expression NULL loophole attempt | Explicit NOT NULL/kind predicate rejects |
| GS-SC21 | Partial UNIQUE duplicate open console-awake segment | Reject second exclusive open segment |
| GS-SC22 | Two closed exclusive segments overlap | Domain/reducer validation rejects overlapping counted seconds |
| GS-SC23 | Credentials inserted in game history row | Schema/repository security contract rejects unreviewed secret fields |
| GS-SC24 | Schema revision transition skipped or repeated | Versioned migration guard, no half-applied schema |

### 4.2 Source evidence, receipts and transactional session reducer — 24 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| GS-TX01 | First verified physical awake observation | One fact, no fabricated backward activity |
| GS-TX02 | Unchanged fresh awake observation | Checkpoint extension as approved, no extra session count |
| GS-TX03 | Transition to standby after unknown interval | No assumption exact state-change instant |
| GS-TX04 | LAN timeout, PSN still online | Physical status unknown when stale, not OFF |
| GS-TX05 | PSN reports game but no physical console mapping | Account-scoped fact only, no local console time |
| GS-TX06 | Same UUID/payload submitted repeatedly | Single committed fact/segment effect |
| GS-TX07 | Same UUID, conflicting digest | Reject conflict and preserve original |
| GS-TX08 | SQL failure after observation but before event | Entire transaction rollback |
| GS-TX09 | SQL failure after segment mutation before checkpoint | No partial segment or false cursor |
| GS-TX10 | SQL failure before final commit cursor | Entire unit atomic |
| GS-TX11 | COMMIT succeeds but async await cancelled | Existing receipt found, no duplicate duration |
| GS-TX12 | COMMIT actually rolled back after process crash | Retry same stable source fact under generation fence |
| GS-TX13 | Old entry generation sends late UDP observation | Rejected for durable write |
| GS-TX14 | Two consoles interleave source sequences | Per-owner ordering and one shared commit cursor |
| GS-TX15 | One console identity conflict, another healthy | Healthy scope continues, conflict fenced |
| GS-TX16 | Source timestamp jumps backward | Quality/gap, no negative segment |
| GS-TX17 | Source timestamp jumps forward several hours | Coverage not automatically filled |
| GS-TX18 | Open session after HA process crash | Closes only at last durable checkpoint |
| GS-TX19 | Disk full during write | No false commit cursor; UNSAVED source status |
| GS-TX20 | SQLITE_BUSY under bounded queue | Backpressure, no endless retries |
| GS-TX21 | Reader examines during write | Sees committed state, no half-reducer projection |
| GS-TX22 | Source confidence inferred/ambiguous | Persist confidence, no confirmed label |
| GS-TX23 | Multiple game candidate titles in one presence | No accidental first-game physical assignment |
| GS-TX24 | Recovery restore changes ledger lineage | Old run callbacks fenced and corrections audit intact |

### 4.3 Timezone, statistics, provider separation and metadata — 24 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| GS-RP01 | Console interval crosses local midnight | Correct day allocation without duplicate boundary |
| GS-RP02 | Europe/Lisbon autumn DST change | Two UTC elapsed hours remain two hours, local labels correct |
| GS-RP03 | Europe/Lisbon spring DST change | Nonexistent wall hour not fabricated |
| GS-RP04 | Leap day interval | Correct Feb 29 and month/year totals |
| GS-RP05 | Session exactly ends at period start | No contribution to next period |
| GS-RP06 | Half-open zero-duration event | Zero counted duration, counts policy explicit |
| GS-RP07 | Local month to date | Incomplete period identified vs full prior month |
| GS-RP08 | Rolling 12 months vs 365 days | Correct chosen window semantics |
| GS-RP09 | Two consoles play simultaneously | Sum of device hours may exceed elapsed wall time |
| GS-RP10 | All-console wall-clock union requested | Separate union computation, never same as device-hours |
| GS-RP11 | Two players on one console, ambiguous | No double billing of same exclusive console awake |
| GS-RP12 | Provider lifetime duration available | Display separately, no local session addition |
| GS-RP13 | Provider duration unit unknown | Preserve raw unit/unknown, no invented seconds |
| GS-RP14 | Account entitlement exists, no play evidence | No session/installed/owned permanently inference |
| GS-RP15 | Game title localized rename | Historical segment identity remains stable |
| GS-RP16 | Artwork URL removed/expired | Historic game time preserved, placeholder displayed |
| GS-RP17 | No linked PSN account, LAN observations | Console awake report remains usable |
| GS-RP18 | Missing title on supported gameplay report | Unattributed/unknown title not silently "no gaming" |
| GS-RP19 | Unknown network gap overlaps report range | Excluded from bounded seconds; completeness reported |
| GS-RP20 | Reopened old session with stale last checkpoint | No extension to current wall time |
| GS-RP21 | Active days counted by positive covered duration | Mere point sample does not imply full active day |
| GS-RP22 | Same cursor/policy/timezone repeated query | Bit-identical deterministic totals |
| GS-RP23 | New committed event invalidates optional report cache | Correct key/cursor/zone invalidation |
| GS-RP24 | Revise inferred attribution | No silent change to raw source; policy/versioned rerender |

### 4.4 Backup, privacy, scale and future upgrades — 24 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| GS-OS01 | Explicit new installation with unique staged genesis | V1 schema validates before active pointer |
| GS-OS02 | Existing DB path missing | mode=rw non-creating failure, RECOVERY_HOLD |
| GS-OS03 | Schema newer than installed code | Guarded no downgrade/no empty replacement |
| GS-OS04 | Normal new-app v1->v2 migration after actual data | Snapshot and atomic/recoverable transition |
| GS-OS05 | Interrupt during future schema migration | No half-applied schema / orphan reference |
| GS-OS06 | Backup snapshot generated with concurrent write | Self-contained validated snapshot and cursor |
| GS-OS07 | Foreign-key_check returns violations on restored DB | Recovery rejects candidate |
| GS-OS08 | integrity_check returns corruption | Preserve originals and report error |
| GS-OS09 | Live WAL version affected by 2026 reset bug | Runtime selection gate/fallback required |
| GS-OS10 | Unpatched/unsupported local filesystem | WAL not silently enabled |
| GS-OS11 | Restoring older backup discards newer commits | Honest as-of cursor and UNKNOWN time |
| GS-OS12 | Clone same ledger UUID but diverged fork | No largest-cursor auto-merge |
| GS-OS13 | HA entity ID or Config Entry ID changes | No durable history identity change |
| GS-OS14 | User deletes one physical console entry | Historical FK parent/evidence still available |
| GS-OS15 | User requests history purge | Explicit ACL and backup/snapshot warning; no casual cascade |
| GS-OS16 | Generic diagnostics output | No raw provider IDs/tokens, private timelines or DB paths |
| GS-OS17 | Large 36-month deterministic synthetic observations | Queries/indexes benchmarked, no invented latency target |
| GS-OS18 | 1/2/4/8 console synthetic concurrency | One writer, owner-scoped and bounded memory |
| GS-OS19 | Every 30-second heartbeat persisted under heavy workload | Measured storage/backup/retention trade-off |
| GS-OS20 | EXPLAIN QUERY PLAN missing/inefficient indexes | Index revisions evidence-based |
| GS-OS21 | SQLite PRAGMA optimize on supported version | Bounded, verified benefit or skip |
| GS-OS22 | Cache invalidation on restored generation | No stale aggregate totals |
| GS-OS23 | User uninstalls new integration code | Data retention policy honored, no accidental SQL purge |
| GS-OS24 | Independent PSN module disabled/unavailable | LAN-based reporting/SQLite core still usable |

**Total: 96 newly enumerated test cases** (24 schema, 24 transaction, 24 reports, 24 OS/privacy). All NOT_RUN; overlaps with earlier SPEC-008 through SPEC-018 are intentional. This is a catalogue, not executable test coverage.

## 5. Sign-off gates — 24 OPEN

| Gate | Evidence | Status |
| --- | --- | --- |
| GS-G01 | Maintainer approves core logical tables and optional modules | PROPOSED |
| GS-G02 | Physical v1 DDL field types/constraints reviewed | NOT_RUN |
| GS-G03 | Actual HA OS linked SQLite version and STRICT compatibility | BLOCKED_HA_OS |
| GS-G04 | PRAGMA foreign_keys ON verified on every connection | NOT_RUN |
| GS-G05 | Explicit NOT NULL/unique/check including NULL edge cases | NOT_RUN |
| GS-G06 | Console/account/title independent owner namespaces | BLOCKED_HARDWARE |
| GS-G07 | FK relationship and no history cascade-delete | NOT_RUN |
| GS-G08 | Source observations append-only and idempotent | NOT_RUN |
| GS-G09 | One transaction fact/event/segment/gap/checkpoint/cursor | NOT_RUN |
| GS-G10 | Ambiguous COMMIT after cancellation reproducibly reconciled | NOT_RUN |
| GS-G11 | Late generation and wrong-owner callbacks fenced | NOT_RUN |
| GS-G12 | One open exclusive awake segment per console; closed overlap validation | NOT_RUN |
| GS-G13 | UTC integer precision, half-open interval validation | NOT_RUN |
| GS-G14 | Unknown gaps and source trust accounted honestly | NOT_RUN |
| GS-G15 | PSN account presence vs local gameplay attribution separated | BLOCKED_API_AUTH |
| GS-G16 | Provider playtime/entitlement units isolated and permitted | BLOCKED_API_AUTH |
| GS-G17 | Title identity and localized artwork independent | NOT_RUN |
| GS-G18 | DST/week/month/rolling report correctness | NOT_RUN |
| GS-G19 | Deterministic reports and cache invalidation by cursor/policy | NOT_RUN |
| GS-G20 | Realistic 3-year multi-console query/ingest/backup benchmarks | NOT_RUN |
| GS-G21 | SQLite WAL/worker/backup local filesystem safety | BLOCKED_HA_OS |
| GS-G22 | First genesis and future new-app schema migration recovery | NOT_RUN |
| GS-G23 | Privacy/ACL, retention, secure export and no Sony secrets | NOT_RUN |
| GS-G24 | Approved ADR and executed HA OS/synthetic release evidence | OPEN |

**All gates remain open and none of the 96 tests has been run.** This is not an official Home Assistant integration quality certification.

## 6. DDL and implementation guard

Only after maintainer approval and version/platform gates may a dedicated implementation work package create SQL migration files, repository interfaces or test fixtures. No SQL statement is emitted as executable code by this research. Do not use legacy develop App schema, App SQLite test records, MQTT integration data, HA Recorder internal tables, OAuth secrets or game artwork binary as the history ledger.

If an exact physical table differs from logical entities for measured performance reasons, preserve these invariants and explicitly update the ADR and spec, rather than silently introducing unexplained denormalization.

## 7. Sources

- [Research audit](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md)
- [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md)
- [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- https://www.sqlite.org/foreignkeys.html
- https://www.sqlite.org/lang_createtable.html
- https://www.sqlite.org/stricttables.html
- https://www.sqlite.org/partialindex.html
- https://www.sqlite.org/lang_upsert.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/lang_analyze.html
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/db_schema.py

**Outcome:** 96 NOT_RUN case descriptions and 24 OPEN gates; no DDL, code, SQLite file, migration or tests created.
