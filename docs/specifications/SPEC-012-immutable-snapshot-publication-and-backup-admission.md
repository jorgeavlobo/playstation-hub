# SPEC-012 — Immutable SQLite snapshot publication, Home Assistant archive admission and guarded restore

**Date:** 2026-11-06  
**Status:** DESIGN_SPECIFICATION / NOT_IMPLEMENTED / ALL_TESTS_NOT_RUN  
**Core reference:** home-assistant/core tag 2026.11.0  
**Supervisor reference:** home-assistant/supervisor commit 69848689a1e982ebe92d80e344fc086d8af667db  
**Research:** [Source-pinned immutable snapshot audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md)  
**Architecture:** [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [SPEC-011](SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md), [SPEC-010](SPEC-010-crash-recovery-restore-provenance-and-archive-access.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md).  
**Branch:** main documentation only; develop preserved.

> Maintainer accepted the **product-level design directions** on 2026-11-06 (logical Hub/Archive config entry; per-console/account entries; one panel/controller; private configuration-root storage direction; historical retention; priority study of immutable snapshots). This does NOT mean the particular SQLite snapshot/backup/restore implementation below is ACCEPTED or passed any test.

## 1. Problem and desired guarantee

Build a future **single integration-wide** history backup design that does not suspend LAN monitoring for an entire Home Assistant backup and that never publishes a corrupt/incomplete snapshot. A pre-hook may complete successfully with no matching post-hook because another integration's pre-hook fails. Core/Supervisor backup filters do not provide a verified custom integration exclude interface, so raw live SQLite files under the config tree may still be archived. Full automatic restore authority is **not established**.

A valid snapshot is a self-contained immutable SQLite database plus exact manifest, proven coherent at its own committed cursor. It is NOT equivalent to a successful whole-home HA backup, automatic correct recovery, or complete historical coverage.

## 2. Invariants to verify

1. **SN-I01** One snapshot producer per ledger/snapshot admission generation; no duplicate SQLite destination writers.
2. **SN-I02** Snapshot reads use distinct source/destination connections with explicit worker/thread ownership; no SQLite I/O blocks the HA event loop.
3. **SN-I03** Snapshot destination remains exclusive while backup API is active.
4. **SN-I04** Concurrent writers never cause an unbounded backup operation; restart-on-write handled with a deadline.
5. **SN-I05** Fatal SQLite errors abort and cleanup without marking any artifact valid; transient failures bounded.
6. **SN-I06** No published snapshot references an open/unflushed/partially copied SQLite destination.
7. **SN-I07** The resulting snapshot is verified with SQLite integrity_check and foreign_key_check and schema/ledger_uuid domain checks.
8. **SN-I08** Committed cursor comes from the **completed snapshot**, never live source just before or after copy.
9. **SN-I09** A generation's snapshot+manifest+completion marker are visible together only after validation under a proven atomic publication protocol.
10. **SN-I10** PUBLISHED artifacts are immutable; all future corrections create a new generation.
11. **SN-I11** Pre-hook can terminate after PUBLISHED without leaving live DB writes frozen; post-hook is best-effort bookkeeping only.
12. **SN-I12** Archive inclusion and local publication are separate states: PUBLISHED does not mean VERIFIED_IN_HA_ARCHIVE.
13. **SN-I13** Raw live DB/WAL copied by Supervisor is not automatically accepted as the authoritative restored history.
14. **SN-I14** No stale snapshot may automatically replace a healthy newer live database at ordinary startup.
15. **SN-I15** Snapshot retirement cannot race a potentially active archive reader and must not destroy the only verified recovery generation.
16. **SN-I16** Hub-only backup preparation is possible without a LAN monitor, if the authorized Hub/Archive entry is loaded; disabled/uninstalled integration must have honest backup limitations.
17. **SN-I17** Data written while snapshot runs remains in the live ledger and may be absent from that snapshot; the manifest's as-of cursor governs historical completeness.
18. **SN-I18** A non-matching ledger_uuid / physical console identity cannot be promoted into the current instance through automatic restore.
19. **SN-I19** A snapshot includes no Sony tokens/Remote Play credentials or raw private diagnostics; protected history remains access-controlled.
20. **SN-I20** If no approved safe automatic restoration policy exists, the product must expose manual administrator recovery as a bounded, explicit fallback rather than claiming automatic full recovery.

## 3. Proposed immutable snapshot workflow — source audit only

    PREPARATION_REQUESTED
      -> SNAPSHOT_LEASE_ACQUIRED
      -> SOURCE_VALIDATED
      -> PRIVATE_STAGING_ALLOCATED
      -> ONLINE_BACKUP_COPYING
      -> DESTINATION_CLOSED
      -> SNAPSHOT_VALIDATED (including cursor read from destination)
      -> MANIFEST_FINALIZED
      -> PUBLISHED_GENERATION
      -> PRE_BACKUP_HOOK_SUCCESS
      -> ARCHIVE_CONSUMER_STATUS_UNKNOWN
      -> RETAINED / VERIFIED_IN_ARCHIVE / SAFE_RETIRED

    any phase before PUBLISHED
      -> FAILED / CANCELLED
      -> disposable incomplete staging; previous good snapshot preserved

    PUBLISHED and missing post hook
      -> ORPHANED_PUBLISHED
      -> still immutable, live history producer unaffected; prune only if safe

The pending snapshot file can be prepared in a private disposable staging area; it must not be treated as authoritative backup data. A private HA cache subdirectory is an option for **in-progress only** data because it is excluded from backed-up config. Final published generation MUST live in a selected archive-included location. Verify same-filesystem rename durability and recovery if staging and final paths differ.

**Publication handshake:** close SQLite destination; validate snapshot as read-only/immutable only if it truly cannot change; obtain ledger UUID, schema and cursor from the destination; compute digest/size; publish generation-specific snapshot+manifest plus completion marker using tested filesystem operations. Do not infer a two-file rename is an atomic transaction. A restart scans only fully validated published generations, never reads pending scratch as a good backup.

**Archiver limitation:** An immutable snapshot can coexist with a mutable live SQLite file inside the same HA config archive. Therefore the backup platform may be able to prepare safe source data but still cannot claim that the complete tar file is automatically safe to restore as a whole. Need an approved restore selection/real-file exclusion solution.

## 4. Concrete proposed manifest contract (not JSON implementation)

| Field | Type / source | Protection |
| --- | --- | --- |
| manifest_format | immutable integer version | Unsupported newer version rejected |
| snapshot_uuid | random opaque stable generation ID | Unique, never reused |
| ledger_uuid | persistent actual source ledger identity | Must match allowed target lineage |
| schema_version | DB read after snapshot completion | No auto-downgrade |
| accounting_policy_version | DB domain metadata | Do not conflate inferred and confirmed duration |
| committed_cursor | read from completed snapshot | No live DB cursor substitution |
| snapshot_as_of_utc | source observation evidence cap | Explicit coverage limit |
| created_at_utc | backup process clock | Not evidence of PlayStation power transition |
| snapshot_relative_basename | internally fixed | No absolute path/.. traversal |
| file_size | bytes from completed snapshot file | Exact size on restore |
| sha256 | digest of final stable snapshot bytes | Not an origin signature |
| sqlite_version | runtime SQLite info | Helps compatibility audit |
| validation_summary | integrity/FK/schema passed | Do not store raw private rows |
| complete_marker | publication protocol generation | Only final validated generation |
| archive_scope | known config scope when verified | Do not fake Supervisor job ID |
| source_kind | OnlineBackup / reviewed other | No third-party raw copy trusted by default |

A complete marker must be consistent with manifest and immutable contents after crash/restart; it is not a cryptographic authorization.

## 5. Acceptance test matrix — ALL NOT_RUN

### 5.1 SQLite Online Backup worker and correctness — 16

| ID | Synthetic future test | Expected result |
| --- | --- | --- |
| SN-COPY01 | Source DB and destination connections are distinct | No deadlock or shared-handle misuse |
| SN-COPY02 | Running backup while 2 console writers commit via manager | Snapshot consistent and source history unaffected |
| SN-COPY03 | Source changed via other SQLite connection mid-step | Backup restarts/reconciles under bounded deadline |
| SN-COPY04 | Continuous write traffic causes repeated restarts | Timeout/error, not infinite task, old snapshot retained |
| SN-COPY05 | SQLITE_BUSY/LOCKED on destination/source | Bounded retry and valid cleanup |
| SN-COPY06 | SQLITE_IOERR / SQLITE_READONLY | Abort, no completed generation |
| SN-COPY07 | Disk full during destination copy | No misleading committed artifact |
| SN-COPY08 | Cancellation between backup steps | Destination cleanup, no stale connection |
| SN-COPY09 | Cancellation after backup complete before close | Not published without close/verification |
| SN-COPY10 | Source closed/reloaded while copy active | Lease fences source safely or classified failure |
| SN-COPY11 | Source worker disallowed on HA event loop | Event loop responsiveness accepted by future benchmark |
| SN-COPY12 | Large 3-year synthetic dataset and incremental pages | Bounded latency/CPU/RAM, progress truthful |
| SN-COPY13 | Snapshot cursor read after concurrent writer advanced | Snapshot cursor exactly matches copied dataset |
| SN-COPY14 | Integrity check passes, FK check fails | Snapshot rejected |
| SN-COPY15 | Destination has mutable SQLite sidecar/connection | Snapshot not published as a single immutable file |
| SN-COPY16 | Current SQLite runtime vulnerable to WAL-reset race | WAL gate blocks unsupported concurrency configuration |

### 5.2 Manifest, publication, retention and crash points — 16

| ID | Synthetic future test | Expected result |
| --- | --- | --- |
| SN-PUB01 | Crash before destination allocated | No artifact advertised |
| SN-PUB02 | Crash during copy | Incomplete disposable staging ignored |
| SN-PUB03 | Crash immediately after copied file closed | No completion marker, never advertised valid |
| SN-PUB04 | Crash during integrity verification | No valid generation published |
| SN-PUB05 | Crash while hashing | No valid generation published |
| SN-PUB06 | Crash after manifest write before final barrier | Staging ignored; no half-generation |
| SN-PUB07 | Crash between snapshot and manifest promotions | Directory/marker protocol rejects partial pair |
| SN-PUB08 | Atomic rename across different filesystems rejected | Safe staged copy into destination, no false atomicity |
| SN-PUB09 | Final manifest references wrong relative filename | Restore rejects and never traverses arbitrary paths |
| SN-PUB10 | Manifest SHA256 differs from SQLite bytes | Restore rejects; old valid artifact retained |
| SN-PUB11 | Completed snapshot modified after publication | Immutable check / hash mismatch prevents promotion |
| SN-PUB12 | Two pre-backup calls concurrently for same ledger | Serialize or explicitly coalesce; no collision |
| SN-PUB13 | Two generations with different cursors | Deterministic listing, never arbitrary "latest filename" choice |
| SN-PUB14 | Retention runs while archive reads published generation | No deletion while archive may still need it |
| SN-PUB15 | Many failed attempts fill temp directory | Bounded cleanup preserving last good snapshot |
| SN-PUB16 | No snapshot available and source corrupt | Backup hook fails explicitly, not false safe archive |

### 5.3 Supervisor archive integration, exclusions and hook failures — 16

| ID | Future HA OS / source test | Expected result |
| --- | --- | --- |
| SN-ARC01 | Inspect Supervisor excluded patterns | No false claim that app can return custom file exclusions via pre/post hook |
| SN-ARC02 | Back up history.sqlite3 + active -wal | Verify exact live files present/absent, classify raw copy trust |
| SN-ARC03 | Backup history.sqlite3-shm with fixed *.db-shm pattern | Verify naming-dependent exclusion, no assumed match |
| SN-ARC04 | Backup immutable published snapshot generation | Manifest and SQLite payload both present and unchanged |
| SN-ARC05 | Prehook online snapshot while LAN monitor writes | No archive-long writer freeze required |
| SN-ARC06 | Another integration prehook fails after our snapshot published | No frozen writer; orphan artifact safe |
| SN-ARC07 | Supervisor backup/start connection fails | No indefinite state lock; no safe-backup claim |
| SN-ARC08 | Supervisor returns no backup/end | Live monitoring remains viable; snapshots retained safely |
| SN-ARC09 | Core non-Supervisor backup implementation used | Source/filters independently checked, not conflated with Supervisor |
| SN-ARC10 | App-specific backup agent writes other archive scope | Does not imply HA OS selected config contains data |
| SN-ARC11 | User deselects Core configuration in partial backup | No claim snapshots included |
| SN-ARC12 | User deselects Recorder DB | Warning: PlayStation Hub data still potentially included |
| SN-ARC13 | Hub-only Config Entry loaded during system backup | Backup platform loads and snapshots existing ledger without console probes |
| SN-ARC14 | No Hub/console/account Config Entries loaded | Explicit absence of prehook guarantee and user documentation |
| SN-ARC15 | Backup tar includes both raw live and validated snapshot | File-level ambiguity recognized, no silent restore policy |
| SN-ARC16 | Backup hook success, archive truncates/corrupts later | Locally published != verified archived; failure visible |

### 5.4 Restore, authority, ACL and release behavior — 16

| ID | Future fault or integration test | Expected result |
| --- | --- | --- |
| SN-REST01 | Normal restart, live cursor 180, snapshot 100 | Use verified live source, preserve 80 newer commits |
| SN-REST02 | Restored archive has raw SQLite + snapshot and valid ledger UUID | Admin-guided choice or proven authority; no blind raw-copy selection |
| SN-REST03 | Raw DB accidentally internally valid but differs from snapshot | Integrity alone does not establish authority |
| SN-REST04 | No verifiable restoration intent marker | Do not claim universal automatic recovery detection |
| SN-REST05 | Explicit snapshot import with wrong ledger UUID | Reject cross-instance auto-merge |
| SN-REST06 | User-approved import after preserving original live files | Copy/validate in isolation then atomically promote with new run generation |
| SN-REST07 | Restore older schema unsupported by current runtime | Guarded readable/recovery error, no destructive migration |
| SN-REST08 | Restore after config/ledger identity split-brain | Fence writes; require review of console/account associations |
| SN-REST09 | Restore snapshot with missing recent hours | Time gap UNKNOWN; no made-up gaming minutes |
| SN-REST10 | Restored snapshot contains OAuth/Remote Play secret | Reject unauthorized leakage / enforce segregation |
| SN-REST11 | Snapshot exposed via static frontend path | No public download of private historical DB |
| SN-REST12 | Non-admin tries recovery/restore command | Denied without side effect |
| SN-REST13 | Old frontend API version issues restore | Rejected or requires compatible refresh |
| SN-REST14 | User deletes physical console but keeps Hub | Archive still queryable; no monitor |
| SN-REST15 | Plugin source upgraded, DB remains, snapshots retained | No overwrite of private app files by HACS update |
| SN-REST16 | Three installation types tested (HA OS/Container/other supported) | Actual path/backup limitations documented by support matrix |

**Count:** 64 proposed new cases (16 COPY + 16 PUB + 16 ARC + 16 REST), all NOT_RUN. Existing SPEC-008 (46), SPEC-009 (56), SPEC-010 (56) and SPEC-011 (64) remain in force; overlap intentional, no unique total claimed as a passed test count.

## 6. Approval and release gates — ALL OPEN

| Gate | Evidence needed | State |
| --- | --- | --- |
| SN-G01 | Actual linked SQLite runtime and patched WAL-release support | BLOCKED_HA_OS |
| SN-G02 | Library/connection worker bound and non-blocking | NOT_RUN |
| SN-G03 | Backup completion under concurrent source writes and bounded deadlines | NOT_RUN |
| SN-G04 | Destination close and self-contained SQLite artifact | NOT_RUN |
| SN-G05 | Integrity, foreign keys, ledger UUID and snapshot-owned cursor verified | NOT_RUN |
| SN-G06 | Crash-safe multi-file publication with generation marker, same-volume / fsync | NOT_RUN |
| SN-G07 | One-flight snapshot job and bounded resource use | NOT_RUN |
| SN-G08 | Missing post/failed other prehook does not affect live write availability | NOT_RUN |
| SN-G09 | Source archive membership and inability to custom-exclude verified | SOURCE_CHECK_DONE / HA_OS_NOT_RUN |
| SN-G10 | No untrusted raw DB/WAL automatically chosen on restore | PROPOSED |
| SN-G11 | Explicit admin recovery or trusted restore intent with lineage proof | PROPOSED |
| SN-G12 | All critical HA OS backup/failure/partial restore cases exercised | BLOCKED_HA_OS |
| SN-G13 | Snapshot cannot be pruned while archive potentially reading it | NOT_RUN |
| SN-G14 | Hub-only backup hook and panel across restart | NOT_RUN |
| SN-G15 | Private data, no Sony token or static exposure, complete ACL | NOT_RUN |
| SN-G16 | Integration release/update/rollback and external backup compatibility | NOT_RUN |

**Research blocker — not a pass:** Core 2026.11.0 pre/post hook has no exposed custom archive-filter return contract; raw DB/WAL copy remains a backup-restore ambiguity unless the actual selected layout eliminates the raw source or the restore selector explicitly handles this risk.

## 7. Documentation approval vs implementation approval

The conceptual data ownership and Hub/Archive Config Entry decisions were accepted by the maintainer on 2026-11-06 and are tracked in ADR-0011. They can be used as design constraints in future research. The complete snapshot API, retention, path, backup/archive selection, restoring old snapshots, SQL PRAGMAs and product restore UX remain CONDITIONAL/PROPOSED and require HA OS/synthetic tests and later explicit implementation authorization.

No source code, fixture, test or migration was created by publishing this specification. The legacy develop branch is frozen; only main documentation is being updated.

## 8. References

- [Pinned upstream source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md)
- [Accepted conceptual scope ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [SPEC-011](SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md)
- [SPEC-010](SPEC-010-crash-recovery-restore-provenance-and-archive-access.md)
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/c3ref/backup_finish.html
- https://www.sqlite.org/uri.html
- https://www.sqlite.org/pragma.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/knx/backup.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Status:** 64 NOT_RUN cases, 16 open gates, no code/tests/HA OS invocation.
