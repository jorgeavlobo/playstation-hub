# ADR-0022 — Deterministic replay, auditable corrections and versioned historical interpretation

**Status:** PROPOSED / DOCUMENTATION-LEVEL DESIGN FINISHED / NOT APPROVED OR TESTED
**Date:** 2026-11-06
**Research:** [Replay, corrections and recovery source audit](../research/deterministic-replay-corrections-and-recovery-closure-audit-2026-11.md)
**Acceptance:** [SPEC-022](../specifications/SPEC-022-replay-correction-and-crash-boundary-acceptance.md)
**Research exit:** [WP-00B](../architecture/WP-00B-research-freeze-and-implementation-readiness.md)
**Dependencies:** ADR-0005, ADR-0006, ADR-0015–0018, ADR-0020 and ADR-0021; no migration of the never-deployed develop fake SQLite data.
**Implementation:** None. Documentation on main only; physical SQLite schema and worker not selected.

## 1. Decision

Select the **following preferred design for explicit maintainer approval**:

1. Accepted observation facts are immutable, versioned and provenance-preserving, including normalized payload necessary for a future replay, not only digests or materialized session rows.
2. Sources and semantic interpretations are separate: provider account/title snapshots never automatically become physical-console gaming, and an observed point is not measured continuous time.
3. The deterministic reducer takes ordered accepted source facts, explicit recorded continuity-break inputs, selected owner/source generation, and a **versioned policy snapshot** and yields bounded coverage, UNKNOWN gaps and interpretable events.
4. Replaying the same committed input/correction stream under the same versioned interpretation yields semantically identical intervals, checkpoints and reports. Runtime-generated IDs/maintenance timestamps may differ but must not influence computed results.
5. Verification is read-only, executed in independent staging, and has explicit PASS/MISMATCH/NOT_REPLAYABLE outcomes. It cannot quietly mutate old history.
6. Late source data, erroneous normalization and user attribution changes produce separately audited correction requests, not in-place overwrites of original observations.
7. Historic totals remain HISTORICAL_AS_RECORDED by default. Optional policy-versioned recalculation is labeled RECOMPUTED_VIEW; changing official stored interpretation requires authorized and tested new-generation rebuild with preview and rollback.
8. Rebuilding/repair requires one integration-wide exclusive lease, verified source-provenance/backup lineage, independently prepared new SQLite generation, worker termination proof and ADR-0015 recovery-journal/pointer cutover. Never replace/rename an open SQLite main/WAL set.
9. An interrupted COMMIT or generation cutover must reconcile with durable source receipts, content digests and journal rather than blindly retrying and counting minutes again.
10. If original normalized evidence or policy definitions were legitimately purged, FULL_REPLAY is explicitly unavailable; report earliest trusted checkpoint/cursor and possible narrower replay rather than inventing missing facts.
11. Do not silently merge backup-restored and live generations, even with matching ledger UUID/cursor; same cursor does not mean same content.
12. No new mandatory physical SQL tables are approved. The 12-table ADR-0020 logical model must be checked for correction/provenance/policy requirements before its final DDL; an optional revision table or separate immutable log is permitted only after performance and integrity review.

## 2. Alternatives and resolution

| Alternative | Benefit | Risk | Result |
| --- | --- | --- | --- |
| Keep only daily totals and current active session | Compact | Cannot reconstruct missing raw facts or correct errors | REJECT |
| Retain original observations but overwrite old timestamps/results | Easy editing | Destroys source truth and audit | REJECT |
| Automatically rewrite all history whenever policy changes | Consistent latest-looking totals | Silent changes in historical meaning; restore hazards | REJECT |
| Immutable observations, versioned derived projections and audited corrections | Reproducibility, traceability | Storage/rebuild complexity | PREFERRED / PROPOSED |
| Synchronous automatic rebuild after every late PSN response | Apparently fresh history | Ambiguous physical attribution and expensive unbounded work | REJECT |
| Read-only verification and separately authorized rebuild | Clear safety boundary | Extra administrative flow | PREFERRED / PROPOSED |

## 3. Concrete operation contract

### VERIFY_REPLAY (non-mutating)

- Require one consistent selected ledger/generation/cursor and known reducer/schema/policy versions.
- Validate full normalized source replayability; if missing, return NOT_REPLAYABLE and stop.
- Recompute in a separate sandboxed staging context with deterministic accepted order and correction stream.
- Compare source/correction digest, owner lineage, all covered/UNKNOWN segments and report totals at fixed cursor.
- Publish privacy-redacted audit diagnostics only. A failed comparison opens Repair, NOT an automatic restore.

### REQUEST_CORRECTION

- Capture request ID, owner/observation target, class, reason, source evidence, expected ledger cursor, authorization and desired interpretation.
- Quarantine untrusted late arrivals; never move a current checkpoint backward.
- Show preview of affected time ranges, console/account/title scopes and policy-version difference.
- On rejection, preserve evidence and do not alter published history. On approval, generate separately versioned revision/rebuild only after safe maintenance gates.
- Never claim user-declared account presence is Sony-confirmed.

### REBUILD_PROJECTION

- Acquire global exclusive maintenance lease and fence source observations.
- Build one new candidate generation; no live in-place table rewrite and no second writer.
- Validate required FK/integrity, nonoverlapping exclusive coverage, chosen policy fingerprint, source/correction stream completeness and sample report parity.
- Close and positively verify worker/reader termination; safely publish new generation pointer with journal; record idempotent receipt.
- Recover by inspecting pointer+journal on crash; no automatic rollback/downgrade based solely on a staged file existing.
- Explicitly disclose potential differences from original history and retained old generation.

## 4. Temporal, identity and reporting invariants

- Time is UTC integer microseconds in half-open intervals and IANA-zone reporting; local 23/25-hour calendar days are valid.
- Last committed observation frontier bounds all durable covered seconds; don't accumulate across crashes.
- Two consoles can simultaneously yield >1 device-hour per wall-clock hour.
- A PSN title screenshot/provider presence is not proof of which PS5 executed a game.
- Duplicate observation ID+digest returns original committed result. Changed digest conflicts; late data does not reassign old session ownership.
- Read-only verify cannot modify commit cursor, live source checkpoint, HA Config Entry, credentials, selected generation or physical console.
- Privacy purge may limit replayability; never preserve personal data after a requested deletion just for convenience.

## 5. Open implementation gates — not further documentation topics

| Gate | Required evidence; future owner |
| --- | --- |
| LAN identity and correct physical power codes | WP-01–03 real PS5/firmware fixtures |
| Exact continuity policy B, failed probes and timestamp anchor | WP-03 deterministic tests with measured polling |
| Immutable raw-normalized observation retention, event breaks, corrections and policy-version fields | WP-04 DDL design/fixture review |
| Linked SQLite C version, WAL/synchronous settings and worker terminal contract | WP-04 instrumented HA OS proof |
| Source receipts, ambiguous COMMIT, staging/pointer/journal and restore divergence | WP-04 fault tests |
| Rebuild/report reproducibility and 36-month performance | WP-04 synthetic test suite |
| Server-side admin ACL, preview/confirmation and privacy | WP-05 integration tests |
| PSN provider permissions and attribution limitations | WP-07 explicit lawful authorization, otherwise deferred |

**Engineering rule:** Unknowns requiring executable/hardware evidence must be tested during implementation, not used as a reason to launch an unlimited new series of research ADRs.

## 6. Decision conclusion and closure rule

**PROPOSED:** Immutable source facts + versioned reducer, read-only verify and explicit audited rebuild. This documentation is sufficient to describe how to implement and test these behaviors; it is **not evidence** that the behaviors exist.

If the maintainer approves the proposed safe baseline, freeze this research track. Do not automatically produce ADR-0023/SPEC-023 or another collection of hundreds of unevaluated test IDs. Proceed with bounded WP-00 decision closure; only implement after explicit instruction.

## 7. Official/reference material

- [Source audit](../research/deterministic-replay-corrections-and-recovery-closure-audit-2026-11.md)
- [SPEC-022](../specifications/SPEC-022-replay-correction-and-crash-boundary-acceptance.md)
- [ADR-0021](ADR-0021-observation-to-session-reducer-and-temporal-coverage.md)
- https://www.sqlite.org/lang_transaction.html
- https://www.sqlite.org/lang_savepoint.html
- https://www.sqlite.org/isolation.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/pragma.html
- https://docs.python.org/3.14/library/zoneinfo.html

**No SQL DDL, code or test executed, approved or deployed by this ADR.**
