# Home Assistant Core 2026.11 — Recovery-hold bootstrap and SQLite worker lifecycle source audit

**Research date:** 2026-11-06
**Status:** SOURCE_REVIEW / PROPOSED_ARCHITECTURE / NO_CODE / NO_TESTS / NO_HARDWARE
**Core source pin:** home-assistant/core tag 2026.11.0
**Python reference:** official Python 3.14 sqlite3 and concurrent.futures/asyncio documentation
**SQLite:** official SQLite threading, interrupt, WAL, and corruption guidance
**Third-party comparison:** omnilib/aiosqlite v0.21.0, examined as a candidate, NOT an approved dependency
**User-approved product scope:** ADR-0011 accepts a user-created logical Hub/Archive Config Entry, independent console/account entries, one global controller and panel, and retention of archived history.
**Related:** [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md), [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md), [SPEC-009](../specifications/SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md).
**Branch policy:** only documentation on main; develop is frozen.

> Evidence labels: CORE_PINNED means exact reviewed Core implementation; PYTHON_OFFICIAL and SQLITE_OFFICIAL mean language/database reference; THIRD_PARTY_PINNED means aiosqlite v0.21.0 reviewed but not integrated; PROJECT_PROPOSAL is an internal candidate that may still be rejected; OPEN_HA_OS means runtime evidence is missing. No source inspection proves PlayStation Hub is operational.

## 1. Executive outcome

**P0 — A Recovery Hold must not be implemented as an indiscriminate ConfigEntryNotReady.** Core 2026.11 maps ConfigEntryNotReady to SETUP_RETRY, a normal error to SETUP_ERROR, migration errors to MIGRATION_ERROR. If the logical Hub entry cannot load, the one-panel administrator recovery path may be unavailable after Home Assistant startup. A valid deliberate **Hub loaded in restricted RECOVERY_HOLD state** is a stronger proposal: the domain-level controller, one authenticated panel/API, a typed inert Hub runtime and a global Repair issue can exist while the history writer remains **CLOSED/FENCED**. This is an internal state, NOT a new Home Assistant ConfigEntryState.

**P0 — Correct task cancellation does not imply worker termination.** Official Python concurrent.futures states running ThreadPoolExecutor jobs cannot be cancelled by Future.cancel or cancel_futures=True. Python sqlite3.Connection.interrupt can request that executing statements abort, but does NOT prove all work has stopped, that a transaction was rolled back, or that a connection was closed. aiosqlite v0.21.0 queues functions onto one worker thread per connection and Connection.close enqueues a close behind queued operations; cancelling a Python await for an already enqueued operation does not logically remove the operation from that worker queue. The application must prove a definitive worker stop, queue drain/fence and closed SQLite handle before any active-generation switch.

**P0 — Platform forwarding requires a prepared entry.runtime_data.** Core and official guidance require entry.runtime_data set before awaiting async_forward_entry_setups. Source-specific sensors can be in an unavailable/degraded projection while the controller recovers; no background historical monitor may submit a persisted observation until current generation and canonical identity are validated.

**P0 — Independent entries race.** Each ConfigEntry owns its own setup_lock. Hub, console A, console B and account can begin setup concurrently, so a single integration-global recovery verdict and a generation-fenced write-admission barrier must exist BEFORE any source runtime can access the writer. A console setup may complete in source-observational degraded mode or be retried based on a deliberate policy; do not treat a shared history error as PS5 network failure or an authentication failure.

**P1 — Global repair issue lifecycle is different from console issues.** Core 2026.11 supports config_entry_id issues that disappear when the entry is removed and are hidden when disabled. A shared ledger issue must not belong to one removable physical console. A domain-wide stable issue ID with no config_entry_id is safer during hub/console deletion, provided integration setup still occurs to create it and clear it after verification.

## 2. Pinned Core source verification

| ID | Pinned source | Finding | Implication |
| --- | --- | --- | --- |
| BH-01 | config_entries.py ConfigEntry.async_setup | disabled/ignored entries return without setup; successful integration setup sets LOADED | Recovery UI needs at least one enabled entry and successful domain setup |
| BH-02 | config_entries.py setup exception handlers | NotReady -> SETUP_RETRY; Error -> SETUP_ERROR; migration error -> MIGRATION_ERROR | Recoverable ledger corruption is NOT merely an offline PS5 retry |
| BH-03 | config_entries.py setup_lock in each ConfigEntry | lock is entry-scoped, not global | Single-flight HubController preflight and write fence |
| BH-04 | config_entries.py async_forward_entry_setups | MUST await platform forwarding while entry setup lock is held | No asynchronous fire-and-forget entity platform initialization |
| BH-05 | Official config entries guide | typed runtime_data set before forwarding to platforms | Prepared Hub and console projections can indicate recovery health |
| BH-06 | config_entries.py _async_process_on_unload | on-unload callbacks run and entry background tasks cancelled; waits about 10 s in pinned source | Await explicit critical SQL closure; callbacks do not provide a durable multi-stage barrier |
| BH-07 | config_entries.py FAILED_UNLOAD path | failed platform unload does not perform successful cleanup | Track leaked/fenced owners rather than announcing writer CLOSED |
| BH-08 | ConfigEntry.async_create_background_task | task belongs to one entry, is cancelled on its unload/shutdown | Source LAN monitor may not own global HistoryService worker |
| BH-09 | core.py async_add_shutdown_job | runs before EVENT_HOMEASSISTANT_STOP and HA background task cancellation | One HubController-owned pre-stop fence/drain, no per-console close of shared writer |
| BH-10 | frontend/__init__.py | panel collision rejected unless update; async_remove_panel available | One registration at integration scope independent of source ready state |
| BH-11 | websocket_api/__init__.py | commands globally mapped by name; duplicate can replace handler | Once-only namespace and current HubController lookup |
| BH-12 | issue_registry.py Core 2026.11 | issue may be global or config_entry_id-scoped | Global ledger Repair must not vanish on PS5 removal |
| BH-13 | bootstrap.py, config_entries.py | domain async_setup happens during component setup, entries then setup | Domain can install guarded controller/API without opening SQL |
| BH-14 | helper/entity_platform.py | platform setup can fail independently and need not retry whole entry | Fatal shared history decision must be made before forwarding, not hidden in sensor platform |
| BH-15 | Core ConfigEntry async_migrate | migration occurs before entry async_setup_entry | Corrupt app SQLite is NOT necessarily a Config Entry format migration error |
| BH-16 | official contributor setup-failures guide | platform NotReady/errors do not produce the same integration-level retry | Do not raise a storage exception from individual entity setup |

Pinned references at §14. Line numbers in upstream versions are navigation hints, not a promised public ABI.

## 3. Official Python/SQLite and third-party worker findings

| ID | Evidence | Behavior | Project consequence |
| --- | --- | --- | --- |
| SW-01 | Python concurrent.futures 3.14 | running Future.cancel returns False; cancel_futures affects only pending jobs | Cancel/timeout is not STOPPED |
| SW-02 | Python Executor.shutdown | shutdown(wait=True) joins after running tasks finish; wait=False returns without join | Never treat wait=False or abandoned future as safe SQLite handle closure |
| SW-03 | Python sqlite3.connect | check_same_thread=True by default; SQLite C library thread mode affects safety | One connection should be owned by one dedicated worker; avoid unsynchronized cross-thread access |
| SW-04 | Python sqlite3.Connection.interrupt | can be called from another thread to abort executing statements with OperationalError | A best-effort abort request, not a worker exit/connection-closed acknowledgement |
| SW-05 | Python sqlite3 connection context manager | context manager may commit/rollback but does not itself close the connection | Must explicitly close and verify worker completion |
| SW-06 | aiosqlite v0.21.0 core.py Connection.run | executes functions sequentially from internal queue on one worker thread | A queued SQL function may run after its awaiting coroutine was cancelled |
| SW-07 | aiosqlite v0.21.0 _execute | submits work before awaiting a future, with no source-level cancelled-future queue removal | Future cancellation cannot be used as proof that work was never executed |
| SW-08 | aiosqlite v0.21.0 close | enqueues sqlite connection close; stop sentinel behind queued work; no API-level join of worker thread in reviewed close path | await close provides an observed queued-closure result but does not by itself prove all lifecycle constraints without reviewing/tested worker thread exit and outstanding operations |
| SW-09 | aiosqlite documentation | async close completes queued queries/cursors then closes | A potentially long queue must be bounded; new admissions fenced before draining |
| SW-10 | SQLite WAL and howtocorrupt | open DB rename and journal/WAL manipulation can corrupt; readers/writers may keep handles | NEVER switch active path based only on cancelled awaitable, timeout or async task done |
| SW-11 | SQLite busy/error codes | COMMIT status may be uncertain after cancellation | Stable observation ID/transaction receipt and post-restart reconciliation still necessary |
| SW-12 | Third-party source tag | aiosqlite v0.21.0 is an example, not known installed or approved on user's Home Assistant OS | Dependency licensing, packaging, version pin and Core compatibility need future review |

**Key new insight:** Two things can be true at once: the asyncio Future has state CANCELLED and the underlying executor/sqlite thread has state RUNNING. Therefore write admission, worker phase, SQL connection phase and durable receipt must be separate state variables, never a single "task cancelled" Boolean.

## 4. Proposed boot architecture: two planes, two barriers

**Control plane — available while historical persistence is unsafe:**
- Domain-level async_setup creates one HubController with a recovery gate default DENY_WRITE; sets up validated, once-only panel/WebSocket registration and a global Repair issue facade.
- The logical Hub Config Entry's typed runtime_data contains a lightweight RecoveryView/HubRuntime in PREPARING or RECOVERY_HOLD, even if the historical SQLite DB is invalid; no expensive SQL in entry state getter.
- The one sidebar panel shows recovery state, sanitized candidate summaries and admin-only actions, not a fabricated empty historical chart.
- A valid read-only history snapshot may be browsed when separately verified and authorized; the current corrupted live generation is not silently adopted as historical truth.
- No LAN monitor, PSN token refresh or wake/standby is owned by the Hub entry.

**Data plane — unavailable until promotion/validation is resolved:**
- HistoryService writer remains CLOSED/FENCED while active pointer/recovery journal/source validity are checked.
- Every per-console transport that could submit observations carries source entry generation, canonical identity and controller storage generation; write admission requires a current ACTIVE lease and global gate OPEN.
- If a console is otherwise usable but history is unsafe, **candidate policy:** allow source-only latest LAN observation with a clearly visible UNSAVED/UNKNOWN historical gap, but do not mutate history or allow physical control under identity conflict. Alternative strict policy: suspend all probes. Both policies require maintainer approval; there is no hidden accumulation of unbounded samples.
- On resolution, all accepted fresh observations begin a new evidence interval; no gap from earlier recovery is filled with assumed gaming/power time.

**Deadlock avoidance:** Do not hold the global lifecycle lock across SQLite I/O, platform forwards or arbitrary entry callbacks. A short guarded state transition publishes a controller generation + gate; all work happens outside with tokens checked again before admission and before commit.

## 5. Proposed startup sequence

| Order | Candidate process | Failure behavior |
| --- | --- | --- |
| B0 | Core begins integration domain setup | No DB writes or console probes before controller exists |
| B1 | Create/store one HubController, set writer gate DENY_WRITE | Domain setup may succeed without live history SQLite |
| B2 | Install one authenticated WS namespace + sidebar/static path with collision checks | Collision fails visibly; don't overwrite other handler |
| B3 | Start bounded, controller-owned preflight of active pointer, application journal, chosen generation and worker state | UI can report CHECKING/RECOVERY_HOLD; never create fresh DB on ambiguous files |
| B4 | Hub entry setup: create inert typed HubRuntime, assign entry.runtime_data before any platform forwarding | Keep Hub entry LOADED in controlled RecoveryHold where safe |
| B5 | Physical console/account entries setup concurrently, each with separate typed runtime/identity | They observe global gate; no historian ownership or implicit migration |
| B6 | Forward only the platforms valid for that entry kind, await forwarding; entities may show unavailable/unsaved status | Do not forward synthetic PS5 platforms from Hub entry |
| B7 | Optional source-only LAN monitoring obeys policy and independent per-entry cancellation | Never queue durable writes under DENY_WRITE; no stale probe after generation switch |
| B8 | If preflight validates pointer+journal and no conflicting owner, open one writer generation and promote gate to OPEN | Every acquired lease matches ledger + manager generation |
| B9 | If unresolved source/worker/identity, remain RECOVERY_HOLD and raise stable domain Repair | Hub/panel remain available when configured/enabled; no false healthy status |
| B10 | On admin recovery, exclusive manager-owned job fences all sources, validates candidate, switches generation, reconciles and opens writer | No automatic stale snapshot promotion; never reopen with unknown running old worker |
| B11 | Normal shutdown: one controller-owned early shutdown job fences, drains and closes; entry callbacks release only their owners | Timeout means degraded/unsafe, not definitive close |

**Special case:** If no Config Entry is enabled after a user disables/removes Hub and consoles, HA is not guaranteed to run the domain setup/panel at next boot. A retained history file alone does not load a recovery UI. This is product behavior, not a database failure.

**Special case:** If entry async_migrate fails before setup, a Hub-only recovery UI may not load even if domain-level panel exists. Config Entry schema migration should avoid opening or mutating a corrupt history ledger; administrative repair of a MIGRATION_ERROR has its own supported HA retry path.

## 6. Boot decision matrix: when to LOADED vs raise

| Condition | Hub Config Entry proposed outcome | Console/account proposed outcome | Reason |
| --- | --- | --- | --- |
| Valid live ledger, no journal conflicts | LOADED normal | LOADED normal if own requirements pass | Writer can open after source validation |
| Pointer old, journal PREPARING, valid old DB | LOADED with RECOVERY_HOLD or controlled resume; old data can remain viewable | Degraded source-only or explicitly SETUP_RETRY based on policy | Pending intent cannot auto-promote |
| Pointer new, journal pre-completion, valid new DB | LOADED RECOVERY_HOLD until reconcile, then normal | No write/commands until identity reconciliation | Do not blind roll back |
| Active DB missing with known prior metadata | LOADED RECOVERY_HOLD | Degraded/blocked writes | Do not recreate empty ledger |
| DB corrupt but panel controller healthy | LOADED RECOVERY_HOLD, global Repair | Degraded/blocked writes | Administrator path needed |
| No writable disk / FULL | LOADED RECOVERY_HOLD where safe | Source-only UNSAVED or blocked | UI safety rather than setup retry loop |
| No Python sqlite3 available | If recovery read-only UI can function, LOADED RECOVERY_HOLD; otherwise real SETUP_ERROR | Setup failure as appropriate | Fatal missing requirement needs honest reporting |
| Known PS5 LAN offline but DB healthy | LOADED Hub | Console may use stale projection or NotReady by policy | Device availability not ledger integrity |
| PSN credentials invalid but DB healthy | LOADED Hub | Account reauth flow, LAN unaffected | Auth failure is per-account |
| Hub Config Entry schema migration fails | MIGRATION_ERROR / official repair retry | Other entries may still independently work | Cannot bypass Core's entry migration |
| All entries disabled | No guaranteed domain panel | All disabled | No source-owned runtime |
| Another console setup fails concurrently | Hub LOADED | That console's SETUP_ERROR/RETRY | Never revoke other entry leases |

**Distinguish design policy from Core state.** RECOVERY_HOLD is a PlayStation Hub internal health state when the Hub entry has actually completed setup. It is not a replacement for Core's SETUP_RETRY, and should not be used to conceal an integration import error or missing essential control-plane capabilities.

## 7. Worker model trade-offs and interruption protocol

### Candidate W1 — stdlib sqlite3 with dedicated bounded ThreadPoolExecutor

Pros: fewer external dependencies and familiar SQLite API, controlled single-writer queue.
Risks: every worker has connection thread affinity; run_in_executor cancellation does not stop running function, a close submitted to same thread may wait behind blocked SQL, and shutdown(wait=False) is not proof of termination. A permanent hung thread can hold a file handle until process exit. A writer-generation cutover in the same process requires confirmed worker closure.

### Candidate W2 — aiosqlite with one worker thread per connection

Pros: library exposes async connections/backup/close and internal serial work queue; aiosqlite docs explicitly describe a shared worker thread.
Risks: cancelled await does not unqueue an already-submitted operation in reviewed v0.21.0 source. Async close awaits queued close but does not directly guarantee a positive join of worker thread if callback/cancellation/queue is obstructed. Multiple connections create multiple threads, readers and checkpoints must be tracked globally; library version/packaging not approved.

### Candidate W3 — dedicated subprocess worker

Pros: killing/awaiting the entire process can provide a stronger OS-level isolation boundary for a hung SQLite operation, in a future architecture.
Risks: HA custom integration portability, packaging, lifecycle, process supervision, security permissions, IPC schema, resource use and Core conventions; not a recommended default for a single pure custom integration without compelling tests. Killing subprocess is not itself an acknowledged SQL COMMIT result; SQLite must recover native transactions on next open.

**Recommended research direction:** evaluate W1 and W2 under injected cancellation/timeouts with a **required observable worker stop acknowledgement** rather than selecting a library by convenience. Favor one dedicated serialized writer owner, bounded readers, ownership tokens, no per-console sqlite3 connection, explicit worker queue drain and closed connection proof; actual selection CONDITIONAL.

### Proposed safe stop protocol for W1 or W2

1. Under controller state lock, change writer generation to FENCING; reject new write/read/backup/export admissions, and require all in-flight entry tokens to release or expire with a classified failure.
2. Stop/await producers and reader leases; distinguish completed SQL transactions from merely cancelled asyncio awaits.
3. Signal cooperative stop and bounded timeouts for SQL operations. sqlite3.Connection.interrupt may help abort a long query, but must not be used as evidence the worker stopped or that COMMIT rolled back.
4. Do not clear/overwrite the only reference to worker/connection while work may still execute. Await a library-specific close operation, its queues and worker termination; verify no in-flight jobs remain, and classify unjoinable worker as UNSAFE_TO_REOPEN.
5. When closure is positively established, update manager state CLOSED and allow pointer/journal generation switch.
6. On timeout/hung worker, remain FENCED/RECOVERY_HOLD; do not open a second writer on same DB path in that process. Reconciliation after process restart requires file preservation and native SQLite recovery at the selected original path.
7. Store committed observation receipts/idempotency keys because a late COMMIT might have succeeded despite cancelled caller.
8. On Home Assistant shutdown, respect pre-stop shutdown job, bounded drain and no misleading "all history saved" claim if stage deadlines were exceeded.

**Subtlety:** A background worker queue can still contain work after every browser/client task has been cancelled. A queue size of zero alone can also be misleading if an operation is currently executing. Require explicit owner lifecycle state and a terminal acknowledgement.

## 8. Operational states (candidate)

**Global control plane:** UNINITIALIZED -> STARTING -> RECOVERY_CHECKING -> READY or RECOVERY_HOLD -> RECONCILING -> READY; SHUTTING_DOWN -> CLOSED.

**Database manager:** ABSENT -> INITIALIZING -> READY -> FENCING -> DRAINING -> CONNECTION_CLOSING -> THREAD_STOPPING -> CLOSED; any stage can transition to FAILED_UNSAFE_TO_REOPEN. Only CLOSED permits a separate generation promotion.

**Hub Config Entry:** HA states remain the official NOT_LOADED / SETUP_IN_PROGRESS / LOADED / SETUP_RETRY / SETUP_ERROR / MIGRATION_ERROR / UNLOAD_IN_PROGRESS / FAILED_UNLOAD. Internal hub_state NORMAL / RECOVERY_HOLD / LIMITED_READ_ONLY / NOT_AVAILABLE.

**Console runtime:** READY / OFFLINE / SOURCE_ONLY_UNSAVED / IDENTITY_CONFLICT / ENTRY_STOPPING. Never conflate an awake PS5 with a writable history DB or a successful game attribution.

**UI:** one panel has normal activity/statistics view or restricted Recovery Required view; backend permissions determine allowed actions, not visual hiding alone.

## 9. Failure cases requiring tests

- Hub async_setup_entry returns success with corrupt historical DB but valid control plane, panel and one global Repair; no new sqlite3.connect auto-creates missing history path.
- DB corrupt during Hub-only startup and no console entry: admin recovery still available after HA restart.
- Console A and B setup while controller preflight is awaiting a busy read: neither accidentally creates its own SQLite manager or submits writes.
- A console's source-only fresh LAN observation during hold remains UNSAVED and does not interpolate recovery downtime.
- Hub setup failure after panel registered: once-only registration survives later retry without duplicate handlers.
- Hub entry disabled: global Repair may exist, but no false claim panel will be loaded next restart with zero other entries.
- ConfigEntry migration fails before Hub runtime setup: no silent bypass; use migration Repairs/retry.
- Platform async_setup_entry raises NotReady: whole-entry retry NOT automatically guaranteed; decide essential setup validity before forwarding.
- Writer future cancelled while COMMIT executes in thread: source SQL can still commit; next recovery checks stable observation receipt, never double counts.
- Close called while outstanding aiosqlite work queued: no late writes admitted; closure and thread stop proven.
- SQLite interrupt raises OperationalError in running query, but worker still alive: do not promote until actual connection close/join verified.
- HA pre-stop job triggers while Hub in recovery/worker closing; no overlapping generation and no false success after 20-second global bound.
- A platform unload failure puts one entry FAILED_UNLOAD, shared controller retains leak/ownership proof; does not close other active console writer.

## 10. New P0 design correction to earlier research

Earlier investigations sometimes described entry-owned monitor startup after a storage lease became ACTIVE and successful platform forwarding. In a **RECOVERY_HOLD** there must be **no ACTIVE durable-write lease**. Any source-only monitor policy requires a separate OBSERVATION_ONLY capability (can update current status without accepting history), and a strict revalidation/fence before enabling DURABLE_WRITER capability.

This prevents the error of treating a prepared Hub runtime or a loaded Config Entry as permission to write. "LOADED" means that integration setup succeeded, not that the historical ledger is valid or current.

The previous model's recommendation for one "dedicated SQLite worker" also remains a candidate, not a selected Python library. aiosqlite queue and cancellation observations make an implementation-specific join/close test mandatory, particularly before the generation-pointer cutover in ADR-0015.

## 11. Remaining approval gates

1. Approve internal Hub RECOVERY_HOLD loaded behavior and its minimal supported control-plane contract.
2. Approve console policy during shared-history hold: source-only UNSAVED observation or no probes at all.
3. Verify whether per-Config-Entry migration and exceptions can coexist with global recovery UI without masking real import and auth errors.
4. Choose W1 stdlib thread/worker or W2 aiosqlite (or an independently justified option) only after fault injection and package review.
5. Prove connection close and worker thread join on target HA OS under cancellation, SQLITE_BUSY, disk full, huge SQL and shutdown overlap.
6. Verify no duplicate writer or accidental new SQLite DB under setup concurrent with recovery/journal processing.
7. Verify stable global Repairs issue and panel after Hub reload, file corruption, last-console removal and disabled entry.
8. Reconcile current source status, durability state and gaps under timeouts; no fabricated history.
9. Verify recovery manager/admin workflow remains independent of browser and Config Entry task lifecycle.
10. Recheck the pinned Core version if minimum supported HA changes; all source-derived timings are implementation details.

## 12. Source index

### Pinned Home Assistant Core
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/bootstrap.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/update_coordinator.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/issue_registry.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/frontend/__init__.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py

### Official Home Assistant Contributors
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/integrations/setup-failures/
- https://contributors.home-assistant.io/core/integrations/repairs/

### Python and SQLite
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://docs.python.org/3.14/library/asyncio-eventloop.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/howtocorrupt.html

### Third-party worker candidate (not accepted or installed)
- https://aiosqlite.omnilib.dev/en/v0.21.0/
- https://aiosqlite.omnilib.dev/en/v0.21.0/api.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py

### Project
- [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md)
- [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md)
- [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)
- [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)

**Final status:** Detailed official and third-party source audit only, not an approved implementation, performance result or simulated/real test. develop not touched.
