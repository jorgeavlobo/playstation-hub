# Home Assistant 2026.11 — Immutable SQLite snapshots, archive ambiguity and recovery source audit

**Date:** 2026-11-06
**Status:** SOURCE_AUDIT / DESIGN_PROPOSAL / NOT_IMPLEMENTED / NOT_TESTED
**Pinned Home Assistant Core:** tag 2026.11.0
**Pinned Home Assistant Supervisor:** 69848689a1e982ebe92d80e344fc086d8af667db
**SQLite:** Official SQLite Online Backup API, WAL, URI, PRAGMA, VACUUM INTO, Python 3.14 sqlite3 documentation; consulted 2026-11-06.
**Repository:** jorgeavlobo/playstation-hub, main (documentation only); develop remains untouched.
**Linked:** [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md), [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md).

> Distinguish SOURCE_CONFIRMED from PROJECT_ACCEPTED and NOT_TESTED. Source evidence proves behavior of reviewed upstream code, not a working custom integration. Product-level approval on 2026-11-06 accepts the Hub/Archive entry, separate hardware entries, one panel and private HA-configuration-root design direction. It DOES NOT approve a specific backup implementation or claim safe automatic restores.

## 1. Executive outcome

**P0:** In the inspected Core/Supervisor backup implementations, there is **no documented custom integration pre/post hook return value to add an arbitrary application-specific file exclusion** to the Core configuration archive. The source archive filter is an internal list of patterns. Therefore a custom integration with a mutable SQLite file inside the backed-up configuration directory cannot assume a backup archive contains only its immutable snapshot. A copy of a live main DB and companion WAL may also be archived.

**P0:** Core backup manager calls all pre-backup platform hooks concurrently via asyncio.gather(return_exceptions=True). Supervisor HomeAssistant.backup awaits begin_backup BEFORE entering the try/finally that sends end_backup. If another platform fails after PlayStation Hub has frozen its database, no matching post hook is guaranteed. An indefinitely frozen database or unconditional timeout-based release is unsafe.

**P0:** The SQLite Online Backup API provides a consistent destination if the backup completes successfully. It allows interleaved source activity, but concurrent writes by other connections can restart a multi-step backup, so a bounded deadline and failure state are necessary. The source-destination handles must be distinct, destination exclusive during backup, and SQLite backup resources must be closed even on error/cancellation.

**P0:** A file-level immutable snapshot + a corresponding manifest can be prepared and published as a consistent artifact before the archive. However, neither a hash nor a completed snapshot indicates whether the host is undergoing an ordinary reboot or restoring an old Core configuration. Snapshot cannot be silently promoted over valid newer live data. Even if the snapshot is the only guaranteed coherent backup artifact, the live source also copied in an archive requires explicit authority on restore.

**P1:** A logical Hub/Archive Config Entry can keep the integration/backup.py platform loaded when consoles are absent; this is an approved product architecture direction, not implemented. One API, one panel, no Hub-owned LAN probe, and no second SQLite writer.

## 2. Source-confirmed facts — SQLite

| ID | Official source | Evidence | Design implication |
| --- | --- | --- | --- |
| IS-01 | sqlite.org/c3ref/backup_finish.html | Backup source and destination must use distinct DB connections; destination transaction held during copying | Dedicated worker-owned destination connection, not shared with normal readers |
| IS-02 | sqlite.org/backup.html | Online backup can copy incremental pages and permit source concurrent writing | Do not freeze app writes for whole backup if implementation supports source locking correctly |
| IS-03 | sqlite.org/c3ref/backup_finish.html | Source modified by other connection during incremental copy may restart the copy | Deadline, abort policy, source write rate and progress must be measured |
| IS-04 | sqlite.org/c3ref/backup_finish.html | SQLITE_BUSY/LOCKED can be retried, IOERR/READONLY/NOMEM are fatal; backup_finish required | Bounded error classification and cleanup |
| IS-05 | sqlite.org/uri.html | immutable=1 skips locking/change detection and is unsafe if target changes | Only inspect a **verified, truly immutable** completed artifact this way, never live DB |
| IS-06 | sqlite.org/pragma.html | WAL checkpoint can return busy; FULL vs NORMAL have different durability | Do not use checkpoint as a proxy for successful online backup; protect actual SQL runtime |
| IS-07 | sqlite.org/backup.html and sqlite.org/lang_vacuum.html | Online Backup and VACUUM INTO are separate consistent-copy options | Benchmark both as optional future candidate, do not assume identical lifecycle |
| IS-08 | Python 3.14 sqlite3 | Connection.backup(dest, pages, progress, sleep) exists; source may be live | Use an executor-owned worker; event loop must not block on synchronous backup |
| IS-09 | SQLite official WAL documentation | WAL-reset concurrency bug fixed in 3.51.3+ and 3.44.6/3.50.7 backports | Actual linked SQLite must be checked before WAL is relied upon |

**Important nuance about snapshot boundary:** A multi-step backup can restart as source writes occur. Do not assert that its committed cursor equals a value read from the live database before initiating backup. Open the FINISHED snapshot read-only, validate it and read the cursor from that snapshot itself after closing the backup destination connection. The cursor describes exactly the copied dataset, not the current live writer state.

## 3. Source-confirmed facts — Home Assistant backup integration

| ID | Source path and version | Verified behavior |
| --- | --- | --- |
| HA-IS01 | core/components/backup/manager.py 2026.11.0 | async_pre_backup_actions uses gather of all platform hooks and raises on any exception |
| HA-IS02 | core/components/backup/websocket.py 2026.11.0 | backup/start calls pre hooks; backup/end calls post hooks |
| HA-IS03 | supervisor/homeassistant/module.py pinned SHA | HomeAssistant.backup calls begin_backup outside try, then finally end_backup after archive |
| HA-IS04 | supervisor/homeassistant/module.py pinned SHA | Archive's HOMEASSISTANT_BACKUP_EXCLUDE contains fixed patterns, no documented pre-hook custom excludes |
| HA-IS05 | core/components/backup/const.py 2026.11.0 | Generic CoreBackupReaderWriter exclusions likewise fixed and Recorder-specific |
| HA-IS06 | supervisor/homeassistant/module.py pinned SHA | Restoring config deletes/copies selected Core config scope; preserve Recorder patterns only in excluded-DB case |
| HA-IS07 | core/helpers/integration_platform.py 2026.11.0 | Backup platform discovery follows loaded integration status |
| HA-IS08 | core/components/knx/backup.py 2026.11.0 | Existing KNX implementation holds writes during backup; it is a real upstream precedent, not proof every failure ordering is safe |
| HA-IS09 | core/components/recorder/backup.py 2026.11.0 | Recorder locks writes in pre and unlocks in post; same potential system-level notification dependency |
| HA-IS10 | contributors HA backup developer guide | Hooks async_pre_backup/async_post_backup are preparation/resumption APIs, not arbitrary file filter customization |

**Scope of absence claim:** no such facility was found in the reviewed public documented hook or the pinned Core/Supervisor archive filter. This is NOT a proof that every alternative third-party backup system forbids excludes; future HA versions or other app-level adapters can differ.

### 3.1 Critical filename mismatch

Pinned Supervisor and generic Core archive exclusions contain the pattern "*.db-shm", but not arbitrary "*.sqlite3-shm". Therefore an application naming its file "history.sqlite3" cannot assume that "history.sqlite3-shm" is omitted. Changing suffix to ".db" can match "* .db-shm" (without the space) but does **not** solve the WAL or active main DB consistency issue. No reliance on filename tricks as a backup strategy.

## 4. Snapshot preparation: recommended conceptual protocol

**Design only, not executable code:**

1. **Acquire snapshot job lease.** The process-global controller serializes snapshot-generation creation per ledger UUID. A second prehook joins same explicitly compatible request or is rejected with a classified conflict; do not overwrite a snapshot generation in progress.
2. **Check source.** Verify initialized compatible schema, private local filesystem, actual SQLite version and free space. If live manager is unloaded but persisted history exists, initialize read-only or a bounded safe snapshot worker, not a new empty ledger. Do not publish a successful archive entry if source is corrupt or unsupported.
3. **Reserve unique generation ID.** Use an opaque non-reusable snapshot_uuid, internal fixed relative file paths, and a PENDING object. No user-controlled filesystem paths, symlinks or externally supplied journal files.
4. **Prepare destination in an isolated staging directory.** Prefer a transient private directory excluded from backup (where supported), e.g. hass.config.cache_path for disposable in-progress files. The final committed history snapshots must NOT be stored in cache. Check the source/destination filesystems and support cross-device staging using an explicit safe-copy-then-publish process.
5. **Execute SQLite Online Backup API.** Use distinct connections, destination exclusive, controlled connection/thread ownership, bounded pages/locks, retries only for known transient errors, deadline and progress telemetry. Do not block HA event loop; concurrent source writes may cause restart and eventual timeout. A timeout does not imply source DB corruption.
6. **Finalize SQLite backup result.** Close destination correctly, ensure the final snapshot is a single self-contained SQLite DB (no mutable sidecar dependencies), and do not publish an incomplete backup. Do not delete/rename open WAL/SHM files manually; let SQLite close/reconcile normal destination state.
7. **Validate snapshot.** Check exact expected schema, ledger_uuid, foreign keys and SQLite integrity_check; read durable cursor from the **snapshot itself**, not from live writer after copying. Check accounting invariants and record immutable metadata. Snapshot validation must not modify snapshot.
8. **Build manifest.** Include format version, snapshot UUID, ledger UUID, source schema/version, policy revision, committed cursor, verified timestamp, size/sha256 and absolute risk classification. A hash detects byte mismatch only; no independent signature/trust claim.
9. **Publish all-or-nothing to final generation.** Use a generation-scoped directory with immutable files and an atomic final visibility barrier, e.g. same-filesystem directory rename after complete write+fsync. Cross-directory/device atomicity is NOT assumed: test atomic rename and directory fsync on actual HA OS storage.
10. **Return pre-backup success only after publication.** No need for a long-held global live write freeze; the final generation is immutable. If pre hook fails at any step, do not advertise a valid snapshot. Fail clearly under correct backup policy.
11. **Archive window.** The Supervisor may read all config files. Final generation and its manifest must remain byte-identical until the archive finishes; even if post hook is never delivered, there is no frozen writer to unstick. Never delete an in-use snapshot because an arbitrary retention timer elapsed during tar creation.
12. **Post-backup (best effort).** Release bookkeeping and observe status, not a mandatory "unlock all live writes". Failure or absence of post hook leaves an orphan but must not degrade runtime liveness. Cleanup must not remove a still-being-archived immutable generation.
13. **Retention and reconciliation.** Prune only completed old generations with a conservative explicit policy, with no known active archiver; keep at least one verified good copy subject to capacity and user choice. No unbounded artifact accumulation. An orphaned snapshot does not gain authority automatically.

### 4.1 Why incremental copy can starve

The official SQLite backup API may restart a multi-step transfer when the source is modified by another connection. A heavily written ledger or repeated metadata updates can prevent a bounded incremental snapshot from finishing. This suggests benchmarking single-step vs incremental copy, or a **brief bounded quiet window only for the source read barrier**, rather than holding a freeze throughout the entire Supervisor tar operation. A short, locally owned barrier is materially different from the unsafe cross-integration pre-to-post freeze; it must also be tested for backpressure and UI coverage.

### 4.2 Why source-side WAL checkpoint does not substitute

An application may successfully checkpoint its WAL into the main DB and then resume writing before the Supervisor copies the files. The main DB can change while being read. Thus even a checkpoint before backup/start is insufficient proof of a stable raw file copy unless the source remains quiesced. An immutable independent snapshot has a stronger contract.

## 5. Snapshot state machine (PROJECT_PROPOSAL)

    REQUESTED
       -> ALLOCATED
       -> COPYING
       -> FINALIZING
       -> VERIFYING
       -> PUBLISHING
       -> PUBLISHED
       -> ARCHIVE_CONSUMER_UNKNOWN / ARCHIVE_IN_PROGRESS / ARCHIVE_FINISHED
       -> RETAINED
       -> RETIRED (when safe)

    REQUESTED/COPYING/VERIFYING/PUBLISHING
       -> FAILED (recoverable, untrusted staging bytes)
       -> ABORTED (not published; source remains active)

    PUBLISHED / NO_POST_HOOK
       -> ORPHANED_PUBLISHED (still immutable; no writer freeze)
       -> RETAINED until safe cleanup

**Mutability invariant:** Published files are never modified in place. Any correction creates a new snapshot generation with a new UUID.

**Backup lifecycle ambiguity:** Published is **not equivalent to included in a completed HA backup**, and post hook success may not equal a verified archive-member inspection. A snapshot record distinguishes "locally valid", "known archived" (only after appropriate verification), and "recovery selected".

## 6. Snapshot manifest: conceptual fields

| Field | Purpose |
| --- | --- |
| format_version | Manifest compatibility |
| snapshot_uuid | Unique generation |
| ledger_uuid | Logical source identity |
| source_schema_version | SQL schema compatibility |
| accounting_policy_version | Duration/gap interpretation |
| source_sqlite_version | Provenance and diagnostics, not arbitrary compatibility waiver |
| created_utc | Audit timestamp (wall-clock accuracy not assumed) |
| source_run_uuid | Runtime generation (if available) |
| committed_cursor | Read from closed validated snapshot |
| max_observation_utc | Capped, source-scoped; not proof later inactivity |
| file_path | **Relative** basename within generation only |
| file_size_bytes | Exact validated bytes |
| file_sha256 | Byte integrity, not origin authenticity |
| validation_integrity_check | Pass result from snapshot |
| validation_foreign_key_check | Pass result from snapshot |
| validation_completed_utc | Completion timestamp |
| publisher_revision | Application release / schema version |
| completion_marker_version | Publication success marker |
| provenance_kind | Online Backup API / manual export / reviewed other |
| backup_archive_id | **NULL unless official API supplies verified mapping** |

No credential, raw PSN account tokens, pairing secrets, arbitrary file system path, provider payload or private game timeline in the manifest.

## 7. Restore authority problem after immutable snapshot

**Two valid authorities may exist in same archive:**
- a verified immutable snapshot with cursor 100;
- raw live SQLite files copied later while the source cursor advanced toward 160; raw files could be inconsistent, or they could be internally valid and newer.

An ordinary reboot can also leave the live source at 160 and the still-present snapshot at 100. Therefore "always apply snapshot" would destroy real recent history. "Always prefer larger cursor" is unsafe if raw copied files were not captured consistently or if source/manifest ledger UUID differs.

**Proposed safe initial behavior:**
- Ordinary start with verified live DB: use it, do not promote a dormant snapshot.
- Missing/corrupt live DB with a verified snapshot: preserve candidates, enter RECOVERY_HOLD and expose admin-guided import if supported.
- Explicit user-authorized restore: exclusive write fence, independent verification, preserve original bytes, promote only a selected compatible snapshot after warning about newer data and new run generation.
- Restore of entire config by Supervisor may not provide a trusted per-integration intent that survives the replacement. A valid restored raw DB could appear ordinary; **do not promise automatic recognition of all restore scenarios**.
- A durable snapshot has a precise as-of committed cursor; missing observations after cursor must be labelled unobserved, never interpolated into playtime.

**Remaining P0 blocker:** identify a supported way to keep mutable live DB outside the Core config archive while maintaining private local persistence, reliable default backup coverage and config/ledger identity synchrony; OR explicitly accept that the first release uses admin-assisted recovery rather than automatic selection after restore. The latter is a product policy, not merely a code issue.

## 8. Alternative mechanisms evaluated

| Candidate | Source-backed strengths | Critical unresolved issue | Position |
| --- | --- | --- | --- |
| Online Backup API staging (recommended research route) | Consistent snapshot while source activity allowed | Archive includes live DB and restore authority unspecified | RESEARCH_PREFERRED, NOT_RELEASE_READY |
| VACUUM INTO | Consistent compact snapshot, official SQLite | Interrupted output can be incomplete; different performance/cancellation/fsync trade-offs | OPTIONAL_BENCHMARK |
| Quiesce active SQLite across entire archive | Main DB stable while locked | Missing post hook after other-platform pre failure; long gaps; cannot safely time-unfreeze | BLOCKED_UNLESS_SAFE_PROTOCOL |
| WAL checkpoint then immediate resume | Reduces outstanding WAL | Source mutates during file copy; no backup coherence | REJECTED |
| Raw DB + WAL tar copy | No extra app logic | Multi-file race and mutable reads, possible mismatched WAL/DB | REJECTED |
| Private out-of-config live store + staged snapshot | Avoid raw live source in Core config backup | Supported path, backup inclusion, split-brain with rolled-back Config Entries | CONDITIONAL, NOT_SELECTED |
| User-confirmed app-specific export/import | Explicit selection and validation | Operational complexity, not automatic HA restore | DEFENSIVE_FALLBACK |
| Rely on generic HACS persistent_directory | Preserves folder across source update | Does not exclude from backup or provide SQL consistency | NOT_A_BACKUP_SOLUTION |

## 9. Failure modes and non-negotiable cleanup

| Phase/failure | Expected contract |
| --- | --- |
| Before allocation | No snapshot exists; no state mutation |
| During copying, power loss | Temporary bytes unusable, live DB recovered normally |
| During backup, source mutation causes repeated restarts | Hard deadline and classified failure, not endless block |
| SQLITE_BUSY/LOCKED | Bounded backoff, no duplicate writer or retry loop |
| IOERR/FULL/READONLY | Abort, preserve previous valid generation, report backup unsafe |
| Destination connection cannot close | Do not publish snapshot whose bytes may still change |
| Integrity/foreign keys fail | Reject, preserve diagnostic reason, do not mask the problem |
| Manifest partially written | No completion marker; untrusted candidate |
| Crash between separate file renames | Generation publication protocol rejects incomplete pair |
| Snapshot metadata cursor read from live DB after copy | Explicitly rejected; must come from copied DB |
| Another pre hook fails after our snapshot publication | No frozen live writes; published snapshot may be orphaned |
| Supervisor sends no post hook | Published artifact retained; runtime monitoring continues |
| HA archive copy includes live WAL | Snapshot remains separate, no assumption raw copies are trusted |
| Retention job races tar reading generation | Do not delete generation until verified not in use |
| Restore points at different ledger UUID | Reject auto-merge and unsafe console/PSN reattribution |
| App/Hub only with no consoles | Backup platform may be loaded, source snapshot if ledger exists |
| No configured entries / plugin uninstalled | No guarantee pre hook runs; must document backup exposure |

## 10. Security / privacy / UX gates

A snapshot is sensitive user data even without credentials. Use protected private directories, avoid exposing the snapshot and manifest through HTTP /local or panel static paths, and do not include title names/private identities in generic diagnostics. Use explicit admin-only recovery and previews; multi-console identity validation and anti-cross-instance import checks. A hash detects corruption; it does NOT authenticate a modified manifest. Home Assistant backup archive encryption does not imply runtime SQL encryption.

The UI may show:
- current LAN status, independent of database backup state;
- last committed history cursor and as-of time;
- last **locally verified** snapshot, not necessarily included in completed HA backup;
- warning when archive correctness or restore automatic selection is unverified;
- an archive-only report view when the approved Hub Config Entry is the only configured entry.

## 11. Decision log and scope

**User acceptance (2026-11-06):** The maintainer accepted the suggested architecture directions in conversation: one user-confirmed logical Hub/Archive Config Entry; separate physical/account entries; one integration/panel/controller; private HA config-root storage direction outside HACS source; preservation of old history on entry removal; priority research into immutable SQLite snapshots. Record these conceptual decisions as ACCEPTED in ADR-0011, with production-sensitive storage path/backup policy explicitly CONDITIONAL and untested.

**Not decided:** SQLite library/PRAGMAs, actual path/permissions, live DB outside backup selection, automatic restore semantics, permitted data retention length, exact snapshot API worker, timeout and file system guarantees. No source code may be committed on the basis of this research.

## 12. Source register

**SQLite official:**
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/c3ref/backup_finish.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/uri.html
- https://www.sqlite.org/pragma.html
- https://www.sqlite.org/lang_vacuum.html

**Python official:**
- https://docs.python.org/3.14/library/sqlite3.html

**Core 2026.11.0:**
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/const.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/knx/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/integration_platform.py

**Supervisor pinned:**
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Home Assistant contributors:**
- https://contributors.home-assistant.io/core/integrations/backup/

**Project:**
- [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md)
- [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md)

**Outcome:** Detailed source-audited candidate protocol only; no runnable code, test, migration, backup creation, hardware contact, source branch change or installed HA OS inspection.
