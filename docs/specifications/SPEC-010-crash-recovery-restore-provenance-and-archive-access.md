# SPEC-010 — Crash recovery, restoration provenance, WAL version and archive-only access

**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_IMPLEMENTATION_AUTHORIZED
**Date:** 2026-11-06
**Sources:** [Official-source recovery audit](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md); Home Assistant Core 2026.11.0; Supervisor SHA 69848689a1e982ebe92d80e344fc086d8af667db; upstream SQLite.
**Related:** [SPEC-009](SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md), [SPEC-008](SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md), [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md), [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md).
**Branch:** main documentation; develop frozen.

> These are proposed internal acceptance contracts, not Home Assistant platform requirements or passed tests. Do not change ADR status, choose a production DB schema or start coding without maintainer approval.

## 1. Purpose

Specify the evidence to prove that the future PlayStation Hub does not double count gaming/console durations, silently erase valid history or promote the wrong SQLite backup after crashes, upgrades, power loss, Home Assistant OS restore or the removal of the last console.

No additional MQTT, external database server, PS5-MQTT app, or multiple panels. Use one manager-owned writer and independently owned console/account entries as described in SPEC-009.

## 2. Core correctness invariants

| Invariant | Proposed MUST property |
| --- | --- |
| R1 Atomic source | An accepted observation, its reducer effect, gap/segment changes and durable checkpoint commit together |
| R2 Idempotency | A retry with the same observation UUID cannot create another billed second or another segment |
| R3 Lost acknowledgement | Client cancellation after SQL COMMIT cannot lead to an ambiguous double write |
| R4 Generation | Old runtime/entry generations cannot append new evidence after they have been fenced |
| R5 Timeline | No seconds may be fabricated between last committed evidence and first new observation after restart or restore |
| R6 SQLite ownership | No premature writer reopen, no manual WAL deletion, no stale DB connection remaining across restore |
| R7 Version | Actual linked SQLite (not Python version alone) is checked against WAL-reset bug fixes and backports |
| R8 Backup | Archive contains one unequivocally restoreable application database source or an approved tested selection mechanism |
| R9 Provenance | A valid snapshot manifest alone never authorizes overwriting a valid live DB at normal startup |
| R10 Restore | New/old backup schema, ledger identity, digest, integrity, FK and cursor must be validated |
| R11 Retention | Removing an entry or panel never means implicitly deleting persistent history |
| R12 Privacy | History snapshots and diagnostics contain no PSN tokens or Remote Play secrets |
| R13 UI | Display distinguishes current observation, last durable history, restored-as-of and unknown gap |
| R14 Recovery hold | Uncertain or corrupted state preserves evidence and fails closed rather than creating a blank ledger |

## 3. Proposed transaction/recovery boundaries

Every admitted write carries its stable observation UUID, canonical console/account key, entry generation, source sequence, source timestamp and accounting policy. The DB transaction creates its own durable cursor in the same atomic unit as observation and session changes.

A caller awaiting a COMMIT that may have succeeded must check the existing committed receipt before retrying. A new runtime epoch is established after startup. The old session is closed only at the latest durably supported boundary; UNKNOWN elapsed time after that boundary cannot be counted as awake, standby or gaming.

Normal startup loads the *live* SQLite file through SQLite native recovery. A leftover backup snapshot is not automatically promoted. If the live ledger cannot be trusted, enter RECOVERY_HOLD, preserve all existing files and demand approved restore intent or user-confirmed action.

## 4. Snapshot and restore protocol candidates

Candidate A (quiesced file backup): pre-backup fences new SQL operations, drains, checkpoints, closes **all connections**, and keeps DB files invariant until Supervisor finishes copying and runs post-backup. Measure how long monitoring becomes unavailable and mark gaps. Ensure the desired DB path is included in the archive.

Candidate B (Online Backup): create a validated immutable snapshot + manifest; live DB continues writing. The archive may also contain raw live db/wal files. Until a trusted one-shot restore-intent/provenance mechanism exists, do NOT automatically promote the snapshot in ordinary startup.

Manifest candidate: format_version, snapshot_uuid, ledger_uuid, schema_version, accounting_policy_version, committed_cursor, timestamp_utc, payload size, sha256, internal snapshot filename, source SQLite version and success/completion flag. Snapshot+manifest must form an archive-valid pair. An archived SQLite history database is not an authentication secret store.

A restore request uses exclusive controller fence and requires no active SQLite connections. Read-only validate candidate first, preserve current files, verify ledger/domain continuity and only then promote one authorized candidate atomically under a tested filesystem strategy. Reopening it starts a new runtime lineage and creates UNKNOWN intervals. Do not automatically merge histories by IP, username or console display name.

## 5. Synthetic test design and evidence requirements

Future tests must use fault-injecting SQLite workers, deterministic fake runtime clocks, synthetic console/account identities, controlled source events and generated archives. Inject faults at transaction boundaries, backup pre/post phases, whole-folder restore, cancellations and restart. A real HA OS exercise must inspect extracted backup member names and restored filesystem. Tests defined here are unrun.

### 5.1 Transaction and acknowledgement — 12 NOT_RUN

| ID | Scenario | Expected acceptance |
| --- | --- | --- |
| CR-TX01 | Failure before SQL BEGIN | No durable evidence or cursor advance |
| CR-TX02 | Failure after observation INSERT before segment update | Transaction rollback; no orphan event |
| CR-TX03 | Failure after segment update before durable cursor | No partial segment or credit |
| CR-TX04 | Failure during COMMIT | Reopen and reconcile either committed or not, never half committed |
| CR-TX05 | COMMIT succeeds but callback gets cancelled | Lookup returns existing receipt |
| CR-TX06 | Retry same UUID 10 times | Exactly one accepted durable effect |
| CR-TX07 | Same UUID submitted with conflicting payload | Reject conflict; never silently reinterpret |
| CR-TX08 | Two consoles interleave commits | Correct owner keys and per-owner order |
| CR-TX09 | Late old-generation observation | Rejected as new write; existing committed history retained |
| CR-TX10 | Worker queue full during commit | Classified UNSAVED, bounded memory, no fake totals |
| CR-TX11 | SQLITE_FULL/IOERR/READONLY | Durable cursor not fabricated; recovery hold/degraded as appropriate |
| CR-TX12 | Constraint error on non-UUID column | Genuine model error distinguished from idempotent duplicate |

### 5.2 Startup and crash timeline — 12 NOT_RUN

| ID | Scenario | Expected acceptance |
| --- | --- | --- |
| CR-ST01 | Clean Home Assistant stop with console awake | Close at last bounded evidence; no shutdown-time backfill |
| CR-ST02 | Crash with open WAL transaction | SQLite recovery yields consistent original/committed state |
| CR-ST03 | Hard-kill after successful receipt | Committed event and cursor preserved when durability permits |
| CR-ST04 | Power-loss simulation under WAL NORMAL vs FULL | Measured durability difference; no unqualified guarantee |
| CR-ST05 | Restart 4 hours after last awake sample | Four-hour gap UNKNOWN; no invented active minutes |
| CR-ST06 | First post-restart console still awake | Starts fresh supported interval, cannot bridge old gap |
| CR-ST07 | First post-restart console standby | Last-known awake not retrospectively extended |
| CR-ST08 | UTC clock moves backward across restart | Negative elapsed time prevented; uncertainty indicated |
| CR-ST09 | UTC jumps forward while run active | Clock anomaly flagged; bounded evidence only |
| CR-ST10 | Existing DB cannot open | Must not be replaced with a new empty database |
| CR-ST11 | Old migration transaction interrupted | Schema not half updated, no destructive upgrade |
| CR-ST12 | 100 restarts and retries of same synthetic observations | Stable repeatable totals, no duplicate segments |

### 5.3 Backup, provenance and Supervisor restore — 14 NOT_RUN

| ID | Scenario | Expected acceptance |
| --- | --- | --- |
| CR-BK01 | Supervisor pre-backup handler invoked | Actual integration hook registration evidenced on target HA OS |
| CR-BK02 | Generic Core backup path | Separately verified; not conflated with Supervisor |
| CR-BK03 | Quiescence A, restore from same archive | Consistent main DB, all connections closed during archive |
| CR-BK04 | A pre-backup hook times out | Backup fails clearly or returns classified unsafe state; never false success |
| CR-BK05 | A backup lasts several minutes | Monitoring/unsaved gaps bounded and explicitly represented |
| CR-BK06 | Online snapshot B while writes continue | Snapshot and manifest agree on durable cursor and integrity |
| CR-BK07 | B's raw live database/WAL also included | Restore selector refuses ambiguous raw candidate |
| CR-BK08 | Snapshot file partially written / absent | Manifest cannot falsely promote incomplete package |
| CR-BK09 | sha256 mismatch | Reject, preserve both candidate and live DB |
| CR-BK10 | Snapshot has foreign-key violation | Reject even if SQLite file opens and hash matches |
| CR-BK11 | Snapshot schema newer than code | Guarded unsupported/read-only, no downgrade |
| CR-BK12 | Normal reboot after snapshot cursor 100, live cursor 180 | Keep valid live 180, never auto-rewind to 100 |
| CR-BK13 | Actual Supervisor full restore from old backup | Recognize historic cursor and unknown gap; no fake post-backup minutes |
| CR-BK14 | Partial Supervisor restore excluding Home Assistant | No claim that the PlayStation Hub database was restored |

### 5.4 Archive access and UI policy — 10 NOT_RUN

| ID | Scenario | Expected acceptance |
| --- | --- | --- |
| CR-UI01 | One console disabled but entry exists | Panel semantics match approved configured-vs-loaded policy |
| CR-UI02 | Two console entries, one removed | Other console + shared panel/history survive |
| CR-UI03 | Last console removed; DB retained | No implicit cascade deletion or unexpected file purge |
| CR-UI04 | Restart with zero Config Entries | UI behavior matches approved archive-access policy |
| CR-UI05 | Only one PSN account entry remains | Account history and per-scope ACL survive |
| CR-UI06 | Hub/Archive Config Entry candidate enabled | One panel, no duplicate registration or LAN monitor |
| CR-UI07 | Hub/Archive entry removed | Archive retention/export/delete policy explicit |
| CR-UI08 | HACS source uninstalled and reinstalled | No unapproved data loss or ownership reassignment |
| CR-UI09 | Two browser users, one unauthorized | No unauthorized private history leaks |
| CR-UI10 | Restored old account/console association | History remains attributed only to validated canonical identity |

### 5.5 SQLite version and low-level recovery — 8 NOT_RUN

| ID | Scenario | Expected acceptance |
| --- | --- | --- |
| CR-SQL01 | Actual linked SQLite 3.51.2 without backport | WAL risk gate fails or mitigation explicitly selected |
| CR-SQL02 | Fixed SQLite 3.51.3+ | Correct fixed-version classification, not proof of overall safety |
| CR-SQL03 | Fixed backports 3.44.6 and 3.50.7 | No naive numerical-version false positive |
| CR-SQL04 | Unexpected second checkpoint connection | Single-checkpointer invariant enforced |
| CR-SQL05 | Active DB-wal copied alone | Treated as unsafe backup candidate, not trusted restore |
| CR-SQL06 | Manual WAL deletion with active DB | Prohibited behavior verified by safety assertions |
| CR-SQL07 | Quick check passes but FK integrity fails | Restore gate correctly rejects |
| CR-SQL08 | WAL vs rollback-mode alternate backend | Benchmark + recovery semantics evaluated on HA OS |

**Total: 56 tests** (12 TX + 12 startup + 14 backup + 10 UI + 8 SQLite). All NOT_RUN. Some intentionally refine SPEC-009's 56 scenarios and SPEC-008's 46; deduplicate eventually rather than summing as unique executable tests.

## 6. Product states and user-visible semantics

| State | What may be reported | What must not be reported |
| --- | --- | --- |
| RUNNING_DURABLE | Latest observed source status plus committed-as-of cursor | Uncommitted provisional time as stored historical seconds |
| RUNNING_UNSAVED | Live console status when valid, clearly marked missing history | Claim that a network probe was durably stored |
| RESTORED_FROM_SNAPSHOT | Snapshot time/cursor, missing coverage, new runtime identity | Missing post-backup time as known play |
| RECOVERY_HOLD | Preserved file existence and sanitized error class; admin repair path | Empty new DB as though original had no history |
| ARCHIVE_ONLY | Read-only reports for validated authorized scopes | Power control or current freshness with no console runtime |
| NO_ENTRIES | Explicit configured-vs-loaded panel behavior | Guaranteed menu persistence after reboot without an owning entry |

## 7. Approval gates — 14 OPEN

| Gate | Required evidence | Status |
| --- | --- | --- |
| CR-G01 | Linked SQLite version and WAL-reset fix/backport verified on target HA OS | BLOCKED_HA_OS |
| CR-G02 | Atomic event/segment/cursor write and stable idempotency receipt | NOT_RUN |
| CR-G03 | Ambiguous COMMIT acknowledgement and cancellation rechecked after restart | NOT_RUN |
| CR-G04 | Old open sessions close only at bounded evidence; gap continuity | NOT_RUN |
| CR-G05 | Actual hardware/filesystem WAL FULL durability and alternatives benchmarked | BLOCKED_HA_OS |
| CR-G06 | Custom backup platform registered and pre/post invoked on HA OS | BLOCKED_HA_OS |
| CR-G07 | Chosen A or B archive strategy yields consistent SQLite and stable copies | PROPOSED |
| CR-G08 | Signed-off restore provenance, selector and fail-closed ambiguity policy | PROPOSED |
| CR-G09 | Distinct normal restart vs historical backup restore proven | NOT_RUN |
| CR-G10 | Full and partial Supervisor filesystem effects checked on target HA OS | BLOCKED_HA_OS |
| CR-G11 | Schema/hash/integrity/FK/ledger-cursor checks validated | NOT_RUN |
| CR-G12 | Admin-only recovery/export workflow and secret segregation | NOT_RUN |
| CR-G13 | Zero-entry archive access policy selected and tested across reboot | PROPOSED |
| CR-G14 | No automatic delete/recreate, credible corrupt-file repair path | NOT_RUN |

## 8. No-code approval considerations

The document may be accepted as a **test plan only** without accepting underlying SQLite, WAL, restore or zero-entry implementation choices. Core 2026.11.0 is the source baseline, not an approved minimum Home Assistant version. Never introduce executable code, empty placeholder files or a feature branch from this research. All code/comments/documentation subsequently created must be in English, modular, privacy-safe and extensible.

## 9. Sources

- [Research findings and alternatives](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md)
- [Shared service lifecycle tests](SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md)
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/howtocorrupt.html
- https://www.sqlite.org/changes.html
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Outcome:** 56 unrun cases, 14 open gates, no code or tests performed.
