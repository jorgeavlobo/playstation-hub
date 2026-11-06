# ADR-0017 — Degraded operation capabilities and positive SQLite worker closure

**Status:** PROPOSED — capability policy, worker dependency and close-proof NOT APPROVED/NOT_TESTED
**Date:** 2026-11-06
**Scope:** One backend capability model across Hub, physical consoles and PSN accounts; defensible SQLite connection/worker termination before ledger cutover.
**Sources:** [Official/pinned source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md); [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md).
**Prior decisions:** ADR-0011 ACCEPTED product architecture; ADR-0004/0008/0009/0010/0015/0016 technical proposals.
**Version pins:** HA Core 2026.11.0; Python 3.14 reference; aiosqlite v0.21.0, v0.22.0 and v0.22.1.
**Branch:** main documentation only; develop unchanged.

> This record is a technical proposal, not an approved user-visible degraded-operation policy or implementation. The maintainer's authorization to research/document does not select an SQLite library, approve wake/standby during recovery or close any runtime test gate.

## 1. Problem

A Hub Config Entry can be LOADED while historical storage is in RECOVERY_HOLD. A physical console can report AWAKE while the historian cannot write. A PSN account may remain authenticated when the console is offline. If all operations are controlled by one Boolean (such as entry loaded or Entity.available), a stale entity, HA automation, service or WebSocket call can bypass the intended historical/identity fence.

A worker may also keep executing SQL after its asyncio caller has been cancelled. The active-generation cutover in ADR-0015 is unsafe unless the application has proof that all connections, queued operations and workers associated with the old generation can no longer execute.

## 2. Official and pinned evidence

- Home Assistant config_entries.py distinguishes native entry states from application-specific data health and has per-entry locks.
- Core helpers/entity.py Entity.available is a presentation/availability property. Entity services and automations have independent dispatch routes; internal action authorization must be checked at the backend service or entity method.
- WebSocket require_admin and entity service admin_only provide caller ACL primitives, but do not by themselves validate canonical PS5 identity, a durable history generation or a current session permission.
- Python ThreadPoolExecutor running functions cannot be cancelled by Future.cancel or cancel_futures=True; shutdown(wait=False) does not prove worker join.
- sqlite3.Connection.interrupt may abort an executing statement, but does not establish the final COMMIT result or close the connection/thread.
- aiosqlite v0.21.0 Connection inherits Thread; v0.22.0/0.22.1 contains a private Thread instead. v0.22.1 adds stop() and an unclosed-connection warning; close() queues SQLite close and stop. A queued SQL function may run after its awaiting Future was cancelled, and stop Future completion is not explicitly a public Thread.join contract.

## 3. Preferred operation model — PROPOSED

Each backend action checks process state, entry kind/state, physical or PSN owner, source freshness, historical ledger provenance, worker/lease state, user/service ACL and operation category. Unknown or contradictory evidence defaults to DENY. The same rule must apply to a Home Assistant automation, entity command, scheduled task or WebSocket call. A hidden button or unavailable entity is not a security gate.

### Proposed capability policy

**Normal, validated**: Hub can serve panel and authenticated archive, console can publish fresh status and (if fully authorized) control power and durably ingest history, and an account can read/refresh PSN within its own permissions. Historical write additionally requires current manager generation and approved durable writer lease.

**RECOVERY_HOLD**: Hub retains administrative Repairs, bounded read-only candidate inspection and its single sidebar. No historical writer admission or implicit empty DB creation. A console may eventually show verified source-only ephemeral status marked UNSAVED, subject to explicit maintainer approval, never backfilling usage. **Conservative default:** disable power and Remote Play controls during the global Hold, even with a verified LAN owner, until separately approved risk policy. Account-only PSN status/token refresh is likewise conditional on independent credential store validity, without historical writes.

**IDENTITY_CONFLICT**: no physical commands, historical attribution or automatic PSN credential binding. Archived read-only views only if independently verified and authorized; never use IP or a display nickname as physical authority.

**FAILED_UNSAFE_TO_REOPEN / SHUTTING_DOWN**: reject new SQL mutation and pointer promotion; avoid physically privileged commands by default; preserve old live DB and hot journal/WAL. A safe global recovery/diagnostic interface may remain available while the control plane runs.

**Verified immutable snapshot**: allow a bounded, independently leased read-only report if identity, schema and ACL are verified; do not re-open the corrupt live SQLite source through the same unsafe worker.

These are candidate product choices, not current integration behavior.

## 4. Worker candidates remain unselected

| Model | Main advantage | Proof needed | Status |
| --- | --- | --- | --- |
| W1 sqlite3 + dedicated serialized executor | No new dependency; public Executor.shutdown(wait=True) semantics | Connection closed in owning thread, bounded work, real terminal wait outside event loop; never assume hung running SQL cancelled | RESEARCH |
| W2 aiosqlite v0.22.1 | Async API, per-connection queue, improved stop/close behavior | Cancelled waiter vs queued work; supported positive worker-terminal contract; package/HA compatibility | RESEARCH |
| W2 legacy v0.21.0 | Previously examined queue/thread behavior | Thread inheritance changed in v0.22; don't carry public join assumptions forward | HISTORICAL |
| W3 separate subprocess | More isolation for uninterruptible thread | IPC, security, packaging, HA OS/Container lifecycle and maintenance | DEFERRED |

No package has been selected, installed or benchmarked on the user's HA OS.

## 5. Proposed stop proof and generation-change protocol

1. FENCE current history generation, rejecting new work at every handler including delayed source callbacks and HA services.
2. ACCOUNT for admitted jobs (QUEUED, EXECUTING, COMMIT_ACK, COMMIT_UNCERTAIN, terminal), independent of whether their asyncio Future is cancelled.
3. DRAIN with bounded queue/reader/backup/export leases and in-flight counters; queue length zero alone is not enough.
4. Optional INTERRUPT requests cancellation of a long query, but does not mark transaction rollback, connection close or worker exit.
5. CLOSE all SQLite connections on their proper owner thread, including readers, snapshot and WAL checkpoint connections. Confirm return/error/terminal receipt.
6. TERMINAL: obtain a supported, positively testable worker termination acknowledgement. With stdlib, shutdown(wait=True) must not block the event loop. With aiosqlite v0.22.1, completion of close/stop queued Future is important but not a documented public Thread.join guarantee; a version-stable supported adapter or a different worker architecture may be required.
7. CLOSED_VERIFIED only after no old connection can run SQL and no related generation lease or operation is outstanding. Only then may ADR-0015 atomically select a new active pointer.
8. On uncertain termination, retain FAILED_UNSAFE_TO_REOPEN, do not open a second writer or rename/delete a hot SQLite source, keep Hub recovery interface when possible and reconcile on fresh process startup.
9. COMMIT uncertain after cancellation remains uncertain; stable source observation IDs and database receipts prevent duplicate gaming duration on restart.

This is not an assertion of unconditional power-loss durability; real HA OS filesystem and SQLite tests remain mandatory.

## 6. Threat, UX and identity rules

- Availability/supported_features are not user permission or canonical identity checks; every power/Remote Play action revalidates physical owner and manager policy at execution.
- Historical state has separate latest observed source, committed-as-of cursor, UNSAVED evidence and UNKNOWN coverage; no inferred OFF/ON/playtime during recovery.
- A loaded Hub with valid control plane can show RECOVERY_HOLD while historian is unavailable; the Hub entry must not create fake PS5 entities or network poll.
- Admin recovery/export/purge remains backend ACL protected and uses a preview/confirm source revision. Browser disconnect does not cancel a durably accepted restore operation.
- A global Repair issue is independent of a removable PS5 entry; diagnostics and logs expose no Sony credentials or raw game/player history.
- Credentials/account refresh are separately protected by PSN account scope; history restore never reauthorizes a token.
- Shutdown of the Home Assistant process does not justify claiming all accepted observations were persisted.

## 7. Approval and next research

**Accepted:** ADR-0011 Hub/Archive, one panel/controller, independent entries and historical retention.
**Still proposed:** matrix for power controls during Hold, source-only UNSAVED LAN observations, PSN account operations under Hold, snapshot read in unsafe-worker state, final SQLite worker library and positive exit contract.
**No runtime proof:** 80 SPEC-017 cases NOT_RUN, 20 OPEN gates, no HA OS/Container test, no linked SQLite C version check.
**Next recommended investigation:** define an authoritative first-boot/new-ledger versus missing/corrupt-ledger classifier with safe filesystem operations, and a versioned worker adapter/protocol suitable for later exhaustive fault injection. Technical approval only after evidence; no code permission.

## 8. Sources

- [Source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md)
- [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md)
- [ADR-0016](ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/service.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://docs.python.org/3.14/library/concurrent.futures.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.0/aiosqlite/core.py
- https://github.com/omnilib/aiosqlite/blob/v0.22.1/aiosqlite/core.py
- https://aiosqlite.omnilib.dev/en/stable/changelog.html

**Outcome:** Proposed technical design; no executable code, tests or real connection closed.


## 9. Missing-history classifier and separate first-run creation permission — 2026-11-06

[Official first-boot audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018](ADR-0018-first-boot-consent-and-ledger-provisioning.md) and [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) add a distinct administrator CREATE_NEW_HISTORY permission, separate from hub Config Entry creation, history recovery, physical control and SQL DURABLE_WRITE. A Hub Config Entry may be HA LOADED but internally INITIALIZATION_REQUIRED, with no provisioned ledger/writer; source-only PS5 observations are optional and cannot create the SQLite file. All existing-ledger opening must use non-creating SQLite modes. Presence of old ledger UUID, pointer, stage, journal, legacy DB or snapshot disallows silently starting an empty new history; permission errors and uncertain filesystem state are STORAGE_INACCESSIBLE, not CANDIDATE_FRESH.

The operation is explicitly confirmed, generation/ACL-revalidated and idempotent under one provisioning lease; it stages a new ledger with an exclusive directory and durable CREATE_INTENT before selecting the new active pointer. Two Config Flows/tabs cannot create parallel genesis ledgers. No implementation or technical acceptance implied; ADR-0017 remains PROPOSED.
