# SPEC-009 — Shared service lifecycle, concurrent Config Entries and SQLite safety

**Status:** PROPOSED / NOT_IMPLEMENTED / ALL_TESTS_NOT_RUN  
**Date:** 2026-11-06  
**Core source baseline:** home-assistant/core tag 2026.11.0  
**Primary evidence:** [Shared service source audit](../research/ha-core-2026-11-shared-services-lifecycle-and-sqlite-audit.md)  
**Related plans:** SPEC-008, SPEC-005, ADR-0004, ADR-0006, ADR-0008, ADR-0010  
**Branch:** main documentation only. develop unchanged. No feature branch or executable work authorized.

> Every normative MUST / SHOULD below is an internal **candidate contract**, not a claim that Home Assistant or PlayStation Hub already implements it. No ADR status changes without explicit maintainer approval.

## 1. Scope and goals

Formalize the interaction between N physical console Config Entries, M optional PSN account Config Entries, one process-global HubController, one serialized SQLite writer, bounded readers, one frontend panel and one authenticated WebSocket command namespace.

The design must prevent duplicate initialization, premature resource closure, lost/duplicated transactions, leaked tasks and misleading historical availability. It must work when setup, unload, network I/O, backup and user dashboard queries overlap.

## 2. Component ownership table

| Component | Construction authority | Holder | Destruction trigger |
| --- | --- | --- | --- |
| HubController / lease registry | Integration async_setup, once per HA process | hass.data scoped to domain | HA process shutdown |
| Static asset path | Domain-level UI registration, once | Home Assistant HTTP router | Core restart unless a verified supported removal mechanism exists |
| Sidebar panel entry | Domain-level UI registration, once | Frontend panel registry | Explicit panel remove policy; not per-console unload |
| WebSocket command handlers | Domain-level API registration, once | HA global WebSocket registry | Process lifetime; handlers must resolve active facade dynamically |
| HistoryService, SQLite writer | HubController single-flight lifecycle | One active/closing DB generation | No holders and no pending accepted operations; bounded close |
| SQLite read transaction | Authorized query operation | Query lease | Pagination completed / deadline / disconnect |
| SQLite snapshot | Verified backup/export operation | Snapshot lease | Completed / cancelled / timeout with classified error |
| ConsoleRuntime / transport | One physical console Config Entry | Typed entry.runtime_data | This entry's unload/failure |
| PsnAccountRuntime | One account Config Entry | Typed entry.runtime_data | This account's unload/failure |
| LAN monitor task | Corresponding ConsoleRuntime | Entry-owned task | This console's unload/polling disabled |
| Frontend subscription | One authenticated WS connection | Connection callback/unsubscribe | Disconnect/unsubscribe/revocation |
| Historical rows | User-controlled persistent storage | Durable ledger, not in-memory task | Explicit documented purge/archive policy |

## 3. Lifecycle lock, generation and lease contract

**L1.** The controller exposes a single serialized state transition guard; no entry may create/close SQLite directly.

**L2.** The guard protects metadata and lifecycle transitions only. SQL, disk I/O, network activity, migrations, platform setup and arbitrary callbacks occur outside the guard using fenced operations.

**L3.** Exactly one initialization result is shared by all concurrent pending owners. When the initializer fails, all waiters see a classified failure; a controlled subsequent retry is permitted without retaining a broken future indefinitely.

**L4.** The controller is independent of which Config Entry started first and may hold zero ready entries.

**L5.** Each lease has an opaque ID and generation, owner kind (entry/query/snapshot/export), associated canonical scope and explicit state. Duplicate release is harmless. Cross-owner or old-generation release cannot alter another owner's count.

**L6.** At most one database generation may be INITIALIZING/READY/QUIESCING/CLOSING at a time. Acquires arriving during CLOSING wait for completion or fail explicitly; they never bypass a partially closed writer.

**L7.** Every accepted write carries the current canonical target ID, entry runtime generation and globally unique/idempotent observation ID. Late work fails its fence.

**L8.** Once an operation is admitted, release/teardown either completes it or returns a classified failure. It must not silently disappear due to cancellation of an unrelated entry/browser.

**L9.** No pending/active entry, query, snapshot or export may be forgotten during close. All leases have deterministic cleanup and meaningful deadlines.

**L10.** Unload failure cannot assert resource-free or signal fully closed until positive evidence exists; may enter FAILED_UNLOAD/DEGRADED.

## 4. Proposed initialization transaction

    1. Validate source identity (without writing history).
    2. Acquire PENDING entry lease under controller lifecycle guard.
    3. Register idempotent fallback cleanup with Config Entry immediately.
    4. Await one manager-owned HistoryService initialization task.
    5. Validate DB file ownership, schema and migrations before enabling writes.
    6. Construct a typed per-entry transport/reducer/coordinator in prepared/inert mode.
    7. Assign entry.runtime_data BEFORE forwarding; register cleanup on allocation.
    8. Await HA platform forwarding; forwarded entities read entry.runtime_data.
    9. Activate entry lease BEFORE admitting monitored observations to the writer.
   10. Start autonomous monitor, and report success only when setup contract holds.

**Failure compensation:** Stop source-owned work and explicitly release the pending/active lease through one awaited cleanup path. Core's async_on_unload callback is a secondary idempotent safety net, not the mechanism that guarantees ordering.

**Shutdown order:** Invalidate source generation -> stop probes/commands -> settle outstanding writes -> unload HA platforms -> detach listeners -> release entry lease -> close DB only when no other holders/operations remain. On platform unload failure, retain a tracked/fenced lifecycle holder rather than claim clean disposal.

## 5. SQLite transaction and visibility model

**Ingest acceptance is not durability.** The reducer may accept an observation before the writer commits it. The API/HA entities must distinguish fresh observation from successfully persisted session evidence.

One logical history transaction should atomically include the validated observation ID, source and owner, state/session segment changes, unknown interval changes, and durable high-water cursor. No partial committed checkpoint.

Use a single serialized writer; multiple bounded read connections are permitted only under an approved connection/worker model. No synchronous SQLite operations on the Home Assistant event loop. SQLite writes must not depend on a browser subscription or the presence of entity listeners.

**Idempotent replay:** If the caller is cancelled after COMMIT but before receiving acknowledgement, lookup/replay using the same idempotency key cannot double-credit session time.

**Backpressure:** Bound queues/worker count/per-console quotas; prioritize orderly draining and error classification. If the writer is unavailable, avoid unbounded in-memory buffering and expose unrecorded intervals.

**WAL:** Long-lived reads can block checkpoint completion. Control query lifetime and observe WAL size/checkpoint success; a clean shutdown must close underlying connections, not assume WAL file removal proves that all data was saved. Exact synchronous/journal/busy PRAGMAs require measurement on target HA OS.

## 6. UI, API and zero-entry semantics

The single panel and registered WebSocket handlers are process-scoped. They do not own a live SQLite writer and do not create independent console pollers. Every query obtains a short-lived data operation lease after server-side authentication/authorization and checks API version and runtime generation.

Registration must:
- establish intended panel and static route ownership before publishing;
- detect route collisions instead of silently hiding them;
- register WebSocket commands exactly once (Core 2026.11.0 does not reject duplicate command names at the inspected helper);
- never re-register the entire panel on a Config Entry reload;
- never return raw provider credentials or unrestricted private history;
- fail safely when no configured/loaded targets are available.

**Candidate initial zero-entry policy:** panel remains while any actual PlayStation Hub Config Entry exists, even if that entry is offline/disabled, but removal of the last entry hides the menu. The DB remains retained until explicit deletion. An archive-only hub entry is a later product decision, not implemented. This policy is not equivalent to closing on zero runtime leases; configured entries and loaded entries differ.

## 7. Backup and restore acceptance blockers

Core's backup platform hooks exist, but **HA OS Supervisor-specific invocation and archive contents remain unverified**. No claim of safe automatic backup until the exact HA OS route has been tested.

A proposed consistent backup has a separately generated SQLite Online Backup API snapshot and manifest, with integrity, checksum, schema/version, canonical data identity, UTC timestamp, committed cursor and an explicit restore selection policy. Snapshot should be immutable while archived.

Tests must inspect:
- inclusion of both snapshot and manifest in a real HA OS backup;
- whether the running DB and WAL are also archived, and if so how unsafe copies are ignored;
- recovery if pre/post hooks do not run or are interrupted;
- partial/no-database/system-level backups;
- backup initiated by other mechanisms or integration disabled;
- first boot restore with stale state, time gap, new runtime generation and zero fabricated minutes.

Backups of the generic Core path are not a substitute for testing the HA OS Supervisor path. An archive containing files is not proof of a recoverable consistent ledger.

## 8. Test methodology (planned; no tests written)

Use synthetic fake entries, fake transports, fault-injecting SQLite worker and a controlled event scheduler to force interleavings. Simulate process crash/kill and recovery in a separate future test layer; then repeat on Home Assistant OS 2026.11 with real backup exports. Assertions must use ownership tokens, generation IDs, transaction receipts, query result counts and actual task/socket counts. No human-readable log alone counts as proof.

Each test must record PENDING / NOT_RUN / PASS / FAIL / BLOCKED_HARDWARE / BLOCKED_HA_OS, pinned Core version, relevant source evidence and reproducible fixture. The matrix below is a design, **not executable code**.

### 8.1 Initialization, acquisition and retry — 12 NOT_RUN

| ID | Synthetic case | Required result |
| --- | --- | --- |
| SH-INIT01 | Entry A and B start simultaneously | One initialized HistoryService, one migration, two independent leases |
| SH-INIT02 | Five entries initialize together | One initialization future and one ready writer |
| SH-INIT03 | A cancels while B waits | B completes; A pending token releases |
| SH-INIT04 | All setup waiters cancel | Initialization and resources quiesce; no orphan |
| SH-INIT05 | First initialization fails | All waiters receive classified error; no false READY |
| SH-INIT06 | Retry after classified transient init failure | One new clean generation, no reuse of corrupted future |
| SH-INIT07 | Init fails after DB connection opens | Connection closed, no dangling worker |
| SH-INIT08 | Concurrent setup during schema migration | Migration once; no reader sees partial schema |
| SH-INIT09 | Entry starts during prior generation CLOSING | Wait/reopen; no overlapping writer |
| SH-INIT10 | Duplicate acquire/release for same entry | Idempotent release; no negative lease count |
| SH-INIT11 | Old runtime releases against new generation | New generation holder unaffected |
| SH-INIT12 | Different physical consoles same model/account | Distinct entry owners, shared data service only |

### 8.2 Unload, final close and crashes — 12 NOT_RUN

| ID | Scenario | Required result |
| --- | --- | --- |
| SH-LC01 | A unloads while B is ready | B continues monitoring/writing; singleton retained |
| SH-LC02 | A unloads while B setup pending | No closure during B's pending ownership |
| SH-LC03 | Last entry unloads with a paged read active | Read completes or fails explicitly before close |
| SH-LC04 | Last entry unloads during backup snapshot | Snapshot lease prevents premature close |
| SH-LC05 | Pending write after entry fence | No illegal new write; prior admitted write settled |
| SH-LC06 | Platform unload raises | FAILED_UNLOAD tracked; no premature shared closure |
| SH-LC07 | Cleanup callbacks race with explicit cleanup | Exactly-once resource release |
| SH-LC08 | Background task ignores cancellation | Leak detected; no false closed status |
| SH-LC09 | HA shutdown with 10 consoles | Bounded shutdown, zero active sources after process exit |
| SH-LC10 | HA shutdown interrupted by process kill | Restart identifies gap and replay cursor without fake duration |
| SH-LC11 | Reload one console 100 times | No excess tasks, sockets, leases, panels or writers |
| SH-LC12 | One account removed while two LAN consoles remain | Account scope only revoked |

### 8.3 Ledger concurrency and fairness — 12 NOT_RUN

| ID | Scenario | Required result |
| --- | --- | --- |
| SH-DB01 | Two consoles commit alternating evidence | Ordered per-source, transactional, no cross-ID attribution |
| SH-DB02 | Same observation submitted twice | One durable row/segment effect |
| SH-DB03 | Commit succeeds, caller loses acknowledgement | Retry does not add minutes twice |
| SH-DB04 | Exception midway through logical SQL write | Entire transaction rolled back |
| SH-DB05 | Queue full on console A | B not starved; A history marked incomplete |
| SH-DB06 | Disk-full condition | No unbounded queue; current state vs history health separated |
| SH-DB07 | SQLITE_BUSY under WAL | Bounded retry/degrade, no event-loop block |
| SH-DB08 | History query cancelled by browser | Query lease released, writer unaffected |
| SH-DB09 | Long reader holds old WAL snapshot | Bounded cancellation, checkpoint recovers |
| SH-DB10 | Corrupt DB on open | Fail safe / quarantine; never silently recreate empty history |
| SH-DB11 | Schema version newer than implementation | No destructive downgrade or migration |
| SH-DB12 | Stable console reconfigured from old IP | Same history namespace; late old-generation packets rejected |

### 8.4 Panel, WebSocket and access — 8 NOT_RUN

| ID | Scenario | Required result |
| --- | --- | --- |
| SH-UI01 | Two entries configured concurrently | Exactly one sidebar route registration |
| SH-UI02 | 100 unload/reloads | WebSocket registrations not multiplied |
| SH-UI03 | Panel route occupied by another component | Safe collision error, no overwrite |
| SH-UI04 | Same WebSocket command accidentally registered twice | Registration guard detects collision before mutation |
| SH-UI05 | Two browser windows connect | One console probe cadence, independent WS subscriptions |
| SH-UI06 | Browser disconnect during report query | Cancellation and query lease release |
| SH-UI07 | Last entry removed | Explicit no-entry panel policy, retained history |
| SH-UI08 | Old frontend sends unsupported schema/target | Unauthorized or incompatible request rejected, no stale action |

### 8.5 Backup, restore and lifecycle interoperability — 12 NOT_RUN / BLOCKED_HA_OS

| ID | Scenario | Required result |
| --- | --- | --- |
| SH-BK01 | Core non-Supervisor backup with custom DB active | Hook invocation and included file paths characterized |
| SH-BK02 | HA OS Supervisor full backup | **BLOCKED_HA_OS** until hook invocation verified |
| SH-BK03 | HA OS partial backup excluding HA config | No false promise that history was backed up |
| SH-BK04 | Live WAL grows while backup is archived | Snapshot remains consistent and attributable to its cursor |
| SH-BK05 | Archive contains raw DB and WAL | Restore explicitly selects verified snapshot, not unsafe copy |
| SH-BK06 | Snapshot interrupted before completion | No valid-looking partial snapshot promoted |
| SH-BK07 | Post-backup hook not called / process killed | Orphan snapshot cleanup and next backup safe |
| SH-BK08 | Restore backup created before latest sessions | Missing time represented as gap, not retroactive continuous usage |
| SH-BK09 | Snapshot checksum or schema mismatch | Restore rejected safely, old files preserved |
| SH-BK10 | Backup overlaps schema migration | Serialized/quiesced; no half-upgraded snapshot |
| SH-BK11 | Two backup requests overlap | One coherent snapshot policy, no temp overwrite |
| SH-BK12 | HA OS upgrade/restart after last Config Entry removal | Archive access/retention behavior matches approved policy |

**Total: 56 new SPEC-009 scenarios** (12 INIT + 12 LC + 12 DB + 8 UI + 12 BK); all are test designs only. SPEC-008's previous 46 cases remain separate and unrun; integration-level duplication can later be collapsed into a canonical test suite.

## 9. Sign-off gates (all open)

| Gate | Evidence to close | State |
| --- | --- | --- |
| SH-G01 | Chosen global ownership and single-flight lifecycle protocol | PROPOSED |
| SH-G02 | Safe pending/active/query/snapshot lease semantics | NOT_RUN |
| SH-G03 | Ordered cleanup that survives failed setup and unload | NOT_RUN |
| SH-G04 | No concurrent writers or duplicate migrations | NOT_RUN |
| SH-G05 | Transactional/idempotent ledger and bounded backpressure | BLOCKED_STORAGE |
| SH-G06 | Verified WAL durability/backup PRAGMAs on target OS | BLOCKED_HA_OS |
| SH-G07 | Real Supervisor pre/post hook and archive verification | BLOCKED_HA_OS |
| SH-G08 | Restore integrity and explicit uncertain gaps | BLOCKED_HA_OS |
| SH-G09 | Once-only panel/static/WS and collision handling | NOT_RUN |
| SH-G10 | Zero-entry menu, archive retention and access product policy | PROPOSED |
| SH-G11 | Shutdown/failure leak proof for many simultaneous entries | NOT_RUN |
| SH-G12 | Privacy-safe diagnostics and ACL for closed/degraded services | NOT_RUN |

**No implementation may claim these gates are passed on the basis of this document.** Hardware status, Sony authorizations, exact SQLite library and minimum Home Assistant version remain separate prerequisites.

## 10. Cross-reference and priorities

**P0 before coding:** approve conceptual ownership, single-flight design, entry cleanup semantics, data failure UX and zero-entry panel policy; source-verify HA OS backups and static route limitations.

**P1 before accepting history functionality:** implement in a later authorized work package and pass SH-INIT, SH-LC, SH-DB suites with fault injection, HA OS backup/restore and schema migration; validate against SPEC-008.

**P2 before release:** longevity, health telemetry, permissions, upgrade/uninstall and catalogue/quality requirements.

Sources:
- [Pinned official-source shared manager audit](../research/ha-core-2026-11-shared-services-lifecycle-and-sqlite-audit.md)
- [SPEC-008](SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md)
- [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html

**Implementation status:** All 56 new tests NOT_RUN, all 12 gates open; no executables, source files, workflow runs or real console/HA OS tests were created.


## 11. Source update — Supervisor backup hooks traced (2026-11-06)

The accompanying research audit §17 now traces a concrete path from Supervisor backup archiving to Core's authenticated **backup/start** and **backup/end** WebSocket handlers, which invoke pre/post integration backup platform hooks (Core tag 2026.11.0; Supervisor pinned commit 69848689). This replaces the weaker "path entirely unverified" source characterization in §7. **SH-BK02 remains BLOCKED_HA_OS for runtime execution**, not for absence of upstream hook code. Exact custom integration platform loading, snapshot location, archiving of live DB/WAL, restore precedence and failure handling are still unproven. The 56 test cases and 12 gates retain their status.

- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/core/blob/2026.11.0/tests/components/backup/test_websocket.py


## 12. Corrected ordering evidence — 2026-11-06

Official Home Assistant [Config Entries guidance](https://contributors.home-assistant.io/core/integrations/config-entries/) requires setting typed entry.runtime_data before async_forward_entry_setups because each forwarded platform accesses the runtime immediately. The setup sequence in §4 was revised accordingly. To avoid writing under an invalid pending owner, the monitor must start only after its lease is ACTIVE. Synthetic future tests SH-INIT01/03/07 and SH-LC07 must assert this ordering explicitly. No tests were run.


## 13. Global graceful shutdown checkpoint — 2026-11-06

Pinned Core 2026.11.0 [core.py](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py) provides **hass.async_add_shutdown_job** ahead of the stop event and automatic background-task cancellation. Stage limits in this source are 20 seconds for shutdown jobs, 100 seconds for stop, 60 seconds for final write and 30 seconds for close. These are **upper execution stages, not per-integration guarantees of successful flushing**. The candidate HubController must register exactly one global shutdown job, fence writers/probes, and request orderly bounded monitor stop/commit drain before the event-based cancellation stage. SH-LC09/10 now require evidence that this pre-stop job prevents new work; add the interleaving "last Config Entry unloads while global STOPPING" to the existing suite fixture coverage. Do not count this extra fixture as a passed test or silently alter the existing 56 IDs. An interrupted close must be detected and reconciled at restart without fabricating sessions.


## 14. Crash recovery / snapshot selection dependency — 2026-11-06

[SPEC-010](SPEC-010-crash-recovery-restore-provenance-and-archive-access.md) and its [official-source audit](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md) refine the manager's existing commit and backup leases with **56 additional NOT_RUN test scenarios and 14 open gates**. In particular, an SQLite COMMIT that succeeds before an async caller receives its receipt is not safe to retry as an additive new event. A staged backup snapshot must not be automatically reapplied on normal startup. The official 2026 SQLite WAL-reset bug adds a linked-library version check before enabling WAL. Supervisor's Recorder-specific exclude_database behavior does not protect arbitrary custom application DB files. SPEC-009 retains its own 56 NOT_RUN scenarios and 12 open gates; do not mark overlap cases passed or accept storage ADRs automatically.


## 15. Storage-root, archive load anchor and unmatched pre/post hook gate — 2026-11-06

[SPEC-011](SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md), [storage source audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md) and [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md) add 64 unrun cases covering portable private paths, archive recovery authority, single logical Hub Config Entry, and four targeted unmatched backup-hook cases. A Hub entry is an HA config/load anchor; shared HistoryService remains a process-global leased manager. A backup pre hook can successfully freeze PlayStation Hub while another platform fails, and pinned Supervisor may never send post; therefore a live writer cannot be safely resumed by a naive timer while an archive may still be reading. Archive-long SQLite freeze is BLOCKED pending verified compensation and no active copy. The preferred next research topic is a staged immutable Online Backup API snapshot with explicit restore source and raw-file treatment. Earlier SPEC-009 tests/gates remain unchanged and NOT_RUN.


## 16. Approved logical Hub and snapshot-owned operation leases (2026-11-06)

The maintainer approved the Hub/Archive product architecture in [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06) while operational backup/restore safety remains conditional. [Immutable snapshot source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md), [ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md), and [SPEC-012](SPEC-012-immutable-snapshot-publication-and-backup-admission.md) add a new shared-manager job lease: ONE snapshot source read and destination writer per snapshot-generation namespace, not a per-console or browser writer. Pre hook should publish a validated immutable generation without holding an archive-long lock on the live ledger. Missing post hook leaves only harmless archive bookkeeping, not a stranded live writer. Queries and snapshot source handles must use bounded lease lifetimes. Existing 56 SPEC-009 tests/gates stay NOT_RUN/OPEN.


## 17. RecoveryManager as global owner, not WebSocket client — 2026-11-06

[Official pinned native recovery audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md), [SPEC-014](SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) refine the global HubController lease protocol. A data-replacement job needs an exclusive recovery generation/lease distinct from entry leases, read-only query leases and SQLite snapshot leases. The HA WebSocket async_response decorator schedules a background handler, while connection-close code only guarantees subscriber removal; neither represents a durable file promotion transaction. Recovery must therefore be one controller-owned job with explicit last-safe-cancel phase, idempotency, reconnect/status and bounded shutdown recovery. A preview/confirm protocol revalidates candidate bytes and current ledger/entry identities under a short global lock before admitting promotion; do not hold the global lifecycle lock across SQLite I/O. If Hub/Archive loads with invalid storage, a degraded RECOVERY_HOLD UI without a new writer is a candidate requiring tests. This extension does not mark any existing 56 SPEC-009 tests PASS.


## 18. Exclusive recovery generation and pointer/journal crash reconciliation — 2026-11-06

[Source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [SPEC-015](SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) and [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) refine the controller's global recovery lease. An SQLite history recovery is **not** an entry-scoped reload or a WebSocket handler coroutine. Fence new write admissions, positively close every writer/read/export/backup worker, preserve the old generation and its SQLite-owned WAL/journal, build and validate a separate candidate working generation, then atomically publish a small active-generation pointer after durable app journal phases. Under a crash the pointer may be committed while the app journal is behind; never blindly revert it, and never start an overlapping second SQLite writer during unresolved closure. After promotion, independently reconcile all HA Config Entries and canonical physical/PSN identities before resuming writes. The proposal does not change HA's independent config-entry setup locks or make SQLite and .storage one transaction. SPEC-009's 56 scenarios/12 gates remain unrun; SPEC-015 provides 80 additional failure cases/20 OPEN gates.


## 19. Preflight default-deny storage gate and worker terminal evidence — 2026-11-06

The [pinned Core/Python/aiosqlite audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md) and [SPEC-016](SPEC-016-recovery-hold-boot-order-and-worker-termination.md) refine the global single-flight HistoryService lifecycle. Domain setup creates one HubController/RecoveryManager and a **DENY_WRITE** gate before independent Hub/console/PSN Config Entries can set up concurrently. The Hub can be HA LOADED while the internal history service is RECOVERY_HOLD. No source monitor or UI request may bypass the gate with a stale lease, and no SQLite writer may be opened for an unvalidated pointer/ledger UUID. The optional source-only observation capability is distinct from active historical writer lease, and history gaps remain UNKNOWN/UNSAVED.

Stop protocol: FENCING -> DRAINING -> CONNECTION_CLOSING -> WORKER_TERMINATING -> CLOSED. A cancelled asyncio Future, configured thread timeout, empty worker queue, Python sqlite3.Connection.interrupt result or Core's 10-second on-unload wait does not alone prove underlying SQLite worker termination. ThreadPoolExecutor running jobs cannot be cancelled; aiosqlite v0.21.0 enqueued SQL functions can still execute after their awaiting Future was cancelled and close may be queued behind pending SQL. Until connection and worker terminal evidence exists, remain FAILED_UNSAFE_TO_REOPEN and do not switch ADR-0015 active generation. All original SPEC-009 56 cases and 12 gates remain unrun; SPEC-016 adds 80 new planned cases and 20 gates.


## 20. Unified capability evaluator and terminal worker proof — 2026-11-06

[Source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) and [SPEC-017](SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) refine the process-wide HubController admission contract. Domain setup constructs the control plane with DENY_WRITE while multiple Hub/console/PSN entries independently load. A current source reading and ConfigEntry LOADED are separate from ledger, worker, canonical identity and user operation authority. The same server-side policy must validate entity service/automations, WebSocket, physical commands, PSN operations and historical write leases; hiding frontend power controls is not a security boundary.

In RECOVERY_HOLD, durable SQL writes are denied. Optional verified SOURCE_ONLY_UNSAVED LAN state must not be replayed to fill missing historical usage. Conservative physical-control policy denies wake/standby and Remote Play during global Hold pending maintainer sign-off; identity-conflicted commands always denied. A validated immutable archival snapshot may use a separate bounded read-only lease and cannot borrow corrupt live SQLite handles.

SQLite terminal-proof correction: v0.22.0/0.22.1 aiosqlite changed Connection from Thread subclass to private-thread owner; v0.22.1 stop/close wait for queue callbacks but no public Thread.join guarantee is established by source. No cutover until FENCING, tracking admitted work, closing every reader/writer/backup connection, and verifying terminal worker/lease state. A cancelled asyncio Future, a zero queue length and an interrupt result do not suffice. SPEC-009's original 56 cases and 12 gates remain NOT_RUN/OPEN; SPEC-017 adds 80 additional test IDs and 20 gates.


## 21. Single-flight first-ledger genesis versus existing/history recovery — 2026-11-06

[Source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md) and [SPEC-018](SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) introduce a separate process-global provisioning lease distinct from normal entry, query, snapshot and recovery leases. A first Hub Config Entry and multiple physical/PSN entries can start concurrently. The HubController remains DENY_WRITE until it identifies either a verified existing active ledger or an explicitly administrator-authorized new genesis. No Config Entry can independently instantiate SQLite by an unsafe create-capable open.

A durable CREATE_INTENT with stable operation/ledger/generation UUIDs precedes exclusive new-generation staging; schema/genesis, connection close, validation and ADR-0015 pointer selection follow. A crash or browser cancellation cannot make next boot allocate a new independent ledger UUID when intent or partial stage already exists. Existing history open uses non-create SQLite modes; a missing selected ledger with previous metadata, snapshots or inaccessible root becomes RECOVERY_HOLD rather than a fresh empty DB. All earlier 56 SPEC-009 cases/12 gates remain unrun; SPEC-018 adds 80 planned cases and 20 gates.
