# ADR-0006 — Session accounting, temporal uncertainty and usage statistics

**Status:** Proposed for review; not accepted, implemented or hardware validated  
**Review date:** 2026-11-05  
**Scope:** Multiple physical PlayStation consoles, optional multiple PSN accounts, game sessions, confirmed observations, statistics, uncertain intervals, restart and offline recovery  
**Inputs:** [ADR-0004](ADR-0004-identity-and-multi-console-ownership.md) (identity, proposed), [ADR-0005](ADR-0005-observation-and-state-reconciliation.md) (source authority and freshness, proposed), Protocols 01–10  
**Consumers:** ADR-0008 (storage architecture), ADR-0009 (native Home Assistant entities/actions), ADR-0010 (sidebar API); future statistics and reporting  
**Reference code:** `develop/backend/app/{session_tracker,database,models,usage_statistics}.py` (legacy source **only**, not copied)  
**Implementation branch:** None; research documentation changes only on `main`

> **Evidence boundary:** The legacy PS5 Monitor shows a working **design approach** with transactional checkpoints, conservative recovery and reporting, but does not prove this ADR is implemented in PlayStation Hub. Sony presence polling does not provide exact game start/end transitions or identify a unique physical console. Numerical examples below are synthetic. The storage backend remains unapproved (ADR-0003).

## 1. Decision problem

PlayStation Hub must produce useful, honest and reproducible console/session statistics when devices are polled intermittently, sources are unavailable, PSN account presence is ambiguous, several consoles are used at once, a Home Assistant server restarts or a console moves between games/accounts. Any calculated duration depends upon the evidence collected and the chosen policy for intervals **between** observations.

We must not silently assert that a console was active throughout a missing interval, that a PSN account was playing locally, or that a game started exactly at a polling timestamp. The system must distinguish:
- Direct, fresh observation of a physical console's mode.
- Persistence of a previously known local state between bounded successful checks.
- PSN's account-level report of game activity.
- Inference linking a PSN account/game to a physical console.
- Provider-supplied all-time played duration from another scope.
- Missing/unobserved time, optional estimates, and user-visible historical uncertainty.

The design must remain fully functional for **LAN-only usage without a linked PSN account**, and it must support a clean mapping from the old single-console/single-player design to multi-console/multi-account without importing any private data automatically.

## 2. Decision candidates

| Option | Benefit | Main problem | Assessment |
| --- | --- | --- | --- |
| A. Assume latest state continues until changed, including during outages | High apparently complete totals | Fabricates hours during downtime, overcounts | Reject |
| B. Treat every pair of successful samples as continuously valid | Easy aggregation | Can count across long gaps and state transitions | Reject unless bounded and labeled |
| C. Record **bounded evidence intervals** and gaps, provide conservative totals | Auditability, privacy, clear source provenance | May undercount actual usage | **Preferred proposal** |
| D. Compute only PSN's provider lifetime duration | Simple account history | Not physical console/time-window precise; may include other hardware | Reject as local usage ledger |
| E. Keep both audited conservative totals and a separately labeled estimated view | Useful comparisons | Requires additional estimation policy, UX and validation | Optional future extension; not initial authoritative figure |

**Preferred architecture (proposed):** An append-only or revision-auditable, idempotent event/checkpoint ledger drives session segments. Confirmed/eligible seconds are accumulated only inside an explicitly bounded observation-continuity policy. Gaps and unassigned activity are first-class data, not zeros silently added to or subtracted from true totals. User estimates, when eventually supported, must remain a separately labeled metric.

## 3. Legacy source audit and what to preserve

Directly inspected `develop`:

- `SessionTracker.process_state` rejects observations with timestamps not newer than the last accepted record and forwards accepted state into a DB transaction; in-memory ordering advances only if the DB write succeeds.
- `Database.apply_observation` uses a default `max_gap_seconds=90.0` in the old program. If elapsed time since a session checkpoint exceeds that bound, it closes the old session **at the last checkpoint**, not at the new response timestamp. An accepted sample may start a fresh session.
- Open console and game sessions are separate types. A game change or cessation closes the current game segment at the previous persisted checkpoint; recurring identical observations update the checkpoint without creating duplicate state-change events.
- `recover_open_sessions` atomically closes unfinished sessions at their last durable checkpoint (or start if no checkpoint), idempotently.
- `StatisticsService._effective_end` excludes uncheckpointed elapsed time. `_intervals` clips sessions to half-open time windows. Local-calendar boundaries use `ZoneInfo("Europe/Lisbon")` and DST-aware UTC conversion.
- The old implementation assumes one exact configured player and an account/game view delivered through MQTT. These single-player assumptions and the hardcoded reporting timezone must **not** become global rules in the new system.

**Important refinement:** The legacy label “confirmed time” is stronger than a point-sampled protocol alone warrants. A successful probe at T0 and another at T1 proves state at observation times; continuity between them is an **accounting assumption with a bounded interval**, not a physically measured continuous signal. The new model should call it `bounded_observed_duration` or another clearly documented name rather than unqualified `exact`.

The old 90-second gap rule is an **upstream legacy policy**, not a validated universal PlayStation Hub value. It must not be adopted without review of the actual LAN poll cadence, retries and topology.

## 4. Canonical identity and independent session dimensions

| Dimension | Record key | Source | Important distinction |
| --- | --- | --- | --- |
| Physical console use | Validated `console_id` | LAN status/Remote Play facts | No player required; never key by IP |
| Account-level PSN presence | Provider `psn_account_id` | Protocol 09 | Can be active on another console |
| Game/title reference | Provider + title-ID namespace + scope | Protocol 10 | Display name or cover is not a unique ID |
| Player-attributed local play | `console_id` + account + title with provenance | Reconciler + evidence | May be inferred or ambiguous |
| Provider lifetime playtime | `psn_account_id` + provider title key | PSN played-games service | Separate snapshot, not local session ledger |
| Session event | Locally assigned immutable event ID | Session engine | Must be deduplicated on replay |

**Proposed layers:**

1. **Physical console activity** — one console's locally reported awake/standby/unknown periods.
2. **Account presence** — per Sony account with provider freshness and privacy states.
3. **Local gaming attribution** — relationship between a console, account and title, only at supported confidence.
4. **Catalog enrichment** — names/artwork and title crosswalk, never retroactively altering session time.
5. **Provider aggregate playtime** — separate view used for comparison, never summed into locally observed seconds.

One physical console cannot have overlapping *mutually exclusive power-state segments*; several people could use the console but exclusive per-player accounting is not assumed without supporting source evidence. Across two consoles, wall-clock totals can legitimately exceed elapsed wall time if both were active simultaneously. Do not truncate independent console totals to one global timeline.

## 5. Event and segment model (conceptual)

```text
SessionEvidenceEvent
  schema_version: integer
  event_id: stable locally unique ID
  observation_id: ADR-0005 observation reference
  console_id: validated immutable hardware key
  account_id: optional provider key
  title_id: optional namespaced game ID
  event_kind: sample | transition | source_gap | recovery | correction
  observed_at_utc: timezone-aware instant
  accepted_at_utc: timezone-aware instant
  source: lan | remote_play | psn_presence | user_declared
  evidence_scope: hardware | provider_account | attributed_activity
  evidence_confidence: confirmed_source | inferred | ambiguous | unknown
  run_id: current integration generation
  sequence: monotonically accepted per source/target
  durability_state: committed | pending | failed
  redacted_diagnostic_code: optional

SessionSegment
  segment_id: immutable ID
  console_id: stable physical key
  account_id: optional when attribution permits
  title_identity: optional verified provider ID
  segment_type: console_awake | player_game | unattributed_activity | unknown_gap
  start_utc: inclusive boundary
  end_utc: exclusive boundary or open
  last_checkpoint_utc: latest successfully persisted accepted time
  start_boundary_kind: observed | bounded_estimate | unknown
  end_boundary_kind: observed | bounded_estimate | unknown
  attribution: confirmed | inferred | ambiguous | unknown
  source_observation_ids: bounded references
  revision: monotonically increasing integer
  closed_reason: state_change | game_change | account_change |
                 source_expired | restart | manual_correction
```

Fields are **proposals**, not database tables or Python classes. If only point observations exist, `observed` means **the time of the sample**, not proof of exact physical transition. An initial successful AWAKE sample cannot justify backdating a session start to before that sample. `Unknown gap` represents lack of evidence, not an actual console OFF interval.

**Event ordering:** Ingestion reuses ADR-0005's `run_id`, source request generation and observation ID. Event IDs must be idempotent, and no late callback may insert activity after unload. A commit acknowledgment, not memory mutation, defines durable accepted history. Source observation and session segment write must be coherently sequenced by one per-console reducer; storage backend chosen in ADR-0008.

## 6. Temporal model and numerical definitions

All stored instants use timezone-aware UTC. Process-local monotonic time is used for freshness and elapsed wait scheduling, never serialized as a clock across restarts. Use integer microseconds or another justified precision representation for persisted durations; avoid cumulative floating-point drift and double rounding.

**Intervals:** All aggregate ranges and session segments are **half-open** `[start_utc, end_utc)`. Zero-length segments contribute zero seconds, and overlapping records of the *same exclusive console resource* are deduplicated or rejected, not double-counted.

**Time classifications:**

- `bounded_observed_seconds`: elapsed time between compatible fresh samples under a configured maximum continuity gap, allocated by the approved accounting rule. This is an estimate bounded by evidence, not infallible proof of continuous activity.
- `confirmed_transition`: an explicit recognized source state at a sample timestamp; does not prove the exact moment of change since previous sample.
- `unobserved_seconds`: identified elapsed intervals for which coverage is insufficient; not added to bounded activity totals.
- `inferred_player_seconds`: game/account/console association requiring assumptions, separately labeled.
- `provider_reported_seconds`: provider total with explicitly verified unit, account and scope, **never** local seconds.
- `durable_seconds`: ledger totals successfully committed; display of uncommitted live time must be visually distinguished.

**No negative and no blind subtraction:** A metric `console_awake - gaming` only represents non-gaming console time when gaming is a known subset of the **same console intervals**, both use compatible coverage and definitions, and no simultaneous game/player overcount exists. Otherwise present unclassified time separately; do not blindly clamp a negative number to zero and call it correct.

## 7. Proposed accounting finite-state machines

### 7.1 Physical console

```text
UNKNOWN -> OBSERVED_AWAKE -> OBSERVED_AWAKE
                            -> OBSERVED_STANDBY
                            -> SOURCE_GAP
SOURCE_GAP -> OBSERVED_AWAKE | OBSERVED_STANDBY | UNKNOWN
OBSERVED_STANDBY -> OBSERVED_AWAKE | SOURCE_GAP
```

State transitions are driven by validated source facts. A missed poll alone is not an OFF transition, although the **availability/freshness projection** may expire. There must be no session that continues accumulating indefinitely after last durable evidence.

### 7.2 Game/account attribution

```text
NO_ATTRIBUTION -> ACCOUNT_REPORTED_GAME
ACCOUNT_REPORTED_GAME -> INFERRED_ON_CONSOLE | AMBIGUOUS | STALE
INFERRED_ON_CONSOLE -> CHANGED_GAME | ACCOUNT_UNAVAILABLE | GAP | AMBIGUOUS
AMBIGUOUS -> INFERRED_ON_CONSOLE | UNKNOWN
```

Sony presence alone confirms **what the provider reported about an account**, not that the game is running on the local physical console. `inferred` player-time segments are separate from confirmed hardware awake time, and are never silently promoted to direct fact.

### 7.3 Transition boundary policies requiring approval

- **Same state at T0 and T1:** If the gap is within the approved maximum and both samples belong to the same identity/source generation, account `[T0,T1)` as bounded observed continuity for that state.
- **Different state at T0 and T1:** The transition occurred at some unknown point in `(T0,T1]`. Conservative policy closes the old segment at T0 and starts the new at T1, marking `[T0,T1)` uncertain rather than attributing it to either state.
- **Expired gap:** Close accounting at last persisted checkpoint. The first sample after the gap starts a new segment; no backfill.
- **Immediate explicit protocol event:** If a genuinely timestamped, verified event signal exists (not merely a poll), define a source-specific rule after wire validation and tests.
- **Command completed:** Successful UDP send/TCP write/socket closure is not a completed power transition; only P07's validated confirmation may affect accounting.
- **Provider game changed between polls:** Do not allocate the entire gap to either game unless a separately approved inference/estimate policy exists.
- **PSN offline/private:** This is not proof of stopped local gaming. Player attribution may become unavailable, but LAN awake time remains independent.

**Open technical policy:** Some user-facing uses may justify separately showing upper/lower bounds for unknown transition intervals. Defining those bounds correctly requires a precise evidence model; do not claim a point estimate is measured reality.

## 8. Checkpoint, heartbeat and observation ingestion

A successful **unchanged** source sample can advance the last checkpoint and bounded active interval; it should not create an additional session-counting event. An actual change in accepted physical state/attributed game creates a new segment/revision. Transport health failures and gap transitions may create source-health events without creating OFF events.

**Per-console serialized ingestion:**

1. Receive the reconciled ADR-0005 observation/event.
2. Verify canonical console ID, generation, idempotency and ordering.
3. Load previous durable session state/checkpoint.
4. Determine if the new sample is compatible and within the continuity budget.
5. Atomically apply event, checkpoint, segment closure/opening and acceptance cursor.
6. Commit before acknowledging durable observation to the session consumer.
7. Publish immutable updated totals/snapshots to HA/frontend.
8. On disk error, retain an explicitly `not_saved` live view if allowed; do not advance durable cursor or claim history success.

No direct database access from transport callbacks, HA entity getters or the sidebar. Avoid double writers for one console; any asynchronous batching must preserve causal ordering and bounded queue capacity.

## 9. Network outage and long-gap behavior

| Scenario | Physical power state shown | Account/gaming state | Historical accounting |
| --- | --- | --- | --- |
| One LAN poll timeout | Last-known may still be fresh per TTL | PSN independent | No immediate fabricated OFF; bounded interpolation only under approved policy |
| LAN TTL exceeded | Current unknown/unavailable, last-known timestamp visible | PSN may still respond | Stop new bounded continuity beyond last confirmed checkpoint |
| PSN 403/privacy | LAN current unchanged | Privacy restricted/unknown | Do not infer game stopped; inferred player accounting loses support |
| PSN 429, outage | LAN current unchanged | PSN stale/unavailable | Retain previously committed segments; no fabricated gameplay |
| HA process terminated | Live state no longer updating | No live PSN polling | Recover open segments at last persisted checkpoint |
| HA resumes after hours | Newly observed LAN state | Fresh PSN data if permitted | New observation begins new segment; missing time remains unknown |
| Physical PS5 changes state between two successful polls | Latest recognized state fresh | Independent | Transition interval marked uncertain; no exact transition time invented |
| Console replaced at same IP | Block identity mismatch | Account unaffected | Never attribute new console to previous hardware ledger |

The **maximum continuity gap** must be calibrated to the final LAN/PSN polling intervals and failure tolerance. Legacy `max_gap_seconds=90` is documented as a reference only.

## 10. Restart, shutdown and restore

### Clean shutdown
- Stop ingestion of new observations; cancel scheduling at a controlled barrier.
- Await bounded in-flight writes and commit final accepted checkpoints.
- Close open segments at their last durable evidence timestamp; do not close at “now” if nothing confirmed the last interval.
- Persist a shutdown marker when storage is available; shut down transport and DB resources in safe order.

### Unexpected crash
- At next startup, read durable open segments and their latest checkpoints.
- Idempotently finalize old runtime segments at latest committed checkpoint (or start if missing).
- Mark the elapsed interval until first new observation as unknown, not as continuous play.
- Prevent old `run_id` events from being accepted after recovery.

### Restored backup
- A backup may contain old open segments and checkpoints. Rehydrate under a new runtime generation; reconcile idempotently and keep provider tokens separate.
- Do not count time between backup creation and restore as observed.
- Preserve original IDs and references if valid; detect identity collisions rather than merging histories by IP.
- Document any missing/replayed data boundaries; do not claim full data continuity when a backup is stale.

**Storage-independent requirement:** No assumption that `SQLite WAL` or `Home Assistant Store` is the final backend. ADR-0008 must prove consistency, backup inclusion, migrations and transactional guarantees before implementation.

## 11. Multiple consoles, players and concurrent activity

**Two physical consoles:** Track each console separately. A combined “all consoles hours” value is the sum of per-console resource time and may exceed one day of wall-clock time if multiple devices run in parallel; alternatively publish `wall_clock_union_seconds` as a **different metric**, explicitly calculated by interval union.

**One account, two consoles:** PSN account presence cannot identify which physical device produced it. The account's cloud-reported game stays account-scoped or ambiguous until reliable direct mapping exists. Do not duplicate a single reported game interval into both consoles' player totals.

**Two accounts, one console:** User-confirmed association shows ownership/link, not simultaneous actual play. Split into distinct attributed gaming segments only when evidence supports the transition; otherwise preserve `unattributed`/ambiguous activity and avoid non-gaming subtraction.

**Game identity change:** Use verified provider title IDs, not mutable display names or artwork URLs. A localized title rename must not create a new session; a genuine title ID change can terminate a known game segment subject to uncertainty policy. A `null` game identity is not proof that console gaming stopped.

**Separate time measures:** `console_awake_seconds`, `account_psn_presence_seconds`, `per_player_attributed_seconds`, `per_game_attributed_seconds` and `provider_lifetime_playtime` must each state the measurement method, scope and confidence. Never compare or add them silently as identical quantities.

## 12. Calendar aggregation, DST and time zones

All persisted boundaries are UTC; the selected Home Assistant/user configured reporting timezone determines local day/week/month/year boundaries. A global hard-coded Europe/Lisbon is not appropriate for the distributed integration, although it remains a mandatory **test fixture**.

- Define reporting periods in **local calendar dates**, then convert their half-open start/end boundaries to UTC for intersection.
- A local day can be 23 or 25 hours around daylight-saving transitions; never assume 86,400 UTC seconds for every day.
- A session ending exactly at local midnight contributes only to the previous day, not both days.
- ISO week convention (Monday vs Sunday) should be documented/configurable; choose a clear default aligned to HA localization.
- Months use actual calendar boundaries, and month-to-date analytics must distinguish a partial current period from a complete historic period.
- An annual report uses calendar-year boundaries in the configured timezone; leap days are ordinary local calendar days.
- For an interval `[start,end)`, accumulate only its intersection with the requested UTC-converted local reporting window. Perform interval union/dedupe first where resource exclusivity applies.
- Sessions crossing DST changes must not produce negative duration or duplicate elapsed hours when wall-clock time repeats.
- Round/display seconds only after aggregation; persist enough precision for repeatable totals.

### Example: DST fall-back (Europe/Lisbon)

A segment spanning 2026-10-25 00:30 UTC to 02:30 UTC covers exactly **two elapsed hours**, even though local wall-clock representations cross the change from WEST to WET. Summaries use UTC duration between instants, then allocate that duration to the corresponding local day. A naive local string subtraction is prohibited.

## 13. Metrics and report semantics

| Metric | Definition | Scope / caveat |
| --- | --- | --- |
| `console_awake_bounded_seconds` | Sum/union of accepted, bounded awake segments | Per physical console; source-based interval assumption |
| `console_awake_sessions` | Unique session IDs with positive covered intervals or explicit start policy | Session count policy must define zero-length records |
| `console_active_days` | Distinct local calendar dates with positive bounded covered awake time | Count each date once |
| `player_game_inferred_seconds` | Attributed, labeled game intervals | Separate from hardware-confirmed usage and provider total |
| `unattributed_console_seconds` | Covered awake time without supported per-person assignment | May include non-gaming and unknown player activity |
| `unobserved_seconds` | Relevant gaps with insufficient evidence | Not equivalent to off/idle |
| `provider_reported_play_duration` | Sony aggregate from compatible provider response | Units/scope must be verified; do not sum with local metrics |
| `game_sessions` | Distinct durable attributed segments for verified game title identity | Inferred vs direct attribution exposed |
| `today/week/month/year` | Intersection with configured timezone calendar window | Includes partially covered periods explicitly |
| `rolling_12_months`, `rolling_36_months` | Calendar period or true rolling-window definition selected and documented | Do not mix last 12 **calendar months** with trailing 365 days |
| `daily_average_seconds` | Total bounded seconds / clearly stated number of calendar days | Month-to-date vs complete period must differ |
| `month_over_month_change` | Difference and percentage only where denominator valid | Zero baseline yields undefined %, not division error |

**Statistics reproducibility:** Summaries must be pure deterministic queries over the same durable segments and reporting timezone. If session corrections are supported, record revision provenance and optionally invalidate/materialize only affected cached aggregates; never maintain independent, irreconcilable cumulative counters in SQLite and HA sensor attributes.

**Negative numbers:** If subtracting gaming from awake yields negative due to different scopes/overlaps, treat it as a modeling error or show incomparable metrics; do not hide it by applying `max(0, ...) ` and declaring non-gaming confirmed.

## 14. Proposed report contract and frontend semantics

```text
UsageReport
  schema_version: integer
  requested_scope: console | account | title | all_consoles
  scope_ids: validated immutable identifiers
  timezone: IANA timezone identifier
  period_start_utc: inclusive
  period_end_utc: exclusive
  period_label: localized display
  accounting_policy_version: versioned policy name
  data_as_of_utc: latest durable checkpoint
  bounded_console_seconds: integer
  inferred_player_seconds: optional integer
  unknown_gap_seconds: integer
  provider_duration: optional amount + verified units + provider timestamp
  session_count: integer
  active_days: integer
  completeness: complete | partial | interrupted | unknown
  attribution: confirmed | inferred | ambiguous | unknown
  persistence_health: durable | degraded | unsaved
  metadata: optional labels and artwork refs, never tokens
```

These are conceptual API fields, **not** implemented message schemas. WebSocket payload size, page limits, ACL and caching belong to ADR-0010. Users should be able to see **time tracked**, **time not observed**, **PSN-reported lifetime time** and (if eventually chosen) **estimated time** as different concepts. Avoid one headline number that combines incomparable evidence.

The panel must still render offline historical reports from durable local data when PSN/cloud is unavailable. Unavailable metadata produces a placeholder, not a vanished history record. A live timer may display provisional elapsed time since the last successful checkpoint only when clearly labeled uncommitted and not incorporated into stored totals prematurely.

## 15. Persistence contract without selecting technology

The ledger implementation must support:
- Atomic `accept_observation_and_apply_segments` semantics per console.
- Idempotency constraints on `event_id`/`observation_id` and versioned schema.
- Durable checkpoint and last accepted generation alongside session writes.
- Bounded read queries intersecting a time range; indexes by console/account/title/time.
- Migration from prior schema versions and a recovery marker after incomplete shutdown.
- Backups/restores consistent with open transactions, WAL if used, multi-console concurrent writers and retention.
- Explicit corruption/disk-full handling without silent reset or historic data loss.
- Stable immutable identifiers and alias migration only under explicit rules.
- Separate secured PSN/Remote Play credential storage.
- Optional exports that redact private account identifiers by default, with user-controlled retention.
- No direct writes into Home Assistant Recorder's internal tables.

These requirements are passed to ADR-0008. SQLite remains a **candidate** (ADR-0003); this ADR neither approves nor requires it.

## 16. Data privacy, ownership and deletions

A user may remove one console, unlink one PSN account, unpair Remote Play, purge social data, export historical totals or uninstall the integration. These are not equivalent operations.

- Removing a console config entry stops future monitoring and removes appropriate entities/credentials, but should offer a clearly documented historical-data policy; do not silently reassign history to replacement hardware.
- Unlinking a PSN account removes or disables provider credentials and account-specific associations while preserving independent LAN console usage. Retention/deletion of account-attributed history must be explicit.
- Game display metadata must not be mistaken for a player's identity and may be retained separately from sensitive account history where lawful.
- Do not keep unrestricted raw provider responses, children/friend lists or exposed NPSSO in session events.
- Diagnostics must not reveal console host ID, private account ID, tokens or precise personal usage history by default.
- Exports/backups containing personal game activity should require user-initiated access control and respect backup security.

No remote Sony-side erasure or revocation is claimed unless the service supports and permits it.

## 17. Error and recovery taxonomy

| Error | Session consequence | User-visible treatment |
| --- | --- | --- |
| `observation_superseded` | Reject duplicate/late event, no new duration | Usually silent diagnostic |
| `identity_mismatch` | No write to wrong console | Warning / reconnect or re-pair |
| `source_gap_exceeded` | Close at last checkpoint, mark uncertain interval | Incomplete coverage |
| `state_changed_with_unknown_boundary` | Split at observed times, record ambiguous interval | Partial coverage |
| `psn_auth_required` | Stop PSN attribution only; LAN continues | Optional reauth |
| `psn_privacy_restricted` | Do not infer person/game | Game/activity unavailable |
| `provider_rate_limited` | No fabricated game event | PSN temporarily unavailable |
| `storage_commit_failed` | Do not advance durable history cursor | Storage issue; live state not saved |
| `history_schema_unsupported` | Stop writes until reviewed migration | Repair/update required |
| `clock_anomaly` | Reject impossible ordering or flag source | Data quality warning |
| `duplicate_session_id` | Idempotent replay or integrity violation | Diagnostic |
| `backup_stale` | Recover last-known only, no backfill | Restored data may have gaps |
| `unknown_player` | Preserve unattributed console interval | Unattributed activity |

No error automatically creates an OFF power transition.

## 18. Acceptance tests (synthetic and later HA integration)

### Evidence, segments and boundaries
- [ ] Two identical fresh AWAKE polls inside budget advance one segment/checkpoint without duplicate sessions.
- [ ] AWAKE then STANDBY yields an uncertain transition interval, not a falsely exact switch time.
- [ ] First-ever AWAKE observation starts no historical activity before the sample.
- [ ] Gap over approved maximum closes at last persisted checkpoint; next AWAKE starts new segment.
- [ ] Source timeout does not create OFF or count hours of unobserved time.
- [ ] Replay of event/observation ID does not increase duration or session count.
- [ ] Older request generation or old run ID cannot move a segment end forward/backward.
- [ ] Invalid negative/zero or contradictory boundaries are handled safely.
- [ ] Source health heartbeat with unchanged state updates checkpoint, not a separate game-start event.
- [ ] Graceful stop and crash recovery are idempotent at last committed checkpoint.

### Identity, attribution and concurrency
- [ ] Two consoles awake concurrently yield separate resource time, sum may exceed global wall time.
- [ ] A single PSN account on two local consoles does not duplicate one game interval into both player totals.
- [ ] Two PSN accounts linked to one console do not double-count physical awake time.
- [ ] PSN online/offline or private profile never overrides LAN state.
- [ ] Changed title display text without changed verified ID does not split game session.
- [ ] Genuine title ID change has appropriately uncertain transition time.
- [ ] A game with unknown account/title appears as unattributed without invented player identity.
- [ ] Device hardware replacement at same IP starts new identity, does not inherit prior sessions.
- [ ] Provider play duration does not enter local aggregate totals.

### Calendar and numerical correctness
- [ ] Two UTC hours spanning 2026-10-25 Lisbon fall-back yield exactly 7200 elapsed seconds.
- [ ] Spring-forward Lisbon day has 23 hours and fall-back day 25 hours.
- [ ] Leap-day sessions count in the correct year/month.
- [ ] Cross-midnight half-open interval is allocated once to each intersected local date.
- [ ] Session ending exactly at 00:00 local does not count active next day.
- [ ] Current partial month and full prior month have correctly distinguished daily-average denominators.
- [ ] Month/year boundaries and rolling-12/36-month definitions are consistent and documented.
- [ ] Union of overlapping segments of same exclusive console resource prevents overcounting.
- [ ] Same history with different legitimate report timezones yields different local-date grouping but identical overall UTC elapsed time.
- [ ] Zero previous month baseline yields undefined/appropriate percentage, no divide-by-zero.

### Persistence, HA and privacy
- [ ] Transaction failure between checkpoint and session update cannot partially commit a false duration.
- [ ] Restart with open ledger segments closes at checkpoint and marks gap.
- [ ] Backup restored from older point does not count time until first fresh probe.
- [ ] History remains queryable without PSN authorization or internet.
- [ ] No history files inside HACS-managed integration source directory.
- [ ] All read queries are bounded/paginated, async-safe and cancelable.
- [ ] A frontend refresh does not cause new session accounting or Sony API calls.
- [ ] Locale and timezone changes trigger report recomputation, not mutation of original UTC records.
- [ ] Unlink removes secrets, not unrelated console history.
- [ ] Sensitive IDs and provider tokens never enter diagnostics by default.

## 19. Worked synthetic timelines

### A — Stable awake samples, bounded continuity

```text
10:00:00 AWAKE, accepted
10:00:30 AWAKE, accepted
10:01:00 AWAKE, accepted
```

If the selected maximum gap is at least 30 seconds, propose bounded awake continuity of 60 seconds (`[10:00:00,10:01:00)`). This is **interval-based evidence accounting**, not proof of physical continuous observation. One session and three checkpoints, not three sessions.

### B — Awake, 8-minute network loss, awake

```text
10:00:00 AWAKE
10:00:30 AWAKE
10:08:30 AWAKE
```

With a maximum continuity gap less than eight minutes, count the first 30 seconds only; mark `[10:00:30,10:08:30)` as unobserved; start a fresh segment at 10:08:30. Never silently add eight minutes.

### C — Awake then standby at next poll

```text
10:00:00 AWAKE
10:00:30 STANDBY
```

The physical transition occurred somewhere between the samples. Proposed conservative counter does **not** allocate the full 30 seconds to awake or standby; the transition interval is uncertain. Reporting “the console switched at exactly 10:00:30” would conflate detection with physical event.

### D — Two consoles and one PSN account

```text
Console A: 10:00 AWAKE -> 10:01 AWAKE
Console B: 10:00 AWAKE -> 10:01 AWAKE
PSN account X: reports title Y on PS5 at 10:00:30
```

Console totals: A 60 bounded seconds, B 60 bounded seconds (120 summed resource-seconds). User X game duration on **either physical console** is unknown/ambiguous; don't record two separate confirmed 60-second player sessions.

### E — HA crash and stale backup

```text
11:00:00 AWAKE observed
11:00:30 AWAKE checkpoint committed
11:20:00 HA crashes/restarts
11:21:00 first new AWAKE sample
```

Only the interval from 11:00 to 11:00:30 is bounded by accepted samples under the policy. Recovered old session ends at 11:00:30 and new segment starts 11:21:00. Do not count 20.5 minutes while unobserved.

## 20. Open decisions and approval checklist

- [ ] Accept preferred option C: bounded evidence intervals with explicit unknown gaps.
- [ ] Select exact terminology for “bounded observed” versus “confirmed/estimated” durations in both backend and UI.
- [ ] Choose and justify initial per-source maximum continuity thresholds (not automatically the old 90 seconds).
- [ ] Decide whether changed-state transition gaps contribute zero to conservative accounting or are shown as ranges.
- [ ] Decide whether optional estimated/interpolated totals are included in initial release (recommended: **no**).
- [ ] Specify whether local “gaming time” is only reported when account/title/console attribution is sufficiently supported, or whether a separate inferred metric can be shown.
- [ ] Confirm duration data type/precision and rounding rules.
- [ ] Decide config-entry and persistence ownership (ADR-0004/0008).
- [ ] Define source event key/generation and database transaction semantics.
- [ ] Confirm timezone selection and weekly calendar convention.
- [ ] Approve statistics and endpoint names, session count/active-day semantics.
- [ ] Decide data retention, correction policy, export and per-user unlink behavior.
- [ ] Verify hardware/sample cadence and network failure behavior in Home Assistant OS.
- [ ] Approve or reject storage and migration design independently of this accounting ADR.

**Provisional recommendation:** Choose conservative, bounded, evidenced time accounting as the authoritative default. Keep optional inferred player/game time and Sony provider-reported lifetime time separate; do not present long periods of silence as measured gaming. This ADR is not yet accepted.

## 21. Sources and related documents

### Internal architecture
- [ADR-0004 — Identity and multi-console ownership](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 — Observation and state reconciliation](ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0003 — Provisional persistence](ADR-0003-persistence-provisional.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)
- [Protocol 02 — Console status](../protocols/02-console-status.md)
- [Protocol 07 — Remote Play commands](../protocols/07-remote-play-commands.md)
- [Protocol 08 — PSN authentication](../protocols/08-psn-authentication.md)
- [Protocol 09 — PSN presence](../protocols/09-psn-presence.md)
- [Protocol 10 — Game metadata](../protocols/10-game-metadata.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

### Legacy audit
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/session_tracker.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/models.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/usage_statistics.py

### Official Home Assistant references
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://developers.home-assistant.io/docs/integration_fetching_data/
- https://www.home-assistant.io/integrations/recorder/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://www.home-assistant.io/common-tasks/general/backups

**Outcome:** A detailed proposed multi-console session ledger, temporal uncertainty policy, statistics and tests are documented; no code, schema, real account or console validation was performed.

## Historical monitoring independence — Core 2026.11 research checkpoint (2026-11-05)

The [multi-console ConfigEntry/coordinator audit](../research/ha-core-2026-11-multi-console-runtime-source-audit.md) and [SPEC-008](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md) add a requirement to ADR-0006: multi-year session evidence must not stop merely because the HA sidebar is closed or a power sensor is disabled. Core's normal DataUpdateCoordinator periodic refresh is listener-dependent; the source collection owner must have an explicit ConfigEntry lifetime, disabled-polling behavior and one probe lane per physical console.

If a user disables automatic polling, HA stops, the console becomes unreachable or the durable writer fails, session continuity must conservatively stop at the most recent persisted checkpoint or mark a gap under the approved policy. No time may be backfilled on reconnection. Monitoring cadence, source TTL and session continuity gap are separate quantities and still require real measurement. No ledger algorithm or storage choice was implemented by this research.


## Crash recovery and ambiguous COMMIT acknowledgement research — 2026-11-06

**Status unchanged: PROPOSED, no tested claims.** See [recovery source audit](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md) and [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md).

- An accepted LAN sample and an **authoritatively committed historical duration** are different facts. Persist observation UUID, accepted source evidence, bounded segment/gap revisions, per-owner checkpoint and global durable cursor atomically.
- A caller losing COMMIT acknowledgement after successful commit must query for the original observation UUID and reuse its receipt; never repeat an additive "seconds" update under a new ID for the same observation.
- After unexpected restart, initialize a new runtime generation; older monotonic timestamps cannot be subtracted across process lifetimes. Existing previous-run segments close only at last durably supported evidence and leave an UNKNOWN gap until newly observed evidence.
- An older backup, even if internally consistent, has historical coverage only until its committed cursor. The restored-to-new-session gap is unknown; do not claim that a console continued gaming while Home Assistant was absent or after the old backup was made.
- Forward/backward UTC clock adjustments and new physical identity at an old IP require uncertainty/identity handling rather than false elapsed time. Derived daily/weekly/monthly sums continue to use half-open intervals and deterministic union/deduplication.
- Archived but unconfigured consoles may have readable historical reports only under an explicitly approved archive-access policy. No runtime monitoring or control is implied by an archival record.


## Archive-only reports and configuration restore boundary — 2026-11-06

See [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md), [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) and [storage/restore audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md). A logical Hub/Archive entry, if approved, permits authorized bounded SQL reports without any console monitor. Its existence never proves the retained historical power/game status is fresh; archive stats refer only to committed segments and coverage.

Restoring old HA config can overwrite local ledger history, while an external ledger may survive and conflict with old physical-console associations. Missing post-backup or post-restore observations must remain UNKNOWN, and source generations/ledger identity must be validated before resuming attribution. Historical rows remain owned by canonical physical/account IDs, not the current HA Config Entry ID or the Hub entry. ADR remains PROPOSED and no actual restore evidence was produced.
