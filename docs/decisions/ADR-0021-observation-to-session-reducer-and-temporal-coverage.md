# ADR-0021 — Observation-to-session reducer, bounded temporal coverage and provenance

**Status:** PROPOSED / MAINTAINER SIGN-OFF OPEN / NOT IMPLEMENTED
**Date:** 2026-11-06
**Research:** [Source-backed observations-to-sessions audit](../research/observations-to-sessions-temporal-reducer-source-audit-2026-11.md)
**Verification:** [SPEC-021 — 96 NOT_RUN scenarios and 24 OPEN gates](../specifications/SPEC-021-observation-to-session-state-machine-and-replay.md)
**Upstream contract:** ADR-0004 identity, ADR-0005 observation envelope and reconciliation, ADR-0006 time accounting, Protocols 01–10.
**Downstream contract:** ADR-0020 v1 logical SQLite schema, ADR-0015–0018 generation/worker/recovery, HA entity and sidebar reports.
**Release guard:** Documentation on main only; no DDL, code or tests.

> Product-level Hub/Archive architecture in ADR-0011 is ACCEPTED. This ADR is **not** automatically accepted by a request to investigate/document. No migration of the never-deployed synthetic develop database is applicable.

## 1. Problem and decision boundary

How can one canonical physical PlayStation's sparse network observations produce reproducible activity durations and gaps without fabricating physical transitions, merging PSN accounts into hardware identity, duplicating sessions on retries, or losing data after crashes?

**Evidence boundary:** A poll returns a state sample, not a continuous time trace. Sony's LED definition is separate from the LAN wire mapping; PSN exposes account-level activity and never universally proves which console is active. An elapsed duration calculated from compatible repeated samples is a **bounded accounting inference**, not verified continuous play.

## 2. Options

| Design | Advantages | Weaknesses | Outcome |
| --- | --- | --- | --- |
| A. Latest state continues indefinitely | Easy growing counters | Hours invented during network/HA outage | REJECT |
| B. Transition at new sample, attribute all time to preceding state | Simple reducer | Invents exact boundary and state between samples | REJECT for authoritative history |
| C. Two compatible point samples cover a bounded interval, changes/gaps become UNKNOWN | Conservative, replayable, auditable | May underestimate time and show uncertainty | PREFERRED / PROPOSED |
| D. No interpolation; only exact samples | Maximum epistemic purity | Point samples yield zero duration permanently | ALTERNATIVE for strict lower bound |
| E. Merge PSN/game activity into console sessions | Simple UI | False device attribution and double counting | REJECT |
| F. Independent estimated game view with confidence and versioned policy | Useful user-facing insights | Needs additional approval and method | FUTURE / OPTIONAL |

## 3. Recommended core rules (technical proposal)

**ADR21-R01 — Distinct axes.** Physical power sample, physical coverage, PSN provider presence, title attribution, source health and ledger capability are independent. Do not project them as a single online boolean.

**ADR21-R02 — Evidence point.** First valid AWAKE/STANDBY sample at T creates an anchor, with duration zero. It cannot backfill earlier unknown time. Recognized physical states require Protocol 02 wire fixtures.

**ADR21-R03 — Continuity.** A second compatible, later sample with same state/owner/source, no break and elapsed time <= approved B can cover half-open interval [T0,T1); label this BOUNDED_CONTINUITY. B is unset until actual cadence validation.

**ADR21-R04 — Change.** If samples at T0/T1 disagree, terminate old covered segment at its last checkpoint T0; mark [T0,T1) UNKNOWN; new state anchors at T1. Physical transition point is unknown, not at T1 by proof.

**ADR21-R05 — Failure.** Timeout, unknown status, outdated packet, 403/429 and lost network are source/availability events, NOT physical OFF. Expiration halts future accrual; no unobserved extrapolation. Conservative default breaks continuity after a failed attempt.

**ADR21-R06 — Restart/restore.** Reconcile old open segments at last committed checkpoint, fence old run/generation; first new observation after restart starts new anchor. Follow ADR-0015–0018 authority gates, NEVER silently create an empty history or merge backup and live cursors.

**ADR21-R07 — Strict identity.** Per-console reducer keyed by validated immutable physical owner. No DHCP IP, account display name, platform PS5, HA entity ID or game title display string as substitute. PSN account fact remains account scoped.

**ADR21-R08 — PSN title accounting.** Provider title and presence are independent point samples. Default no durable per-console player/title seconds from PSN alone. Optional inferred view only under separately approved versioned policy; no provider lifetime total in local durations.

**ADR21-R09 — Idempotency.** Stable observation ID + digest with canonical namespace; identical replay returns original durable receipt, changed content under same ID is conflict. Late or cross-run callbacks cannot reopen prior histories.

**ADR21-R10 — Commit boundary.** Accepted sanitized observation, meaningful event, covered interval/gap, last source checkpoint and ledger cursor share one SQLite write transaction. Acknowledgement after verified commit only; ambiguous/cancelled COMMIT requires safe receipt reconciliation, not blind repeat.

**ADR21-R11 — Coverage exclusivity.** Within each physical console timeline, bounded awake, bounded standby and UNKNOWN coverage cannot overlap in time for the same exclusive scope. A per-console partial UNIQUE open-row index alone does NOT prevent closed-row overlaps.

**ADR21-R12 — Timing.** Use UTC integer microseconds, half-open intervals, process-local monotonic freshness and a versioned sampling policy. Timestamp of physical transition is not inferred from response reception. Quarantine clock reversals and suspicious jumps; use ZoneInfo for local reports.

**ADR21-R13 — No durable totals.** Daily/monthly totals are queries over covered committed segments. Caches carry cursor/ledger UUID/policy/timezone and are disposable. One console-hour metric is not PSN playtime or player/game-specific hours.

**ADR21-R14 — Multi-console isolation.** Many consoles may be sampled concurrently; each owner reducer is causally serialized and commits through one shared ledger writer. Removing a Config Entry does not cascade-delete owner history. Two awake consoles may yield two hours in one hour of wall time.

**ADR21-R15 — Degraded mode.** If global writer is FENCED or RECOVERY_HOLD, source-only status may be presented as UNSAVED if approved, never masquerading as saved session time. No frontend/home-assistant property getter performs SQL/network work.

**ADR21-R16 — Auditability.** Persist source/evidence references and policy version needed for deterministic rebuild; corrections must be separately versioned/audited. A read report sees one consistent committed ledger snapshot (owner, generation, cursor, intervals).

## 4. Proposed deterministic transition contract

| Old accepted point -> new input | Session effect | Confidence |
| --- | --- | --- |
| NONE -> AWAKE | New 0-length AWAKE anchor | Point observed only |
| AWAKE -> AWAKE within B, no break | Cover [old,new) as AWAKE | Bounded inference |
| STANDBY -> STANDBY within B, no break | Cover [old,new) as STANDBY | Bounded inference |
| AWAKE -> STANDBY | Close awake coverage at old checkpoint; UNKNOWN between; new standby anchor | Both endpoints observed, transition unknown |
| STANDBY -> AWAKE | Close standby at old checkpoint; UNKNOWN between; new awake anchor | Both endpoints observed, transition unknown |
| State -> timeout | No POWER_OFF; break continuity; no new duration | Last known may display stale |
| State -> same state after long gap/restart | UNKNOWN gap and new anchor | No retroactive accumulation |
| Any -> PSN game | Provider-account report only | Local device assignment unknown |
| Any -> duplicate ID/digest | Return old receipt | Exactly once logical effect |
| Any -> wrong owner/old generation | Reject for history | Integrity preserved |

**Synthetic fixture:** 10:00 AWAKE, 10:00:30 AWAKE, 10:01 STANDBY, 10:01:30 STANDBY, 10:02 timeout, 12:00 AWAKE, 12:00:30 AWAKE => **60 seconds bounded awake** (assuming B >= 30s); 10:00:30–10:01 UNKNOWN and 10:01:30–12:00 UNKNOWN. No claim of 2h gameplay.

## 5. Data contracts / effects on ADR-0020 v1 schema

No 13th core table is mandated at this stage. Review whether ADR-0020's 12 logical tables can represent:

1. Sampling policy version B, source-specific timing/precision and exact provenance of the two boundary observations.
2. Owner/source/coverage-scoped checkpoints, break reasons and isolated run/generation fences.
3. The difference between first point anchor (zero duration), bounded covered segment, and open/closed UNKNOWN intervals.
4. Source attempt failures and health markers without pretending they are valid power samples.
5. Independent PSN/account/title snapshots and inferred/manual associations, never multiplied into physical console use.
6. An immutable observation digest, terminal receipt, committed cursor and consistent report snapshot.

Physical DDL and indexes require explicit review and tests. Cross-row overlap must be prevented by reducer transaction plus invariants, and verified with query-based audits. Never store credentials in observations.

## 6. Risk and mitigation register

| Risk | Mitigation / gate |
| --- | --- |
| LAN status code interpreted incorrectly | Protocol 02 firmware fixtures before implementation |
| False minutes between sparse observations | Strict bounded model, discontinuity UNKNOWN, public completeness |
| Poll jitter / timeout during short network loss | Calibrate B and failed-probe break policy |
| Clock jumps / ambiguous event timestamps | UTC + monotonic per process; quarantine anomalies |
| PSN user/console conflation | Independent provider account timeline; attribution opt-in only |
| Repeated/late request overwrites history | Owner/run/generation ordering, id/digest receipts |
| SQLite uncertain COMMIT or unsafe WAL version | ADR-0015–0017 worker proof, exact runtime gate |
| Backup restoring older metadata than ledger | Recovery authority and generation reconciliation |
| HA entity removed, listener count drops | Explicit entry-owned monitor lifecycle (SPEC-008) |
| History archived but no console configured | Persistent Hub/Archive entry (ADR-0011) |
| Daily totals change across DST | UTC clip after IANA timezone resolution |
| Too much history / replay storage | Retention/schema/index design and 36-month synthetic workload |

## 7. Acceptance dependencies and explicit open decisions

- Approve (or modify) strict two-point BOUNDED_CONTINUITY and UNKNOWN gap default.
- Agree a **versioned budget B** based on actual LAN/PSN polling behavior, not old develop 90s.
- Confirm precise timer sample anchor: response receipt versus bounded request window, latency and clock-step policy.
- Decide policy for one or more failed attempts between two compatible successful samples.
- Verify physical status parsing and source identity with actual console/firmware.
- Reconcile whether game sessions can ever be CONFIRMED without a directly verified local source.
- Fix storage worker terminal-proof, restore safety, uncertain COMMIT and linked SQLite gates.
- Approve additional schema columns/constraints only after test design, not as assumed existing DDL.
- Set user-facing statistics and interval-quality labels and coverage/uncertainty reporting.
- Review replay and policy-evolution spec before any implementation.

Each item is tracked in SPEC-021 as OPEN; user instruction to document/investigate does not constitute test evidence.

## 8. Decision status and next work

**PREFERRED MODEL — NOT YET APPROVED.** This ADR refines, rather than supersedes, ADR-0005, ADR-0006 and ADR-0020. It never applies legacy develop schema/data. Nothing was deployed or tested.

**Next priority:** source-backed deterministic replay, correction/versioning, policy evolution and crash-boundary/restore simulation (candidate ADR-0022/SPEC-022), before closing SQLite physical DDL.

## 9. Sources

- [Research audit](../research/observations-to-sessions-temporal-reducer-source-audit-2026-11.md)
- [SPEC-021](../specifications/SPEC-021-observation-to-session-state-machine-and-replay.md)
- [ADR-0005](ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006](ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0020](ADR-0020-greenfield-sqlite-v1-data-model.md)
- https://www.playstation.com/en-gb/support/hardware/ps5-ps4-power-indicator-lights/
- https://www.home-assistant.io/integrations/playstation_network/
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/isolation.html
- https://www.sqlite.org/wal.html
- https://docs.python.org/3.14/library/time.html
- https://docs.python.org/3.14/library/zoneinfo.html

**Outcome:** Proposed decision only. No software, DDL, schema migration, database, CI, fixture, or executable test created.

## 10. New LAN title evidence from upstream source audit (2026-11-06)

A detailed comparison of [Chiaki-ng's discovery parser](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L115-L135) and [playactor's `extras` model](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L115-L126) shows optional LAN headers `running-app-titleid` and `running-app-name`. See [complete upstream audit](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md). These are source code observations, NOT verified PS5 hardware behavior.

**Proposed source-family amendment:** An accepted, verified physical console's status response may yield a separate `LAN_RUNNING_APP` candidate title observation alongside a `LAN_STATUS` power sample. Missing, empty, malformed, unknown namespace and stale app fields must remain distinct. Do not let provider-account PSN presence automatically override this local source field, or infer the PSN player from the local title. Do not accumulate confirmed per-game duration without on-device semantics, foreground/background tests, bounded same-source point continuity, power-state constraints and source-specific policy approval.

**Potential impact:** This opens a LAN-only title metadata route and removes a false assumption that all displayable games require optional Sony PSN calls; it does not guarantee that a console will send the headers, or that they are equivalent to active gameplay. The model of 12 logical SQLite tables remains PROPOSED and should allow adding an optional source-specific app/title payload without mixing user/account identities. No implementation authorized or tested.

## 11. Discovery app fields are point samples, not playable-time proof (2026-11-06)

[Second upstream source audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) further strengthens the possibility of a console-scoped `LAN_RUNNING_APP` sample, but **does not demonstrate exact foreground gameplay time** or identity of the user. Chiaki-KM uses local app metadata to choose input profiles; this shows a real software consumer, not a verified PlayStation Hub session reducer. A repeated title with approved continuity can at most become `bounded_reported_app_duration` under an independently tested title-scoped policy. Never automatically conflate it with `player_game` or subtract it as a guaranteed subset of physically awake time.

Source break/timeout, unknown code, missing metadata, restart, policy change or app switch must create UNKNOWN/uncertain title coverage rather than fabricate exact switch instant. The existing 96 SPEC-021 cases remain planned/unrun. Unlike the PS5-MQTT UI state publication, the PlayStation Hub's entry-owned monitor must admit explicit compatible same-state samples/checkpoints for credible duration accounting, even if the HA entity value remains unchanged.

## 12. Bounded duration cannot assume UDP poll-response causality (2026-11-06)

[Deep first-party DDP wire audit](../research/lan-ddp-wire-and-temporal-correlation-audit-2026-11-06.md) found no on-wire request ID/nonce in inspected SRCH messages and no guarantee that a response received within one local poll window actually originated in that poll. Local \`request_generation\` tags and fencing protect our callbacks, **not the age/source authenticity of the datagram itself**.

Consequently an accepted 200/620 is a *time-of-receipt* source report, with quality \`WINDOW_ASSOCIATED_UNVERIFIED\`, not an exact physical state time. Two compatible points can form versioned **bounded inference only** within approved cadence/continuity budget B; packet delay, protocol ambiguity, identity conflict or uncertain timing must not be silently converted to measured time. A source gap stays UNKNOWN, a command send does not prove a state and no local title metadata proves human gameplay.

Chiaki's source updates per-host last-ping position even on unchanged observations but only emits visible callbacks for changed fields. Therefore repeated same-state points must feed the history ledger independently of entity/UI events; no need to publish all heartbeats to every entity listener. This is an epistemic refinement, not a physical schema change or executable code authorization.
