# PlayStation Hub — SQLite crash recovery, backup provenance and archive-only access

**Review:** 2026-11-06 | **Status:** SOURCE_RESEARCH / PROPOSED / NOT_IMPLEMENTED / NOT_TESTED
**Pinned sources:** Home Assistant Core 2026.11.0; Supervisor commit 69848689a1e982ebe92d80e344fc086d8af667db; official SQLite and Python documentation.
**Branch:** main documentation only; legacy develop untouched.
**Related:** [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md), [SPEC-009](../specifications/SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md), [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md), [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md).

> Evidence classes: SQLITE_OFFICIAL, PYTHON_OFFICIAL, CORE_PINNED, SUPERVISOR_PINNED, PROJECT_PROPOSAL and OPEN. Upstream source inspection does not prove this custom integration works or has passed HA OS testing.

## 1. Findings: crash recovery is not backup restore

- SQLite can atomically commit or roll back a transaction and usually automatically recovers journal/WAL state when reopening after a crash. This differs from restoring an old HA backup, which **replaces files** and may rewind application history.
- A callback may lose its COMMIT acknowledgement even though COMMIT succeeded. Blindly retrying a derived "add seconds" operation can duplicate history.
- A snapshot plus checksum proves neither freshness nor that a restore happened. Automatically applying a leftover backup snapshot on **every normal restart** can destroy newer history.
- Python version does not guarantee a safe linked SQLite version. The upstream **WAL-reset corruption bug** existed through 3.51.2 and was fixed in 3.51.3 (2026-03-13) and backports 3.44.6 / 3.50.7. It requires multiple SQLite connections with precisely overlapping writer/checkpointer operations.
- Supervisor's "exclude database" filters apply to named Home Assistant Recorder database files, NOT arbitrary application DBs. A PlayStation Hub SQLite file inside /config may be copied even with Recorder DB excluded.
- A history DB and its WAL copied independently during live writes are not a verified, application-consistent archive. The separate Online Backup API is a candidate safe snapshot producer, but authoritative selection on restore remains unsolved.
- One integration with zero configured entries is not guaranteed to have its sidebar panel loaded after reboot. Historical data retention and archive browsing are separate product requirements.

## 2. Upstream evidence table

| ID | Classification | Verified source fact | PlayStation Hub consequence |
| --- | --- | --- | --- |
| REC-01 | SQLITE_OFFICIAL | Transactions are atomic; multiple readers, one simultaneous writer | Observation, segment changes and cursor must share a transaction |
| REC-02 | SQLITE_OFFICIAL | WAL carries recovery data; copying/deleting a hot WAL can corrupt | Let SQLite reopen/recover; never manually delete WAL to repair |
| REC-03 | SQLITE_OFFICIAL | WAL NORMAL may lose COMMIT durability after power loss; FULL syncs per commit | Benchmark FULL; no untested performance trade-off |
| REC-04 | SQLITE_OFFICIAL | Online Backup API generates consistent snapshots from live DB | Candidate for immutable staged archive copy |
| REC-05 | SQLITE_OFFICIAL | quick_check is weaker than integrity_check; foreign_key_check is separate | Layer integrity, FK and domain/provenance checks |
| REC-06 | SQLITE_OFFICIAL | WAL-reset bug fixed in 3.51.3 and specific backports | Verify linked library, writer/checkpointer ownership |
| REC-07 | PYTHON_OFFICIAL | Python sqlite3 wraps SQLite C library and exposes Connection.backup | Verify actual sqlite3.sqlite_version on HA OS |
| REC-08 | CORE_PINNED | backup/start, backup/end invoke BackupManager integration pre/post hooks | Check custom backup platform discovery in future tests |
| REC-09 | SUPERVISOR_PINNED | Supervisor HomeAssistant.backup sends begin/end around config archive | Source-confirmed notification chain, not runtime proof |
| REC-10 | SUPERVISOR_PINNED | Restore clears config contents, then copies backed-up tree | Newer ledger files may be replaced by older ones |
| REC-11 | SUPERVISOR_PINNED | Exclude DB names target Recorder DB and Recorder WAL | Custom history inclusion independent of this checkbox |
| REC-12 | SUPERVISOR_PINNED | Default archive filter excludes *.db-shm, not custom DB/-wal | Full HA archive may contain mismatched live files |

## 3. Crash/recovery taxonomy and receipts

| Incident | Safe interpretation | Prohibited assumption |
| --- | --- | --- |
| Graceful HA stop | Stop observations, settle accepted writes, close at last durable evidence | "HA stop time = PlayStation off time" |
| Process crash | SQLite rollback/WAL recovery on reopen; validate schema and cursor | All previously scheduled commits succeeded |
| Hard power loss | FULL helps durability on supported storage; possible hardware/OS failures remain | Every in-memory observation was persisted |
| Commit succeeded but response lost | Lookup same stable observation ID and return existing receipt | Retry as a fresh additive event |
| DB full/readonly/IO error | Degraded or UNSAVED; clear gap; preserve originals | Create an empty DB automatically |
| Corrupted/incompatible schema | Non-destructive recovery hold, read-only when safe | Drop files, delete WAL, auto-downgrade |
| Old HA backup restored | Restore has older committed cursor; later time is not observed | Backfill missing gaming minutes |
| Clock NTP jump | Monotonic timestamps only meaningful within one runtime | Subtract monotonic across HA restarts |

## 4. Atomic logical write proposal

A durable operation includes: ledger_uuid, canonical_console_or_account_key, observation_uuid (stable for retries), runtime_run_uuid, entry_generation, per-owner source sequence, accepted UTC, source evidence/freshness, derived state/session transitions and unknown gaps, accounting policy revision, and a DB-managed monotonic commit cursor.

One writer owns the SQL transaction: insert evidence with unique observation UUID, apply idempotent segment/gap transitions, advance per-owner high water and global durable cursor, then COMMIT. Nothing becomes labelled DURABLE before definite commit. The cursor must not be a volatile number outside the SQL transaction.

If awaiting a writer is cancelled after its COMMIT, a retry checks whether the same observation UUID already has a stored receipt and reuses it; it must not invent a different UUID for the same event. A stale entry generation cannot commit new observations after reconfigure, but previously admitted and committed evidence remains.

Reconstructed summaries use half-open UTC intervals and source-specific union/dedupe rules from ADR-0006; do not increment an independent cumulative counter on every replay.

## 5. Startup sequence and physical time

**PROJECT_PROPOSAL:** At startup, resolve the intended database path, **never create an empty database if an existing one failed verification**, let SQLite recover its own WAL, verify schema version/ledger UUID/transaction cursor, perform chosen integrity and foreign-key checks, reconcile open previous-runtime segments only up to last committed evidence, mark a genuinely unobserved interval UNKNOWN, start a fresh runtime generation, then admit new observations. An old monotonic clock value is not comparable across runs; corrected UTC/NTP jumps are also uncertainty, not proof of power transitions.

Normal light health checks may use quick_check; restore/repair approval requires stronger integrity_check and foreign_key_check, plus checks of domain keys, expected cursor and schema. Note: hash/integrity validation cannot detect every semantically wrong but internally valid record.

## 6. Critical 2026 SQLite WAL-reset bug

[SQLite WAL upstream](https://www.sqlite.org/wal.html) documents a rare corruption race where one connection checkpoints while another commits and resets WAL. Versions affected likely span 3.7.0–3.51.2, excluding backported fixes; fixes in 3.51.3+, 3.44.6, 3.50.7. This is a correctness gate rather than an assertion about the user's HA OS version.

**Proposed requirements:** query the actually linked SQLite version via Python sqlite3 / SELECT sqlite_version(), consult the upstream fixed release matrix, guarantee only one writer/checkpointer authority (including automated checkpoints and backup workers), constrain concurrent connections, and test the final connection library under the actual HA OS image. If running vulnerable SQLite cannot be avoided, compare a rollback-journal alternative rather than blindly enabling WAL. Never silently replace HA OS system libraries.

## 7. Consistent backup design options

| Option | Mechanism | Benefit | Cost/blocker | Status |
| --- | --- | --- | --- | --- |
| A — full quiescence | On pre-backup, fence new SQL writes, drain, checkpoint and close every DB connection; keep DB immutable until post-backup | Single stable main DB copied by Supervisor | Multi-minute archive pause, monitoring gaps/queues, post-hook failure, precise timeouts | Candidate initial proof |
| B — Online Backup API | Snapshot to immutable staged file and manifest while live writer resumes | Small writer pause, live operation continues | Raw live DB/WAL may also be copied, cannot blindly choose snapshot on next boot | Preferred future, blocked on authority |
| C — app live store outside archived config, staged snapshot inside | Cleanly separates source from archive | Avoids raw live DB copies | Persistent supported HA OS path and recovery semantics unverified | OPEN |
| D — raw active db/-wal copy | Rely on Supervisor copying each file while app writes | No implementation cost | Can be inconsistent, no restore guarantee | REJECTED |
| E — manual export/import | Controlled app-specific package | Explicit provenance | Not automatic HA backup | Fallback option |

**Do not automatically claim option A or B is production-ready.** A must enforce a complete write freeze throughout archive, and ensure that all connections are actually closed. B must prove a trusted one-time restoration intent or user-approved import, and source/backup file separation.

## 8. Manifest and snapshot provenance proposal

Versioned snapshot package candidate: snapshot_uuid, ledger_uuid, snapshot_schema_version, accounting_policy_version, creation_utc, durable_cursor, last_evidence_cursor, source_runtime_sqlite_version, fixed relative snapshot basename, snapshot_file_bytes, sha256, validation_success, optional upstream backup identifier ONLY IF API exposes it.

A sha256 hash checks accidental mismatches but is not proof of authentic origin if attacker can replace both files. Snapshot creation must finish, validate, sync/rename as supported, then publish a completed manifest; an incomplete snapshot must never look complete. Secrets remain outside public history export. Both snapshot and manifest must appear in actual archive.

The pre/post hook contract in Core is source-confirmed. **No evidence yet that hook arguments include the Supervisor backup job ID**; do not fabricate such a correlation.

## 9. Snapshot selection must distinguish normal restart from restore

**Counterexample:** snapshot S at cursor 100 is created at noon. Live monitoring subsequently commits to cursor 180. A normal HA restart at 19:00 still finds S100 on disk. If the system blindly "restores the latest valid snapshot" on any startup, it silently deletes 80 confirmed commits.

**No silent restore policy:**
1. On normal startup, prefer *valid live database* via SQLite recovery; never automatically replace it solely because a snapshot exists.
2. If the live DB fails validation, preserve originals, enter explicit recovery hold and require a verified restore mechanism or user action. Never automatically overwrite it with an older snapshot.
3. If an actual restore is provably invoked, verify snapshot/manifest, domain lineage and schema before exclusive, fenced promotion.
4. Promote only with no open DB connections, preserving the original live files and failed candidates for inspection; consume a one-time restoration intent.
5. Record new restore_generation and UNKNOWN gap after the snapshot's last evidence. Revalidate physical identities/accounts before new write attribution.
6. Do not presume a Core-specific .HA_RESTORE marker will exist for a Supervisor-based restore. The official Core restore path is separate and does not prove a universal, integration-visible restore event.

An archived copied live DB may pass a basic integrity check yet disagree temporally with a separately staged snapshot. Simply picking the candidate with the greatest cursor is not a rigorous source-of-truth protocol.

## 10. Supervisor full vs partial restore — pinned source

At Supervisor commit 69848689, HomeAssistant.restore extracts the backup, clears the config content (or preserves files matching Recorder-specific exclusions when exclude_database is true) and copies the archived tree with shutil.copytree. Full restore includes HA config; partial restore may choose not to restore Core config.

Implications: restored PlayStation Hub ledger may be older than what the user last observed; a backup with Recorder excluded does not necessarily exclude PlayStation Hub data; an app DB under /config may be replaced even when Recorder is preserved. An old restored source may contain valid metadata but stale console address/token values; separate credentials are governed by ADR-0007. Verify the exact installed Supervisor version and actual archive members before adopting a restore policy.

## 11. Errors, migrations, integrity and privacy

Classify BUSY/LOCKED (bounded retry), FULL/READONLY/IOERR (degraded/unsaved, no unbounded queue), CORRUPT/NOTADB (stop writes and preserve originals), SCHEMA/newer version (no destructive downgrade), CONSTRAINT (may be idempotent duplicate or genuine violation), and timeout after COMMIT (unknown acknowledgement until receipt lookup).

All backups and diagnostic exports may include sensitive gameplay histories: no raw private record dumps, credentials or file paths in public diagnostics. SQLite history ledger is not the Sony token store, and Home Assistant Recorder history is a separate data owner.

## 12. Archive-only product policy (OPEN)

| Condition | Expected behavior | Design trade-off |
| --- | --- | --- |
| Console asleep | Entry remains, history visible | Current power UNKNOWN or stale, not OFF by timeout |
| All runtimes unloaded but entries configured | Menu may remain if global integration loads | Evaluate disabled-entry setup and HA restart semantics |
| Last physical entry removed | History retained unless explicit purge | No entry may cause panel to disappear after Core restart |
| Only PSN account entries | Account-scoped history and menu still relevant | Account entry independently authorized |
| User uninstalls HACS integration | No executable UI, data policy explicit | Reinstall/import/export path needed |
| Restore old backup | Lineage and cursor verified; unknown coverage | No silent history reassignment to same IP |

Candidate **A**: panel follows at least one configured entry; archive restored only after setting up a new entry. Simpler but weak archive UX.
Candidate **B**: permanent explicit Hub/Archive Config Entry independent of console entries, providing archive access. More predictable multi-year UX but more flows, ownership and tests.
Candidate **C**: offline export/restore utility, distinct from one permanent panel.

No policy auto-deletes historical rows when the final monitor stops. Choice remains with maintainer; do not create a hub entry without approval.

## 13. Approval blockers

- Confirm actual linked SQLite library in target HA OS and WAL-reset backport status.
- Validate one-writer/one-checkpointer lifecycle and idempotent COMMIT receipts under fault injection.
- Test crash recovery at every transaction edge, clock rollback and no-history fabrication.
- Establish HA OS source-consistent backup design including WAL path and no lost raw-file authority.
- Find a trusted restore-intent mechanism, or approve fail-closed/manual restored snapshot selection.
- Verify full and partial HA restore file replacement, special Recorder DB exclusions and archive inclusion.
- Approve archive-only UI lifecycle and data-retention policy independently of entry reference counts.
- Do not equate SQLite checksum/quick_check with proof of correct historical attribution.

## 14. Primary sources

SQLite: https://www.sqlite.org/lang_transaction.html ; https://www.sqlite.org/wal.html ; https://www.sqlite.org/changes.html ; https://www.sqlite.org/backup.html ; https://www.sqlite.org/pragma.html ; https://www.sqlite.org/fileformat2.html ; https://www.sqlite.org/howtocorrupt.html ; https://www.sqlite.org/rescode.html

Python: https://docs.python.org/3.14/library/sqlite3.html

Core 2026.11: https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py ; https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py ; https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py ; https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py

Supervisor SHA: https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py ; https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py ; https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py

**Outcome:** Source evidence and explicit unapproved alternatives only. No program, tests, package, migration, PS5 hardware contact or HA OS restore was executed.
