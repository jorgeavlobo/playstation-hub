# ADR-0012 — Immutable SQLite snapshot backup protocol and safe restoration authority

**Status:** PROPOSED — research preference accepted; implementation method and restore policy NOT ACCEPTED
**Date:** 2026-11-06
**Domain:** playstation_hub
**Decision owner:** Project maintainer
**Source:** [Immutable snapshot source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md)
**Test contract:** [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md)
**Dependencies:** [ADR-0011 conceptual architecture](ADR-0011-storage-layout-restore-authority-archive-hub.md), ADR-0006/0008/0010, SPEC-009/010/011.
**Environment:** HA Core 2026.11.0, Supervisor SHA 69848689a1e982ebe92d80e344fc086d8af667db.
**Branch:** main documentation only; legacy develop frozen.

> The maintainer accepted the suggestion to **prioritize research into immutable Online Backup API snapshots** and the archive-first product architecture. This is not approval to implement an unvalidated snapshot protocol or assert that an HA OS archive is safely restorable.

## 1. Context

PlayStation Hub should keep long-lived private SQLite history across backups, recover from crashes and respect independent runtime entries. An SQLite Online Backup API snapshot is internally consistent while live data may continue changing. However Home Assistant Supervisor may concurrently archive the mutable live application database and its WAL from the same configuration tree. The tested upstream backup pre/post interface offers preparation/resumption callbacks, not a documented per-integration file-exclusion request.

The existing alternative — quiescing all SQLite writes until Supervisor ends its archive — is source-blocked: Core may have completed the PlayStation Hub pre hook, another integration fails its pre hook, Supervisor begin_backup raises before entering its end_backup finally; there is no matching post hook guaranteed. A timeout unfreeze during an active archive may invalidate it.

## 2. Unconditional project requirements already accepted

- One Marketplace/HACS custom integration and one full-page sidebar, with a single shared manager.
- A separately user-confirmed logical Hub/Archive Config Entry, plus independently owned physical-console and PSN account entries.
- Historical data retained independently of entry removal; deletion requires explicit user action.
- Private app-owned historical data outside HACS executable source, using supported HA APIs, not host hardcoded paths.
- No unconditional MQTT broker, add-on, external database or cloud dependency.
- An ordinary restart must NEVER automatically overwrite a valid newer ledger with an older snapshot.
- The initial archive and restore product must be honest about coverage gaps and permissions.

The **exact database path**, backup technology selection, automatic restore guarantee and security/durability benchmarks are not unconditional accepted deliverables.

## 3. Alternatives considered

| Option | Strength | Weakness/blocker | Decision state |
| --- | --- | --- | --- |
| I. Online Backup API snapshot + self-derived manifest | Consistent immutable copy, no archive-long freeze | Live raw DB/WAL also archived and automatic selection unknown | Preferred subject for investigation — NOT_IMPLEMENTATION_APPROVED |
| II. Full pre/post write quiescence | Stable raw main DB during tar | Post hook not guaranteed if other pre hook fails; long polling gaps | BLOCKED_PENDING_SAFE_RESUME |
| III. WAL checkpoint before tar, then resume | Fewer outstanding WAL frames | File can mutate while tar reads | REJECT |
| IV. Raw SQLite DB/WAL copies in tar | No integration-specific hook | No consistent atomic multi-file snapshot | REJECT |
| V. Private live SQLite outside config; only staged snapshot under config | Archive omits live source by placement | Path portability and older-config/newer-ledger identity split-brain | CONDITIONAL_RESEARCH |
| VI. User-authorized app-specific export/import | Explicit provenance and restore | No seamless whole-home restore | Fallback candidate |
| VII. VACUUM INTO | Official consistent compact copy | Crash, I/O and deadline differences | Optional benchmark |

## 4. Proposed bounded snapshot producer contract

- One HubController-owned snapshot lease per ledger and generation, separate from normal console probes.
- Verify database schema/owner version, actual SQLite runtime, free space and private path; refuse silent empty recreation on failure.
- Create disposable private staging and a distinct SQLite backup destination. Run SQLite Online Backup API off the HA event loop using a reviewed worker, with bounded page count/deadline and exact cleanup on cancellation.
- Understand API restarts when other source connections commit during incremental copying. The copy cannot be assumed bounded without a deadline, write-rate control or short verified barrier.
- Finish/close destination, verify it is self-contained and immutable, inspect integrity_check, foreign_key_check, schema and ledger_uuid, read its own committed cursor, then compute exact SHA256/byte size.
- Publish snapshot+manifest within a unique immutable generation with a crash-safe final visibility barrier; a pair of independent file renames is not automatically atomic.
- Return successful pre hook only when snapshot is locally PUBLISHED and validated. This does not certify that Supervisor included it in a finished backup archive.
- Make post hook best-effort cleanup, not a necessary release of the live SQL write lock. Missing post hook must leave live observations/writes operational.
- Guard retention against snapshots still being archived; maintain last known verified good artifact and bounded disk use.

**Not a release guarantee:** The implementation does not yet have an upstream-supported method to exclude the active app DB/WAL from the same HA configuration archive. This is the primary reason automatic restoration remains conditional.

## 5. Snapshot authority and backup metadata

The manifest stores only safe, necessary provenance: format version, snapshot_uuid, ledger_uuid, schema version, policy version, exact relative snapshot filename, byte size, hash, completed UTC, DB-owned cursor, source SQLite library version and validated completion marker. No Sony tokens or raw history records.

A healthy live DB always wins on an ordinary startup; archived snapshots are not blindly promoted. A selected restore requires a verified explicit admin action or supported trusted intent, exclusive database lifecycle fencing, preservation of existing original files, exact hash/integrity/FK/identity checks and a new runtime lineage. The Supervisor can already have overwritten live config files before the integration boots, so detecting every true restore purely from local files is not guaranteed.

Do not guess a snapshot's inclusion from pre-hook success; do not guess a matching HA backup job ID if not exposed to the custom integration. Do not infer snapshot freshness from file mtime alone.

## 6. Risks, mitigations and evidence needed

| Risk | Mitigation to investigate | Evidence required |
| --- | --- | --- |
| Missing post hook | Snapshot producer without archive-long live lock | Simulated other integration's failed prehook and HA OS |
| Unbounded SQLite copying | Bounded job and controlled short source barrier | Heavy-write synthetic 3-year dataset |
| Published snapshot invalid | Snapshot-contained cursor, integrity/FK, digest, publication marker | Crash at each publication edge |
| Raw DB/WAL archived | Exact Supervisor file enumeration plus explicit authority | Real tar member inspection and restore |
| User restores old snapshot at normal reboot | Never auto-promote when valid newer live source exists | Restore/reboot round trip tests |
| Snapshot deleted during tar read | Lifecycle lease and safe GC after real archive completion proof | Race injections |
| No Hub Config Entry loaded | Honest backup platform availability | Disabled/hub-only restart tests |
| External live root split-brain | Stable identity association epoch, manual recovery | Partial old-config restore test |
| History or keys exposed | Private paths, ACL, distinct secret store | Security review / malicious requests |

## 7. Decision status

- **ACCEPTED at product/design direction level via ADR-0011:** logical Hub/Archive entry, one integration/controller/panel, independent console/account entries, history retention and private path direction.
- **ACCEPTED as next research priority:** immutable online SQLite snapshots with non-destructive publication and recovery semantics.
- **PROPOSED / NOT_IMPLEMENTED:** using Online Backup API specifically as first-release backend, exact snapshot format/path/worker, automatic restore, retention, free-space limits, runtime SQLite version policy.
- **BLOCKED:** archive-long quiescence without a proven safe resume; custom per-file exclusion in the pinned Supervisor archive not established; HA OS test results absent.
- **NOT_RUN:** 64 SPEC-012 cases and 16 gates (alongside older specs).

No new code, test, database, environment mutation or implementation branch is authorized.

## 8. Sources

- [Research audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md)
- [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md)
- [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md)
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/c3ref/backup_finish.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/uri.html
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Outcome:** Research direction approved; operational protocol and restore correctness still unapproved and untested.
