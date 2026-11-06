# SPEC-022 — Deterministic replay, corrections and crash-boundary acceptance

**Date:** 2026-11-06
**Status:** DOCUMENTED TEST DESIGN / 32 CASES NOT_RUN / 8 RELEASE EVIDENCE GATES / NO CODE
**Research:** [Replay/corrections source audit](../research/deterministic-replay-corrections-and-recovery-closure-audit-2026-11.md)
**Decision:** [ADR-0022 PROPOSED](../decisions/ADR-0022-deterministic-replay-and-versioned-corrections.md)
**Readiness / STOP rule:** [WP-00B](../architecture/WP-00B-research-freeze-and-implementation-readiness.md)
**Repository:** main documentation only; develop remains a never-deployed fictional prototype, not an importer.

> Deliberately concise implementation-stage test catalogue. We already have 934 enumerated earlier planned case IDs with overlap, none run; adding more documents is not a substitute for executing a small, representative automated suite. No fixture, script, SQL schema, worker or HA OS test is created by this spec.

## 1. Acceptance meaning

All tests currently have **status NOT_RUN**. Each becomes PASSED only with future code, reproducible fixture, exact source/policy fingerprint, expected ledger cursor and normalized intervals, execution version/environment and recorded CI or HA OS evidence.

Replay is a semantic comparison at a selected cursor and policy; it is not a statement that a Sony device physically remained awake between samples. Raw normalized accepted facts, source failures that break continuity, accepted order and policy versions must be sufficient to reconstruct coverage; otherwise mark NOT_REPLAYABLE.

## 2. Minimal future regression catalogue — 32 NOT_RUN

### A — Replay completeness, ordering and equivalence — 8 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| RP-A01 | Full normalized observation + policy history retained | VERIFY_REPLAY reconstructs equivalent event/segment/gap and cursor views |
| RP-A02 | Original payload digest retained but source fact deleted | Returns NOT_REPLAYABLE; no fabricated reconstruction |
| RP-A03 | Same accepted events replayed twice | Semantic intervals/gaps/report totals identical regardless runtime UUIDs |
| RP-A04 | Request completion order differs from accepted cursor order | Replay uses stored acceptance/source order and yields original result |
| RP-A05 | Failed-poll continuity break retained | Replay does not join otherwise compatible points across broken coverage |
| RP-A06 | Failed-poll break evidence not retained | Reject FULL_REPLAY scope or explain weaker checkpoint-only reproducibility |
| RP-A07 | Same ledger UUID/cursor but different event-content digest | Mismatch/lineage conflict; no false PASS |
| RP-A08 | Original source data preserved and derived segment modified incorrectly | Read-only verify detects discrepancy without changing live tables |

### B — Corrections, versions and privacy — 8 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| RP-B01 | Late physical observation arrives after committed cursor | Quarantine; no silent historic insertion or negative checkpoint movement |
| RP-B02 | Same observation ID different payload | Hard conflict; preserve original source fact |
| RP-B03 | User attributes PSN title to a console | USER_DECLARED/INFERRED revision only; never source-confirmed physical play |
| RP-B04 | Decoder bug found in previously admitted sample | Preserve original fact and decoder version, introduce audit revision |
| RP-B05 | Continuity policy B changes | Historical-as-recorded report stable; recomputed view labelled with new fingerprint |
| RP-B06 | Policy changes across segment boundary | No continuity interpolated across policy boundary by default |
| RP-B07 | Authorized correction rebuild preview rejected | No active history, cursor or policy change |
| RP-B08 | Privacy purge legally removes raw evidence | Historic full replay flagged NOT_REPLAYABLE rather than secreting deleted records elsewhere |

### C — Crash and generation failure injection — 8 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| RP-C01 | Crash after observation insert before segment update | No partial durable observation/segment/cursor |
| RP-C02 | Crash after interval changes before global cursor | Atomic rollback/recovery, no invisible extra time |
| RP-C03 | COMMIT submitted and caller acknowledgement lost | Reconcile durable receipt ID/digest before logical retry |
| RP-C04 | Crash during staging database build | Original generation still active; stage not mistaken for restored DB |
| RP-C05 | Crash after stage validation before pointer publication | Old pointer authoritative; journal reconciles safely |
| RP-C06 | Crash after new pointer publication before admin receipt | One active generation; operation receipt idempotently recovered |
| RP-C07 | Old worker has queued writes during attempted cutover | Refuse switch until positive terminal evidence |
| RP-C08 | Older HA backup config conflicts with newer ledger | Recovery Hold; no silent overwrite/merge or identity reauthorization |

### D — Reporting, isolation and authorization — 8 NOT_RUN

| ID | Scenario | Acceptance |
| --- | --- | --- |
| RP-D01 | Replay verify from read-only context | No mutation to selected ledger, Config Entry, live cursor or console |
| RP-D02 | Two simultaneous consoles with account presence | Separate device-hours; no PSN physical attribution by default |
| RP-D03 | DST spring/fall and leap-day report comparison | Same UTC interval clipping and policy fingerprint yields same report |
| RP-D04 | Different current labels or game covers | Historical IDs and activity intervals remain unchanged |
| RP-D05 | Snapshot read during concurrent admission | Compare consistent selected generation/cursor, not mixed records |
| RP-D06 | Unauthorized admin rebuild request | Server rejects before lease, staging or history mutation |
| RP-D07 | REBUILD after safe completed offline source audit | Reconciled policy/cursor and unique generation, original retained for recovery |
| RP-D08 | 36-month retained source data and many consoles | Bounded memory, measured performance budget and no duplicate report totals |

## 3. Go/no-go gates — 8 evidence groups

| Gate | Proof required | Ownership / status |
| --- | --- | --- |
| RP-G01 | ADR-0022 conceptual model decision and no auto-ADR policy | OPEN_MAINTAINER; NOT_VERIFIED |
| RP-G02 | Physical schema preserves replay-necessary normalized evidence, break markers, policy snapshots and corrections | WP-04; NOT_VERIFIED |
| RP-G03 | Per-source accepted ordering, immutable receipts and id/digest conflict tested | WP-03/WP-04; NOT_VERIFIED |
| RP-G04 | Recoverable writer, linked SQLite version, WAL and positive worker closure proven | WP-04_HA_OS; NOT_VERIFIED |
| RP-G05 | Crash/restore cutover, pointer/journal and source-lineage proofs passed | WP-04_HA_OS; NOT_VERIFIED |
| RP-G06 | User/admin correction preview, ACL and privacy retention proven | WP-05; NOT_VERIFIED |
| RP-G07 | No automatic console-game attribution from PSN plus provider authorization gate | WP-07; NOT_VERIFIED |
| RP-G08 | Core 2026.11+/release baseline and 36-month performance/report evidence recorded | WP-04/WP-08; NOT_VERIFIED |

## 4. Crash-proof method to implement later

All future SQLite fault scenarios must test at least: before BEGIN; after observation INSERT; after derived segments and before checkpoint; after COMMIT dispatch but before caller acknowledgement; during staging; after stage validation and before promotion; after pointer publication; after restart/restore. Use a **separate synthetic test ledger**, never a user's actual Home Assistant history.

For a generated test fixture, assert `accepted_observation_id + digest`, `ledger_uuid + generation_uuid + cursor`, canonical owner identity, segment/gap intervals and actual SQL integrity, not merely successful API status. Require explicit worker terminal evidence before database generation switching. The test runner must not silently delete journals while a connection may be open.

For reports, compare half-open UTC interval inputs to timezone-aware local day/week/month/year ranges (including Europe/Lisbon DST). Record initial and final cursor/policy, source facts and coverage quality.

## 5. Stop condition for further documentation

This is the **last scheduled new SPEC for the current pre-implementation research track**. Further acceptance scenarios belong as additions to existing SPEC-001–022 alongside actual code/test results, not by creating endless new SPEC IDs.

**Next action is not SPEC-023.** Follow WP-00B: approve a bounded LAN-first implementation baseline, select the release/tool versions, and move unresolved facts requiring live environment evidence into the relevant WP implementation test. Additional research is permitted only on a specific verified contradiction or newly requested capability.

## 6. References

- [Research audit](../research/deterministic-replay-corrections-and-recovery-closure-audit-2026-11.md)
- [ADR-0022](../decisions/ADR-0022-deterministic-replay-and-versioned-corrections.md)
- [WP-00B](../architecture/WP-00B-research-freeze-and-implementation-readiness.md)
- [SPEC-021](SPEC-021-observation-to-session-state-machine-and-replay.md)
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/lang_savepoint.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/isolation.html

**Outcome:** 32 planned tests, 8 evidence groups, none executed. No implementation, code, SQL, test file, credential or Home Assistant device was accessed.
