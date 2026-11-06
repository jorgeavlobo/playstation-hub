# SPEC-021 — Observation-to-session reducer, uncertainty, idempotency and replay-readiness

**Date:** 2026-11-06
**Status:** PROPOSED / ALL_96_CASES_NOT_RUN / 24_GATES_OPEN_OR_BLOCKED / NO_CODE
**Research:** [Observation-to-session source audit](../research/observations-to-sessions-temporal-reducer-source-audit-2026-11.md)
**Decision:** [ADR-0021 PROPOSED](../decisions/ADR-0021-observation-to-session-reducer-and-temporal-coverage.md)
**Baseline:** HA Core 2026.11.0 research pin; runtime SQLite, linked library, worker and actual PS5 firmware remain untested.
**Lineage:** New PlayStation Hub only; synthetic never-deployed develop database and SPEC-019 retirement are not part of testing.

> All scenarios below are planned acceptance descriptions, NOT executable test code, passed checks, synthetic fixtures already built, SQL schema, a real console capture, or evidence of API authorization. A nominal test requires a future deterministic fixture and assertions under the agreed policy. No B continuity budget has been chosen.

## 1. Acceptance model and definitions

- One valid state sample gives an observed **point**, not positive duration.
- Two compatible same-state points may yield `[T0,T1)` bounded continuity only with an approved maximum B, no broken source continuity and correct identity/generation.
- Different states, prolonged/untrusted gaps, unknown power, failed source health and restart cannot be silently allocated to either state; they produce explicit UNKNOWN.
- PSN presence, provider lifetime playtime and local physical console awake are separate metrics and owner scopes.
- Accepted observation, events, covered segments, gaps, source checkpoint and ledger cursor must be in a single durable transaction.
- Observations are identified by stable ID plus immutable digest. Same ID/same digest is an idempotent receipt; same ID/different digest is a conflict.
- Home Assistant entity current availability never substitutes for durable historical evidence. No physical OFF from a LAN timeout.
- All metrics are reproducible by intervals, policy version, UTC integer times, per-report IANA timezone and committed cursor.

## 2. Nominal acceptance catalogue — 96 future tests

### A — Sample normalization and source authority — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-A01 | First valid AWAKE observation | Create one zero-duration physical anchor; no pre-anchor time |
| OTS-A02 | First valid STANDBY observation | Create standby anchor without previous awake history |
| OTS-A03 | LAN 620 standby parsing | Require Protocol 02 source-validated fixture, do not rely on LED rule |
| OTS-A04 | Unrecognized but valid LAN code | Reachability may be known; physical mode UNKNOWN |
| OTS-A05 | Timeout without valid packet | No new OFF or STANDBY state; source health changes only |
| OTS-A06 | Malformed LAN response | Reject physical mode; sanitized error, no history mutation |
| OTS-A07 | Console identity mismatch at same IP | Reject source fact and privileged commands; no owner reassignment |
| OTS-A08 | PSN online while LAN STANDBY | Preserve physical standby; independent provider account view |
| OTS-A09 | PSN offline while LAN AWAKE | Preserve confirmed local awake sample |
| OTS-A10 | PSN title present without physical ID | Never create confirmed console-title duration |
| OTS-A11 | PSN private/403 response | Account visibility RESTRICTED; console timeline unchanged |
| OTS-A12 | PSN throttled/429 or timeout | Provider degraded, last-known stale; no local power mutation |
| OTS-A13 | Two consoles A and B reporting simultaneously | Separate source/owner entries; no global state overwrite |
| OTS-A14 | New DHCP address for same verified device | Retain canonical owner and historical continuity subject to ordering |
| OTS-A15 | Same IP reused by different console | Do not merge console histories or credentials |
| OTS-A16 | Remote Play command sent without observed confirmation | No invented AWAKE/STANDBY accounting transition |

### B — Temporal coverage and state machine — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-B01 | No prior sample -> AWAKE T0 | Point duration zero; historical start T0 |
| OTS-B02 | AWAKE T0 -> AWAKE T1 within B | Exactly [T0,T1) bounded awake once |
| OTS-B03 | STANDBY T0 -> STANDBY T1 within B | Exactly [T0,T1) bounded standby once |
| OTS-B04 | AWAKE T0 -> STANDBY T1 | UNKNOWN [T0,T1), new standby anchor T1 |
| OTS-B05 | STANDBY T0 -> AWAKE T1 | UNKNOWN [T0,T1), new awake anchor T1 |
| OTS-B06 | AWAKE T0 -> valid UNKNOWN T1 | UNKNOWN gap and no fictitious OFF; retain last-known |
| OTS-B07 | Same AWAKE state with elapsed > B | Gap UNKNOWN, no extra bounded awake |
| OTS-B08 | Same STANDBY state with elapsed > B | Gap UNKNOWN, fresh standby anchor |
| OTS-B09 | One failed poll between two successful same-state samples | Default continuity break, not interpolation over failure |
| OTS-B10 | Many consecutive failed polls | No repeated counting or duplicative gap rows |
| OTS-B11 | Failed poll followed by opposite state | Bracket UNKNOWN; neither direction time invented |
| OTS-B12 | First successful point after multi-hour loss | New anchor, preceding hours remain UNKNOWN |
| OTS-B13 | Zero-length repeated sample timestamp | No additional duration or extra session |
| OTS-B14 | Negative apparent timestamp ordering | Quarantine; no negative durations or ledger reset |
| OTS-B15 | Open UNKNOWN gap at report time | Do not count future/present unconfirmed duration; label open gap |
| OTS-B16 | Synthetic 10:00–12:00 worked example | Two valid 30s awake windows total 60s, not two hours |

### C — Idempotency, causal ordering and concurrency — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-C01 | Same observation ID/digest repeated | Return same committed receipt; no mutation |
| OTS-C02 | Same observation ID with new digest | Hard conflict; no update to immutable fact |
| OTS-C03 | Old request finishes after newer request | Newer accepted anchor not overwritten |
| OTS-C04 | Old run UUID callback after restart | Rejected and cannot reopen historical state |
| OTS-C05 | Old console Config Entry callback after unload | No writer or state resurrection |
| OTS-C06 | Callback from previous DB generation | Reject without touching selected ledger |
| OTS-C07 | Out-of-order PSN response | Account timeline handles sequence; physical timeline unaffected |
| OTS-C08 | Concurrent successful AWAKE samples same owner | Serialized single logical coverage outcome |
| OTS-C09 | Concurrent console A and console B ingestion | Separate timelines; shared ledger writer remains serialized |
| OTS-C10 | Duplicate event on replay with same derived key | No duplicate meaningful transition |
| OTS-C11 | Unchanged heartbeat | Advance coverage/checkpoint, no additional session start count |
| OTS-C12 | Observation ID collision across different sources | Scoped uniqueness validated, no false dedup or merge |
| OTS-C13 | Source generation counter restart | Run UUID/source-instance scoping prevents collision |
| OTS-C14 | Provider event timestamp earlier than receipt | Does not backdate physical console timeline |
| OTS-C15 | Idempotent repeated UNKNOWN closure | Gap remains single normalized interval |
| OTS-C16 | Policy version changes while a segment is open | Segment closed at committed boundary, subsequent version explicit |

### D — SQLite atomicity, receipts and writer lifecycle — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-D01 | Accepted sample transaction | Observation, events, coverage, checkpoint and cursor commit together |
| OTS-D02 | Failure before COMMIT | No durable cursor or partial segment advancement |
| OTS-D03 | SQLITE_BUSY | Retry/fail boundedly without success receipt or double write |
| OTS-D04 | SQLITE_FULL | Record durability fault, no imaginary saved time |
| OTS-D05 | SQLITE_READONLY | Deny write, preserve old generation and cursor |
| OTS-D06 | SQLITE_IOERR | No silent reset to empty database |
| OTS-D07 | COMMIT acknowledged | Publish cursor-matched durable projection only after success |
| OTS-D08 | COMMIT may have succeeded but caller cancelled | Reconcile ID/digest via verified worker before retry |
| OTS-D09 | Same receipt persisted but caller timed out | Retry returns original cursor, no double seconds |
| OTS-D10 | Reader during pending writer transaction | Reader never sees half-completed segment/checkpoint |
| OTS-D11 | Report mixes metadata and intervals | Single coherent read snapshot or explicit rejection |
| OTS-D12 | Foreign key disabled on reader | Connection admission must reject/repair per policy before trusting data |
| OTS-D13 | Closed segment overlaps same console exclusive scope | Reducer reject or consistently normalize, verify SQL invariants |
| OTS-D14 | Two open AWAKE rows for same console | Constraint/reducer prevent duplicate open exclusive coverage |
| OTS-D15 | RECOVERY_HOLD source-only observation | UNSAVED live status only, no historical write |
| OTS-D16 | Global SQLite worker closure in progress | Fence new observations, no late write/cutover |

### E — Runtime, crash, restart, archive and restore — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-E01 | Dashboard opened twice | No duplicate source poller or historical session |
| OTS-E02 | Final HA entity listener removed | Entry-owned monitor still observes if configured |
| OTS-E03 | Single console entry unloaded | Its source stops, other console monitors unaffected |
| OTS-E04 | Hub entry without any console | Archive access with no phantom physical observation |
| OTS-E05 | Graceful shutdown after last committed AWAKE | Stop at last committed checkpoint, not shutdown wall clock |
| OTS-E06 | Unexpected HA crash with open segment | Idempotently recover to last persisted checkpoint |
| OTS-E07 | New boot after 6 hours downtime | Six-hour interval UNKNOWN until fresh sample |
| OTS-E08 | Crash during ambiguous COMMIT | Digest/receipt reconciliation, no duplicate credits |
| OTS-E09 | Old generation callback during promotion | Fenced and rejected |
| OTS-E10 | DB worker fails terminal close proof | No unsafe reopening or DB-generation switch |
| OTS-E11 | HA OS backup with live DB/WAL and snapshot | Treat restored mixed content as provenance risk, not automatic trusted ledger |
| OTS-E12 | Restore of older backup cursor | No silent merge with newer live lineage |
| OTS-E13 | Restored config entry conflicts with ledger UUID | RECOVERY_HOLD and administrator review |
| OTS-E14 | Missing DB file on known installation | No create-on-open, preserve recovery diagnostics |
| OTS-E15 | Open session after restore to new generation | No time backfilled across restore boundary |
| OTS-E16 | Console Config Entry removed with archived facts | History retained; reports still accessible via Hub entry |

### F — Attribution, reports, privacy and edge conditions — 16 NOT_RUN

| ID | Scenario | Expected invariant |
| --- | --- | --- |
| OTS-F01 | One PSN account active across two consoles | No automatic physical-device attribution |
| OTS-F02 | One console AWAKE without PSN account | Valid local console coverage, no player required |
| OTS-F03 | Provider reports different game after poll | Title switch bracket uncertain, not timestamp exact |
| OTS-F04 | PSN no-title list | No assumption console OFF or game stopped |
| OTS-F05 | Provider lifetime playtime present | Do not add to local bounded duration |
| OTS-F06 | User links account to console | Link alone creates no confirmed player-game sessions |
| OTS-F07 | Change game display name or cover | Historical IDs and durations unchanged |
| OTS-F08 | Two consoles awake same wall hour | Two device-hours allowed; union-of-wall-clock distinct |
| OTS-F09 | UTC half-open midnight boundary | No duplicate or missing microsecond at adjacent windows |
| OTS-F10 | Europe/Lisbon spring DST transition | Correct 23-hour local day via UTC window |
| OTS-F11 | Europe/Lisbon fall DST transition | Correct 25-hour local day via UTC window/fold |
| OTS-F12 | Leap day monthly report | No fabricated/missing daily minutes |
| OTS-F13 | Zero activity with full coverage vs no coverage | Different report completeness and explanation |
| OTS-F14 | Time zone or policy changed after history | Versioned report interpretation; no silent source history rewrite |
| OTS-F15 | Source title/account/user identifiers in diagnostics | Privacy-safe redaction, no tokens or secrets |
| OTS-F16 | 36-month multi-console workload | Deterministic totals, documented query plan and performance budget |

## 3. Cross-suite replay fixture — planned, NOT_EXECUTED

Use synthetic timestamps and **only for this fixture** assume B >= 30 seconds:

| UTC point | Input | Expected physical coverage delta |
| --- | --- | --- |
| 10:00:00 | AWAKE valid | Anchor only, +0 seconds |
| 10:00:30 | AWAKE valid | Bounded AWAKE +30 seconds |
| 10:01:00 | STANDBY valid | UNKNOWN +30 seconds; no AWAKE from 10:00:30 |
| 10:01:30 | STANDBY valid | Bounded STANDBY +30 seconds |
| 10:02:00 | Poll timeout | Break, no OFF and no counted time |
| 12:00:00 | AWAKE valid | UNKNOWN [10:01:30,12:00:00); new anchor |
| 12:00:30 | AWAKE valid | Bounded AWAKE +30 seconds |

**Assertions:** bounded awake 60 seconds, bounded standby 30 seconds, unknown 30 seconds plus 1h58m30s; no game-specific confirmed seconds; at most one exclusive physical classification per [start,end); no extrapolation beyond last committed checkpoint. The 10:02 failed poll may create a health event but cannot count an OFF observation.

Derive exact integer microseconds using UTC conversion, not floating-point summation. Replay the same accepted observation sequence with the same policy+input IDs and compare normalized segment/event/cursor results modulo explicitly non-deterministic metadata that must not affect reports. Repeat with out-of-order response arrival, restarts, interrupted COMMIT receipts, two consoles, one PSN account, backup restore hold, and local DST windows.

## 4. Gate register — 24 OPEN or BLOCKED

| Gate | Required proof or maintainer decision | Current state |
| --- | --- | --- |
| OTS-G01 | Maintainer approves bounded two-point evidence model | OPEN |
| OTS-G02 | LAN awake/standby mapping validated with real firmware fixture | BLOCKED_HARDWARE |
| OTS-G03 | Canonical physical console identity validated | BLOCKED_HARDWARE |
| OTS-G04 | Sample anchor timestamp and latency decision | OPEN |
| OTS-G05 | Continuity budget B calibrated and policy versioned | OPEN |
| OTS-G06 | Failure attempt marks continuity-break policy approved | OPEN |
| OTS-G07 | Long-gap and still-open UNKNOWN representation approved | OPEN |
| OTS-G08 | Exclusive interval closure/overlap invariants proven | NOT_RUN |
| OTS-G09 | Source/owner/run/generation ordering and dedup proven | NOT_RUN |
| OTS-G10 | Atomic observation/event/segment/checkpoint/cursor commit proven | NOT_RUN |
| OTS-G11 | Ambiguous COMMIT receipt reconciliation proven | BLOCKED_SQLITE_WORKER |
| OTS-G12 | Linked SQLite version, WAL bug and durability configuration checked | BLOCKED_HA_OS |
| OTS-G13 | Reader snapshot and report cursor coherence checked | NOT_RUN |
| OTS-G14 | Worker terminal proof, fence and generation lease checked | BLOCKED_SQLITE_WORKER |
| OTS-G15 | Backup/restore selected-generation provenance tested | BLOCKED_HA_OS |
| OTS-G16 | Home Assistant listener-independent monitor lifecycle tested | NOT_RUN |
| OTS-G17 | PSN permissions, privacy, supported data and title IDs verified | BLOCKED_PROVIDER |
| OTS-G18 | Default no-automatic device/title attribution approved | OPEN |
| OTS-G19 | Per-console/account/title/all-consoles reporting scopes approved | OPEN |
| OTS-G20 | Timezone/DST/report completeness verified | NOT_RUN |
| OTS-G21 | No credential persistence/privacy/retention checks passed | NOT_RUN |
| OTS-G22 | 36-month synthetic workload and query indexes tested | NOT_RUN |
| OTS-G23 | Deterministic correction/replay and policy-version plan defined | OPEN_NEXT_RESEARCH |
| OTS-G24 | Full implementation/DDL authorization and all acceptance tests executed | NOT_AUTHORIZED |

## 5. Release acceptance / evidence tracking

A scenario is not PASSED until future implementation tests have fixture input, expected ledger mutation (or explicit zero mutation), stable policy version, exact SQLite cursor/receipt assertion, expected frontend projection, code location, execution environment and traceable CI result.

Keep **source-derived, project-proposed, hardware-verified and execution-verified** classifications separate. A source audit is not implementation evidence. Do not auto-approve DDL because 12 logical tables and a transition table are described.

For every test case that changes data, assert invariants on both current state and committed ledger, including the old-generation rejection path. Cross-row exclusive coverage overlap cannot be proven by a single CHECK/UNIQUE constraint. Explicitly test failure injection at pre-commit, post-dispatch/pre-acknowledgement and recovery boot.

No application or testing files should be added until the maintainer explicitly authorizes implementation; this specification is purely Markdown.

## 6. Decisions needed before implementation

1. Confirm default conservative bounded continuity, explicit UNKNOWN coverage and source-failure break.
2. Validate real device status mapping, identity and requested/received timestamp semantics.
3. Approve B and session-policy versioning after calibration, **not** the old develop 90-second value.
4. Approve event/segment/gap physical schema and proof of one single ledger worker.
5. Test crash/restore/worker/SQLite runtime constraints from SPEC-009–018 and 020.
6. Decide how inferred console-title time will be presented separately, respecting PSN permission gates.
7. Complete next replay/correction/policy-evolution research before claiming replay-ready reproducibility.

## 7. Source references

- [Full 2026-11-06 source audit](../research/observations-to-sessions-temporal-reducer-source-audit-2026-11.md)
- [ADR-0021](../decisions/ADR-0021-observation-to-session-reducer-and-temporal-coverage.md)
- [ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md)
- https://www.playstation.com/en-gb/support/hardware/ps5-ps4-power-indicator-lights/
- https://www.home-assistant.io/integrations/playstation_network/
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/isolation.html
- https://www.sqlite.org/foreignkeys.html
- https://www.sqlite.org/wal.html
- https://docs.python.org/3.14/library/time.html
- https://docs.python.org/3.14/library/zoneinfo.html

**Final checkpoint:** 96 case descriptions, 24 gates, 0 RUN/PASSED; new greenfield application only. No executable code, database, SQL migration, hardware test, simulation, or PSN request performed.

## Source-triangulation refinement: no change-only history and no speculative game sessions (2026-11-06)

[Second pinned upstream audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) demonstrates that PS5-MQTT's `check-devices-state.ts` suppresses HA publication for a healthy device with unchanged reported state; history cannot rely on this UI/MQTT change-only stream to prove repeated samples. Entry-owned LAN monitoring must produce independently accepted observations/heartbeats for bounded temporal continuity even when entity-visible state doesn't change.

Potential `LAN_RUNNING_APP` metadata from Chiaki-ng, PS5-Wake C and older pyremoteplay is an **observation candidate** whose data semantics and firmware support need validation; it does not automatically establish that a game is foreground or being played. Keep account/provider-derived titles separate. Use the existing temporal invariants (no interpolation over failed polls, changed title -> transition bracket UNKNOWN, unvalidated header absence != no game) to govern any later title-specific policy. Source trace IDs SRC-HIST-01 and SRC-HIST-02 in the research are review references, not two new executable tests now; the existing 96 scenarios remain all NOT_RUN.

## UDP temporal-quality uncertainty: source generation is not a Sony response nonce (2026-11-06)

[New DDP wire audit](../research/lan-ddp-wire-and-temporal-correlation-audit-2026-11-06.md) establishes that inspected SRCH requests contain no request ID/nonce or timestamp echo. Therefore in-process \`request_generation\` is an ordering and callback-fencing helper, **not hard evidence of exact causal response age**. A delayed UDP response can arrive during a new scanner's reception window; it remains \`WINDOW_ASSOCIATED_UNVERIFIED\`. Status 200/620 at reception is still a bounded source report, and session intervals remain inferred between compatible points, not measured physical uptime. Unknown timing/identity and source failures must not extend history.

The Chiaki service's last-ping index changes on unchanged valid replies, while UI change notifications are sparse, as in PS5-MQTT. Future reducer tests must admit duplicate-looking *new* source points (different valid source observation IDs) as continuity checkpoints without incrementing session-start counts; repeated exact observation ID/digest remains idempotent, as before. All existing cases remain NOT_RUN. No executable code, historical data or DB DDL was altered.

## Foreground/game duration semantic limit — LAT trace supplement, NOT_RUN (2026-11-06)

The [LAN reported-app deep source study](../research/lan-running-app-identity-foreground-and-provider-boundary-2026-11-06.md) and [title evidence contract](../architecture/lan-running-app-evidence-and-title-identity-contract.md) add a crucial epistemic guard: Sony officially states some games pause behind Home, so \`LAN_DDP_RUNNING_APP\` point samples are **not** measured user playtime. In any future title-coverage projection, qualify metrics as bounded **reported-app coverage**, not \`PLAYER_GAME\`, \`ACTIVE_FOREGROUND\` or account hours without new independent source evidence.

**Qualitative future LAT cases:** A→B game transition between samples is UNKNOWN, A→header ABSENT does **not** prove ended/Home, A→explicit EMPTY is accepted only if firmware supports empty fields, A→same ID/different display name maintains title identity, two IDs/same title name remain distinct, 200 READY + title A while Home pauses A still cannot be called actual play. Failed polls/restarts preserve unknown gaps. No claims of tests run, no new SPEC number or SQL DDL.
