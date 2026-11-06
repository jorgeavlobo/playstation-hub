# PlayStation Hub — Observation-to-session temporal reducer: source and contract audit (2026-11-06)

**Status:** RESEARCH / DESIGN PROPOSAL / NOT IMPLEMENTED / NO HARDWARE VALIDATION
**Baseline:** Home Assistant Core 2026.11.0, Python >=3.14.2 research target; actual supported minimum and linked SQLite still OPEN.
**Scope:** Per-console LAN power and coverage, optional PSN account/title observations, local game attribution, bounded-duration derivation, gaps, idempotent durable transactions, report projections.
**Outputs:** [ADR-0021](../decisions/ADR-0021-observation-to-session-reducer-and-temporal-coverage.md) and [SPEC-021](../specifications/SPEC-021-observation-to-session-state-machine-and-replay.md).
**Existing decisions:** ADR-0004/0005/0006/0008/0015/0016/0017/0018/0020; SPEC-008–018/020; Protocols 01–10.
**Repository boundary:** main documentation only; the develop prototype was never deployed, and every old SQLite row is synthetic. NO IMPORT or migration of develop data.

> The precise transitions below are **our proposed accounting policy**, not a Sony protocol guarantee. A successful poll observes a point in time; it does not prove the state of every intervening instant. The Sony power-indicator documentation describes physical LED states, not the network response status-code mapping. No live console, account, worker, SQLite DDL or runnable test was used.

## 1. Official-source evidence register and limitations

| ID | Official source | Fact supported | Does NOT support |
| --- | --- | --- | --- |
| SRC-21-01 | [Sony PS5 power indicator](https://www.playstation.com/en-gb/support/hardware/ps5-ps4-power-indicator-lights/) | White = ON, orange = rest, unlit = OFF; transitional lights exist | A UDP timeout or undocumented LAN status code proving physical OFF |
| SRC-21-02 | [Sony PS5 support](https://www.playstation.com/pt-pt/support/hardware/ps5/) | Rest mode can suspend running software and perform some background functions | Rest mode equals active gameplay or necessarily PSN offline |
| SRC-21-03 | [HA PlayStation Network](https://www.home-assistant.io/integrations/playstation_network/) | Official HA integration is an account/provider activity view with documented limitations | Provider presence identifies a unique local physical console or exact game transition |
| SRC-21-04 | [HA state objects](https://www.home-assistant.io/docs/configuration/state_object/) | HA entities have present state and separate unknown/unavailable semantics | HA entity state history is an authoritative lossless event ledger for this product |
| SRC-21-05 | [HA fetching data](https://contributors.home-assistant.io/core/integrations/fetching-data/) | Coordinator/push interfaces, update lifecycle and entity data practices | Guaranteed polling schedule, monotonic physical observations, or HA lifecycle-independent session duration |
| SRC-21-06 | [SQLite transactions](https://www.sqlite.org/lang_transaction.html) | BEGIN/COMMIT/ROLLBACK and only one simultaneous writer | Committing a separate HA Store/Config Entry transaction atomically with our SQLite ledger |
| SRC-21-07 | [SQLite isolation](https://www.sqlite.org/isolation.html) | Separate readers see fully committed transactions rather than partial writes | Snapshot reads automatically use the same cursor if issued in different transactions |
| SRC-21-08 | [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html) | Unique conflicts can drive explicit update/no-op behavior | Duplicate detection of a different payload under the same observation ID |
| SRC-21-09 | [SQLite FK](https://www.sqlite.org/foreignkeys.html) | FK enforcement must be enabled/verified per connection | All history consistency can be expressed via FKs and CHECK |
| SRC-21-10 | [SQLite WAL](https://www.sqlite.org/wal.html) | WAL may allow concurrent readers/writer, has checkpoint and compatibility caveats, documented WAL-reset bug | Guaranteed custom DB backup/restore on HA OS or guaranteed safe worker cutover |
| SRC-21-11 | [SQLite result codes](https://www.sqlite.org/rescode.html) | BUSY/FULL/IOERR etc. have differentiated failure semantics | COMMIT result known if a caller task was cancelled after dispatch |
| SRC-21-12 | [Python time](https://docs.python.org/3.14/library/time.html) | monotonic/perf-counter clocks are suitable for in-process elapsed comparisons | A monotonic epoch can be persisted and meaningfully compared across process restarts |
| SRC-21-13 | [Python zoneinfo](https://docs.python.org/3.14/library/zoneinfo.html) | IANA time zones and DST fold support | Local midnight corresponds to a fixed 24-hour UTC interval |
| SRC-21-14 | [SQLite savepoints](https://www.sqlite.org/lang_savepoint.html) | Inner savepoint RELEASE does not make changes independently durable | A multi-step reducer is safe without one outer successful COMMIT |

### Community-derived implementation hints (NOT Sony guarantees)

- [playactor discovery parser](https://github.com/dhleong/playactor/blob/main/src/discovery/messages.ts), [PS5-MQTT polling](https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/redux/sagas/poll-devices.ts): candidate LAN request/response models, subject to Protocol 01–02 wire fixture checks.
- [psn-api basic presence](https://github.com/achievements-app/psn-api): provider-sampled account title candidates, not exact local session events; Protocol 09 permissions and legality remain unresolved.
- [Pinned HA Core](https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network): comparative architecture only; using an existing HA integration's entity outputs must NOT replace source and provenance validation.
- No observed fixture in the current documents proves exact moment a game launches/stops on the PS5; verify any claimed event-timestamp API before adding it.

## 2. Evidence taxonomy (three separate timelines)

1. **Physical console timeline** — validated console owner, recognized LAN-derived AWAKE/STANDBY, source-specific freshness; OFF only with independently proven trustworthy source. A failed request is an observation attempt/error, NOT OFF.
2. **Provider account timeline** — provider account ID, online/presence/title candidates, privacy and freshness; may reference another PlayStation, different platform, mobile app, or delayed account state.
3. **Attributed local game timeline** — link to a particular physical console AND account AND title only when evidence supports that claim, with explicit CONFIRMED_SOURCE / INFERRED / AMBIGUOUS / UNKNOWN type; provisional in v1.

A title name, artwork, console IP, HA entity ID, or current PSN profile display name is **never** a durable identity or timeline join key. A manual account-to-console association records possibility/intent, not per-minute proof.

## 3. Time language (avoid misleading 'measured' duration)

- **OBSERVED_POINT:** normalized state at bounded request/response sample time. A point has **zero duration**.
- **BOUNDED_CONTINUITY:** duration within `[previous_accepted_sample, next_accepted_sample)` *when both point states are the same, identity and source are compatible, there is no intervening break, and elapsed time is within approved continuity budget*. It is an accounting **inference**, never proof of physical uninterrupted state.
- **UNKNOWN_COVERAGE:** interval with insufficient compatible evidence; cannot be assigned to AWAKE, STANDBY, OFF, or a game.
- **TRANSITION_UNCERTAINTY:** last observation of state A to first observation of state B. Actual transition occurs somewhere in the bracket; choose UNKNOWN for the whole bracket by default.
- **PROVIDER_REPORTED:** a snapshot or aggregated provider quantity with its independent scope; never add to local console usage.
- **UNSAVED_LIVE:** transient frontend source observation under ADR-0017 degraded mode; MUST NOT contribute to committed history or projected durable metrics.

Proposed user-facing terms: `bounded observed console time`, `unobserved coverage`, `inferred game time`, `provider-reported lifetime time`. Never call bounded interpolation 'exact', or represent unknown as zero use.

## 4. Canonical input and normalizer contract

```text
NormalizedTemporalObservation (proposal, not Python code)
  schema_version
  observation_id                      // persisted idempotency key
  canonical_source_key                // typed source + owner + adapter instance
  ledger_uuid / selected_generation   // validated BEFORE durable write
  owner_kind / canonical_owner_id     // console OR PSN account, never accidental join
  run_uuid / source_attempt_generation
  sequence_or_request_generation      // monotonic within documented source scope
  requested_at_utc_us? / received_at_utc_us
  source_event_at_utc_us?              // NEVER silently substitute for sample timestamp
  source_timestamp_precision?
  monotonic_received_at_ns?           // in-memory only; not persisted
  source_kind / evidence_kind / scope
  physical_state?                     // AWAKE, STANDBY, UNKNOWN, future verified OFF
  psn_online_state? / title_candidates?
  validity / freshness / identity_quality
  sanitized_payload_digest
  source_error_code?                  // failure attempt; may not be a new state observation
```

**Time endpoint choice (OPEN):** prefer `received_at_utc_us` as the observation-anchor approximation, with request-start/duration retained. Timestamp precision cannot be conflated with time-of-physical-transition accuracy. Excessive request latency, clock skew, negative elapsed, clock step, or boundedness failures must yield an UNKNOWN gap/QUARANTINED sample, not backdated activity.

**Monotonic clock:** in-process freshness, deadline and jitter calculations use a monotonic source. Across restart, source IDs, UTC anchors, and generation receipts are the durable basis. Never serialize a monotonic reading as an absolute time or assume OS clock stable between power cuts.

**Canonical source authority:** a LAN source can advance physical coverage only after correct physical identity/protocol normalization. PSN can advance provider account coverage but not physical console coverage. Remote Play command send or session liveness cannot validate a power change; a later recognized response may.

## 5. Reducer: two-layer state, not a single online boolean

```text
Console sample state: NONE | AWAKE | STANDBY | UNKNOWN | VERIFIED_OFF_FUTURE
Coverage state:       NO_ANCHOR | ANCHORED | COVERED | GAP | HOLD
Provider state:       NO_DATA | REPORTED_TITLE | REPORTED_NO_TITLE |
                      RESTRICTED | STALE | ERROR
Attribution state:    NONE | CANDIDATE | INFERRED | AMBIGUOUS | CONFIRMED_FUTURE
Ledger capability:    READY | DENY_WRITE | RECOVERY_HOLD | FAILED_UNSAFE_TO_REOPEN
```

The physical power sample, source health, temporal coverage, PSN account state, attribution and persistence capability are orthogonal dimensions. The last known AWAKE sample may still be shown historically while current power is UNKNOWN and history is no longer accruing.

### 5.1 Deterministic console transition table (default proposal)

| Previous durable compatible anchor | New accepted input | Continuity precondition | Persisted result |
| --- | --- | --- | --- |
| None | AWAKE | n/a | Anchor AWAKE at T, zero elapsed; no pre-start backfill |
| None | STANDBY | n/a | Anchor STANDBY at T, zero elapsed |
| AWAKE at T0 | AWAKE at T1 | Same owner/source and `0 < T1-T0 <= B`, no break | Cover [T0,T1) as bounded AWAKE; checkpoint T1 |
| STANDBY at T0 | STANDBY at T1 | Same qualified preconditions | Cover [T0,T1) as bounded STANDBY; checkpoint T1 |
| AWAKE at T0 | STANDBY at T1 | Any positive gap | Close AWAKE at T0; UNKNOWN [T0,T1); new STANDBY anchor T1 |
| STANDBY at T0 | AWAKE at T1 | Any positive gap | Close STANDBY at T0; UNKNOWN [T0,T1); new AWAKE anchor T1 |
| Any known at T0 | Valid UNKNOWN at T1 | Identity valid, power not interpretable | Stop old coverage at T0; UNKNOWN [T0,T1); record reachable/unknown as separate source fact |
| Any known at T0 | Timeout/error | Not a valid state sample | Retain last-known and health; set continuity-break marker; no OFF and no future earned duration |
| Prior valid at T0 | Later valid at T1 after a break or `T1-T0 > B` | Discontinuous | UNKNOWN [T0,T1); fresh anchor at T1, even if same state |
| Same key + payload | Repeated observation ID | Existing committed digest matches | Existing durable receipt; zero new time/events |
| Same key + different payload | Repeated observation ID | Digest mismatch | Conflict; no historical mutation |
| Any | Out-of-order / wrong run / wrong owner / old generation | Invalid lifecycle | Reject for session timeline; secure diagnostic only |
| Any | Hub RECOVERY_HOLD / writer denied | No history capability | No historical ingest, no checkpoint change; optional UNSAVED live only |

**B** is a policy/versioned maximum continuity budget; NO value has been approved. Legacy develop 90s is historical source behavior only. B must not be chosen as a universal 'normal refresh interval'. Whether same-state samples across an intervening failed poll can be joined is an OPEN safety decision; **default is break**, even if elapsed time is short.

### 5.2 Exact sample arrival is NOT exact physical transition

Example synthetic UTC times:

```text
10:00:00  LAN AWAKE sample     -> anchor, counted duration 0
10:00:30  LAN AWAKE sample     -> [10:00:00,10:00:30) bounded awake = 30s
10:01:00  LAN STANDBY sample   -> [10:00:30,10:01:00) UNKNOWN = 30s
10:01:30  LAN STANDBY sample   -> [10:01:00,10:01:30) bounded standby = 30s
10:02:00  LAN request timeout -> STOP continuity, no asserted OFF
12:00:00  LAN AWAKE sample     -> [10:01:30,12:00:00) UNKNOWN; new anchor
12:00:30  LAN AWAKE sample     -> [12:00:00,12:00:30) bounded awake = 30s
```

**Total bounded AWAKE = 60 seconds**, NOT two hours; UNKNOWN spans 10:00:30–10:01:00 and 10:01:30–12:00:00. Assumes B >= 30s solely for this synthetic fixture. The first state after reconnect does not reveal what happened during the outage.

### 5.3 Idempotency and unobserved gap canonicalization

- A retry with identical ID/digest returns existing durable result. No second event, segment, checkpoint or cursor increment.
- An unseen later observation must advance exactly one deterministic owner/source checkpoint (plus global cursor) per accepted logical operation.
- UNKNOWN intervals for the same owner/scope must be coalesced where adjacent and compatible, or stored as ordered non-overlapping segments with deterministic revisions; never double-count overlapping gaps or relabel them as an OFF interval.
- A timeout event may mark `continuity_broken` immediately but cannot assert the duration of an outage before a future anchor; committed UNKNOWN is finalized when the next anchor arrives, or reported as an open-ended gap with display as-of boundary and explicit NOT-COUNTED flag.
- A policy reconfiguration during an open session must cut the coverage at a known committed boundary and version the next continuity policy. No silent recompute of original ledger history.
- Each exclusive console coverage interval has exactly one classification: bounded awake, bounded standby, bounded independently verified other mode, or UNKNOWN. Reporting subsets are views and not independent authoritative counters.
- Account/title attribution is a separate non-exclusive layer, subject to lineage and evidence constraints; it must NOT be subtracted from hardware awake coverage as though it were guaranteed nested.

## 6. Proposed event grammar and output

**Input facts**: `PowerSample(console,state,time,source,receipt)`, `ProviderPresence(account,titles,time,visibility)`, `SourceAttemptFailed(owner,cause,time)`, `LifecycleFence(generation)`, `PolicyChanged(owner,version)`, and explicit authorized correction/recovery events.

**Outputs**:
- `ObservationAccepted`, `StateSampleChanged` or `HeartbeatAccepted` (not each heartbeat a session increment).
- `CoverageExtended(kind,start,end,evidence_pair,policy_version)`.
- `UnknownCoverageOpened/Extended/Closed(reason,range,anchor_ids)`.
- `SourceHealthChanged/SourceStale` without fake POWER_OFF.
- `ProviderPresenceSnapshotAccepted` independent of console ownership.
- `AttributionCandidate/Changed/Revoked` only with qualified source join and confidence.
- `DurableReceipt(observation_id,digest,ledger_uuid,generation,cursor)` after commit.

A transition at a polled timestamp generates **sample-change evidence**, not an event asserting exact physical switch timestamp. Distinguish `sample_change_at` from `transition_occurred_at` (unknown bracket). Avoid event explosion: same-state heartbeat extends coverage/checkpoint, not a new session-start event; original observations can be sampled/retained under a separate documented retention policy without losing dedup receipts.

## 7. Source sequencing, retries, clock anomalies

- Allocation/acceptance keys: `(ledger_uuid, generation_uuid, owner_kind, owner_id, source_instance, run_id, source_attempt_generation, observation_id)`; define exact lifetime/namespace before final physical DDL.
- Per-console logical reducer is serialized; many console pollers may run concurrently. Shared storage uses one coordinator-owned writer per ADR-0008/SPEC-009.
- Reject callbacks from past Config Entries, superseded request generations, swapped physical consoles at same IP and old active database generations. Do not reassign prior identity by display name.
- If source has trusted sequence, order by that protocol-specific sequence; else order by request-attempt generation and compatible normalized sample anchor. Two workers completing in reverse order must NOT rewrite history backwards.
- If equal/newer request returns a timestamp earlier than previous durable anchor, quarantine for time reconciliation; NEVER use negative or zero-duration as a reason to reset an entire ledger.
- Nonzero clock step, huge requested-to-received latency, system clock repair or leap/DST display conversions must not mint extra minutes. UTC epoch microseconds are the storage proposal; local calendar windows are computed via IANA zoneinfo.
- Poll timeout plus subsequent same-state sample does NOT retroactively establish continuity unless a separately approved alternative policy explicitly addresses failed probes.
- Backfilled provider event timestamps and reordered PSN presence must not be silently threaded into local physical power durations.

## 8. Durable writer transaction and snapshot/read contract

One accepted durable observation should atomically:
1. Verify controller `READY`, active ledger/generation, owner/source/run lease, and canonical policy version before admission.
2. Begin an explicit write transaction (exact `BEGIN IMMEDIATE` choice and busy policy pending SQLite runtime audit).
3. Lookup `observation_id` and canonical payload digest; return exact durable receipt if already applied, fail on conflict.
4. Load current per-source checkpoint and owner temporal head; reject stale/invalid input, and enforce evidence-boundaries.
5. Persist sanitized observation and required domain events; update/close/insert covered segments and unknown intervals; update source checkpoint, policy version and global ledger cursor **in one transaction**.
6. COMMIT once. Only then mark the observation committed and publish cursor-matched immutable projections.
7. On known failed write/rollback, return UNSAVED/ERROR without modifying durable cursor. On a potentially completed but unacknowledged COMMIT, fence uncertain work and re-query id+digest after worker state is safely known; do not blindly retry insert/increment.

SQLite readers must use one consistent transaction/snapshot for a report, capturing ledger UUID, active generation, cursor, policy and intervals as one read view. A report cannot mix 10:00 cursor metadata from one reader transaction with 10:01 segments from another and claim consistency.

SQLite constraints: FK ON/verified on each connection; explicit non-NULL canonical keys; partial UNIQUE only where resources are truly exclusive. SQL CHECK constraints do not prove no overlap between different rows: reducer and acceptance tests must. Do not use UPSERT to overwrite immutable source payload.

**Failure path:** BUSY/FULL/READONLY/IOERR cannot move durable evidence frontier. If the writer fails, health/Repairs path may show an error but cannot claim successful data saving. FENCING/RECOVERY_HOLD follows ADR-0015–0017; never recreate a missing ledger or rename open DB/WAL.

## 9. PSN game/title attribution and unresolved data capability

Provider title presence is point-sampled and potentially hidden by privacy; profile platform `PS5` is not a physical device ID. Even a sole console configured in Hub is not a cryptographic device attribution.

**Default v1 recommendation:** Show PSN game as `account-reported title` with independent as-of, **not** count it in per-console game usage by default; any estimated, manual or confidence-labeled inferred attribution is opt-in and separately versioned. A future directly verified console/title source can add a stronger qualified ledger event, subject to a protocol, provenance and license gate. PSN offline or absent title does NOT imply game ended or physical console powered off; account-title continuity has its own bounded rules and privacy break markers.

**Important:** This is a recommendation, not maintainer approval to exclude game time forever. Study a user-facing estimate that never contaminates conservative physical totals.

## 10. Lifecycle, recovery, multiple owners, reports

- Hub/Archive logical Config Entry owns global history availability and optional recovery UI; physical consoles/accounts have separate entries. Removing one must not erase its historical owner or change other owners' reducer timelines.
- Per-console monitor continues independent of frontend listeners per SPEC-008; restarting frontend/dashboard cannot open or close a session.
- Clean shutdown: fence ingestion, drain and commit, finalize covered end at last committed checkpoint; all unobserved time until later restart remains UNKNOWN.
- Crash: persisted last checkpoint is authoritative. Never infer activity between it and next new verified sample. If crash occurred during COMMIT, use durable observation ID/digest receipt reconciliation.
- Restore: untrusted copy or restored older cursor never silently combines into current live ledger. Follow restore-authority, immutable-generation, journal and RECOVERY_HOLD gates from ADR-0011–0018; run no reducer until selected writer is positively verified.
- Two consoles A and B may both earn one hour of console-hours during the same wall hour; a union-of-wall-clock metric is separate. Provider-account hours may overlap console-hours and are never added to them.
- Query day/week/month/year by clipping `[start,end)` UTC sessions to UTC boundaries derived from the selected IANA report timezone. Fall-back DST day may have 25 hours; spring-forward may have 23. Avoid local naive subtraction.
- Bounded sessions and UNKNOWN gap ranges must be independently inspectable; a report includes `as_of_cursor`, `coverage_fraction` only where denominator and scope are defined, `policy_version`, `timezone`, `last_seen` and `not_sure` visibility.
- Zero minutes **with complete coverage** is not the same as zero minutes **with no coverage**.

## 11. Unresolved P0/P1 decisions before physical DDL or implementation

**P0-01** Validate LAN awake/standby wire code and physical identity with firmware fixtures; official LED states do not prove UDP mapping.

**P0-02** Agree the default continuity model: strict two-point bounded continuity, break on every failed poll, no game attribution from PSN alone.

**P0-03** Calibrate budget B and request latency floor from actual supported poll cadence, network jitter and tests. Do not copy 90s from develop.

**P0-04** Define whether the first post-timeout sample counts an UNKNOWN interval from last checkpoint and how to represent still-open unknown spans without unbounded rows.

**P0-05** Specify canonical `sample_at` in presence of retries, wall-clock corrections, request duration, monotonic runtime and malformed source timestamps.

**P0-06** Bind terminal evidence, single-writer admission and uncertain COMMIT recovery to ADR-0015–0017 and SQLite runtime/WAL bug gates.

**P0-07** Confirm exact exclusive interval DB constraints; 12-table ADR-0020 logical model may need policy-version, evidence-pair and gap flags without automatically adding new tables.

**P0-08** Verify no dual counting across AWAKE/STANDBY/UNKNOWN, current versus last-known, and game/PSN scope.

**P0-09** Check source/account privacy, title/console trust and platform attribution via Protocol 09; do not call undocumented PSN APIs without separate authorization.

**P0-10** Define replay source-of-truth: immutable accepted observations and policy-versioned deterministic rebuild, with explicit revision not silent historical rewrite.

**P1-11** Confirm scheduler behavior independent of HA entity listeners and bounded queue at scale.

**P1-12** Report timezone and account/console/all-console query plans and 36-month synthetic performance.

**P1-13** Version semantics of estimates/unknown when user edits accounts or renames a game.

**P1-14** Define observation retention, privacy/erasure implications, archive exports and snapshot reconciliation.

**P1-15** Decide UX terminology, completeness indicators and whether optional bounded estimates are separately visible.

**P1-16** Obtain explicit maintainer sign-off of ADR-0021, DDL and worker/test gates before implementation.

## 12. Next prioritized investigation

Research **deterministic replay, correction/versioning and crash-boundary simulation** as the next step (proposed ADR-0022/SPEC-022): replay from accepted observations, policy evolution, late data correction, open-segment recovery, sample-boundary ambiguity, report equality and restore divergence. This is needed before fixing physical SQL DDL or authorizing a real reducer.

**Outcome:** Source-backed architecture only. No table, migration file, Python/JS module, simulation, Home Assistant installation, PSN request, console access or test was created or executed.
