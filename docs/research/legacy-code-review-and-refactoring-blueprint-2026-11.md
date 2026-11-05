# Legacy code review and future refactoring blueprint — no implementation

**Date:** 2026-11-05  
**Status:** Source-based review and architectural improvement plan; not an implementation, code patch or test result  
**Source branch:** `develop` (read only)  
**Documentation destination:** `main`  
**Scope:** Existing PS5 Monitoring backend, SQLite session tracking, historical reporting, application lifecycle and configuration; cross-referenced to current PlayStation Hub architecture  
**Related:** WP-00, WP-00A, Protocols 01–10, ADR-0004–0010, SPEC-001–007

> This review is deliberately restricted to **reading and analyzing existing code**. Do not modify `develop`, create source modules on `main`, reintroduce MQTT or start WP-01. “Code improvements” below are **future implementation recommendations**, subject to ADR review, synthetic tests, pinned Home Assistant Core compatibility and explicit authorization.

## 1. Executive findings

The legacy backend contains valuable patterns: a dedicated session tracker, explicit SQLite transaction boundaries, durable observation checkpoints, idempotent recovery and calendar-aware reporting. It is **not** a suitable direct basis for the new HACS integration because its application lifecycle, configuration and identity model are tied to a standalone Supervisor App, MQTT and one configured player.

**Priority findings:**

| ID | Priority | Source observation | Recommendation |
| --- | --- | --- | --- |
| LEG-001 | P0 design | Main application creates one configured player, one tracker and MQTT client | Separate per-console physical state and account/player associations |
| LEG-002 | P0 portability | App reads Supervisor options from `/data/options.json`, requires SQLite path under `/data` | Replace with HA Config Entries and approved HA configuration storage |
| LEG-003 | P0 async | `sqlite3` work uses a process-shared synchronous connection and `threading.RLock` | Dedicated nonblocking repository worker/actor and bounded async APIs |
| LEG-004 | P0 accounting | Runtime sets `max_gap_seconds=30.0` | Make continuity/freshness separate evidence-based policies |
| LEG-005 | P0 identity | One `monitoring_state` row and sessions without independent physical-console ownership | Canonical console keys, per-source observations and multi-console schema |
| LEG-006 | P1 lifecycle | Exception in stop sequence can short-circuit later MQTT/DB cleanup | Explicit best-effort staged cleanup with error aggregation and no leaked resources |
| LEG-007 | P1 reporting | Statistics code uses global `ZoneInfo("Europe/Lisbon")` | Inject Home Assistant/user IANA timezone and test DST |
| LEG-008 | P1 scale | `Database.get_sessions` executes an unpaginated `fetchall()` | Bounded time-window/keyset query APIs with indexes and cancellation |
| LEG-009 | P1 history | Event/session checkpoint transactions are good but tied to a single configured player | Preserve atomicity/idempotency while expanding domain and provenance |
| LEG-010 | P1 resilience | Source has extensive defensive exception handling and recovery; no HA lifecycle integration | Rework as per-entry coordinators, generation fencing and shared storage ownership |
| LEG-011 | P1 source trust | Legacy tracker assumes upstream MQTT retained messages already filtered | Native LAN adapter must validate origin, generation and observation evidence itself |
| LEG-012 | P2 code quality | `config.py` imports `os` before its documentation string | Improve module conventions when code is eventually replaced; do not alter legacy now |

**Review confidence:** Source-observed or derived from explicit control flow; none of these constitutes a measured bug, proven runtime failure or executed test in PlayStation Hub.

## 2. Code evidence register (exact branch and paths)

| Reference | File and source section | Evidence |
| --- | --- | --- |
| SRC-L01 | [`develop/backend/app/main.py` lines 74–140](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/main.py#L74-L140) | Single `SessionTracker`, one `player_name`, MQTT and live worker initialized |
| SRC-L02 | [`develop/backend/app/main.py` lines 303–391](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/main.py#L303-L391) | Ordered shutdown stages and early re-raises |
| SRC-L03 | [`develop/backend/app/session_tracker.py` lines 49–180](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/session_tracker.py#L49-L180) | In-memory last-observation check, DB atomic delegation, recovery |
| SRC-L04 | [`develop/backend/app/database.py` lines 49–104](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py#L49-L104) | SQLite connection, WAL, RLock, immediate transactions |
| SRC-L05 | [`develop/backend/app/database.py` lines 609–920](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py#L609-L920) | Transactional observation handling, checkpoint upsert, session/event updates |
| SRC-L06 | [`develop/backend/app/database.py` lines 922–976](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py#L922-L976) | Idempotent recovery closes at last checkpoint |
| SRC-L07 | [`develop/backend/app/database.py` lines 544–587](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py#L544-L587) | Unbounded overlapping-session query using fetchall |
| SRC-L08 | [`develop/backend/app/usage_statistics.py` lines 18–195](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/usage_statistics.py#L18-L195) | UTC/Europe-Lisbon conversion, half-open intervals |
| SRC-L09 | [`develop/backend/app/config.py` lines 20–130](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/config.py#L20-L130) | Supervisor options, `/data` path and single player |
| SRC-L10 | [`develop/backend/app/main.py` lines 255–302](https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/main.py#L255-L302) | Standalone signal handlers and loop |

The review does not claim exhaustive coverage of every frontend component, test file or transitive library. Follow-up audits should expand that scope separately and record exact lines.

## 3. Existing patterns worth preserving

### 3.1 Atomic observation transitions

The legacy `apply_observation` updates sessions, checkpoints, normalized monitoring state and change events inside one explicit transaction. This supports a robust **all-or-nothing** state ledger. The new implementation should retain a transaction boundary tying accepted evidence to durable checkpoints and session revisions, even if the physical schema and repository API change.

### 3.2 Checkpoint-based crash recovery

`recover_open_sessions` closes an open session at its last persisted checkpoint, or at session start if no checkpoint exists. It is atomic and repeatable. This conservatively avoids attributing unobserved time after a crash. Preserve that principle, adding independent console/owner keys, unknown gaps and restored-backup high-water marks.

### 3.3 Half-open UTC intervals and DST-aware reports

The existing report service intersects sessions with `[start,end)` windows and maps UTC to Europe/Lisbon with a real IANA timezone. This is a correct *type of design approach* for DST handling. Keep half-open UTC intervals and local calendar aggregation; replace the global hardcoded timezone with a configured source.

### 3.4 Source-change deduplication

Repeated heartbeat observations update checkpoints while distinct changes create events. Preserve event deduplication and idempotent observation IDs, but distinguish periodic accepted evidence, offline gaps and externally reported PSN activity instead of treating one MQTT payload as the unified fact source.

## 4. Incompatibilities with the target integration

| Legacy capability | New architecture requirement | Action |
| --- | --- | --- |
| Supervisor App startup, PID/signals, own forever-loop | HA Core manages config entries, async tasks and shutdown | Replace, not port |
| MQTT subscription to PS5 MQTT | Native PlayStation LAN transport | Delete dependency from new architecture |
| One `player_name` globally | Independent multi-console, optional multi-account attribution | Introduce canonical identity and association model |
| `/data/options.json` and `/data` SQLite | HA configuration and protected storage paths | Redesign storage ownership |
| Global threading locks | HA asyncio/event loop and controlled storage worker | Review thread safety and cancellation |
| One `monitoring_state.id=1` | Fact-specific latest state by console/account/source | Versioned per-owner snapshots |
| Local timezone fixed to Lisbon | HA/user IANA timezone | Inject locale/timezone reporting context |
| SQLite `fetchall()` over history | Bounded/paged WebSocket queries | Add index + keyset query contract |
| MQTT retained-message guard delegated upstream | Native LAN source verification | Validate response, generation and target identity |
| Separate app monitoring signal | Native HA entity availability/freshness and repairs | Implement later under ADR-0009 |

## 5. Session accounting review: the 30-second policy

`main.py` passes `max_gap_seconds=30.0` to `SessionTracker`, while `SessionTracker.__init__` and `Database.apply_observation` define broader defaults of 90 seconds. Therefore the **effective configured runtime continuity threshold is 30 seconds** in the reviewed startup path. It is not an approved default for the new product.

Why this matters:
1. A 31-second valid observation gap closes previously open sessions at their prior checkpoint in the legacy algorithm, even if the console is still awake at the new sample.
2. Source freshness TTL, polling frequency, command confirmation deadline and durable session continuity threshold are **four independent decisions**.
3. For multi-console systems, failures and timing must be tracked per console; one timeout cannot close unrelated sessions.
4. A transition observed between two polls has an uncertain physical boundary; reports must not overstate exact continuous duration.
5. The original code used MQTT messages, not directed UDP probes; the reliable cadence differs and must be measured.

**Improvement blueprint:** Define a versioned `ContinuityPolicy` with per-source evidence requirements and explicit max gap, plus a separate `FreshnessPolicy`. Approval depends on synthetic timelines and real measurement, not the legacy numerical defaults.

## 6. Persistence and query modernization

Retain the transactional approach but do not reuse the legacy schema version as the new schema identity. ADR-0008's SQLite candidate remains unapproved until backup/restore tests. A future repository should have:
- A single controlled writer with bounded queue and graceful fail/stop semantics, or another proven nonblocking ownership strategy.
- Atomic `commit_observation` with unique observation ID, source/run generation, console key, segment/checkpoint state and committed high-water mark.
- Bounded indexed queries with mandatory filtering and cursor pagination, avoiding unbounded `fetchall()` over multi-year history.
- Explicit UTC timestamp storage and separate report-time timezone conversion.
- Per-console/account ownership, association changes and no unintended cascade deletion of history.
- Schema migrations, invalid database quarantine, disk-full errors and WAL snapshot verification.
- No OAuth/Remote Play credentials in the historical database, exports or frontend API.

**Error classification:** A synchronous connection managed behind an RLock may be thread-safe for the standalone app as written, but this does **not** make its blocking operations safe to call directly from Home Assistant's event loop. That is a portability constraint, not proof the old code is defective in its original environment.

## 7. Lifecycle and cancellation risks

The old main process owns SIGTERM/SIGINT signal handlers, starts publication workers, loops until a stop event and performs manually ordered shutdown. This pattern is inappropriate for an integration loaded/unloaded as one of many HA components.

The reviewed shutdown contains `raise` statements after failure to stop the history/live worker or MQTT. **Control-flow risk:** a failure in an early stage can bypass later cleanup stages, including closing the database, when no outer finally handles each resource independently. This should be tested with injected errors; do not state that a real leak has been reproduced.

**Proposed HA design:** Each per-entry runtime owns its tasks/listeners; an integration-scope manager reference-counts shared storage/panel components. Unload uses cancellation/fencing, independent guarded cleanup for all owned resources and error aggregation; each task's final state and any unsaved observations are visible diagnostically. No extra process signal handlers.

## 8. Identity and state normalization

The new transport starts from native PS5 UDP discovery/status. A `host-id` is a source-asserted candidate, **not** proof of immutable hardware identity or cryptographic trust. IP address changes cannot create new history ownership, and a new identity at the same IP cannot receive the previous console's credentials.

Model independent dimensions:
- Physical power: `AWAKE`, `STANDBY`, `UNKNOWN`.
- Source reachability and last successful observation.
- Freshness deadline and historical last-known state.
- PSN account presence and provider activity (optional, permission-gated).
- Command attempt and confirmation (optional Remote Play).
- Durable local session interval and uncertainty (future ledger).

Do not expose an optimistic Boolean power switch just because the old MQTT integration had one.

## 9. Test cases derived directly from source risks

| ID | Test scenario | Expected |
| --- | --- | --- |
| LEG-T001 | Runtime gap 30 vs default 90 | Assert actual configuration and no accidental adoption |
| LEG-T002 | 31-second gap in legacy fixture | Previous session closes at prior checkpoint; preserve unknown interval |
| LEG-T003 | Duplicate timestamp | No second committed observation |
| LEG-T004 | Two consoles, one offline | Independent state and checkpoint recovery |
| LEG-T005 | Late older probe | Generation protection and idempotency |
| LEG-T006 | Crash between event and checkpoint | Atomic rollback or complete commit |
| LEG-T007 | Two HA entities reading same history | No blocking event-loop database access |
| LEG-T008 | Read 36 months, large row count | Bounded query, pagination and memory |
| LEG-T009 | DST spring/fall with injected timezone | Correct calendar aggregation, no hardcoded Lisbon |
| LEG-T010 | User renames console/entity | Stable physical/historical identity |
| LEG-T011 | Shutdown worker throws | Remaining owned resources still cleaned up |
| LEG-T012 | HA unload during pending UDP read | Cancellation and no stale callback |
| LEG-T013 | Missing or colliding host-id | No unsafe permanent device entry |
| LEG-T014 | SQLite WAL live backup | Restored DB integrity and exact high-water mark |
| LEG-T015 | Config entry removed | Explicit retention/delete semantics, no automatic data loss |
| LEG-T016 | Optional PSN disabled | LAN monitoring and statistics stay independent |
| LEG-T017 | Remote Play permission unavailable | No unauthorized wake/standby |
| LEG-T018 | Long-lived cached source state | Freshness expires without inventing OFF |
| LEG-T019 | Multi-console same player/account | No duplicate attributed player duration |
| LEG-T020 | No sensitive source fields in UI/logs | Privacy boundary preserved |

**All cases are proposed, NOT_RUN.** Legacy code behavior should be captured by reproducible tests only if doing so serves the migration; do not invest in maintaining the obsolete App's MQTT stack.

## 10. Proposed future code review checklist

Before implementing a module, require:
1. A documented responsibility and interface contract derived from ADR/SPEC.
2. No implicit transport/import dependencies in pure domain modules.
3. Proper async cancellation/timeout behavior, no blocking I/O on HA loop.
4. Immutable typed models, explicit `None`/unknown semantics and UTC instants.
5. Owner-scoped identifiers; no global player setting for session identity.
6. Security classification of input and stored fields.
7. Deterministic test fixtures, including malformed input and identity collisions.
8. Observable failures, no empty blanket `except` hiding critical errors.
9. Release-pinned HA API references and translation requirements.
10. Module-level and public method English documentation/comments with rationale.
11. No direct reuse of legacy MQTT or Supervisor app-specific storage APIs.
12. Complete-file review and integration tests before merging to `main`.

## 11. Ordered documentation-only improvements

**DOC-CODE-01:** Record a normalized legacy-to-new module map with precise interface owners (this document starts it).  
**DOC-CODE-02:** Create source-derived synthetic timeline fixtures for legacy session behavior and the proposed conservative new policy, without executable test code.  
**DOC-CODE-03:** Specify fully bounded `HistoryRepository` and `ContinuityPolicy` contracts before accepting ADR-0006/0008.  
**DOC-CODE-04:** Document multi-console identity collisions and explicit migrations from legacy single-player data, opt-in only.  
**DOC-CODE-05:** Review the legacy frontend source tree and identify reusable *information architecture* separately from Lovelace implementation.  
**DOC-CODE-06:** Establish a static code-review gate and secure dependency provenance for each future implementation module.  
**DOC-CODE-07:** Revisit official Home Assistant Core changes during each stable version and update the living Bible.

These are documentation/research tasks, not implementation work packages. They can be performed on `main` without creating a `feature/*` branch.

## 12. Decision and implementation status

| Item | Result |
| --- | --- |
| Legacy code read and analyzed | Completed for the five targeted backend files |
| Source code changed | **No** |
| Existing runtime bug reproduced | **No** |
| Tests executed | **No** |
| New code modules or CI workflows created | **No** |
| Code review findings | Twelve source-derived observations and corresponding recommendations |
| Next development branch created | **No** |
| ADR statuses changed | **No** |
| Intended next phase | Documentation/code auditing, not WP-01 implementation |

## 13. References

- [Architecture guide](../../ARCHITECTURE_GUIDE.md)
- [WP-00 readiness](../architecture/WP-00-implementation-readiness-and-decision-closure.md)
- [WP-00A LAN-first contracts](../architecture/WP-00A-home-assistant-baseline-and-lan-contracts.md)
- [ADR-0004 physical identity](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 state reconciliation](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 session accounting](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0008 persistence](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [SPEC-001 LAN acceptance](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-005 release quality gates](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [SPEC-006 security](../specifications/SPEC-006-security-privacy-threat-model.md)
- [Original legacy source tree](https://github.com/jorgeavlobo/playstation-hub/tree/develop/backend/app)
- [Pinned Home Assistant Core source baseline](https://github.com/home-assistant/core/tree/2026.11.0)

**Outcome:** Documented source-grounded legacy code review and future refactoring requirements. No programming performed.
