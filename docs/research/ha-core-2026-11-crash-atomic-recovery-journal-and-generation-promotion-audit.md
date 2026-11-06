# PlayStation Hub — Crash-atomic recovery journal and SQLite generation promotion audit

**Research date:** 2026-11-06
**Status:** OFFICIAL_SOURCE_RESEARCH / PROPOSED / NO_CODE / NO_TESTS
**Home Assistant source baseline:** Core 2026.11.0; Supervisor 69848689a1e982ebe92d80e344fc086d8af667db
**Platform scope:** HA OS and supported Container-like installations; exact filesystems and Python-linked SQLite not verified on a live machine.
**Maintainer product decision:** ADR-0011 ACCEPTED at conceptual Hub/Archive level. The specific recovery protocol below is NOT approved or implemented.
**Related:** [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md), [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md), [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md).
**Repository:** jorgeavlobo/playstation-hub; main documentation only, develop unchanged.

> Evidence levels: SQLITE_OFFICIAL / PYTHON_OFFICIAL / POSIX_LINUX_MANUAL / CORE_SOURCE / PROJECT_PROPOSAL / OPEN. Exact upstream descriptions are cited by URLs below. System behavior has not been tested on this user's HA OS. A file-system atomic rename is not a cross-file, cross-service transaction and must never be represented as such.

## 1. Critical source findings

**Finding CRJ-01 — Renaming an open SQLite DB is unsafe.** Official SQLite howtocorrupt warns that unlinking/renaming a DB in use can let different connections see different database objects under one name while sharing WAL/journal names, leading to corruption. It also warns about copying the main DB without a hot journal, moving/deleting a hot journal, or mixing journals from different DBs. Therefore an application must never swap the live main-file path while any SQLite connection or worker might still hold it. Merely renaming quickly is NOT a safe cutover protocol.

**Finding CRJ-02 — SQLite WAL and the application recovery journal solve different problems.** SQLite WAL/rollback journal protects SQLite transaction atomicity and supports native crash recovery. It does not make a chain of application-controlled file copies, renames, a pointer file and HA Config Entry store updates atomic as a group. Our recovery journal would be separate metadata for supervising that multi-step application workflow. Never delete SQLite-generated -wal/-shm/-journal as an application cleanup trick.

**Finding CRJ-03 — os.replace atomicity is limited to ONE filesystem entry.** Python documentation states a successful os.replace rename is atomic on POSIX and cross-filesystem moves may fail. It does not atomically update three separately renamed files, or HA .storage and SQLite together. The active pointer, recovery journal and SQLite generation contents require ordering, version checks and crash recovery, not an assumed multi-file transaction.

**Finding CRJ-04 — fsync a file is not necessarily fsync of its directory entry.** Linux fsync(2) specifies that synchronizing a regular file does not guarantee the containing directory entry reached stable storage; explicit directory fsync is needed. Neither a successful function return nor general POSIX atomicity guarantees data survived faulty hardware/controller caches. File and directory durability, error classification and power-cut tests must be performed on supported HA OS filesystem(s).

**Finding CRJ-05 — A self-contained snapshot can be built independently.** SQLite Online Backup API produces a consistent completed destination while source writes may continue. To promote as a live generation, the destination must be successfully closed, independently integrity-checked, schema/ledger UUID/cursor checked, and kept immutable until chosen. The resulting live copy must have its own unique SQLite namespace and source file path. Incremental copying may restart under concurrent writes; timeouts remain mandatory.

**Finding CRJ-06 — Native SQLite recovery is not application migration recovery.** SQLite's documented recovery can replay hot journals/WAL on the original path, assuming those companions remain paired. If an application moved/deleted the path first, the database may be damaged. Recovery must resolve the intended generation using a durably published pointer and journal BEFORE opening a mutable source, then let SQLite perform normal WAL recovery on that generation's original path.

**Finding CRJ-07 — A single new-generation pointer can reduce multi-file switch risk, but is only a PROPOSAL.** Preparing an entirely separate database generation while old paths remain intact, then atomically switching a single small pointer/index (and syncing it), avoids renaming active SQLite files during cutover. This is a much better starting design than performing old.db -> old.backup, candidate.db -> old.db, candidate-wal manipulation. It introduces its own journal/pointer ordering and stale-file/backup scope problems that must be tested. It does NOT make the HA backup archive unambiguous.

**Finding CRJ-08 — Independent HA configuration is not one database transaction.** Home Assistant Config Entries, device/entry registries and application-owned SQLite are managed separately. Promotion of a ledger generation cannot atomically replace or update all HA Config Entries with one SQLite COMMIT. A post-promotion reconciliation gate must explicitly check physical console and account associations before monitoring or privileged controls resume.

## 2. High-risk alternatives compared

| Candidate | Description | Key risk | Research verdict |
| --- | --- | --- | --- |
| F1 — in-place main DB replacement | Close, rename live DB to backup, rename chosen snapshot into old filename, manipulate WAL/SHM | Crash between distinct renames; previously open worker; hot sidecars; cross-filesystem moves | NOT RECOMMENDED |
| F2 — versioned generation + atomic active pointer | Create validated new directory and standalone DB, fence/close old handles, fsync and atomically swap one small pointer | Pointer/journal dual state, durability ordering, old generation retention, startup resolver and extra storage | PREFERRED FOR RESEARCH, NOT ACCEPTED |
| F3 — SQLite-to-SQLite logical import | Open both DBs and copy reconciled rows in transactional SQL on same live source | Large duration, incompatible schemas, merged histories and source attribution; only one SQL DB transaction where supported | NOT A GENERAL RESTORE SUBSTITUTE |
| F4 — always restore newest snapshot | Use filename/mtime/cursor to choose automatically | A dormant old snapshot can destroy newer live data; forked histories | REJECT |
| F5 — file-system snapshot of entire HA config | Use external atomic image snapshot of SQLite, config and metadata | No universal app-controlled HA OS/Core/Container capability or restore support | OUT OF SCOPE AS DEFAULT |
| F6 — symlink switch to DB | Flip symlink for DB path | Different names/journal derivation, ambiguous locking and unexpected alias behavior | REJECT AS DEFAULT |

**Preferred conceptual F2 hierarchy:** one active ledger UUID, one active generation ID, one single atomic pointer, immutable completed recovery artifacts, one controller-wide recovery gate, bounded generations and a separate application recovery journal. Every physical-console runtime must resolve the active DB through the manager, not cache a file path forever.

## 3. A proposed generation-based directory layout

All paths are examples only, NOT created or approved:

    <HA config>/.playstation_hub/
        ledger/
            control/
                active.json             # Small atomic pointer, not SQLite's WAL
                journal/                # Append/rewrite versioned recovery intent records
                    <operation-uuid>.json
            generations/
                <generation-uuid>/
                    history.sqlite3     # Selected mutable generation when active
                    ...SQLite-managed sidecars if live in WAL mode...
                    generation.json     # Identity and format metadata, not a trust signature
            recovery/
                immutable/
                    <snapshot-uuid>/    # Verified immutable snapshot + manifest
                originals/
                    <job-uuid>/         # Preserved old source, constrained retention

Use only internally generated safe names and known private roots; no supplied absolute path, "..", symlinks, URLs, legacy HACS executable folder or public media/static path. Do not assume the file system supports durable atomic directory publication without testing.

**Key distinction:** only the unselected snapshot/recovery candidates are immutable. The database in the ACTIVE generation remains MUTABLE and uses SQLite-managed WAL/SHM if WAL mode is eventually approved. A generation may be immutable only after it was closed and safely preserved. A pointer file is NOT an encryption key, signature, user consent or proof of restored backup provenance.

**A trade-off:** this layout may cause backups of HA configuration to include multiple historical generations, one currently mutable active DB and WAL, and all staged recovery artifacts. It therefore increases archive-size/copy ambiguity unless separate retention/snapshot-scope controls are designed. F2 resolves live cutover atomicity under assumptions, not automatic backup completeness.

## 4. Desired metadata contracts (no JSON or SQL created)

### 4.1 Active pointer

- pointer_format_version
- ledger_uuid
- active_generation_uuid
- journal_decision_uuid (last successfully committed selection)
- expected_schema_version
- expected_lineage_epoch
- minimal checksum/digest for pointer-corruption detection, not authentication
- created/updated UTC timestamp for diagnostics only, not source authority

Stored as a single small file atomically replaced using temp file + successful fsync + same-filesystem os.replace + directory fsync, subject to OS tests. Avoid a mutable direct-write pointer; an interrupted pointer write must never produce partially trusted JSON.

### 4.2 Recovery operation journal

- job_uuid, logical ledger_uuid, admin-authorized preview/decision digest and expiry state
- old_generation_uuid, new_generation_uuid, chosen immutable snapshot_uuid
- source snapshot digest, stored committed_cursor, physical/account association revision and app schema
- phase, monotonically increasing journal_revision, pending/committed marker
- expected pointer version and requested generation, no arbitrary path
- last durable phase and terminal verified status
- sanitized failure class and recovery action

Do not store Sony credentials, raw account tokens, full user gameplay history, arbitrary paths or names in this journal. Write new journal revisions through a crash-safe publish protocol, not casual in-place JSON updates. Journal describes state, not a second source of truth that can silently override a valid active pointer.

### 4.3 SQLite ledger metadata

Inside the candidate snapshot and active generation: ledger_uuid, schema_version, lineage_epoch, restore_origin_snapshot_uuid, durable_commit_cursor, account/console identity mapping revisions and last evidence/coverage frontier. These are independently validated from the database before allowing writers. Ledger_uuid alone is insufficient to distinguish diverged forks; event digest/parent relation require future exact schema and test evidence.

## 5. Recovery sequence: before promoting anything

**P0** Confirm administrator privileges through HA backend, reviewed preview ID, still-current ledger revision, candidate content/digest and durable source identity. A stale preview fails. Acquire global exclusive RECOVERY_LEASE and set writes/privileged commands for affected owners to fenced/unavailable.

**P1** Drain or classify every previously admitted writer transaction; stop per-console and account work that could append to historical ledger; bound all readers, backups and exports; wait for final positive SQLite connection/worker closure rather than treating cancellation as completion. A stuck worker is FAILED_UNSAFE_TO_REOPEN.

**P2** Persist durable journal PREPARING with old active pointer and chosen source. Maintain old live DB and its correctly paired SQLite sidecars intact at the old generation path. No rename/delete of the old live DB. Before storage mutation, preserve at least one recoverable original and verify available disk capacity.

**P3** Create new generation with a unique path; populate from a validated immutable snapshot via an independently verified standalone copy mechanism. The immutable source remains untouched. Open new generation in isolation through SQLite, let it recover its own sidecars if any and validate schema/integrity/FK, exact ledger UUID and snapshot cursor. Close all candidate connections and flush under selected safe strategy.

**P4** Finalize generation metadata; fsync required data/metadata and containing directory entries and publish new generation under a crash-safe same-filesystem protocol. No active pointer change yet. Revalidate that current HA configuration associations still correspond to the expected restore decision; conflicts hold.

**P5** Persist journal READY_TO_COMMIT with old/new IDs, decision and last validated properties. Create temp active pointer referencing the *fully published new generation*, fsync pointer, atomically replace active pointer on same filesystem, fsync directory. This is the **logical promotion point**, not a SQLite COMMIT or multi-file atomic transaction. Ensure the old generation remains preserved if power fails immediately after this step.

**P6** Persist journal POINTER_COMMITTED / ACTIVATING, close stale error handles, open selected generation through the sole HubController and run SQLite native verification. Reconcile HA Config Entries and canonical hardware/account identities. Only after a consistent identity mapping is independently verified can relevant monitors and controls resume.

**P7** Record new lineage epoch, migration/restore provenance and missing observation gap as needed, and journal COMPLETED. Retain old originals for safe rollback/administrative export until retention criteria met. Clear global Repair issue only after all invariant checks; UI must say "RECOVERED" only once operational state is verified.

**Caveat:** Step P7 cannot use a SQLite update after re-opening without carefully preserving the snapshot's integrity/commit semantics. Choose exact metadata ownership/reconciliation order in future implementation; crash tests must prove no fabricated session counter or spontaneous history merge.

## 6. Crash matrix for the active pointer/journal protocol

| Crash point | Durable evidence may exist | Safe startup behavior |
| --- | --- | --- |
| A: Before journal PREPARING published | Old active pointer and ledger only | Use old validated ledger (ordinary startup); no restore inferred |
| B: After PREPARING, before any copy | Old pointer + pending journal | Keep old if valid; mark aborted/orphan pending; no new generation choice |
| C: During generation copy | Old pointer, partial new generation | Never select partial candidate; preserve old; cleanup incomplete staging after safe review |
| D: Snapshot copied but validation not finished | Old pointer + new file, no validated marker | Old remains authority; new not adopted |
| E: Validation complete, generation not durably published | Old pointer + staged candidate | Do not assume candidate survived power; validate again or discard |
| F: New generation complete, READY_TO_COMMIT durable, pointer still old | Old pointer + verified new candidate | Old remains selected; request fresh admin decision before applying; do NOT silently finish destructive choice |
| G: Atomic pointer replace returns but directory sync not confirmed | Old or new pointer may be visible after crash | Validate actual pointer and matching new generation; do not assume which one won |
| H: New pointer durable, journal still READY_TO_COMMIT | New selected pointer + old journal | **Do not blindly roll back**: validate pointer generation/source decision and reconcile safely; this is an uncertain ACK, not necessarily a failed operation |
| I: Pointer committed, before new SQLite open | New pointer/new generation, old preserved | Open ONLY new selected generation after evidence validation, do not reopen old under same active namespace |
| J: New DB opened but Config Entry reconciliation pending | New pointer, incomplete journal, mismatched HA associations | RECOVERY_HOLD; no writes/privileged actions on mismatched identities |
| K: Reconciliation complete, journal COMPLETED not persisted | New valid pointer and ledger, prior journal state | Verify identity and job result idempotently; complete journal safely without repeating promotion |
| L: New live writes accepted, old generation GC pending | New pointer and old preserved | Do not auto-rollback to old or erase newer commits during GC |
| M: Crash during old-generation deletion | Current pointer must still reference valid new generation | Keep active; classify GC-only incomplete work; no rollback |
| N: External Supervisor restore replaces whole config tree | Pointer+journal+generations may all become older simultaneously | Cannot reconstruct absent commits or infer an out-of-band restore from local files alone; follow ADR-0013/0014, require safe source validation |

**Key guarantee limit:** A Linux process crash with intact filesystem is different from sudden loss of power, disk write-cache lies, full-file-system restore, and tampering with both manifest and pointer. Tests must distinguish them. A pointer and matching journal are not a universal proof of authenticity.

## 7. Startup reconciliation and source-of-truth rules

1. Initialize the integration-wide HubController in read-only/preflight mode; no LAN historical writes until pointer/journal reconciliation.
2. Read active pointer via a bounded, non-symlink path; validate version, checksum, ledger UUID, generation path existence and allowlist. Never accept a user-supplied path as the pointer target.
3. Enumerate known recovery journals and only internally recorded generations. If pointer is absent and there are previous data/recovery candidates, enter RECOVERY_HOLD; do not fabricate a new ledger.
4. On selected generation path, let SQLite recover a hot WAL/journal as normal **without moving/deleting sidecars**. Verify exact schema, foreign keys, ledger UUID, lineage and committed cursor; classify state.
5. Compare active pointer to last durable journal revision. If pointer and journal are out of sync, do not automatically treat the journal as authoritative: the pointer may have committed before journal completion. Accept only a positively validated selected source or enter RECOVERY_HOLD with candidate inspection.
6. If pointer old and READY_TO_COMMIT journal/new generation exist, prefer old current source, not an unconfirmed new promotion. Require renewed admin approval to commit the new generation after reconnect/restart, because live/history facts may have changed.
7. If pointer new and journal not terminal, treat promotion as *possibly complete*, validate selected new source and existing original; safely finish reconciliation under fresh identity checks rather than replaying the atomic pointer replacement or rolling back blindly.
8. If mismatched physical console/account associations, fence those owners and show admin Repair; no automatic reauthorization or bulk rewriting of old events.
9. If source validity cannot be established, keep all candidates and enter RECOVERY_HOLD. If current live DB is healthy in ordinary startup, a dormant snapshot must not overwrite it.
10. Persist definitive status and unknown coverage only under the reviewed transaction model; status inquiry/repair job may resume without the browser that initiated it.

**Never use "highest cursor wins".** A restored fork can carry same ledger UUID with different event content and different Config Entry mappings. Never retry already-committed promotion just because the browser did not receive confirmation.

## 8. What can be safely garbage-collected

Only artifacts that are: unselected; independently verified as completed/failed; not referenced by the current pointer, pending journal, active BackupManager/archiver, user-selected export or recovery job; not the only preserved original; and eligible under explicitly approved retention. A broken or missing post-backup notification is insufficient permission to remove an immutable generation while Supervisor might still be reading it.

Garbage collection is NOT a recovery mechanism for hot SQLite WAL or an excuse to delete an on-disk journal that SQLite still needs. Old active generations may contain WAL if a process died unexpectedly and must be opened/recovered under SQLite at their original path or preserved intact. A recovered old copy can be exported only through authorized safe flow; never exposed as static /local data.

## 9. Privacy and multi-tenant authorization

- All destructive source selection, recovery promotion and old-file removal require current server-side HA administrator authorization; a preview token cannot authorize itself after expiry or permission revocation.
- No arbitrary paths, foreign file IDs, symlink escapes or accepted uploaded tar members outside verified roots.
- Generation UUIDs, ledger UUIDs and job IDs are not secrecy mechanisms; protect histories with filesystem/HA ACL, and do not leak raw private game timelines/PSN aliases.
- Separate credential repositories under ADR-0007; restoring session history does not automatically link or authorize Sony accounts/Remote Play pairing.
- A Hub-only entry should stay available in RECOVERY_HOLD for admin review without starting LAN probes or silently creating fresh history.
- Reports reflect verified persisted coverage and unknown gaps; no guessing duration between old checkpoint and restart.

## 10. Missing experimental proof

**HA OS platform:** Whether the chosen filesystem offers durable same-filesystem atomic rename and directory fsync; what happens under sudden power loss vs process SIGKILL; how a container executor/worker is terminated and joined; unsupported network filesystems; exact SQLite runtime and WAL bug patch.
**SQLite:** Whether the selected backup API destination is truly self-contained (no hot sidecars) and the old generation can be kept intact; whether every connection/worker closes within bounded time.
**Home Assistant:** Whether backend Hub/Archive RECOVERY_HOLD can load while the database fails, whether global Repairs stays visible; whether Config Entry registry is updated between preview and commit and requires abort; whether a Supervisor restore overwrites pointer and journal together.
**Release:** Snapshot size/retention, disk-full behavior, read-only UI scope, supported installation types and persistent off-host independent backups.

All absent evidence must remain OPEN, not become a passed gate by source inspection.

## 11. Sources

- https://www.sqlite.org/howtocorrupt.html — hot journals/WAL pairing, open DB rename corruption, POSIX locking quirks
- https://www.sqlite.org/wal.html — WAL lifecycle, sidecars and automatic recovery
- https://www.sqlite.org/backup.html — Online Backup API consistent snapshot
- https://www.sqlite.org/atomiccommit.html — SQLite transaction and filesystem synchronization assumptions
- https://docs.python.org/3/library/os.html#os.replace — one-path atomic POSIX replacement and cross-filesystem limitation
- https://man7.org/linux/man-pages/man2/fsync.2.html — fsync(file) does not necessarily sync parent directory entry
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py — private runtime config path
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — independent entry lifecycle and runtime data
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py — global shutdown jobs
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py — archive hooks and event state
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — backup/restore config folder
- [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)
- [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md)

**Outcome:** A precise candidate recovery journal and generation/pointer model, 14 crash checkpoints and an explicit no-claims boundary. No executable code, storage or tests created. This research does not authorize implementation or change develop.
