# ADR-0016 — Recovery-hold startup, Config Entry setup boundaries and SQLite worker ownership

**Status:** PROPOSED — preferred technical policy; no implementation/tests
**Review date:** 2026-11-06
**Scope:** Keep the one-panel Hub/Archive recovery UI accessible while shared history is invalid; prevent premature source writes; prove SQLite worker shutdown before journal/pointer cutover.
**Evidence:** [Pinned official/third-party audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md)
**Acceptance plan:** [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md), 80 NOT_RUN cases, 20 OPEN gates.
**Dependencies:** ADR-0011 ACCEPTED conceptual Hub/Archive, ADR-0012/0013/0014/0015 technical proposals, ADR-0004/0006/0008/0009/0010, SPEC-008/009/010/015.
**Source:** HA Core 2026.11.0, official Python 3.14 sqlite3/ThreadPoolExecutor, candidate third-party aiosqlite v0.21.0.
**Branch:** main documentation only; develop frozen.

> The user authorized the investigation and documentation, NOT implementation of SQLite, not a new custom component, and not acceptance of the unverified worker/thread model.

## 1. Decision problem

The accepted logical Hub/Archive entry is intended to preserve archived history access when consoles are removed. But if a recovery journal or active SQLite generation is invalid during boot, treating the Hub's setup as ConfigEntryNotReady or ConfigEntryError can put it into SETUP_RETRY/SETUP_ERROR. That removes a vital recovery entry point.

Separately, an old worker may be writing to an SQLite generation even after its asyncio caller was cancelled. A full data-generation replacement is unsafe unless worker/connection closure is positively proven. We must distinguish Home Assistant entry lifecycle, integration-level control plane, SQLite data plane, and independently running OS threads.

## 2. Source facts

- Home Assistant Core 2026.11.0 first invokes integration/domain setup, then Config Entry setup for enabled entries; every entry has its own setup lock, not a global one.
- ConfigEntryNotReady is a transient failure and schedules SETUP_RETRY; ConfigEntryError is fatal SETUP_ERROR; migration errors produce MIGRATION_ERROR. All are HA states distinct from our proposed internal RECOVERY_HOLD.
- Typed entry.runtime_data must be assigned before awaiting async_forward_entry_setups, because platforms read it immediately.
- Background tasks owned by a Config Entry are cancelled on its unload; the pinned Core's on-unload wait has a 10-second bound and failed unload does not automatically complete successful cleanup.
- Home Assistant frontend exposes one-time panel registration and collision handling; Repairs issue registry supports global issues independent of console entries.
- Python concurrent.futures.Future.cancel does not stop already running ThreadPoolExecutor jobs, and shutdown(cancel_futures=True) affects pending jobs only; shutdown(wait=False) is not thread join.
- Python sqlite3 Connection.interrupt requests an executing statement to abort; it does not close the connection, complete all queued SQL work or establish a definitive transaction receipt.
- Python sqlite3's ordinary context manager commits/rolls back but does not automatically close the connection. sqlite3 has per-connection thread ownership by default.
- The inspected aiosqlite v0.21.0 connection uses one worker thread and an internal queue. Enqueued SQL may still execute after a waiting Future is cancelled. Its close places a close behind queued actions and stops the worker; positive exit/queue drain still needs proof before cutover.

## 3. Proposed architectural policy

**Control plane always separate from data-plane liveness.**

A healthy integration/domain configuration may provide one HubController, one panel/API, a global Repair and a typed logical Hub entry with internal recovery health RECOVERY_HOLD. A failed SQL open does NOT automatically constitute failure of the Hub Config Entry. Domain setup must never eagerly create an empty replacement historical DB when old pointer/journal/generations remain.

**Candidate boot contract:**
1. Create integration-global controller in DENY_WRITE state before any source entry can admit SQL operations.
2. Register panel/WS once at integration scope and create lightweight recovery preflight state.
3. Hub entry can successfully load a typed inert runtime and a restricted admin recovery view even when the DB is broken; label it RECOVERY_HOLD.
4. Console/account setup can proceed concurrently, but all historical writer leases are withheld until global source and identity validation. The accepted per-console LAN monitor is independent of panel listeners, not necessarily independent of write admission.
5. A source-only OBSERVATION_ONLY capability is a candidate that can display current LAN AWAKE/STANDBY with UNSAVED history under hold; no inferred history accumulation and no privileged physical controls when identity conflicted. Exact source-only policy awaits maintainer approval.
6. One controller-owned recovery job can validate/promote selected generation after admin confirmation, positively close old worker, revalidate physical/account ownership, then open gate to durable writes under a new generation.
7. Global Repairs is persistent while corrupt ledger exists; do not scope it to one PS5's entry or clear it simply because a user dismisses the UI.
8. Native HA migration and fatal setup exceptions remain honest: do not swallow a broken config-flow migration merely to show a recovery screen if essential Hub entry data are invalid.

**Important:** A Hub entry state LOADED does not mean historical data READY. Recovery Hold is a private app state, not a new HA ConfigEntryState or an implicit Recorder/SQLite database writer.

## 4. Worker architecture: alternatives still open

| Candidate | Benefits | Required safety proof | Status |
| --- | --- | --- | --- |
| W1: stdlib sqlite3 with one tracked dedicated ThreadPoolExecutor | No new library dependency, explicit serialized writer | Running Future cannot be cancelled; queue fencing, connection thread affinity, positive completion/close/join | Preferred to evaluate, NOT_SELECTED |
| W2: aiosqlite v0.21.0 with one queue/thread per connection | Async user API, serial queue, async close/backup | Cancelled awaiter may leave queued SQL; close behind queue; multiple read/backup worker tracking and terminal thread proof | Preferred to evaluate, NOT_SELECTED |
| W3: supervised dedicated subprocess | Stronger process isolation for a truly hung worker | IPC, HA OS/Container portability, process exit/fsync, packaging, permissions, nonzero resource overhead | Deferred, not default |

The selected worker must make SQL COMMIT receipt, accepted work count, worker lifecycle and actual underlying connection closure observable. Neither a cancelled asyncio.Task, an awaited timeout, an empty queue, nor an aiosqlite close call by itself is a universal worker-stopped guarantee without reviewing the exact implementation and verifying it.

## 5. Cancellation, fencing and close handshake (proposed)

**Phase A — prevent new work:** Controller FENCING state disallows all new SQL admissions for affected ledger generation; stale source runtime generations and browser requests cannot bypass it.

**Phase B — settle admitted work:** Bound and classify old in-flight commits, cursors, reads, exports and snapshots, without dropping their receipts. An interrupted caller must not cause double-add of game sessions on retry.

**Phase C — request cooperative stop:** For slow SQL, use reviewed statement timeout or sqlite3.interrupt when supported; an OperationalError from interrupted SQL means a statement aborted, not that worker thread/DB connection no longer exists. Ask worker to close in its own thread; no unsynchronized connection access.

**Phase D — obtain terminal evidence:** Await actual worker close response, drain and terminal/join state under a bounded contract; validate no outstanding file handles, queue jobs or leases. If this cannot be proved, controller state FAILED_UNSAFE_TO_REOPEN, no new writer and no pointer switch. Recheck after process termination/restart using SQLite native recovery at the selected original filename.

**Phase E — promote:** Only after CLOSED and full source/fork/identity validation may ADR-0015's separate new-generation pointer be promoted.

**Phase F — reconcile:** Independently verify HA Config Entry association versions and canonical physical PS5/PSN identities, with a new manager generation before opening DURABLE_WRITE admissions. Reports show unknown gaps for every unobserved interval.

**Key constraint:** Do not hold the global lifecycle lock during long SQL calls, platform forwards or shutdown waits; use fenced state transitions and token checks. Global shutdown must use a bounded early controller job and not claim full durability if a worker remains.

## 6. Startup and failure classification

| Condition | Proposed Hub action | Data-plane action |
| --- | --- | --- |
| Valid active pointer and journal, schema healthy | LOADED normal | One writer ACTIVE after identity checks |
| Partially committed pointer/journal mismatch | LOADED RECOVERY_HOLD | DENY_WRITE; admin reconciliation |
| Missing/corrupt DB with previous recovery evidence | LOADED RECOVERY_HOLD | No empty new DB, leave old bytes |
| Busy/locked file during preflight | LOADED CHECKING/RECOVERY_HOLD | Retry bounded; no duplicate writer |
| Missing essential Python dependency or broken integration import | SETUP_ERROR or control-plane failure | Do not disguise genuine fatal errors |
| Hub Config Entry schema migration incompatible | Native MIGRATION_ERROR and Repairs path | Do not bypass migration via stored runtime |
| PS5 offline while Hub healthy | Hub LOADED | Per-console offline/retry without affecting Hub |
| PSN account reauth needed | Hub LOADED | Account-scoped reauth, LAN unaffected |
| Worker still running after cancellation | Hub RECOVERY_HOLD | FAILED_UNSAFE_TO_REOPEN; keep current generation |
| Admin recovery completed, current identity mapping valid | Hub LOADED normal | Writer can OPEN with new generation |
| No enabled entries after HA reboot | No guaranteed panel | Archived files retained but no loaded owner |

## 7. Questions that still require explicit product and technical approval

- During shared storage RECOVERY_HOLD, allow per-console SOURCE_ONLY_UNSAVED LAN updates, or suspend all probes? Preferred research direction: source-only observation after canonical identity verification, clearly UNSAVED; no unbounded queue.
- In Hub-only RECOVERY_HOLD, should read-only reports from a separately validated immutable snapshot be accessible before repair? Preferred direction yes for admin under provenance labelling, subject to privacy and consistency tests.
- Which SQLite worker design W1 vs W2 meets correct shutdown/zero-duplicate-write and Home Assistant packaging requirements on HA OS? Neither approved.
- How to react if preflight blocks beyond an application-defined time: keep Hub loaded checking/degraded vs HA setup retry? Avoid indefinite startup wait; tests required.
- How should disabled Hub entry, Config Entry migration error or panel collision be explained to users so recovery is not silently inaccessible?
- How to verify handle closure in a worker library that does not expose thread join directly, without reaching into unsupported internal attributes?
- Should original-file preservation require a separate off-host copy before replacing a historical generation? Disk-full/retention and security considerations remain open.

## 8. Approval/test gates

Technical ACCEPTED status requires maintainer agreement on degraded Hub boot semantics and source-only policy, pinned HA OS/Container startup+reload evidence, negative auth/identity cases, proof of close/worker termination under fault injection, a selected worker/library and safe async lifecycle, no false reports or copied raw database authority, and 80 SPEC-016 scenarios executed with results. Core source inspection cannot satisfy the test gate.

**No implementation authorization.** Any future code must be modular, English commented, compatible with supported HA versions and subject to independent review. develop remains frozen.

## 9. References

- [Pinned Core/Python/aiosqlite audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md)
- [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md)
- [ADR-0015](ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md)
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/integrations/setup-failures/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://aiosqlite.omnilib.dev/en/v0.21.0/api.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py

**Decision:** PROPOSED / NOT_IMPLEMENTED / NOT_TESTED. Accepted ADR-0011 product direction unchanged.
