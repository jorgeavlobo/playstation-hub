# SPEC-016 — Recovery-hold bootstrap, Config Entry ordering and SQLite worker termination

**Date:** 2026-11-06
**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_CODE
**Evidence:** [Pinned Core/Python/aiosqlite source audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md)
**Decision:** [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md) PROPOSED
**Prior contracts:** SPEC-008/009/010/011/012/013/014/015, ADR-0004/0006/0008/0009/0010/0011 (accepted product)/0015 (proposed cutover).
**Reference versions:** HA Core 2026.11.0; Python 3.14 reference; SQLite C actual runtime pending HA OS; aiosqlite v0.21.0 examined as an *unapproved* alternative.
**Working branch:** main documentation; develop frozen; no implementation or tests.

> Internal normative statements are FUTURE acceptance criteria, not existing behavior of PlayStation Hub or official guarantees of Home Assistant. The accepted Hub/Archive product architecture from ADR-0011 does not automatically approve a degraded runtime or sqlite3 worker library.

## 1. Core objective

In a partially promoted SQLite recovery, the next Home Assistant start MUST keep an administrator path to repair history without creating a new blank database, reusing an open worker, writing into an unverified generation or mapping a restored old Config Entry to the wrong physical console.

A logical Hub Config Entry should be capable of achieving HA state LOADED with an internal Hub recovery health state RECOVERY_HOLD, while the SQL data plane is globally FENCED. The integration cannot guarantee any sidebar after a restart with no enabled Config Entries; the user-approved Hub entry is its normal load anchor.

No additional server, MQTT dependency or generic historical SQL database in HA Recorder is permitted.

## 2. Proposed invariants

| ID | Future invariant |
| --- | --- |
| BH-I01 | Domain async_setup creates exactly one HubController before entry setup can request SQL writes. |
| BH-I02 | History write gate is DENY_WRITE from controller construction until verified active generation and identity mapping. |
| BH-I03 | Panel and WebSocket registration is at most once per HA process, independent of SQL open or source count. |
| BH-I04 | A loaded Hub entry with internal RECOVERY_HOLD can expose restricted admin API but cannot open an unverified writable SQLite ledger. |
| BH-I05 | Internal RECOVERY_HOLD does not pretend to be a native Home Assistant ConfigEntryState. |
| BH-I06 | Genuine import/config schema migration errors and missing control-plane prerequisites are not disguised as storage hold. |
| BH-I07 | Hub typed runtime_data exists before any Hub platform forward, and forwarding is awaited under HA entry setup lock. |
| BH-I08 | Console/account Config Entries never own or initialize a separate shared SQLite history manager. |
| BH-I09 | Multi-entry startup, including Hub plus several PS5s, uses a single process-level preflight/manager generation and one historian. |
| BH-I10 | Source-only LAN observation under RECOVERY_HOLD is an explicit capability separate from DURABLE_WRITER. |
| BH-I11 | No historical writer lease is granted during hold, regardless of whether HA entry is LOADED and source is AWAKE. |
| BH-I12 | Stale old-entry UDP callbacks, browser requests and worker futures are fenced against later pointer generations. |
| BH-I13 | Console PSN account authentication failures remain per-account; they do not revoke the global Hub recovery UI. |
| BH-I14 | A sleeping console or offline LAN is not classified as a history database error. |
| BH-I15 | Every stopped/cancelled asyncio task is distinguished from a completed SQL worker and closed SQLite connection. |
| BH-I16 | Cancellation of a running ThreadPoolExecutor job does not authorize source file rename/promotion. |
| BH-I17 | sqlite3.Connection.interrupt is only an abort request for executing queries; positive connection/worker closure is still required. |
| BH-I18 | Queued aiosqlite v0.21.0 operations can outlive cancelled waiter Futures; queue fence/close must prevent late writes. |
| BH-I19 | No unbounded SQL task queue, read lease or application observation buffer under lost storage. |
| BH-I20 | No second SQLite writer generation opens while a previous worker may still hold the same DB path. |
| BH-I21 | A positive CLOSED state is based on observed close/join/terminal receipt, not timeout, task.cancel or a counter reset. |
| BH-I22 | On unsafe or hung worker, remain FENCED/FAILED_UNSAFE_TO_REOPEN; preserve SQLite source and its sidecars. |
| BH-I23 | HA pre-stop shutdown job is registered once for controller and runs before background task cancellation, with bounded but honest guarantees. |
| BH-I24 | A failed Config Entry unload is tracked, not silently discarded, and cannot close resources belonging to other entries. |
| BH-I25 | Shared ledger Repair issue is global or deliberately anchored to stable Hub, never solely tied to a removable PS5 entry. |
| BH-I26 | A history data folder is never created as a blank new ledger if an old pointer/journal/recovery artifact is present. |
| BH-I27 | RecoveryHold reports distinguish fresh source observation, UNSAVED intervals, last durable cursor and unknown coverage. |
| BH-I28 | Recovery under one HubController is admin-authorized and does not depend on browser connection lifetime. |
| BH-I29 | When generation promotion commits, new runtime identity tokens are issued and old callbacks cannot continue writing. |
| BH-I30 | No source-derived timeouts, worker semantics or status names are represented as tested production behavior. |

## 3. Proposed boot barrier protocol

A global manager state gate controls writes independently of Core ConfigEntry states.

    HA_DOMAIN_SETUP
      -> HUB_CONTROLLER_CREATED : DENY_WRITE
      -> PANEL_AND_API_REGISTERED_ONCE
      -> RECOVERY_PREFLIGHT : DENY_WRITE
      -> VALIDATED_ACTIVE_GENERATION : potential OPEN gate
      -> OWNER_ASSOCIATIONS_CHECKED : OPEN gate after identity validation

If at any point pointer, journal, schema, integrity, worker or canonical mapping is ambiguous:

    RECOVERY_PREFLIGHT -> RECOVERY_HOLD : DENY_WRITE
      -> HUB_RUNTIME_LOADED (if control plane is healthy)
      -> GLOBAL_REPAIR_AND_ADMIN_UI_AVAILABLE
      -> AUTHORIZED_MANAGER_RECOVERY
      -> VALIDATE_GENERATION_AND_OWNER_MAPPINGS
      -> OPEN / otherwise remain RECOVERY_HOLD

**Proposed separation:** a hub-only startup may install the admin interface with no SQL history connection. A physical-console source may be LOADED and in SOURCE_ONLY_UNSAVED mode if explicitly approved, where it can show current LAN data while no historical writer lease exists. An offline console can alternatively enter SETUP_RETRY based on source availability policy. A storage hold should not be incorrectly raised as ConfigEntryNotReady on the Hub.

**No unconditional platform forwards:** assign typed entry.runtime_data to prepared inert runtimes before awaiting async_forward_entry_setups. Hub entry may have no ordinary sensor entities; per-console entities must show appropriate availability when the writer is locked. A platform failure after forward does not necessarily retry whole integration; verify essential preconditions before forwarding.

## 4. Worker ownership and stop protocol

| Worker condition | Awaiter condition | Safe promotion? |
| --- | --- | --- |
| Work queued, not started | Awaiter active or cancelled | NO; queue needs explicit fence/cancel/terminal record |
| SQL statement running | Awaiter cancelled | NO; underlying thread can still write |
| sqlite3.interrupt called | SQL may raise OperationalError | NO; connection/thread may still be live |
| SQL operation returns | Worker still active with queued work | NO |
| Connection close submitted | Queued close may not have executed | NO |
| Connection closed | Worker thread not joined/still executing callbacks | NO, until lifecycle and handles verified |
| Worker terminal/joined, pending queue empty, tokens released | Controller classified terminal | MAY proceed, subject to recovery gate and filesystem checks |
| Worker unresponsive after bounded wait | Unknown | NO; FAILED_UNSAFE_TO_REOPEN |

The exact stop/join API varies between stdlib executor and aiosqlite; no vendor library is accepted by this specification. W1 dedicated ThreadPoolExecutor and W2 aiosqlite are future evaluation candidates, not commands to implement now. Every connection and cursor belongs to a tracked generation. Backup/export/read leases must close before promotion.

## 5. Candidate error and user-visible semantics

- RECOVERY_HOLD: application's internal state (can coexist with native Hub Config Entry LOADED).
- UNSAVED: valid current LAN observation but not durably accepted into history.
- UNKNOWN: historical interval where source evidence does not justify usage.
- FAILED_UNSAFE_TO_REOPEN: worker/connection cannot be proven stopped; prohibit new writer and promotion for affected path.
- SETUP_RETRY: genuine Home Assistant transient setup issue; not a substitute for user-driven recovery.
- SETUP_ERROR: integration entry setup cannot succeed; distinguish fatal control-plane error from deliberately degraded history mode.
- MIGRATION_ERROR: native HA entry version migration failure; cannot be silently bypassed using stale runtime_data.
- FAILED_UNLOAD: Core unload unsuccessful; do not assume on-unload callbacks/connection cleanup ran.
- RESTORED_READ_ONLY: a validated archive source available for authorized reports but no active writer.

Every state should have translated, privacy-safe documentation; never show a misleading "data saved" confirmation based solely on active source.

## 6. Test plan — 80 NOT_RUN scenarios

### 6.1 Domain and Hub bootstrap, panel/Repair — 20 NOT_RUN

| ID | Future synthetic/HA OS test | Expected result |
| --- | --- | --- |
| BH-BOOT01 | First boot with no history and explicit new Hub confirmation | Safe first-setup policy; no foreign blank overwrite |
| BH-BOOT02 | Hub-only entry with corrupt existing ledger | Hub LOADED internal RECOVERY_HOLD; recovery API available |
| BH-BOOT03 | Pointer missing but known recovery journal exists | No blank DB; global Repair active |
| BH-BOOT04 | Pointer new, journal READY_TO_COMMIT | Boot holds/reconciles; no automatic rollback |
| BH-BOOT05 | Pointer old, journal ready new | Old remains selected; no stale automatic promotion |
| BH-BOOT06 | Invalid Hub Config Entry version migration | Native MIGRATION_ERROR; no bypass or fabricated healthy state |
| BH-BOOT07 | One Hub entry disabled, no other entries | No guaranteed panel next restart |
| BH-BOOT08 | Hub removed while console entry exists | One panel/controller and unaffected console ownership |
| BH-BOOT09 | Last console removed while Hub remains | Panel and read-only archive health remain |
| BH-BOOT10 | Disk full at initial history preflight | Hub RECOVERY_HOLD but no new SQLite ledger |
| BH-BOOT11 | SQL sqlite3 module/essential platform missing | Explicit control-plane setup failure, not fake recovery success |
| BH-BOOT12 | Panel route collision with another integration | Fail closed; do not overwrite the other panel |
| BH-BOOT13 | WebSocket command collision | One-time registration rejects replacement |
| BH-BOOT14 | Global Repair exists and console A removed | Issue retained while shared ledger unresolved |
| BH-BOOT15 | Hub Repair associated with disabled Hub entry | Issue visibility policy explicit (global vs entry-scoped) |
| BH-BOOT16 | Hub-only startup after successful recovery | Exactly one manager/panel, proper Repair clearance |
| BH-BOOT17 | Unresolved restored old Config Entries | Current power controls remain identity-fenced |
| BH-BOOT18 | Two administrator browsers open Recovery UI | One backend preflight, independent subscriptions |
| BH-BOOT19 | Hub loaded with no valid SQL reader | UI shows error/candidates without invented statistics |
| BH-BOOT20 | Startup interrupted during control-plane registration | No duplicate handlers on subsequent setup/reload |

### 6.2 Multi-console entries, forwarding and gate races — 20 NOT_RUN

| ID | Scenario | Expected result |
| --- | --- | --- |
| BH-ENTRY01 | Hub + A + B setup concurrently | One shared controller, DENY_WRITE until validated |
| BH-ENTRY02 | Console setup completes before Hub entry | One global fence still enforced |
| BH-ENTRY03 | Hub-only setup reaches panel while pointer preflight slow | UI CHECKING/RECOVERY_HOLD; no event-loop block |
| BH-ENTRY04 | Assign entry.runtime_data after platform forward (negative case) | Contract detects invalid setup ordering |
| BH-ENTRY05 | Forwarded sensor reads prepared unavailable projection | No KeyError, no false awake |
| BH-ENTRY06 | Platform raises NotReady after forwarding | No assumed full-entry automatic retry |
| BH-ENTRY07 | PS5 offline while DB good | Source retry/offline policy; Hub unaffected |
| BH-ENTRY08 | PSN auth failure while history unsafe | Account reauth scoped, Hub controls preserved |
| BH-ENTRY09 | A removed while B ready and Hub holding | B continues; no global closure |
| BH-ENTRY10 | A entry FAILED_UNLOAD while B active | Tracked leak/fence; B not revoked |
| BH-ENTRY11 | A sleep/standby sample arrives while DENY_WRITE | Current status may be shown, history stays UNSAVED |
| BH-ENTRY12 | A stale UDP response after pointer changes | Old-generation sample cannot commit |
| BH-ENTRY13 | Gate OPEN only after pointer, source and identity checks | Exactly one active writer generation |
| BH-ENTRY14 | Gate closes while writer queue has admitted operations | Settled receipts or classified uncertain; no unbounded queue |
| BH-ENTRY15 | Two consoles request SQL init simultaneously | One single-flight init, no duplicate DB |
| BH-ENTRY16 | Hub entry setup fails after shared controller published | Retried setup has once-only panel/WS registration |
| BH-ENTRY17 | No console listeners for push-only coordinator | History observation policy remains entry-owned, not panel-owned |
| BH-ENTRY18 | Source-only monitoring during 1-hour recovery | Historical hour UNKNOWN, no fabricated sessions |
| BH-ENTRY19 | New console discovered while Hub RECOVERY_HOLD | Identity flow remains safe; no history writer |
| BH-ENTRY20 | Global recovery ends and several entry probes race | Gate/lease generation validation; no double counted time |

### 6.3 SQLite worker cancellation, queue, join and correctness — 20 NOT_RUN

| ID | Scenario | Expected result |
| --- | --- | --- |
| BH-WORK01 | Running ThreadPoolExecutor future.cancel | Running work may persist; no false CLOSED |
| BH-WORK02 | Executor shutdown(cancel_futures=True) with running SQL | Running operation not deemed cancelled |
| BH-WORK03 | Executor shutdown(wait=False) | No false thread-joined claim |
| BH-WORK04 | stdlib sqlite3 connection used from wrong thread | ProgrammingError and clear ownership |
| BH-WORK05 | check_same_thread=False with unsynchronized writes | Rejected unsafe topology; serialization required |
| BH-WORK06 | sqlite3.interrupt long-running query | OperationalError classified, connection still explicitly closed |
| BH-WORK07 | sqlite3 context manager exits | Does NOT imply connection close |
| BH-WORK08 | aiosqlite v0.21 queued INSERT future cancelled | Queued SQL may execute; receipt/idempotency handles ambiguity |
| BH-WORK09 | aiosqlite queued close behind long query | Close not marked complete until actual return + worker exit proof |
| BH-WORK10 | aiosqlite multiple independent connections | No untracked reader/backup worker during promotion |
| BH-WORK11 | Queue full from 2 consoles | Bounded ingress and no starving global recovery |
| BH-WORK12 | COMMIT succeeds after awaiting task cancelled | Durable receipt reconciled, no double credit |
| BH-WORK13 | SQLITE_BUSY during shutdown drain | Deadline, error class, no premature reopen |
| BH-WORK14 | Disk FULL while closing/checkpointing | Preserve WAL/source, no false saved status |
| BH-WORK15 | Worker hangs after cancellation | FAILED_UNSAFE_TO_REOPEN, generation fenced |
| BH-WORK16 | Last connection close still leaves another read connection | No generation cutover until all handles closed |
| BH-WORK17 | Worker queue empty but SQL currently executing | In-flight counter prevents false IDLE/CLOSED |
| BH-WORK18 | Two worker shutdown requests race | Idempotent terminal acknowledgment; no duplicate close |
| BH-WORK19 | Old worker finishes late after new generation selected attempt | Admission fencing prevents unsafe cross-generation write |
| BH-WORK20 | Process kill before worker completion | Next boot SQLite-native recovery, no assumed all commits durable |

### 6.4 Shutdown, restoration, privacy and lifecycle robustness — 20 NOT_RUN

| ID | Scenario | Expected result |
| --- | --- | --- |
| BH-OS01 | Core pre-stop job fires before entry background cancellation | Controlled one global fence/drain |
| BH-OS02 | Core global shutdown stage expires | No success claim; correct recovery on next boot |
| BH-OS03 | HA reload during active admin recovery | Manager job remains tracked and explicitly bounded |
| BH-OS04 | Browser disconnect during restore | Backend operation not abandoned/doubled |
| BH-OS05 | Repeated Hub reload 100 times | One panel/repair manager, zero orphan worker threads |
| BH-OS06 | Supervisor full config restore rewinds journal/pointer/DB | No phantom post-backup history |
| BH-OS07 | Partial restore old config with newer external DB | Conflict/hold, no identity graft |
| BH-OS08 | Backed-up valid snapshot but live DB corrupt | Hub-only admin recovery accessible |
| BH-OS09 | Old DB source has hot WAL | Allow SQLite native recovery at original path |
| BH-OS10 | Unsafe WAL file manually deleted (negative) | Prohibited repair shortcut |
| BH-OS11 | User removes one PS5 during global Repair | Repair remains valid |
| BH-OS12 | Hub disabled or removed after Repair creation | Document UI access/visibility limits accurately |
| BH-OS13 | Old Config Entry points to new PS5 at same IP | No wake/standby or history reassignment |
| BH-OS14 | Stale PSN refresh after account unlink | No reauthorization from old runtime |
| BH-OS15 | User has only Hub/Archive, no consoles | Historical read-only mode, zero LAN probes |
| BH-OS16 | Non-admin calls restore API | Rejected before candidate paths revealed |
| BH-OS17 | Diagnostics export in RECOVERY_HOLD | No raw player/game timeline or tokens |
| BH-OS18 | Incompatible new schema on old integration version | Hold, no automatic destructive migration |
| BH-OS19 | SQL and Config Entry association revision changes during hold | Preview/confirm invalidated, mapping rechecked |
| BH-OS20 | Multi-year synthetic history and repeated boots | Memory/time and task count within measured budgets, no false durations |

**Exactly 80 planned cases** (20 BOOT + 20 ENTRY + 20 WORK + 20 OS), all NOT_RUN. Existing SPEC-008–015 test identifiers intentionally overlap. No test suite was created or executed.

## 7. Sign-off gates: 20 OPEN

| Gate | Evidence | State |
| --- | --- | --- |
| BH-G01 | Domain-wide controller and default DENY_WRITE before all entry setup | NOT_RUN |
| BH-G02 | Hub LOADED with internal RECOVERY_HOLD and valid recovery panel | NOT_RUN |
| BH-G03 | Correct errors vs internal Hold vs HA Retry/Migration Error | NOT_RUN |
| BH-G04 | Typed runtime_data prepared before awaited platform forwarding | SOURCE_VERIFIED / NOT_RUN |
| BH-G05 | One panel/WS global registration across concurrent entries | NOT_RUN |
| BH-G06 | Process-level recovery preflight and single-flight SQLite init | NOT_RUN |
| BH-G07 | No historical writer lease while unsafe, source-only policy approved | PROPOSED |
| BH-G08 | Per-entry source/PSN auth errors isolated from shared ledger | NOT_RUN |
| BH-G09 | One global Repair issue lifecycle through console removal | NOT_RUN |
| BH-G10 | W1 stdlib vs W2 aiosqlite selected through fault evidence and packaging review | PROPOSED |
| BH-G11 | Cancelled futures do not imply SQL worker termination | SOURCE_VERIFIED / NOT_RUN |
| BH-G12 | Exact queue drain and positive worker join/close proof | BLOCKED_IMPLEMENTATION |
| BH-G13 | sqlite3.interrupt limited to query abort, no unsafe reopen | SOURCE_VERIFIED / NOT_RUN |
| BH-G14 | All reader/export/snapshot handles fenced for generation change | NOT_RUN |
| BH-G15 | Ambiguous COMMIT receipts idempotently reconciled | NOT_RUN |
| BH-G16 | Core pre-stop and Failed Unload behaviors safely handled | NOT_RUN |
| BH-G17 | Restart with hot WAL, pointer/journal mismatch and stuck-worker old state | NOT_RUN |
| BH-G18 | Privacy-safe admin recovery, diagnostics, source-only projection | NOT_RUN |
| BH-G19 | HA OS and HA Container boot/shutdown/storage version matrix | BLOCKED_HA_OS |
| BH-G20 | Explicit maintainer acceptance of internal Hold and selected worker semantics | OPEN |

## 8. Release and code authorization boundary

A Source-level finding is not runtime success. Future test evidence must include pinned HA/Python/SQLite/aiosqlite version, serialized worker state transitions, number of tracked connections, last committed observation receipt, gate generation, entry state, no false historical coverage, and actual HA OS/Core startup/stop logs with personal data redacted. A mock alone cannot prove file handle closure.

No worker library is chosen, no executable code or test fixtures created, no new branch, no modification of legacy develop and no approval of technical ADR-0016.

## 9. References

- [Source audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md)
- [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md)
- [SPEC-015](SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/integrations/setup-failures/
- https://contributors.home-assistant.io/core/integrations/repairs/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/frontend/__init__.py
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://aiosqlite.omnilib.dev/en/v0.21.0/api.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py

**Outcome:** 80 unrun test designs, 20 open gates; official/third-party research only.
