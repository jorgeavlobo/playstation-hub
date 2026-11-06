# PlayStation Hub — Deterministic replay, corrections, policy evolution, and research closure

**Reviewed:** 2026-11-06  
**Status:** DOCUMENTATION COMPLETE FOR THIS RESEARCH TOPIC / ENGINEERING PROOF NOT RUN  
**Decision:** [ADR-0022](../decisions/ADR-0022-deterministic-replay-and-versioned-corrections.md) (PROPOSED)  
**Acceptance plan:** [SPEC-022](../specifications/SPEC-022-replay-correction-and-crash-boundary-acceptance.md) (NOT_RUN)  
**Readiness boundary:** [WP-00B](../architecture/WP-00B-research-freeze-and-implementation-readiness.md)  
**Inputs:** ADR-0005/0006/0015–0018/0020/0021, SPEC-015–018/020/021, Protocols 01/02/09. Greenfield only; old develop SQLite was fictional and never deployed.

> The following is a source-informed **proposed PlayStation Hub contract**. SQLite documents transactions, isolation, backup, WAL and integrity checking; it does NOT dictate our event sourcing, temporal semantics, Sony identity mapping, corrections or Replay API. None of those are claimed tested on Home Assistant OS or a physical PlayStation.

## 1. Official evidence and design implications

| Official source | Verified platform behavior | Project-specific implication (proposal, not a source fact) |
| --- | --- | --- |
| [SQLite transactions](https://www.sqlite.org/lang_transaction.html) | One simultaneous writer; explicit COMMIT/ROLLBACK and error-specific transaction handling | Write observations, derived segments, checkpoints and commit cursor atomically; never assume every SQLITE_BUSY means transaction was fully rolled back |
| [SQLite savepoints](https://www.sqlite.org/lang_savepoint.html) | Releasing an inner savepoint is NOT a durable outer COMMIT | Replaying in a staging ledger requires a final verified outer commit/close before activation |
| [SQLite isolation](https://www.sqlite.org/isolation.html) | Read transactions see committed snapshots | Compare a single version/cursor-consistent live snapshot to a staged replay result |
| [SQLite WAL](https://www.sqlite.org/wal.html) | WAL files and checkpoint semantics matter for backups/recovery | Never copy only an active main .db, rename open databases or mix journals; preserve pending WAL after a crash |
| [SQLite backup API](https://www.sqlite.org/backup.html) | Can create a consistent database copy under its documented constraints | Candidate staging source; verify worker closure, corruption, writer lease and archive provenance in situ |
| [SQLite PRAGMA](https://www.sqlite.org/pragma.html) | integrity_check, foreign_key_check, journal/synchronous settings | Require both relational and structural validation; success is not semantic proof of correct activity durations |
| [SQLite UPSERT](https://www.sqlite.org/lang_upsert.html) | Conflict handling requires a matching uniqueness constraint | Same observation ID/digest is an idempotent receipt; mismatched digest is a hard conflict, not an upsert replacement |
| [Python ZoneInfo](https://docs.python.org/3.14/library/zoneinfo.html) | IANA time zones and DST fold | Evaluate reports from UTC half-open intervals, and carry timezone and reporting policy into comparison |
| [Python time](https://docs.python.org/3.14/library/time.html) | Monotonic clocks measure process-local elapsed durations | Never rely on persisted monotonic values for replay after boot |
| [HA integration quality/testing](https://developers.home-assistant.io/docs/development_testing/) | HA provides documented test/developer practices | Planned replay and crash scenarios need executable assertions later; documentation alone is not a passing quality gate |

**Unverified:** Sony LAN status identity/code mapping, any PSN title provider authorization, precise HA OS SQLite linked version and WAL fix, worker terminal guarantee, actual custom SQLite inclusion/exclusion in backups, safe automatic restore intent. Earlier research remains authoritative about these blockers.

## 2. The core challenge: an observation log is not automatically replayable

For replay to reconstruct *the same historical interpretation*, the authoritative record must include:
1. Immutable admitted observation identity and normalized fact, not just a digest.
2. Canonical console or account owner, source scope, source version, run/generation, ordering decision, request/receipt timestamp precision and normalization version.
3. Explicit gap/failure/continuity-break facts affecting policy, including when source attempts failed or the worker was unavailable.
4. The **policy version** used when converting successive compatible observations to bounded time, together with the deterministic policy parameters (B, break-on-failed-poll, source selection, source-timestamp boundary rules).
5. The accepted ordering and relative source semantics; completion order alone is not sufficient.
6. Explicit correction decisions and their effective source/target scope, authorization, revision and reason.
7. A deterministic way to derive segment IDs/ordering (or a comparison that canonicalizes harmless generated IDs), and a defensible retention policy that does not claim full replay from deleted evidence.

**Important new dependency:** ADR-0020's 12 logical tables must be reviewed for enough event/source failure, policy snapshot and correction provenance. If full immutable raw normalized observations are not retained, **FULL_REPLAY is unavailable**. A checkpoint/snapshot alone can support a narrower REPLAY_FROM_TRUSTED_CHECKPOINT but not a universal original-data rebuild. Never present the digest as reconstructable source content.

## 3. Replay model: two explicitly different operations

### 3.1 VERIFY_REPLAY (read-only audit)

1. Pin selected ledger_uuid, generation UUID, schema version, commit cursor, and policy fingerprint.
2. Acquire a consistent bounded read snapshot and export the *authorized, fully reconstructable normalized source sequence* plus relevant policy/correction history into an isolated staging context. If unavailable, report NOT_REPLAYABLE and the earliest replayable cursor.
3. Normalize canonical order using persistent accepted source sequence and admitted cursor; do not use system current time, nondeterministic random IDs or response completion scheduling.
4. Apply deterministic reducer with fixed policy to rebuild derived events, covered intervals, unknown gaps and source checkpoints in an independent staging target.
5. Canonicalize comparison views and compare semantic intervals, cursor, ledger identity, attribution provenance and aggregate summaries, including UTC/DST clipping.
6. Report PASS/MISMATCH/NOT_REPLAYABLE with redacted details. Neither repair live data nor overwrite the original log.

**Invariant:** Verify never authorizes restore or physically controls consoles. A passing replay does not prove actual physical PlayStation truth, only deterministic derivation from recorded evidence and policy.

### 3.2 REBUILD_PROJECTION (explicit administrative maintenance)

1. Require admin authorization with preview of differences, expected cursor, lineage, target policy, backup availability and historical effects.
2. Fence admissions and obtain integration-wide controller write/rebuild lease; no concurrent writer or stale source callbacks.
3. Build a separate unique SQLite generation from trusted source evidence/checkpoint; validate FK, schema, semantic no-overlap, cursor and spot-check report totals. Never patch active live DB tables in-place from a side worker.
4. Durably stage independent result; close reader and writer workers with positive terminal evidence; follow ADR-0015's crash-safe journal and active-generation pointer promotion contract.
5. On restart, reconcile journal and selected pointer, and ensure old and new histories cannot both accept live observations.
6. Keep the prior generation recoverable under explicit, bounded retention. No automatic deletion or branch merge.

**Not yet authorized:** Exact schema, retention window, the worker, admin API, staged promotion and other implementation details.

## 4. Corrections should preserve evidence, not erase it

Correction classes:
- **Transport normalization bug:** a previously interpreted source field was wrong; record original observation, decoder version and a separately reviewed deterministic correction/rebuild proposal.
- **Delayed/out-of-order evidence:** preserve as QUARANTINED evidence with explanation and no immediate mutation of accepted past segments. Administrator or reviewed deterministic backfill may create a new interpretation revision; no silent insertion into older cursors.
- **User claim or attribution change:** label an account-title association as USER_DECLARED or INFERRED, not a source-confirmed fact; retain prior claim and effective-time context.
- **Source clock correction:** maintain original recorded request/receipt instant and a revisioned adjusted interpretation only after explicit evidence; never rewrite timestamps in place.
- **Retention/privacy deletion:** distinct security workflow; cannot preserve a purged secret/data item in supposedly complete backups; once raw evidence is legitimately removed, its past projection may be retained with constrained claims but FULL_REPLAY of that period is no longer possible.

Suggested logical correction record (not DDL): `correction_id, revision_id, target_observation_or_interval, kind, old_interpretation_reference, proposed_interpretation, submitted_by_role, authorized_at_utc, reason_code, source_evidence_ref, policy_version, effective_cursor, immutable_digest, status`. No raw credentials.

**No self-healing by guess:** Mismatch or checksum failure is a Repair and RECOVERY_HOLD/READ_ONLY diagnostic, not an opportunity to overwrite the live ledger.

## 5. Evolving duration policy without rewriting history invisibly

- Policy v1 e.g. BOUNDED_TWO_POINT with max continuity B (UNSET until validation) and failed-request BREAK; do not copy the legacy synthetic 90-second gap.
- New policy v2 cannot silently redefine existing 'official' daily totals. Explicitly distinguish:
  - HISTORICAL_AS_RECORDED: historical intervals and policy versions as originally committed.
  - RECOMPUTED_VIEW(policy_fingerprint): optional read-only estimate/re-analysis over trusted retained normalized source evidence, clearly labeled and never replaces historical data by default.
  - AUTHORISED_REBUILD: administrator-approved promotion to new generation with audit and displayed numerical difference.
- If a policy changes at time T, source continuity must be cut at an accepted durable anchor; record precise effective ledger cursor and T. Repeated samples before and after policy boundaries require a deterministic bridge rule (default no coverage across boundary).
- Two reports may differ legitimately under different policies; preserve both policy fingerprints in audit/correction UI.

## 6. Crash injection boundaries (design, no tests run)

| Failure point | Required future behavior |
| --- | --- |
| Before accepted source insert | No observation receipt or history delta |
| After observation insert, before derived segment update | Outer SQL transaction rollback prevents partial admitted history |
| After segment update, before checkpoint/cursor | Same atomic rollback, not half-updated ledger |
| After COMMIT dispatched, before caller acknowledgement | Treat as UNKNOWN_COMMIT; fence unsafe worker and reconcile observation ID/digest after positive terminal evidence |
| During staging generation build | Staging is never active; keep old pointer and old ledger intact |
| After stage validated, before pointer promotion | Resume journal/review; old generation remains selected |
| After atomic pointer publication, before acknowledgment | Boot reconciles pointer+journal; one active generation only |
| After worker quit requested, while queue contains old writes | Do not promote; cannot rely on Future.cancel to terminate a worker |
| During Home Assistant shutdown or Supervisor backup | No assumption that pre/post hooks automatically exclude live DB/WAL or yield trusted restore intent |
| Restored old configuration with newer external ledger | Detect mixed lineage and stop autonomous writes |
| Same ledger UUID/cursor but divergent content | Compare independent lineage/content evidence; never infer equality from cursor alone |
| Crash after correction approval but before rebuild | Idempotent operation receipt; do not implicitly count corrected data before successful promotion |

Risk distinction: a SQLite **transaction** is not an atomic transaction spanning Config Entries, snapshot file directories, HA backup metadata and a generation pointer. One durable cross-component recovery journal is a proposed coordination mechanism subject to future power-cut tests, not a proven implementation.

## 7. Idempotent identities and proof of equivalence

**Replay input ordering** must be independent of wall-clock processing order. Define stable `accepted_cursor` or a canonical source order and enforce per-source sequence/owner isolation. Replaying identical accepted input, same policy fingerprint and same selected source snapshot should yield equal *semantic* intervals, gap classification, attributed scope and aggregates. Generated runtime UUIDs and auto-increment SQL row IDs must not affect user-visible history.

**Strong equivalence predicate:** same ledger lineage and source/correction history digest, accepted observation set/order, policy fingerprint, normalized intervals, UNKNOWN ranges, selected owner/report scopes and resulting report totals at a fixed cursor. Same cursor or total **alone** is insufficient proof.

**Secondary safety invariants:** no overlapping exclusive power classifications for same console; no negative duration; no future extrapolation after last committed evidence; no implicit PSN physical attribution; no suppression of privacy restrictions.

## 8. Minimal implementation/testing boundary — stop researching

Additional source-reading without concrete experiments will not close the remaining HA OS/SQLite worker, Sony firmware, backup, or PSN provider blockers. The **documentation-level requirements can now be frozen** after reviewing ADR-0022 and WP-00B, leaving implementation-stage empirical questions to WP-01 onward.

Do NOT create ADR-0023 or SPEC-023 automatically. Escalate only a proven contradiction or new requirement, rather than creating another 80+ unexecuted cases by default.

### Implementation-phase proof ownership

- WP-01–03: LAN source contracts, hardware identity, monitored lifecycle, pure source/reducer tests.
- WP-04: SQLite v1 physical DDL, writer, crash/restore, replay corrections and reporting fixtures.
- WP-05–08: panel/permissions, optional Remote Play and Sony-authorized PSN, release validation.
- Required launch proof: selected Core/Python version, linked SQLite C version and feature gates, HA OS backup/restore, worker shutdown/cutover and real PS5 compatibility.

**Outcome:** Research complete as a design, all technical mechanisms proposed/unverified; zero source code or executed simulations. Next responsible step is **closing a bounded architecture decision register** and then, only when user authorizes, implementing and testing incrementally — not continuing open-ended literature reviews.
