# Home Assistant 2026.11.0 — Shared services, SQLite ownership and multi-entry race audit

**Review date:** 2026-11-06  
**Status:** Source-pinned research, not implementation, approval or testing  
**Branch:** main (documentation only); develop remains frozen  
**Authority:** Supplements the Bible, SPEC-008, ADR-0004/0006/0008/0010; does not silently accept any proposed ADR  
**Scope:** One Home Assistant instance, many independently configured PlayStation consoles, optional PSN accounts, one integrated sidebar, one application-owned historical store

> Evidence labels: CORE_SOURCE means directly checked against Home Assistant Core tag 2026.11.0; SQLITE_OFFICIAL means SQLite upstream documentation; PROJECT_PROPOSAL is a design to approve/test; OPEN is not verified on HA OS or hardware. Source code establishes framework behavior, **not** that PlayStation Hub works.

## 1. Main result and precise problem

SPEC-008 correctly proposes separate console Config Entries and a shared history writer, but does not yet define a safe protocol for concurrent acquisition, partial setup, unload, reload, long-running historical readers, backup and final shutdown.

The entry-local setup lock is **not a global lock**. In pinned Core, each ConfigEntry constructs its own setup_lock. Different entries may configure/unload concurrently. A naive "if no manager, create one" check containing an await may create two SQLite workers, apply migrations twice or register the same panel twice. Equally, closing the writer when entry A unloads is unsafe if B is still loading or a browser report is running.

**Recommended project structure, not approved:**

    Integration-wide HubController (one object per Home Assistant process/domain)
      Control plane: registry of entry owners, generation, initialization single-flight,
                     lifecycle lock, entry leases, query leases, backup leases, health
      Stable API plane: once-only WebSocket command handlers and sidebar registration
      Data plane: lazily opened HistoryService with exactly one serialized writer
      Entry A: typed ConsoleRuntime + LAN monitor + push-only coordinator + entry lease
      Entry B: independent ConsoleRuntime + LAN monitor + push-only coordinator + entry lease
      Entry C: optional PsnAccountRuntime + scoped token refresh + optional data lease
      Browser connection: separately cancellable, authorized subscription/report query

A "singleton" here means **one live service per HA process and integration domain**. It does not magically enforce one instance across two HA installations sharing a filesystem; multiple Core processes writing the same application directory are out of scope and require explicit protection.

## 2. Pinned Home Assistant source findings

| Finding | Pinned file / behavior | Architecture consequence |
| --- | --- | --- |
| CORE-SH01 | config_entries.py: setup_lock instantiated on each ConfigEntry (~601); independent async_setup_locked (~1085) | Serialize shared resource transitions ourselves; do not mistake per-entry locking for a global mutex |
| CORE-SH02 | config_entries.py: async_setup_entry failure runs _async_process_on_unload (~1045) | Register compensating cleanup immediately after acquiring each resource; ensure it is idempotent |
| CORE-SH03 | config_entries.py: successful unload runs async_unload_entry, then _async_process_on_unload and removes runtime_data (~1173-1183) | Complete ordered stop/flush/release in the awaited integration unload method; unload callbacks are a safety net |
| CORE-SH04 | config_entries.py: failed unload moves entry to FAILED_UNLOAD without running successful on-unload processing (~1184-1200) | Retain ownership and flag a failed lifecycle; never shut down shared resources assuming cleanup completed |
| CORE-SH05 | config_entries.py: _async_process_on_unload schedules returned coroutines as entry tasks, cancels background tasks, waits up to 10 seconds (~1378-1405) | Do not rely on callback registration order to sequence asynchronous DB drains; cleanup must be separately awaited and bounded |
| CORE-SH06 | config_entries.py: async_forward_entry_setups must be awaited while setup lock held (~2720 onwards) | No fire-and-forget entity platform initialization |
| CORE-SH07 | frontend/__init__.py: async_register_built_in_panel rejects an existing route unless update requested (~249-278), and async_remove_panel exists (~280+) | Register one known-owned route, reject collisions, provide explicit hide/remove behavior |
| CORE-SH08 | panel_custom/__init__.py: async_register_panel delegates to frontend global panel registry (~80-145) | Sidebar registration belongs to integration-scope controller, not console entries |
| CORE-SH09 | websocket_api/__init__.py: async_register_command stores handlers in a global command dictionary by name (~77-94) | Duplicate names can replace handlers rather than raising; guards and ownership checks are mandatory |
| CORE-SH10 | knx/websocket.py: KNX registers WebSocket handlers and one panel / static path in its integration scope (~67-118) | Useful upstream one-panel pattern, not a proof of our teardown or user access model |
| CORE-SH11 | backup/manager.py: pre/post backup platform hooks exist and are invoked for CoreBackupReaderWriter (~547-573; ~1902, ~1973) | Hook mechanism exists; it is NOT sufficient proof that HA OS Supervisor backup invokes the same hooks |
| CORE-SH12 | hassio/backup.py: SupervisorBackupReaderWriter delegates creation to the Supervisor backup job | Verify HA OS/Supervisor callback and filesystem inclusion separately before claiming supported consistent backups |
| CORE-SH13 | backup/const.py and manager.py: generic Core backup excludes **.db-shm, not arbitrary custom .db or .db-wal files**; exclude_database targets Home Assistant's Recorder DB only | A live PlayStation SQLite file may be copied as an unsafe moving target; a consistent additional snapshot does not automatically exclude the live file |
| CORE-SH14 | frontend async_remove_panel is available, but no supported static-path removal was established in this audit | Do not promise full unload/re-install of static routes without a HA restart |
| CORE-SH15 | entry.async_create_background_task is entry-owned and cancelled on unload; normal coordinator interval polling is listener-owned | LAN producer remains entry-owned, writer global, frontend never an observation owner |

Pinned upstream links are indexed in §16. Line numbers are navigation hints for the exact tag, not an API stability guarantee.

## 3. Three distinct lifetimes (PROJECT_PROPOSAL)

**Process / integration-control lifetime:** HubController, command route registration, panel route registration and lifecycle state are created once on integration-domain setup, and persist until Home Assistant stops. A controller object remains even while data plane is closed. It must not be captured in stale unregistered callbacks after a replacement.

**Entry lifetime:** Each ConsoleRuntime and PsnAccountRuntime is owned by its ConfigEntry, tracked by entry ID and runtime generation. An entry can be unloading or failed while others are active. A physical console's LAN socket/probe is never owned by the shared writer or a browser.

**Data operation lifetime:** History query, export, consistency snapshot or pending writer commit is owned by a bounded operation with its own token/deadline. Unloading the last entry must not close a connection used by a *legitimate* in-flight read or backup, nor may an abandoned browser query keep it alive forever.

The sidebar and WebSocket command **registrations** are control-plane objects, not owners of an open SQLite connection. Their handlers resolve the current manager/lease on each permitted operation. Idle UI connections do not pin the writer or enable extra LAN polls.

## 4. Creation protocol and one-flight initialization (PROJECT_PROPOSAL)

1. Integration async_setup constructs the domain-scoped controller with an internal asyncio.Lock (or a supported equivalent). The controller is inserted into hass.data[DOMAIN] once, with collision detection; no physical console is made the "first owner".
2. Panel/static/WS registrations are separately guarded by the controller's **registered** state; fail closed on a conflicting route or command namespace instead of replacing another integration's handler.
3. Every Config Entry asks the shared controller for a **pending lease** before starting any task that might write history. The controller serializes lease acquisition, open/close transitions, and datastore schema initialization.
4. If datastore state is NEW, create one manager-owned initialization task/future and transition to INITIALIZING under the lifecycle lock. Release the lock before waiting on blocking/async file I/O; all concurrent entries await the *same* initialization result.
5. A cancelled entry setup must detach only its waiter; it must not cancel initialization that another waiter still needs. Manager-owned single-flight work, cancellation shielding where justified, and explicit shutdown fencing need synthetic tests; do not adopt a bare untracked create_task.
6. Initialization opens the database once, performs integrity/version preflight, migrations, path verification and writer startup in an executor/owned worker; only READY is leasable for durable commits. Migrations are never run in parallel.
7. The pending lease becomes ACTIVE only after that entry has completed its own setup contract. Setup failure releases pending ownership even if the failure occurred after allocating a socket; late callbacks from the failed generation are fenced.
8. An initializing manager with zero remaining prospective leases must cancel/finish initialization safely and close itself, not leave an orphan writer.
9. A new acquire while CLOSING must wait for the old generation to be completely CLOSED and then create the next generation, **not** concurrently open a second writer.
10. Do not hold the controller lifecycle lock across arbitrary user callbacks, network calls, SQL migration or platform forwards. Separate short transitions from awaited work; impose a consistent lock acquisition order.

**Lease identity:** unique opaque token, owner type, entry_id or operation_id, generation, status (PENDING/ACTIVE/RELEASING/RELEASED), and acquisition timestamp. A lease is not only a numeric reference count. Duplicate release is harmless and must not make the count negative. Entry reconfigure/reload gets a new runtime generation.

## 5. Data service state machine and invariants (PROJECT_PROPOSAL)

    ABSENT -> INITIALIZING -> READY -> QUIESCING -> CLOSING -> CLOSED
                 |              |          |          |
                 v              v          |          v
             FAILED_INIT     DEGRADED  DRAINING     FAILED_CLOSE
                 |              |                     |
                 +---- controlled retry/recovery ----+

- S1: at most **one READY/INITIALIZING/CLOSING writer generation** per Home Assistant process and database path.
- S2: every accepted durable write belongs to a validated current console/account owner and entry generation.
- S3: no new operations are admitted after the applicable generation is fenced.
- S4: CLOSE requires zero PENDING/ACTIVE entry leases, zero admitted reads/exports/backup snapshots and zero outstanding durable transactions; already admitted operations must drain or fail explicitly.
- S5: data read views never depend on active browser panels or HA entities.
- S6: panel + WebSocket namespace is registered at most once within the process. A panel being registered does not imply the DB is READY.
- S7: one console's failure cannot revoke another console's lease.
- S8: closing/opening generations may not overlap at the same SQLite file.
- S9: unknown, stale, unsaved and durable are visibly different states; there is no silent replay of unavailable intervals.
- S10: permanent data deletion requires explicit user-authorized policy and never follows from one Entry unload.

A counting-only implementation violates S4 if a read was issued just before the last entry releases. A manager with unlimited write queue violates S3/S4 under disk failure.

## 6. Setup ordering, partial failure and compensation

**Corrected proposed order, aligned with official HA runtime-data guidance:** validate canonical identity -> acquire PENDING data lease -> register idempotent fallback cleanup -> initialize shared datastore -> construct typed per-entry transport/reducer/coordinator in an inert state -> **assign entry.runtime_data before forwarding platforms** -> register owned cleanup -> **await platform forward** -> activate lease -> start the single entry-owned monitor only after the lease is active -> return setup success. If activation or monitor startup fails, fence the entry generation and run compensating cleanup. No observation is admitted for durable writing while the entry lease is only PENDING.

**Mandatory change from a naive design:** register cleanup *before* each irreversible allocation. In Home Assistant Core, entry async_on_unload callbacks are executed on setup failure. However, asynchronous callbacks are scheduled and waited together, not sequentially guaranteed by their registration order. Therefore ordered cleanup cannot simply be spread across a stack of callbacks that happen to be registered last-in-first-out.

During setup failure the integration should explicitly request bounded cleanup, with async_on_unload providing idempotent fallback if called by Core. If cleanup cannot complete safely, record a leak/degraded state; do not announce READY or discard the only reference to an active writer/socket.

A previously identified sleeping console may load as degraded (per SPEC-008), but a storage failure cannot be silently classified as "history saved". Whether LAN-only operation is allowed without history is a separate product acceptance decision (recommended: yes, explicitly flagged UNSAVED).

## 7. Unload ordering and failed unload

**Proposed normal order:** fence entry generation -> disallow new manual operations/probes -> stop monitor and await in-flight bounded probe -> finish or explicitly invalidate accepted write operations -> unload native entity platforms -> unsubscribe per-entry callbacks -> release active data lease -> clear runtime projection. Ensure shutdown order does not deadlock against callbacks that need the manager lock.

If a platform unload fails, Home Assistant may leave the entry FAILED_UNLOAD and **does not** automatically process successful cleanup. It would be dangerous to mark resources fully freed and close shared storage while callbacks could still be running. A failed unload remains a tracked/diagnosable owner in the controller, with writes fenced and no claim of clean shutdown. Recover through controlled retry/restart after the failure; never fake success.

Under Core 2026.11.0 the on-unload task wait has a ten-second bound. This does not guarantee a hung Python operation has stopped. A timed-out worker is a fatal "unsafe to reopen" condition for the same DB path until ownership is positively resolved (or HA restarts with verified process exit).

## 8. Writer, readers and fairness

- One serialized database writer owns commits and schema migration. Use a dedicated worker/executor design proven to avoid Home Assistant event-loop blocking and unsafe concurrent sqlite3 usage.
- Writes contain observation ID, console ID, accepted-generation fence, session reducer transition and durable cursor in **one transaction**. A callback receiving "accepted" before COMMIT is not a durable acknowledgement.
- Each console gets a bounded per-source ingress budget; the writer uses bounded fair scheduling so repeated faults in A do not indefinitely starve B.
- API queries use read-only, bounded-life snapshot transactions with concurrency limits, quotas, cancellation and server-side page limits. Long readers can prevent WAL checkpoints: bound transaction and cursor lifetime.
- Manual refresh must use the existing per-console probe owner and cannot bypass writer backpressure or identity checks.
- If ingress is full or SQLite is read-only/full/busy, current LAN observations may still be shown but history is explicitly UNSAVED/INCOMPLETE with a coverage gap. Do not keep a limitless queue or pretend uncommitted observations were stored.
- Cancellation of a client/entry is not a licence to cancel a SQLite thread mid-transaction and claim rollback; wait for a definitive commit result or use idempotent recovery with uncertain acknowledgement.
- A temporarily failed writer may recover using bounded retry with reason classification. Permanent corruption never triggers silent replacement with an empty database.

## 9. SQLite official semantics and project design consequences

SQLITE_OFFICIAL (https://www.sqlite.org/wal.html): WAL supports overlapping readers and one writer, but readers with long-lived snapshots can starve checkpoints; WAL mode can still return SQLITE_BUSY. It requires compatible local-filesystem sharing, not arbitrary remote/network mounts.

SQLITE_OFFICIAL (https://www.sqlite.org/pragma.html): in WAL mode synchronous=NORMAL can lose a recently acknowledged transaction on power failure, even when database consistency is preserved; synchronous=FULL adds a WAL sync on each commit. **Preferred safety candidate:** benchmark FULL before accepting any downgrade, since the product promises conservative durable session evidence. FULL does not protect from every hardware/filesystem failure.

SQLITE_OFFICIAL (https://www.sqlite.org/backup.html): SQLite Online Backup API makes an internally consistent database snapshot of a running database, with defined concurrent use. SQLITE_OFFICIAL (https://www.sqlite.org/lang_vacuum.html): VACUUM INTO also creates a consistent snapshot but an interrupted output may be incomplete and does not itself guarantee fsync of the destination.

**Project proposals:** bounded busy timeout and retries; enable foreign keys on every connection; transactional migrations; read-only repair path after corruption; per-transaction ID constraints; deterministic crash/restart reconciliation; explicitly budget WAL checkpointing and disk use. Exact PRAGMAs, storage path, backup inclusion and maintenance cadence remain OPEN until HA OS tests.

## 10. Backup and restore: newly identified critical blocker

**Core-source-confirmed:**
- Core BackupManager supports async_pre_backup and async_post_backup integration-platform hooks.
- The non-Supervisor CoreBackupReaderWriter calls pre hooks, creates the backup archive, then runs post hooks in finally.
- Its generic archive exclusions omit arbitrary custom SQLite databases and **.db-wal**; a broad *.db-shm exclusion alone does not make a WAL database-copy consistent.
- HA OS uses SupervisorBackupReaderWriter, a different code path. This audit did not prove identical hook invocation or file-selection semantics for the Supervisor's archived Home Assistant configuration.

**Consequences:** "a backup hook exists" is not equivalent to "our live SQLite data will be consistently backed up on Home Assistant OS." A normal copy of the active .db without an atomic snapshot can be inconsistent and must not be trusted as a verified restore point.

**Candidate design pending validation:**
1. During a verified backup handshake, take a bounded Online Backup API snapshot to an immutable temporary file plus versioned manifest/checksum; the writer may continue when snapshot succeeds.
2. Verify snapshot integrity, free space and the inclusion of the *snapshot and manifest together* in the actual HA OS archive.
3. Do not rely on the concurrently copied live DB or WAL as the authoritative restore source. Determine whether Supervisor can exclude/mask live files via supported integration facilities; if not, preserve the snapshot, define deterministic startup restore selection and label extra live copies as non-authoritative.
4. A failed/partial snapshot must abort the relevant backup handshake or emit a clear failure; never claim success.
5. Post-backup cleanup, cancellation and orphan snapshot GC must be safe even if post hook never fires (power cut); test repeated backups and upgrades.
6. The restoring process must verify checksum, schema, identity and checkpoint before adopting data. Offline/unknown gaps are recorded; never join durations across a restore gap.
7. If platform hooks do not run under HA OS Supervisor, this strategy is **blocked**; investigate supported Supervisor/Core integration lifecycle and test archive contents before implementing.
8. If an external backup method bypasses Home Assistant entirely, consistent database snapshot creation is not implied.

**Additional pitfall:** a snapshot copied just before a long-running archive may be internally consistent but represents an earlier point in time; record the snapshot cursor and time. Do not advertise the backup as containing observations that occurred after that cursor.

## 11. One panel and one WebSocket namespace

CORE_SOURCE: frontend.async_register_built_in_panel rejects unrequested overwrites and exposes async_remove_panel. CORE_SOURCE: websocket_api.async_register_command stores handlers by command string without rejecting duplicate registrations in the inspected function. A naive "register if not already registered" shortcut can hide route collisions owned by another integration.

**Recommended control-plane lifetime:** register static paths, panel and WebSocket command handlers at most once in the HA process, using a domain-owned installation guard and deterministic route names; functions resolve the *current* HubController instead of closing over an obsolete HistoryService. For zero active entries, show an explicit no-device/offline/archived state if the panel remains registered, or deliberately remove its menu entry according to §12.

No supported static-path **unregistration** interface has been established. Removing only the frontend panel does not necessarily remove the HTTP static path or WebSocket handlers. Do not promise fully reversible hot-uninstall or in-process code replacement; verify the actual Marketplace restart policy.

All queries/actions revalidate HA authentication, authorization, owner existence and runtime generation at request time. Browser disconnection removes its own subscriptions only; it never closes a console monitor or writer. A stale frontend bundle cannot submit legacy operations without schema/version negotiation.

## 12. The zero-entry and archive-access decision (OPEN)

**Policy A (recommended for initial release):** keep sidebar visible whenever at least one configured PlayStation Hub entry exists, even if that entry is temporarily unloaded/degraded. After the **last entry is removed**, hide panel on next controlled reconciliation and preserve the historical DB under an explicit retention policy. If an already-running process can still serve the page, it must show inactive state; after restart with no entries the integration may not load at all.

**Policy B:** install a separate permanent "hub" Config Entry owning archived-data access. Better no-console archive UX but adds special lifecycle/setup semantics; not approved.

**Policy C:** keep panel visible after last entry removal in the current process, then lose it at the next restart. Inconsistent UX; reject as deliberate product design.

No policy may equate "last active monitor stopped" with "delete all history". Account-only entries and users with only archives need explicit acceptance criteria. Count configured entries, loaded runtime leases and active queries separately; they are different quantities.

## 13. Failure scenarios and required results

| Scenario | Failure risk | Required project behavior |
| --- | --- | --- |
| A and B run setup concurrently | Two DB instances, two migrations | Single-flight initialization, one writer and panel |
| A setup cancels while B waits | A cancels B's initialization | Independent pending lease cancellation; shared task continues if needed |
| A fails after socket creation | Socket/task/pending lease orphaned | Registered fallback + awaited compensation |
| A unloads while B writes | A closes B's writer | A release does not revoke B's token |
| Last entry unloads during a read | Connection closes mid-page | Bounded query lease or explicit cancellation/error before shutdown |
| Last entry unloads during backup | Archive/snapshot uses closed file | Snapshot lease with bounded completion or explicit backup failure |
| New entry appears during CLOSING | Two writers / SQLITE_BUSY | Wait for generation closure, reopen once |
| C loses PSN authorization | A/B LAN history stops | Account tasks only stop; LAN unaffected |
| Shared disk becomes full | Queue grows, fabricated history | Bounded queue; UNSAVED and gap; optional LAN-only degraded mode |
| One read stalls checkpoint | WAL expands indefinitely | Read deadlines, interrupt/release, WAL telemetry and safe maintenance |
| HA stops during COMMIT | Unknown acknowledgement | Recover transaction/idempotency; never invent uptime |
| Unload method raises | Core leaves FAILED_UNLOAD | Retain owner/fence, diagnose; no premature global close |
| Reconfigure IP while UDP arrives | Old packet updates new identity | Generation and canonical-ID fences |
| Another integration registers our panel URL | Wrong panel shown/overwritten | Detect ownership collision, fail closed |
| Restore old archive | Time gap misattributed to game | Restore cursor, stale/unknown coverage |
| Last entry deleted | Lost ability to browse archives | Explicit archive accessibility and retention policy |
| Two HA instances access same DB path | Two process owners | Unsupported; detect and document rather than guarantee |

## 14. Operational observability and bounded recovery

Track **sanitized** manager_state, generation, pending/active entry count, active read/snapshot count, queue depth/high-water mark, oldest pending write age, last successful COMMIT, WAL growth/checkpoint health, last backup cursor, close wait time, recovered/unrecoverable error class, leak state. No raw account identifiers, tokens, packet payloads or private history in public diagnostics.

Classify errors as transient busy/timeout, disk full/read-only, schema mismatch, corruption, failed unload, stale-generation, and backup failure. Apply bounded jitter/backoff and one-event-on-change logging rather than noisy per-probe stack traces. A repair workflow must not overwrite damaged data or silently migrate incompatible schema.

## 15. Design questions before code approval

- Q1: Should the initial product allow **LAN-only degraded operation** while history SQLite is unavailable, with explicitly unsaved intervals? Recommended yes, subject to clear UI contract.
- Q2: Should the data manager close immediately when the last active entry/query lease releases, or remain idle for a short bounded grace interval? Recommend immediate deterministic close first; optimize later after lifecycle tests.
- Q3: Is the panel registered during integration async_setup or on first verified entry? Verify setup semantics with zero entries and panel collision handling; recommended domain-level registration with explicit no-entry policy.
- Q4: Can Home Assistant OS Supervisor backups run pre/post integration hooks and capture an immutable snapshot while excluding non-authoritative live files? **BLOCKED until source and HA OS archive verification.**
- Q5: Which exactly supported data path and retention/permissions are safe on HA OS? OPEN.
- Q6: What guaranteed interruption/timeout contract will the selected SQLite worker library provide? OPEN.
- Q7: Is a hub-only archive Config Entry required for a useful multi-year history product? DEFER until UX decision.
- Q8: Which shutdown event/task mechanism is appropriate to fence integration-global work before the HA process exits? Verify pinned Core and HA OS synthetic test.

## 16. Primary sources and related project documents

### Exact Home Assistant Core 2026.11.0 source
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/frontend/__init__.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/panel_custom/__init__.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/__init__.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/knx/websocket.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/const.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/http/server.py

### SQLite upstream
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/lang_vacuum.html
- https://www.sqlite.org/pragma.html

### PlayStation Hub
- [SPEC-008: Multi-console runtime and coordinator lifecycle](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md)
- [SPEC-009: Shared services and SQLite lifecycle tests](../specifications/SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md)
- [ADR-0008: Storage, durability and backup](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0010: Sidebar and API](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)

**Outcome:** Source evidence and explicit proposals added; no code, executables, tests, hardware observations, approved ADR or new branch. The critical unresolved issue is HA OS/Supervisor backup consistency, not whether generic SQLite snapshots exist.


## 17. Supervisor-to-Core backup handshake re-audit — 2026-11-06 (stronger source evidence)

**Correction to §2/§10/§15:** The previous audit correctly identified the HA OS backup implementation as distinct from CoreBackupReaderWriter but was **too cautious about whether a Supervisor-to-Core hook path exists in source**. That path is now traced explicitly, without claiming live HA OS validation.

**SUPERVISOR_SOURCE**, pinned to [Supervisor commit 69848689](https://github.com/home-assistant/supervisor/tree/69848689a1e982ebe92d80e344fc086d8af667db):
1. [supervisor/backups/backup.py](https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py) store_homeassistant delegates to sys_homeassistant.backup.
2. [supervisor/homeassistant/module.py](https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py) backup calls **begin_backup** before archiving the HA config path, then **end_backup** in finally; begin/end send WebSocket command types **backup/start** and **backup/end** to Core.
3. **CORE_SOURCE**, pinned Core [backup/websocket.py](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py), defines Supervisor-only authenticated backup/start and backup/end commands, which await BackupManager.async_pre_backup_actions and async_post_backup_actions respectively. Core tests [test_websocket.py](https://github.com/home-assistant/core/blob/2026.11.0/tests/components/backup/test_websocket.py) cover both commands.
4. The same pinned Supervisor module's **HOMEASSISTANT_BACKUP_EXCLUDE** excludes *.db-shm, but excludes the HA Recorder DB/-wal only if the Recorder option is selected. It **does not** automatically exclude an independent PlayStation Hub SQLite file or its WAL. The archive uses atomic_contents_add to traverse the HA config folder; that function name does not mean a concurrent collection of unrelated files is an atomic database snapshot.

**Refined evidence boundary:** The platform backup notification path is **SOURCE_CONFIRMED** for these specified upstream versions. It is still **NOT_TESTED** whether the user's installed HA OS/Supervisor version executes the hooks when our future custom backup platform is registered and whether our proposed immutable snapshot/manifest will be included together and restored unambiguously. Final decisions on snapshot placement, live DB handling, backup orchestration and restore remain open.

**Test plan impact:** SH-BK02 is now a source-verified mechanism with a **BLOCKED_HA_OS execution test**, not a source-unknown feature. SH-BK04/05/06/07/09/10 remain critical. Freeze/thaw outside a normal backup is documented by the Supervisor API and needs separate coverage. The source chain makes the proposed snapshot design more credible but does not prove it correct.


## 18. Runtime data setup-order correction from official contributors documentation — 2026-11-06

The official [Config entries](https://contributors.home-assistant.io/core/integrations/config-entries/) and [runtime-data guidance](https://contributors.home-assistant.io/core/quality-scale/runtime-data/) explicitly assign the typed entry.runtime_data **before** awaiting async_forward_entry_setups, because forwarded platforms read it immediately. The first draft of §6 placed runtime_data after forwarding and incorrectly risked missing runtime state. §6 has now been corrected. Separately, monitor activation must not precede promotion of a PENDING data lease to ACTIVE if the monitor can submit observations. Prepared runtime can expose null/stale cached data to HA entities before observation begins. Add this order to synthetic setup and partial-failure tests; do not code until approved.


## 19. Global Home Assistant shutdown ordering — pinned Core 2026.11.0

**CORE_SOURCE:** [homeassistant/core.py at 2026.11.0](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py) defines **hass.async_add_shutdown_job** (~1104-1136), whose documented contract is that registered jobs run (and coroutine returns are awaited) **before** EVENT_HOMEASSISTANT_STOP. In async_stop (~1187-1325) the observed sequence is:

1. Run shutdown jobs under STOPPING_STAGE_SHUTDOWN_TIMEOUT=20 seconds (pinned implementation detail).
2. Move to stop stage; **cancel HA-owned background tasks**, fire EVENT_HOMEASSISTANT_STOP and await integrations under STOP_STAGE_SHUTDOWN_TIMEOUT=100 seconds.
3. Fire EVENT_HOMEASSISTANT_FINAL_WRITE and await tasks under FINAL_WRITE_STAGE_SHUTDOWN_TIMEOUT=60 seconds.
4. Fire EVENT_HOMEASSISTANT_CLOSE and continue terminal cleanup, with CLOSE_STAGE_SHUTDOWN_TIMEOUT=30 seconds.

**Crucial implication:** using only EVENT_HOMEASSISTANT_STOP to begin graceful per-entry monitor cancellation risks racing with Home Assistant's own background-task cancellation. An integration-global shutdown job can instead **begin controlled fencing earlier**, stop new probes, bound completion of accepted writes, close or classify pending query/snapshot leases and ask the shared manager to close before its entry-owned monitor background tasks are automatically cancelled. It must not assume the Core timeouts guarantee its own work finished; other shutdown jobs run concurrently and an uncooperative job can be timed out.

**PROJECT_PROPOSAL:** Register exactly one controller-owned shutdown job at the integration scope, not per console. Use state RUNNING -> STOPPING, generation fence, stop manual commands and browser queries, request all per-console monitors to stop cooperatively, bound writer draining/DB close, and record unresolved/unsaved coverage for the next startup. Make this handler idempotent against a concurrent Config Entry unload; no network probes or new DB admissions after the shutdown fence. Normal entry unload retains its separate ordered cleanup contract. A fallback final-write hook may only finish already admitted writes if supported and safe; do not initiate fresh work after the stop stage.

**TEST REQUIREMENTS:** SH-LC09 and SH-LC10 must assert pre-stop fencing and shutdown job once-only registration, plus forced timeout/kill with conservative restart gaps. Add a distinct synthetic case for a concurrent user unload while global STOPPING. All remain NOT_RUN. Exact global shutdown timing is source-verified only for Core 2026.11.0 and must be rechecked when the supported minimum changes.
