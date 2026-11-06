# SPEC-017 — Degraded capability matrix, backend action gates and SQLite worker terminal proof

**Review date:** 2026-11-06
**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_IMPLEMENTATION
**Source audit:** [Core 2026.11 and aiosqlite 0.21/0.22 worker comparisons](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md)
**Decision proposal:** [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md)
**Existing:** ADR-0011 ACCEPTED product architecture; ADR-0004/0008/0009/0010/0015/0016 technical details still proposed; SPEC-006/008/009/014/015/016.
**Pinned sources:** Core tag 2026.11.0; Python 3.14; aiosqlite v0.21.0, v0.22.0 and v0.22.1; SQLite official WAL.
**Git:** main documentation only; develop untouched.

> The test plan is not an implemented or passed suite. All operation permissions and worker protocols described below are internal candidate contracts and require maintainer approval/testing. No package selection or source code is authorized.

## 1. Objective and design constraints

Provide a deterministic, deny-by-default operation permission model for one process-global HubController with three kinds of Config Entries (HUB, PHYSICAL_CONSOLE, PSN_ACCOUNT). Health states must distinguish source identity/freshness, history provenance/commit state, worker closure and current HA user/automation authorization. A source-ready console does not imply a valid history writer, and a loaded Hub Config Entry does not imply automatic permission to wake a PS5.

All command entry paths (entity method, Home Assistant service/automation, WebSocket handler, scheduled coordinator and future public API) must call the same current server-side capability evaluator. Frontend entity availability or hidden buttons must not be the only permission gate.

## 2. Proposed invariants

| ID | Future requirement |
| --- | --- |
| CAP-I01 | HA native entry state is never interpreted as a blanket source/control/SQL capability. |
| CAP-I02 | Capability decisions combine process lifecycle, entry kind/state, source verification/freshness, ledger authority, worker/lease, user/automation permission and operation. |
| CAP-I03 | All operations default to DENY on unknown or contradictory evidence. |
| CAP-I04 | Hub/Archive entry owns no physical PlayStation or PSN action, probe or fake device. |
| CAP-I05 | One global RECOVERY_HOLD does not silently create a blank ledger or permit historian writes. |
| CAP-I06 | OBSERVATION_ONLY is distinct from DURABLE_WRITE and from CONTROL_POWER. |
| CAP-I07 | Verified fresh source-only LAN status during Hold is never backfilled into historical sessions; mark UNSAVED and gaps UNKNOWN. |
| CAP-I08 | Physical identity conflict denies wake/standby, Remote Play, stale attribution and binding to unrelated historical records. |
| CAP-I09 | PSN account auth/refresh is independently scoped and never imports credentials from archived history. |
| CAP-I10 | All physical-control operations are denied by conservative default during global RECOVERY_HOLD until explicit product approval. |
| CAP-I11 | Read-only archived snapshot access requires independent verified artifact, a bounded read lease and server authorization. |
| CAP-I12 | No use of corrupt/unverified live source for historical reports just because a UI can render it. |
| CAP-I13 | HA Entity.available and frontend visibility are presentation, not backend authorization guards. |
| CAP-I14 | WebSocket, entity service and scheduled operations apply the same generation and physical ownership fence. |
| CAP-I15 | Loss of history writer does not manufacture OFF or extend AWAKE/playtime over unobserved intervals. |
| CAP-I16 | Global shutdown or FAILED_UNSAFE_TO_REOPEN immediately denies new mutation admission. |
| CAP-I17 | Every queued/running SQL job is recorded independently of its awaiting asyncio Future. |
| CAP-I18 | Cancelling an asyncio Future does not imply that the worker's SQL function was cancelled/removed from its queue. |
| CAP-I19 | Native SQLite interrupt does not prove connection/thread closure or the final state of a COMMIT. |
| CAP-I20 | Selected worker has a positive, reviewed, testable terminal/close contract, with no reliance on unsupported private attributes. |
| CAP-I21 | All connection kinds, including readers, snapshots, checkpoints and exports, must terminate before destructive generation switch. |
| CAP-I22 | No generation pointer change while any old worker could still execute SQL. |
| CAP-I23 | On unprovable worker termination, preserve original DB and SQLite sidecars and enter FAILED_UNSAFE_TO_REOPEN; never claim CLEAN_STOP. |
| CAP-I24 | Aiosqlite 0.21 Thread-inheritance design and 0.22.x private-thread model are tested/assessed separately. |
| CAP-I25 | Aiosqlite 0.22.1 queued close/stop Future is not automatically equated to a public Thread.join guarantee. |
| CAP-I26 | stdlib ThreadPoolExecutor shutdown(wait=True) must be performed without blocking the HA event loop; a hung running job requires fail-safe status. |
| CAP-I27 | Old-generation COMMIT acknowledgements can be uncertain after cancellation; stable observation receipts prevent duplicate history. |
| CAP-I28 | A Hub-only recovery UI remains independently accessible when data plane is fenced (subject to enabled entry and control-plane health). |
| CAP-I29 | Repairs/diagnostics respect global ledger ownership, not an arbitrary removable console entry, and redact sensitive history/credentials. |
| CAP-I30 | All adopted policy decisions must be pinned to concrete library/HA versions and validated on supported installations. |

## 3. Decision precedence — candidate backend evaluator

1. Confirm integration is RUNNING, backend service is initialized, requested operation is version-supported, and HA caller/service authorization is valid. During controlled shutdown, only minimal read-only diagnostics may remain if safe.
2. Resolve specific entry kind and state; HUB cannot accept a physical device command, and disabled/unloaded console cannot be commanded via stale entity ID.
3. For a physical action, validate current canonical hardware identity, entry generation, freshness, control transport and permissions. Any identity conflict denies action even if frontend says available.
4. For historical write, additionally require approved live ledger, current writer generation, active source lease, per-source durable cursor and queue capacity. A delayed callback from the previous generation is rejected.
5. For history read, require a known validated ledger or immutable snapshot, ACL and bounded reader lease. Corrupt or unverified live files are never queried as authoritative data.
6. For admin recovery, check current HA administrator rights, exclusive RecoveryManager state, preview expiry/digest/revision and old-worker terminal proof before promotion.
7. For PSN token refresh, require account-scoped valid authorization and independently healthy credential store; shared history never grants authentication privileges.
8. Emit a structured denial reason and sanitized diagnostics; no giant logs or raw token/history leakage.

The evaluator must not perform network or SQLite I/O while holding the short global lifecycle mutex. Validate generation again at admission/execution boundary to close time-of-check/time-of-use races.

## 4. Proposed capability summary

**HUB** — Normal: panel, global status, authorized archive reports, repairs, admin recovery. Hold: panel/repairs and candidate inspection; separately verified snapshot read-only. Never source/PSN probe or wake.

**PHYSICAL_CONSOLE** — Normal: verified fresh state, bounded autonomous monitoring, permitted control and durable ingestion with current source+ledger lease. Hold: source-only ephemeral observations CONDITIONAL (policy not yet accepted), no history writes, power/Remote Play denied by conservative default. Identity conflict: no attributed current state, hardware command or historical write. Offline: cached stale is labelled, cannot claim live current state.

**PSN_ACCOUNT** — Normal: authenticated per-account read/refresh, permitted account-derived evidence if ledger ready. Hold: account-only reads and refresh CONDITIONAL if credential store/owner independently valid and no persistence; no account-derived historical ingestion. Account identity conflict/auth failure: deny refresh/attribution and require reauth.

**GLOBAL** — FENCING/FAILED_UNSAFE_TO_REOPEN: no new SQL mutation, backup of unsafe live DB, SQLite generation change or privileged console action; minimal recovery UI/diagnostics may remain if control plane healthy. Verified read-only snapshot may be read via a wholly separate safe reader only if its lease is independent and can close positively.

See source audit §4 for complete operation-by-mode table. These are proposed internal contracts, not HA's built-in permission system.

## 5. SQLite worker close proof: candidate requirements

Future worker adapter must expose distinct states:
- ACCEPTING; FENCING; DRAINING; EXECUTING; CLOSE_REQUESTED; CONNECTION_CLOSE_CONFIRMED; WORKER_STOP_REQUESTED; WORKER_TERMINAL_CONFIRMED; CLOSED_VERIFIED; FAILED_UNSAFE_TO_REOPEN.
- Job receipts: QUEUED, EXECUTING, COMMIT_ACK, COMMIT_UNCERTAIN, CANCELLED_BEFORE_ADMISSION, TERMINAL_FAILURE.
- A monotonically increasing manager generation and unique accepted-job IDs.

The stop handshake is FENCE -> ACCOUNT -> DRAIN -> optional INTERRUPT -> CLOSE all connections in their owning threads -> VERIFY worker terminal -> zero in-flight/leases -> CLOSED_VERIFIED -> only then ADR-0015 generation pointer cutover.

**W1 stdlib sqlite3 + dedicated executor**: Futures/cancel_futures cannot cancel running functions. A correct worker ownership layer can use a dedicated executor, bounded submissions, connection closure in owner thread and Executor.shutdown(wait=True) outside the HA event loop; a hung function still blocks and must leave cutover denied.

**W2 aiosqlite candidate**: 0.21 Connection inherits threading.Thread; 0.22.0 and 0.22.1 Connection owns a private Thread. In 0.22.1 close queues sqlite3.close then stop() and awaits stop Future. The worker schedules completion callback BEFORE its own sentinel break. That Future may not be literally a public join guarantee. Need an approved supported terminal contract or version-aware adapter with tests, not unsupported private thread manipulation. The library version is NOT selected.

Every reader, backup source, immutable snapshot reader and export connection is tracked. Cancellation/timeout does not reduce this count to zero by assumption. Do not use SQLite hot WAL/journal deletion as a repair shortcut.

## 6. Test catalogue — 80 cases, all NOT_RUN

### 6.1 Capability combinations across entry kinds — 20 NOT_RUN

| ID | Synthetic scenario | Expected result |
| --- | --- | --- |
| CAP-MODE01 | Hub-only normal verified archive | One panel, authorized history, no PS5/PSN probe |
| CAP-MODE02 | Hub-only corrupt live DB | RECOVERY_HOLD, repair UI, no blank ledger |
| CAP-MODE03 | Console AWAKE with healthy history | Authorized current observation and durable lease |
| CAP-MODE04 | Console AWAKE during global HOLD | Optional ephemeral UNSAVED, no SQL historian |
| CAP-MODE05 | Console stale/offline with healthy history | Old status labelled stale, not currently AWAKE |
| CAP-MODE06 | Console physical identity conflict | Deny physical controls and attribution |
| CAP-MODE07 | Console old runtime after reload | Reject stale LAN callback and writer generation |
| CAP-MODE08 | Hub disabled, only historical files remain | No false guarantee sidebar available next reboot |
| CAP-MODE09 | PSN authenticated and physical console offline | Scoped PSN read independent of LAN |
| CAP-MODE10 | PSN authentication failure with Hub healthy | Reauth only account, history control stays |
| CAP-MODE11 | PSN identity conflict during HOLD | No token refresh, attribution or relink |
| CAP-MODE12 | Verified read-only immutable snapshot while live corrupt | Bounded archived report without unsafe live DB access |
| CAP-MODE13 | Raw unverified tar DB present | No archive report trusted from it |
| CAP-MODE14 | Manager FENCING while A and B probes arrive | Reject new writes, no unbounded buffer |
| CAP-MODE15 | FAILED_UNSAFE_TO_REOPEN while source fresh | Live status optional only, no writer/power by default |
| CAP-MODE16 | Global shutdown during account refresh | No new privileged activity admitted |
| CAP-MODE17 | Identity verified but storage hold, manual power | Denied by conservative default pending approval |
| CAP-MODE18 | Restore resolved, gate reopened | Fresh evidence starts new segment; outage UNKNOWN |
| CAP-MODE19 | Hold begins mid-play session | No continued historical playtime without evidence |
| CAP-MODE20 | Two consoles differ in health, shared DB valid | One's offline/failed identity does not revoke other's safe scope |

### 6.2 Backend action entry paths and stale clients — 20 NOT_RUN

| ID | Synthetic scenario | Expected result |
| --- | --- | --- |
| CAP-ACT01 | UI hides power control; HA service calls directly | Server capability denies operation under HOLD |
| CAP-ACT02 | Entity available=False but direct service invokes method | Identity and global guard still enforce |
| CAP-ACT03 | WebSocket power request during IDENTITY_CONFLICT | Denied server-side |
| CAP-ACT04 | HA automation queued before global gate closes | Revalidate at execution; no late control |
| CAP-ACT05 | Old frontend sends command with stale generation | DENY, no source mutation |
| CAP-ACT06 | Unauthorized user tries recovery preview | Deny, no candidate enumeration |
| CAP-ACT07 | Non-admin invokes export/restore/purge | Deny with no side effect |
| CAP-ACT08 | Admin preview changes before confirmation | Stale revision/digest rejected |
| CAP-ACT09 | Hub entry receives console wake request | Reject wrong entry kind |
| CAP-ACT10 | PSN token refresh requested using history snapshot account ID | Not accepted as authorization |
| CAP-ACT11 | Two admins try competing restores | One exclusive job or explicit conflict |
| CAP-ACT12 | Browser disconnect during recovery | Backend job unchanged, subscription removed |
| CAP-ACT13 | Current status entity cached as AWAKE after source offline | Mark stale, no action authorization |
| CAP-ACT14 | Switch entity registers service but user action bypasses UI | Guard protects same backend operation |
| CAP-ACT15 | Scoped read of verified snapshot via non-admin | Denied until explicit archive ACL approved |
| CAP-ACT16 | Backpressure full while source valid | No unbounded historical queue, UNSAVED gap |
| CAP-ACT17 | Service call reaches unloaded Config Entry | Deny, no stale entity invocation |
| CAP-ACT18 | Restore job pointer changed between two calls | Fresh global revision checked |
| CAP-ACT19 | User permission revoked mid-operation | No new sensitive action; admitted atomic job safely settles |
| CAP-ACT20 | Global Repair issue after console removal | Remains until actual shared DB health verified |

### 6.3 Worker version, queued cancellation and positive closure — 20 NOT_RUN

| ID | Future fault case | Required evidence |
| --- | --- | --- |
| CAP-WORK01 | aiosqlite 0.21 Connection inheritance | Version-specific API behavior recorded |
| CAP-WORK02 | aiosqlite 0.22.0 private worker thread | Old public Thread.join assumption rejected |
| CAP-WORK03 | aiosqlite 0.22.1 stop() and close() | Supported close receipt tested |
| CAP-WORK04 | aiosqlite Future cancelled after SQL queued | SQL may still execute; receipt correct |
| CAP-WORK05 | aiosqlite queued close behind long write | Close does not falsely report terminal early |
| CAP-WORK06 | Stop Future delivered before thread loop returns | Terminal evidence stronger than callback required |
| CAP-WORK07 | aiosqlite connection forgotten without close | ResourceWarning/fallback not relied on |
| CAP-WORK08 | stdlib running Future.cancel() | SQL continues/settles; no false CLOSED |
| CAP-WORK09 | Executor.shutdown(wait=False) | Rejected as terminal proof |
| CAP-WORK10 | Executor.shutdown(wait=True) via worker-safe off-loop call | Thread completion positively observed |
| CAP-WORK11 | ThreadPoolExecutor cancellation of queued but not running SQL | Correct queue accounting |
| CAP-WORK12 | sqlite3.interrupt aborts long SELECT | OperationalError, connection still separately closed |
| CAP-WORK13 | sqlite3.interrupt during COMMIT ambiguity | Receipt reconciliation, no blind rollback |
| CAP-WORK14 | Reader holds WAL while writer stopped | No pointer switch until all readers closed |
| CAP-WORK15 | Snapshot backup connection still open | No cutover, no sidecar removal |
| CAP-WORK16 | Queue length zero but active SQL function running | In-flight guard prevents false terminal |
| CAP-WORK17 | Close timeout leaves worker unknown | FAILED_UNSAFE_TO_REOPEN; no new writer |
| CAP-WORK18 | Two shutdown requests race | Idempotent state, no double close or reopened worker |
| CAP-WORK19 | Late old-generation SQL completion after caller cancelled | Old result fenced, no new-generation corruption |
| CAP-WORK20 | Process death mid worker call | Next startup SQLite-native recovery and receipt validation |

### 6.4 HA OS, security, history and migration regressions — 20 NOT_RUN

| ID | Future scenario | Expected result |
| --- | --- | --- |
| CAP-OS01 | Hub-only startup in HOLD | LOADED control plane, admin UI and Repair, no writer |
| CAP-OS02 | 100 Hub/console entry reloads | One controller/panel, no leaked worker |
| CAP-OS03 | Core early shutdown job overlaps recovery | Fence/close protocol, no false success |
| CAP-OS04 | Core unload fails while worker still live | Tracked FAILED_UNLOAD owner |
| CAP-OS05 | Linked SQLite runtime has WAL-reset bug | Feature/version gate, no unsafe WAL usage |
| CAP-OS06 | HA OS filesystem has network mount | WAL locality check, no unsupported live writer |
| CAP-OS07 | App schema migration incompatible with restored ledger | Recovery hold, no downgrade |
| CAP-OS08 | Full old HA backup restores config/pointer/journal | Missing later history UNKNOWN |
| CAP-OS09 | Legacy saved snapshot only, no current live DB | Admin recovery, no automatic destructive overwrite |
| CAP-OS10 | Config Entry identity restored to different hardware | No control or historical graft |
| CAP-OS11 | Admin Repairs contains secret/token | Disallowed diagnostics/translation content |
| CAP-OS12 | Sensitive snapshot exposed by frontend static route | Rejected, no raw download |
| CAP-OS13 | One account unlinked while PSN refresh queued | Scope revoked, no late refresh claim |
| CAP-OS14 | Source-only observation caches fill under hold | Bounded eviction, zero historical replay |
| CAP-OS15 | CLI/third-party direct service call during hold | Same permission guard applies |
| CAP-OS16 | HA user privilege changed while WebSocket connected | Backend revalidation before action |
| CAP-OS17 | Container vs HA OS worker thread lifecycle | Supported installs separately tested |
| CAP-OS18 | Restart after failed worker closure | No stale generation cursor or false saved time |
| CAP-OS19 | Real-world standby/awake and recovery time gap | No fabricated duration or incorrect OFF |
| CAP-OS20 | 3-year synthetic history after repeated recovery | Bounded resource use, exact durable receipts |

**80 newly defined test IDs** (20 MODE + 20 ACT + 20 WORK + 20 OS), all NOT_RUN. These overlap earlier SPEC-008 through SPEC-016 deliberately and do not add executable test files.

## 7. Sign-off gates — all 20 OPEN

| Gate | Required proof | State |
| --- | --- | --- |
| CAP-G01 | Multidimensional operation guard and deny-precedence approved | PROPOSED |
| CAP-G02 | Hub/console/PSN kind-specific matrix approved | PROPOSED |
| CAP-G03 | Source-only UNSAVED vs durable history semantics accepted | OPEN_PRODUCT_DECISION |
| CAP-G04 | Power/Remote Play controls during HOLD policy accepted | OPEN_PRODUCT_DECISION |
| CAP-G05 | PSN account read/refresh during history hold accepted | OPEN_PRODUCT_DECISION |
| CAP-G06 | Verified read-only snapshot reports under hold proven | NOT_RUN |
| CAP-G07 | Entity availability, HA services and WS enforce same backend guard | NOT_RUN |
| CAP-G08 | Canonical physical/account identity and generation fencing | BLOCKED_HARDWARE |
| CAP-G09 | Zero false historical backfill across storage hold | NOT_RUN |
| CAP-G10 | Exact aiosqlite version change and package compatibility reviewed | SOURCE_REVIEWED, NOT_SELECTED |
| CAP-G11 | v0.22.1 close/stop signal vs worker termination verified | NOT_RUN |
| CAP-G12 | Stdlib executor closure and off-loop shutdown verified | NOT_RUN |
| CAP-G13 | All queued/running/commit-uncertain SQL jobs tracked | NOT_RUN |
| CAP-G14 | All source/reader/backup/export SQLite connections closed before cutover | NOT_RUN |
| CAP-G15 | Unknown worker terminal causes FAILED_UNSAFE_TO_REOPEN | NOT_RUN |
| CAP-G16 | HA shutdown/unload and recovery overlap safe | NOT_RUN |
| CAP-G17 | Privacy-safe snapshots, Repairs and admin ACL | NOT_RUN |
| CAP-G18 | Multi-console concurrency and HA OS/Container regression | BLOCKED_HA_OS |
| CAP-G19 | Linked SQLite/WAL fix and local filesystem tests | BLOCKED_HA_OS |
| CAP-G20 | Maintainer sign-off and positive release testing | OPEN |

## 8. No-code release boundary and traceability

- ADR-0017 describes candidate choices, not accepted operational policy.
- ADR-0011's Hub/Archive product architecture remains ACCEPTED.
- Neither sqlite3 dedicated executor nor aiosqlite v0.22.1 is selected.
- No SQL code, runtime tests, API handlers, service registrations, front-end changes, new branch or Home Assistant host mutation.
- Future implementation requires approved version pins, complete fault results and permission tests; no claim of automatic lossless restore.

Primary references:
- [Source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md)
- [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md)
- [SPEC-016](SPEC-016-recovery-hold-boot-order-and-worker-termination.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/service.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.1/aiosqlite/core.py
- https://aiosqlite.omnilib.dev/en/stable/changelog.html

**Outcome:** 80 NOT_RUN, 20 OPEN, no implementation or tests.
