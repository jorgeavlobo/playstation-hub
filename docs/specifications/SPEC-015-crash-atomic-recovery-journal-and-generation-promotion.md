# SPEC-015 — Crash-atomic recovery journal, SQLite generation promotion and restart reconciliation

**Date:** 2026-11-06
**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_CODE
**Research:** [Pinned SQLite/POSIX crash atomicity audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md)
**Decision:** [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) PROPOSED
**Previous:** [SPEC-014](SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md), [SPEC-013](SPEC-013-restore-authority-storage-topology-and-reconciliation.md), [SPEC-012](SPEC-012-immutable-snapshot-publication-and-backup-admission.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md).
**Pinned platforms:** Home Assistant Core 2026.11.0, Supervisor commit 69848689a1e982ebe92d80e344fc086d8af667db. Python/Linux/SQLite official documentation.
**Branch:** main documentation only. Frozen develop untouched.

> Every MUST/SHOULD below is an internal **candidate acceptance contract**, not a fact about a working PlayStation Hub. No implementation, test scripts, HA OS operation, user data migration or ADR approval is authorized.

## 1. Goal and non-goals

Provide a fault-injection-ready specification for safely promoting a user-authorized, previously validated SQLite recovery candidate without renaming an open SQLite database or confusing a partially updated journal with a durable pointer.

The project must preserve:
- one single integration global HubController and history writer;
- one accepted logical Hub/Archive entry and independent console/PSN account entries;
- archived data after console removal;
- admin-only, two-phase preview/confirm and durable job ownership from SPEC-014;
- historical UNKNOWN gaps and no arbitrary automatic fork merge;
- no mandatory MQTT, add-on or external DB.

It must **not** falsely claim lossless restore from a stale backup, universal power-cut safety across all storage or atomicity between SQLite and Home Assistant config/registry JSON.

## 2. Candidate invariants

| ID | Requirement |
| --- | --- |
| JR-I01 | Exactly one selected active SQLite generation per ledger UUID at a time, recorded through a verified active pointer. |
| JR-I02 | Every promotion belongs to a unique durable admin-authorized job, not a browser connection. |
| JR-I03 | Source snapshot and old live generation remain unmodified during candidate staging. |
| JR-I04 | No live SQLite main DB can be renamed, unlinked, overwritten or reused while a writer, reader, backup/export worker or stale file descriptor may remain open. |
| JR-I05 | SQLite-owned -wal/-journal/-shm must never be manually removed, swapped or detached as application cleanup. |
| JR-I06 | All accepted old-generation transactions are definitively completed/classified before fencing writes and closing connections for promotion. |
| JR-I07 | A new generation uses its own isolated path and cannot share another generation's sidecars. |
| JR-I08 | Candidate schema/ledger UUID/lineage/committed cursor and source associations are read from validated candidate SQLite data, not unverifiable file names. |
| JR-I09 | Recovery job phases are durably published as complete revisions; no direct in-place overwrite of recovery intent JSON. |
| JR-I10 | The sole active pointer is a single small publication object, replaced atomically within a proven same filesystem, with file and directory synchronization. |
| JR-I11 | An atomic pointer replacement is not asserted to be an atomic pointer+journal+SQLite+HA registry transaction. |
| JR-I12 | During startup, inspect actual pointer and journal before opening any mutable selected generation, then permit SQLite native WAL/journal recovery on its original path. |
| JR-I13 | If pointer and journal disagree, classify source/phase; do not blindly roll back or replay promotion after a possibly successful pointer replacement. |
| JR-I14 | If old pointer is selected but a READY_TO_COMMIT journal points at new, keep old if verified; require new admin review before committing. |
| JR-I15 | If new pointer is selected but journal is pre-completion, validate new generation and resume reconciliation idempotently, not repeat or delete it. |
| JR-I16 | No PUBLISHED snapshot or retained generation can be removed while referenced by pointer, journal, active backup/export or last-known-good recovery policy. |
| JR-I17 | New SQLite generation activation fences all stale console/account runtime generations, file handles and queued observations. |
| JR-I18 | HA Config Entry/device/account associations cannot be atomically promoted with SQLite and require separately verified reconciliation before privileged control/writes. |
| JR-I19 | A crashed promotion is never reported SUCCEEDED solely because os.replace returned or the browser got a result. |
| JR-I20 | Immutable prior records and unknown observation gaps cannot be converted into fabricated usage seconds during restart/reconcile. |
| JR-I21 | An invalid active pointer, missing selected generation, corrupt journal or unresolved filesystem durability puts the hub into RECOVERY_HOLD without empty DB creation. |
| JR-I22 | A full Supervisor restore replacing the config folder can roll back pointer, journal and DB together; no claim to reconstruct later unsaved copies. |
| JR-I23 | All filesystem operations are confined to private supported roots with fixed generated names, symlink/path traversal protection and disk quota. |
| JR-I24 | Candidate administrative preview expires or conflicts upon changes to current ledger revision, associations, source bytes or filesystem generation. |
| JR-I25 | All repair/diagnostics are privacy-safe and share a global hub owner rather than one removable console. |
| JR-I26 | The final promotion strategy must be verified under SIGKILL, abrupt power interruption and HA OS restoration as separate fault categories. |

## 3. Candidate control files and state

**Active pointer (one small file):** pointer format, ledger UUID, selected generation UUID, last committed promotion job ID, expected schema/lineage epoch, bounded checksum. Internal references must be relative and allowlisted, not arbitrary user paths or symlinks.

**Recovery journal (revisioned records):** job ID, admin decision/preview receipt identity, old/new generation UUID, source immutable snapshot ID/digest, expected current pointer revision, old/new cursor/lineage, phase, revision, error class, reconciled association generation. Each revision must be durably published or ignored after a crash. The recovery journal is NOT the SQLite WAL or a secret/authorization database.

**Generation directory:** one SQLite working DB at a unique path, SQLite-created sidecars only when active, separate validated metadata. Unselected immutable snapshots remain separate and are never modified to make an active live DB.

**Suggested process phases (future names, not executable):**
CREATED -> AUTHORIZED -> FENCING -> OLD_WRITES_DRAINED -> OLD_HANDLES_CLOSED -> JOURNAL_PREPARING -> NEW_GENERATION_STAGING -> NEW_GENERATION_VALIDATED -> NEW_GENERATION_DURABLE -> READY_TO_COMMIT -> ACTIVE_POINTER_COMMITTED -> NEW_GENERATION_OPEN -> IDENTITY_RECONCILING -> VERIFIED_COMPLETE.

Errors: FAILED_PRECOMMIT (old pointer remains), FAILED_UNSAFE_TO_REOPEN (uncertain worker/handle), RECOVERY_HOLD (ambiguous authority), FAILED_AFTER_POINTER_COMMIT (requires startup reconciliation). Cancellation is safe only before irreversible pointer commit, with bounded component cleanup.

## 4. Promotion and last-safe-cancel contract

1. Confirm preview and administrator authority; re-validate candidate digest/ledger/lineage and expected state_revision.
2. Fence historical writes and affected hardware controls. Allow only read-only non-attributed current status if safe; mark unsaved intervals.
3. Settle in-flight commits, readers, exports and snapshot operations; positively verify writer/executor/SQLite connection closure, not only task cancellation.
4. Publish durable recovery-intent journal referring to the old current pointer. If disk full or fsync fails, stop and keep old.
5. Prepare new generation from an already validated immutable source, with distinct internal file path; SQLite opens/recovers/verifies its own destination and closes.
6. Validate integrity_check and foreign_key_check, schema, ledger UUID, lineage/restore parents and its own durable cursor.
7. Make new directory and metadata durably published. Exact file and directory fsync ordering needs target filesystem proof.
8. Publish READY_TO_COMMIT journal revision. Confirm current pointer still refers to the old expected generation and no foreign process modified data.
9. Use same-filesystem atomic active pointer replacement, followed by containing-directory fsync. The point of irrevocable choice is the verified durable pointer selection, **not** the journal final revision.
10. Open ONLY the selected new generation. If SQLite/associations fail, enter RECOVERY_HOLD and preserve old/new; do not blindly point back at old when new writes might have occurred.
11. Reconcile current HA entry identities independently, fence unknown or stale owners, establish new runtime/restore epoch and UNKNOWN historical gaps.
12. Persist final journal VERIFIED_COMPLETE and publish diagnostics/Repairs updates only after positive validation. Resume authorized source monitoring; no user-facing success earlier.

**Key edge:** if new pointer is durable but journal still READY_TO_COMMIT, startup must use actual pointer + independent generation verification to decide. Repeating an old rename or blindly reverting to old would lose or duplicate data.

## 5. Startup algorithm (PROPOSED)

- Do not allocate a blank ledger merely because an expected active filename is absent.
- Read fixed-path pointer/journal atomically where supported; verify schema, ids, revision and expected generation directory.
- If pointer old and incomplete job with new prepared generation, keep old if valid, keep new unselected and request admin reconfirmation if needed.
- If pointer new and journal incomplete, validate new source, reconcile identity, safely finalize the journal idempotently. Do not repeat promotion.
- If pointer corrupt, generation missing, or both disagree irreconcilably, RECOVERY_HOLD; preserve bytes and Repairs. Never guess based on newest mtime.
- Open selected SQLite at its own original path and allow native WAL/journal recovery. Never delete/rename hot journals in search of a clean reopen.
- Check all stale source generations, queued writes, HA Config Entry/PSN associations and unauthorized operations before enabling monitoring.
- An orphan staging directory can be garbage-collected only when no active journal/pointer/backup reference needs it and other verified recovery originals remain.
- A Supervisor whole-config restore may restore a consistent old pointer+old journal+old SQLite, leaving no local evidence of later writes; the latest surviving backup cursor limits the honest history.

## 6. Future test catalogue (80 cases; ALL NOT_RUN)

### 6.1 Promotion phases and durable journal — 20 NOT_RUN

| ID | Fault injection | Required result |
| --- | --- | --- |
| JR-PH01 | Crash before durable intent | Old valid ledger remains active |
| JR-PH02 | Disk full while writing journal PREPARING | No mutation/promotion, readable old |
| JR-PH03 | Journal temp file partially written | Incomplete revision ignored |
| JR-PH04 | Power loss after fsync journal file but before directory | Correct old/recovered revision, no false phase |
| JR-PH05 | Crash after PREPARING but before staging | Old remains, pending job classified |
| JR-PH06 | Crash during snapshot-to-generation copy | Partial destination cannot become active |
| JR-PH07 | Crash after candidate copied but before independent DB verification | No promotion marker |
| JR-PH08 | Snapshot integrity passes but FK fails | Candidate rejected, old preserved |
| JR-PH09 | Candidate lineage UUID differs from preview | Reverify and abort |
| JR-PH10 | Crash after validation before generation directory publication | Old active, new candidate unselected |
| JR-PH11 | os.replace new generation directory across different volumes | Fail cleanly or perform approved safe staging, not claim atomicity |
| JR-PH12 | Crash after directory rename before parent sync | Startup re-evaluates durable generation, no blind trust |
| JR-PH13 | Crash after READY_TO_COMMIT journal with old pointer | Keep old and require new authorization |
| JR-PH14 | Pointer temp file corrupted/incomplete | Pointer not promoted |
| JR-PH15 | os.replace pointer succeeds but directory fsync fails | Commit uncertain, next boot validates actual pointer |
| JR-PH16 | New pointer durable, journal old phase | Validate selected new, do not blind rollback |
| JR-PH17 | New pointer durable before new DB reopened | Next boot opens new safely, old preserved |
| JR-PH18 | Crash during identity reconciliation | RECOVERY_HOLD and no unauthorized attribution |
| JR-PH19 | New pointer+data valid but COMPLETED journal missing | Idempotent reconcile/finalize, no second promotion |
| JR-PH20 | Crash during old generation cleanup | Current new remains active; cleanup retried safely |

### 6.2 SQLite handles, sidecars and filesystem — 20 NOT_RUN

| ID | Fault injection | Required result |
| --- | --- | --- |
| JR-SQL01 | Reader connection open on old WAL | Promotion waits or fails; no rename |
| JR-SQL02 | Writer thread ignores cancellation | FAILED_UNSAFE_TO_REOPEN, no second writer |
| JR-SQL03 | Existing source DB has hot WAL after process kill | SQLite native recovery at original path |
| JR-SQL04 | Source DB has hot rollback journal | Same-path SQLite native recovery, no delete |
| JR-SQL05 | Application attempts old .db rename while open | Guard disallows unsupported operation |
| JR-SQL06 | Application tries to delete -wal or -journal manually | Disallowed by design and tests |
| JR-SQL07 | New generation sidecar named like old generation | Must not share path/namespace |
| JR-SQL08 | SQLite destination snapshot not closed | No publication/pointer commit |
| JR-SQL09 | Connection closes after timeout but operation completion unknown | Must positively verify close before opening new writer |
| JR-SQL10 | WAL checkpoint returns BUSY | Bounded, explicit failure; no false clean snapshot |
| JR-SQL11 | Pointer replaced on local supported POSIX same-filesystem path | Atomic visibility verified under process crash |
| JR-SQL12 | Pointer replacement across filesystems | Rejected, no fallback to non-atomic rename claim |
| JR-SQL13 | File fsync succeeds but parent directory sync not done | Crash may lose directory entry; no assumed durability |
| JR-SQL14 | Directory fsync unsupported or fails | Fail closed/alternate tested persistence plan |
| JR-SQL15 | Hardware lies about write-cache flush | Document limitations, never unconditional power-loss guarantee |
| JR-SQL16 | WAL reset bug affected linked SQLite runtime | Version gate fails until patched/fallback tested |
| JR-SQL17 | Filesystem is NFS under apparent local mount | No default WAL promotion without verified locking |
| JR-SQL18 | Symlink/hardlink to DB generation attempted | Reject alias/path escape, no hidden second namespace |
| JR-SQL19 | Source old generation contains sidecar after SIGKILL | Preserve same filenames/dir until SQLite recovery |
| JR-SQL20 | Power failure after new committed observations | No rollback to old generation, data gap conservative |

### 6.3 Startup reconciliation, duplicate operations and identity — 20 NOT_RUN

| ID | Future case | Required result |
| --- | --- | --- |
| JR-BOOT01 | Normal startup, no pending job | Open validated pointer-selected ledger |
| JR-BOOT02 | Missing pointer but known old history exists | RECOVERY_HOLD, no blank ledger |
| JR-BOOT03 | Pointer references missing generation | RECOVERY_HOLD preserving originals |
| JR-BOOT04 | Pointer file hash/format bad | RECOVERY_HOLD, no newest-file guess |
| JR-BOOT05 | Pointer new, journal old, both candidates valid | Treat selected pointer as possibly committed and validate |
| JR-BOOT06 | Pointer old, journal ready new | Keep old; require new admin preview |
| JR-BOOT07 | Same ledger_uuid/cursor but different fork history | Conflict, no auto-union |
| JR-BOOT08 | Old snapshot present, valid live pointer newer | Do not promote stale snapshot |
| JR-BOOT09 | Admin confirmation retransmitted after committed pointer | Return one existing job result |
| JR-BOOT10 | Two admin tabs confirm different candidates | One exclusive accepted job |
| JR-BOOT11 | Mobile browser closes before pointer commit | Backend safely continues/aborts under owner, not browser |
| JR-BOOT12 | Browser closes after pointer commit | Status reconnect; no second promotion |
| JR-BOOT13 | Permission revoked after preview before confirm | Deny stale confirmation |
| JR-BOOT14 | HA config registry from old backup, newer ledger survives | Owner association hold, no physical rebind |
| JR-BOOT15 | Console replaced at same IP | No old historical/Remote Play association |
| JR-BOOT16 | PSN account restored to old token state | No auto reauthorization from history |
| JR-BOOT17 | Restore missing recent gameplay observations | UNKNOWN gaps; no invented elapsed minutes |
| JR-BOOT18 | Hub-only startup, selected generation corrupt | RECOVERY_HOLD sidebar/Repairs, no poll |
| JR-BOOT19 | Console unloading while global recovery | Independent active entries fenced correctly |
| JR-BOOT20 | 100 repeated restart/reconcile cycles | Stable one writer/one pointer, no duplicate records |

### 6.4 Supervisor restore, retention, security and longevity — 20 NOT_RUN

| ID | Future case | Required result |
| --- | --- | --- |
| JR-OS01 | Supervisor full config restore replaces pointer+journal+generations | No false claim to recover absent later commits |
| JR-OS02 | Supervisor partial config-only restore, external ledger survives | Identity split-brain detected |
| JR-OS03 | Supervisor share-only restore with current config | Inverse conflict detected |
| JR-OS04 | Core .HA_RESTORE separate mechanism | Not assumed same token as Supervisor event |
| JR-OS05 | HA backup contains active generation+WAL and snapshot | Raw copies not automatically trusted |
| JR-OS06 | Snapshot archived with stale pointer | Archive scope and restored state clearly classified |
| JR-OS07 | GC targets pointer-referenced generation | Deletion forbidden |
| JR-OS08 | GC targets pending recovery journal source | Deletion forbidden |
| JR-OS09 | GC runs while Supervisor may be archiving | Preserve immutable generation until safe |
| JR-OS10 | Last known good recovery snapshot threatened by quota | Retain/alert, not silently delete only copy |
| JR-OS11 | History retention after last console removal | Hub archive remains; no implicit purge |
| JR-OS12 | Hub deleted as last entry | Private data retained under approved policy |
| JR-OS13 | Imported malicious file path contains traversal | Rejected, no arbitrary file change |
| JR-OS14 | Imported generation path uses symlink | Rejected as untrusted |
| JR-OS15 | Non-admin requests pointer/journal mutation | Unauthorized/no mutation |
| JR-OS16 | Recovery diagnostics/log after failure | No token, private timeline or path leak |
| JR-OS17 | HA Core update while a recovery journal pending | Old state handled by declared schema version compatibility |
| JR-OS18 | Rollback to older integration version with newer pointer schema | Read-only hold, no destructive downgrade |
| JR-OS19 | HA shutdown job overlaps pointer commit | Safe fence/finish/hold, no false COMPLETED |
| JR-OS20 | Three-year synthetic history at large scale | Bounded disk/latency, as-of cursor and exact gaps verified |

**80 planned cases:** 20 promotion, 20 SQLite/filesystem, 20 startup/identity and 20 Supervisor/security. All NOT_RUN. Intentional overlaps with SPEC-008 through SPEC-014 are documented; no test was executed.

## 7. Acceptance gates — 20 OPEN

| Gate | Evidence required | State |
| --- | --- | --- |
| JR-G01 | One exclusive global recovery job and lifecycle lease | PROPOSED / NOT_RUN |
| JR-G02 | File-pointer model or safer selected alternative approved by maintainer | PROPOSED |
| JR-G03 | Source and destination SQLite worker closure fully verified | NOT_RUN |
| JR-G04 | SQLite WAL/hot-journal safe pairing and native crash recovery | NOT_RUN |
| JR-G05 | Atomic one-path pointer replacement under supported HA OS filesystem | BLOCKED_HA_OS |
| JR-G06 | Parent-directory fsync and power-failure durability proven | BLOCKED_HA_OS |
| JR-G07 | No cross-volume atomic rename assumption | NOT_RUN |
| JR-G08 | Durable journal revisions, checksum/version/phase ordering | NOT_RUN |
| JR-G09 | Candidate snapshot standalone verification incl own cursor/FK | NOT_RUN |
| JR-G10 | Old generation preserved until verified new selection | NOT_RUN |
| JR-G11 | Every pointer/journal crash interleaving classified deterministically | NOT_RUN |
| JR-G12 | No blind rollback after pointer commit and lost acknowledgement | NOT_RUN |
| JR-G13 | No repeated promotion on browser reconnect/restart | NOT_RUN |
| JR-G14 | Config Entry and physical-console/account lineage reconciliation | BLOCKED_HARDWARE |
| JR-G15 | RECOVERY_HOLD with Hub-only UI, Repairs and admin ACL | NOT_RUN |
| JR-G16 | Explicit UNKNOWN historical gaps and no fabricated sessions | NOT_RUN |
| JR-G17 | Safe old-generation GC, active archive and retention | NOT_RUN |
| JR-G18 | Hostile import/path/symlink and private diagnostics defenses | NOT_RUN |
| JR-G19 | Supervisor full/partial backup/restore, HA OS/Container tests | BLOCKED_HA_OS |
| JR-G20 | Maintainer approval of final on-disk protocol and release limits | OPEN |

**No PASS states.** Source-based reasoning and the existence of these requirements do not satisfy HA OS, physical hardware or crash fault-injection gates.

## 8. Future implementation boundaries

Do not create code, tests or fixtures as part of this documentation task. Before implementation select and approve exact pointer/journal encoding, fsync semantics on supported filesystems, SQLite connection library, watchdog, migration, admin API and test fixtures. All code/comments/documentation, when eventually authorized, will remain English, modular, extensible, with full-file review for changes. A new feature branch only after explicit approval; existing develop remains legacy reference.

## 9. Official sources and internal references

- [Source-pinned audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md)
- [ADR-0015 proposal](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md)
- [SPEC-014 admin recovery API](SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md)
- [ADR-0011 product architecture](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- https://www.sqlite.org/howtocorrupt.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/atomiccommit.html
- https://docs.python.org/3/library/os.html#os.replace
- https://man7.org/linux/man-pages/man2/fsync.2.html
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py

**Status at publication:** 80 NOT_RUN cases, 20 OPEN gates, no code or live test.


## 10. Boot-time controller gate and worker cancellation boundary — 2026-11-06

[Source audit of pinned HA Core/Python/aiosqlite](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md) and [SPEC-016](SPEC-016-recovery-hold-boot-order-and-worker-termination.md) add 80 NOT_RUN cases/20 OPEN gates focused on the preconditions of this specification's active-generation pointer switch. A Hub-only entry should be able to load with internal RECOVERY_HOLD and one restricted admin panel while the global historical writer is DENY_WRITE. A console entry LOADED with fresh LAN AWAKE does not imply a durable write lease.

Critical worker fact: standard Python ThreadPoolExecutor running jobs are not cancelled by Future.cancel or cancel_futures=True, and the reviewed aiosqlite v0.21.0 worker may execute already queued SQL after the awaiting Future was cancelled. sqlite3.Connection.interrupt aborts queries, not the underlying worker/connection lifecycle. For SPEC-015 promotion, require separately observed completion of accepted SQL work, connection close, worker terminal/join and zero outstanding related leases before changing the active-generation pointer. Unknown state is FAILED_UNSAFE_TO_REOPEN; preserve old DB path and WAL sidecars, and never assume the pointer can be safely switched due to asyncio timeout. Native HA ConfigEntry migration failure and history recovery are different categories; the accepted Hub entry may load degraded where the control plane still succeeds. The original 80 SPEC-015 tests/20 gates remain NOT_RUN/OPEN.


## 11. Versioned aiosqlite terminal proof and service capability fences — 2026-11-06

[Capability and aiosqlite 0.22 source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) and [SPEC-017](SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) refine conditions for this specification's atomic active pointer promotion. No stale Home Assistant automation, entity method, console wake/standby, WebSocket action, cancelled source probe or previously queued SQL may bypass a global FENCING gate. Core's Entity.available is presentation availability, not authorization.

Aiosqlite 0.21 Connection inherits Thread; in 0.22.0 and 0.22.1 Connection owns a private Thread, and v0.22.1 adds stop and a different queued close flow. The stop Future callback is scheduled before the underlying thread loop return, so a close receipt cannot simply be called a documented public Thread.join. Old-generation connection closure, all outstanding jobs and a supported positive worker-terminal proof are required before pointer cutover. In RECOVERY_HOLD, optional verified source-only observations are UNSAVED, never replayed into history; physical power/Remote Play controls default to deny pending owner approval. The 80 original SPEC-015 crash cases/20 gates remain NOT_RUN/OPEN; SPEC-017 adds 80 more proposed cases and 20 gates.
