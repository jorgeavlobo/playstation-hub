# Home Assistant Core 2026.11 — Degraded-mode capabilities and SQLite worker terminal-evidence audit

**Date:** 2026-11-06
**Status:** SOURCE_RESEARCH / PROPOSED / NOT_IMPLEMENTED / NOT_TESTED
**Versions reviewed:** Home Assistant Core 2026.11.0, Python 3.14 reference, SQLite upstream, aiosqlite v0.21.0, v0.22.0, v0.22.1.
**Project assumptions:** ADR-0011 ACCEPTED at product level: one Hub/Archive Config Entry, separate console/PSN entries, one global controller and panel, long-lived archive, no mandatory MQTT/add-on/external DB.
**Companions:** [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md), [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md).
**Git:** documentation on main; develop frozen.

> Source-confirmed framework behavior is separated from the proposed PlayStation Hub policy. Source review does NOT establish a working integration, a selected worker library, a safe SQLite cutover, or an approved product decision about degraded controls.

## 1. New findings

1. An HA ConfigEntry being LOADED means its configuration setup succeeded. It is not a capability token to write history or control hardware. Likewise Entity.available is a presentation/availability property, not a substitute for backend operation authorization.
2. HA services, entity actions and authenticated WebSocket commands are distinct entry points. A hidden frontend power button or an unavailable-looking entity is not a sufficient backend security boundary; the handler must recheck controller generation, current canonical console identity and user/service permissions.
3. State is a product of several dimensions: global controller recovery/shutdown state, physical source freshness and identity, PSN account authorization, selected ledger provenance, worker/lease health, entry-kind native state, and caller identity. Store capability decisions as derived ephemeral results; never use one overloaded "healthy" Boolean as permission for all operations.
4. In aiosqlite v0.21.0 Connection inherits threading.Thread. In v0.22.0 Connection owns a private Thread. In v0.22.1 stop() was added and a ResourceWarning is emitted for an unclosed connection. These API and lifecycle changes invalidate source assumptions that depend on Connection.join being publicly available.
5. In all three pinned aiosqlite versions, a queued SQL operation is submitted BEFORE the caller awaits its Future. Cancelling an await may therefore leave SQL running or waiting. Python concurrent.futures likewise cannot cancel already-running ThreadPoolExecutor functions.
6. aiosqlite v0.22.1 close first awaits SQLite close and then a queued stop sentinel; that sentinel's Future is notified via event-loop call_soon_threadsafe before the worker breaks and returns from its thread function. Therefore the close Future is stronger than cancelling a waiter, but is not literally a public Thread.join proof for all interruption cases. A generation cutover requires an approved positively testable worker-terminal contract.
7. A history RECOVERY_HOLD need not suppress all useful source observations. Candidate default: permit only ephemeral, clearly UNSAVED status if a physical console is independently verified; deny physical wake/standby and Remote Play control during global recovery until a separate maintainer policy decision. Always deny attribution/control when identity is disputed.
8. A verified immutable archival snapshot may be read under separate bounded read-only leases and authorization even if the active live SQLite writer is fenced. Never silently treat a raw tar copy, corrupted live DB or abandoned worker as safe history.

## 2. Evidence register

| ID | Evidence kind | Reviewed source behavior | Implication |
| --- | --- | --- | --- |
| DC-01 | CORE_PINNED | config_entries.py: independent entry locks and native LOADED / SETUP_RETRY / SETUP_ERROR | No global data permission inferred from entry state |
| DC-02 | CORE_PINNED | helpers/entity.py Entity.available returns entity availability | UI and entity status are not backend ACL |
| DC-03 | CORE_PINNED | websocket_api/decorators.py require_admin checks user.is_admin | Admin recovery operations enforce backend authorization |
| DC-04 | CORE_PINNED | helpers/service.py entity-service helper has admin_only option | Automations and services require the same gate as WS |
| DC-05 | CORE_PINNED | helpers/entity_platform.py entity service registration is shared at platform level | No per-browser/UI-only safety logic |
| DC-06 | CORE_PINNED | Core global shutdown job runs before background task cancellation | Global write fence is possible, but timeouts not proof of worker close |
| DC-07 | CORE_PINNED | ConfigEntry.background tasks are entry-owned | Cannot own process-global history writer through one PS5 task |
| DC-08 | PYTHON_OFFICIAL | Executor.shutdown(wait=False) is not a worker join | Running operation can persist |
| DC-09 | PYTHON_OFFICIAL | cancel_futures only cancels work not started | Running COMMIT may finish despite cancelled caller |
| DC-10 | PYTHON_OFFICIAL | sqlite3.Connection.interrupt aborts executing statement | Not a close/join/COMMIT receipt |
| DC-11 | PYTHON_OFFICIAL | sqlite3.check_same_thread default true; sqlite_version is linked C runtime | Explicit connection/thread and version ownership |
| DC-12 | THIRD_PARTY_PINNED | aiosqlite 0.21 Connection(Thread), FIFO queue | Cancelled Future does not unqueue SQL |
| DC-13 | THIRD_PARTY_PINNED | aiosqlite 0.22 Connection owns private Thread | A prior public Thread.join-based plan is invalid |
| DC-14 | THIRD_PARTY_PINNED | aiosqlite 0.22.1 stop, close and destructor warning | New cleanup path, still needs terminal proof |
| DC-15 | THIRD_PARTY_PINNED | Worker posts sentinel Future result before loop breaks | Async close receipt not equivalent by definition to join |
| DC-16 | SQLITE_OFFICIAL | hot WAL/SQLite rename hazard and distinct generations | Cutover only after no old connection can act |
| DC-17 | PROJECT_PROPOSAL | Source observation-only lane during RECOVERY_HOLD | Keep current status possible without historical write |
| DC-18 | PROJECT_PROPOSAL | Read-only archive candidate independently validated | Recovery UI usable without unsafe live writer |

## 3. Capability dimensions (not one flat status)

Global controller: STARTING, READY, RECOVERY_HOLD, FENCING, SHUTTING_DOWN, FAILED_UNSAFE_TO_REOPEN.
Entry kind: HUB, CONSOLE, PSN_ACCOUNT, with independent native ConfigEntry lifecycle.
Source: VERIFIED_FRESH, VERIFIED_STALE, OFFLINE, UNVERIFIED_IDENTITY, IDENTITY_CONFLICT.
Ledger: LIVE_VERIFIED, SNAPSHOT_VERIFIED_READ_ONLY, MISSING_WITH_RECOVERY_EVIDENCE, CORRUPT, FORKED_OR_AMBIGUOUS.
Worker: READY, FENCED, CLOSING, TERMINAL_VERIFIED, TERMINATION_UNKNOWN.
Caller: SERVER_INTERNAL, AUTHORIZED_ADMIN, AUTHORIZED_USER, AUTOMATION_SERVICE, REVOKED.
Operation: SEE_STATUS, OBSERVE_LAN, READ_HISTORY, INGEST_HISTORY, POWER_CONTROL, REMOTE_PLAY, PSN_READ, TOKEN_REFRESH, MAKE_SNAPSHOT, RESTORE_PREVIEW, RESTORE_COMMIT, EXPORT, PURGE, DIAGNOSTICS.

**Deny-precedence proposal:** shutdown/unsafe worker denies mutation; failed/unloaded entry denies source-owned operations; identity conflict denies hardware control and attribution; unverified ledger denies historical write/read from corrupt source; user ACL denies privileged recovery/exports irrespective of displayed sidebar. Only thereafter consider a narrow per-operation allow.

## 4. Proposed operation capability matrix

Key: A = allow after independent auth/evidence checks; S = ephemeral status-only, labelled UNSAVED and never persisted; R = read-only separately verified artifact; X = deny; ? = future maintainer policy/implementation proof.

| Operation | NORMAL (fresh identity, ledger READY) | Global RECOVERY_HOLD (identity verified) | IDENTITY_CONFLICT | Verified archive but physical source OFFLINE | FAILED_UNSAFE_TO_REOPEN |
| --- | --- | --- | --- | --- | --- |
| Hub panel and global Repair | A | A | A | A | A if control plane works |
| Ephemeral current LAN state | A | S? | X as trusted state | X for fresh status | S? only if independent |
| Read trusted committed live history | A | X if live not validated | X for cross-identity attribution | A from valid source | X if unsafe live handles |
| Read immutable verified snapshot | R | R if independent lease safe | R only if owner ACL validated | R | ? safe separate reader, no old handles |
| Commit historical observation | A | X | X | X without new evidence | X |
| Physical power / Remote Play | A with identity/permission | X default (review later) | X | X without source channel | X |
| Read PSN account status | A if account valid | ? account-only, not history | X for disputed account | A if independent account valid | ? independent of DB |
| Refresh account token | A for valid per-account authorization | ? only isolated credential store | X | A if valid account independently | ? defer |
| Create backup snapshot of active ledger | A from validated source | X from corrupt/unverified source | X if metadata disputed | A if ledger verified | X |
| Candidate inventory / recovery preview | A admin | A admin | A admin with redaction | A admin | A admin if no unsafe worker touched |
| Promote recovery | A admin after fence/close | ? admin after positive terminal proof | ? identity review required | ? | X until terminal proof |
| Purge history | ? privileged and separate consent | X | X | ? policy | X |
| Sanitized diagnostics | A | A | A | A | A |

The matrix is **not** the Home Assistant native Quality Scale, access-control implementation, or an approved final user policy. Entity.available=False cannot alone prevent an automation or service handler from calling a source method; revalidate at every backend action entry point.

### By entry kind

- HUB: can expose one admin panel, Repairs, known validated archive reads, and recovery actions. Never creates a pretend PS5 entity, physical monitor or account token refresh.
- CONSOLE: owns LAN monitoring, current state and local device entities, but never a second global history writer. Durable writes require an active generation-fenced lease. In RECOVERY_HOLD a separately approved OBSERVATION_ONLY capability may show current status UNSAVED, with no backfill.
- PSN_ACCOUNT: can authenticate/account-read independently where credentials are valid; no Sony token is inferred from restored game history. Shared history hold denies account-derived historical attribution. Token refresh during storage hold is optional and unapproved; identity conflicts deny it.

### Source changes vs history

A transition READY -> HOLD revokes future historian admission immediately, settles previously accepted work with receipts, and labels subsequent ephemeral observations UNSAVED. Returning to READY starts a new evidence range; the down interval remains UNKNOWN. A manager state transition does not prove the physical console changed power state or gameplay.

## 5. Worker lifecycle differences

### aiosqlite v0.21.0

Connection extends threading.Thread; a connection worker drains queued (future, function) jobs. close queues SQLite close and then signals a stop sentinel. _execute submits the SQL function before await. Cancellation of an awaiting Future is not removal of the already enqueued function.

### aiosqlite v0.22.0

Connection no longer inherits Thread; it owns an internal _thread, and worker function lives outside class. The close path awaits a queued stop sentinel. Code expecting a public Connection.join cannot be ported directly.

### aiosqlite v0.22.1

Connection.stop() requests worker-owned close_and_stop and returns a Future if an event loop exists; __del__ warns and attempts fallback stop for unclosed connections. close() awaits queued sqlite3.close and then awaits a stop future. _execute still enqueues before await. The worker publishes Future completion through call_soon_threadsafe before breaking on the stop result. **Positive closure and practical terminality need explicit adapter test; a public join guarantee was not identified from this API.** Do not rely on private _thread attributes in a compatibility-sensitive integration.

### W1 stdlib sqlite3 + dedicated executor

A dedicated single-worker executor permits explicit owner-controlled sqlite3 close and Executor.shutdown(wait=True) in a safe non-event-loop-blocking context; already-running functions cannot be cancelled. Need bounded queue, receipts, join proof, and tracking of ALL reader/snapshot connections, not just the writer.

### W2 aiosqlite (version not selected)

One queue per connection, async API and easier event-loop use; no cancellation-based guarantee that queued work is abandoned, and version 0.22 changed terminal API shape. Require a documented, compatible positive worker-stop signal or a reviewed adapter and fault tests before selecting it.

### W3 subprocess isolation (deferred)

Can supply process-exit boundary for irrecoverably hung in-process worker but adds IPC, maintenance, HA installation packaging and supervision complexity. Not default.

## 6. Proposed positive terminal handshake

1. FENCE current manager generation, denying all new historical write/read/snapshot admissions and source/service commands that depend on that generation.
2. ACCOUNT for every accepted SQL job with stable receipt and states QUEUED, RUNNING, COMMIT_ACK, COMMIT_UNCERTAIN, TERMINAL.
3. DRAIN bounded outstanding operations and readers. An empty queue alone does not prove no executing job.
4. Optional sqlite3.interrupt may abort a long query but does not prove a rollback, connection closure or worker exit.
5. CLOSE every connection in its owner thread via a supported close API, including read-only and backup workers, and handle errors.
6. WAIT for a supported terminal worker acknowledgement (e.g. dedicated executor shutdown(wait=True) performed off event loop; aiosqlite requires review of public lifecycle). Do not promote pointer if join/termination remains unproven.
7. VERIFY zero in-flight/queued jobs and active leases; no old generation path may be touched by old worker. State becomes CLOSED_VERIFIED.
8. Only then permit ADR-0015's separate active-generation pointer switch and new writer opening.
9. On timeout/failure, record FAILED_UNSAFE_TO_REOPEN, retain old SQLite file and hot WAL/journal and keep Hub RECOVERY_HOLD UI available if the control plane remains healthy.
10. On next clean process start, let SQLite perform native recovery at the selected original path; reconcile ambiguous COMMIT receipts and history gaps.

A closed connection receipt is stronger than a cancelled asyncio task, but *proof of terminal worker* is a separate requirement until explicitly established for the selected library. The goal is no old worker that can execute SQL after the pointer changes.

## 7. Priority and uncertainty

**P0:** Backend permission checks at entity service, WebSocket and device control execution; per-source canonical identity/generation fences; no historical ingestion under RECOVERY_HOLD.
**P0:** Actual worker close/terminal contract with cancellation and busy SQL; test aiosqlite v0.22.1 against stdlib executor and verify the version distributable in the target HA installation.
**P0:** No active generation switch before all old SQLite connections/workers are positively terminal.
**P1:** Approve whether LAN-only status should remain visible in hold, and whether power controls should ever be permitted while storage is degraded. Conservative candidate: deny controls.
**P1:** Decide scope for PSN read/refresh under hold and independently validated immutable snapshot read.
**P1:** Define exact public entity availability semantics and localization with no security inference from frontend.
**P1:** Test bounded data refresh, automatic retries, recovery status under two browser/admin tabs, and policy on last enabled Hub entry removal.

## 8. Source links

- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/service.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.1/aiosqlite/core.py
- https://aiosqlite.omnilib.dev/en/stable/changelog.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/howtocorrupt.html
- [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md)
- [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md)

**Final status:** source-backed architectural research only; no tests, code, new branch, installed package or Home Assistant user data changed.
