# Formal architecture review — ADR-0004 through ADR-0010

**Date:** 2026-11-05  
**Status:** Review completed at document-consistency level; decisions remain proposed and implementation is NOT authorized by this review  
**Branch:** `main` documentation only  
**Inputs:** Protocols 01–10, ADR-0002–0010, SPEC-001–007, cross-protocol review, compliance matrix, quality gates, legacy `develop` source previously inspected.

## 1. Executive decision

The proposed architecture is **directionally coherent**, but not ready to be marked fully accepted or release-ready. The one-HACS-integration/no-MQTT and one-sidebar-panel choices are established product decisions. Physical identity, source semantics, historical accounting, credentials, storage, native HA entry lifecycle and frontend authorization remain proposed. No test, Sony permission or real-console evidence is supplied by writing documentation.

**Recommended implementation sequencing, subject to explicit project approval:** isolated LAN-only foundation and synthetic test harness first; then HA multi-console config flows and cached state; then bounded ledger, backup and UI; separately gated Remote Play; separately permission-gated PSN. Do not automatically reduce the ultimate product goal to LAN-only: this is a staged engineering approach, not abandonment of PSN or Remote Play.

## 2. ADR decision register

| ADR | Decision under review | Review disposition | Conditions |
| --- | --- | --- | --- |
| ADR-0002 | One full-page sidebar panel, no parallel Lovelace card | Previously ACCEPTED product decision | Verify HA panel APIs and distribution |
| ADR-0003 | App-owned SQLite history | PROPOSED | Snapshot consistency, schema, performance, backup |
| ADR-0004 | One console entry per physical console, account entries separate | RECOMMEND CONDITIONAL ACCEPTANCE | Stable hardware identity and HA multi-entry flow |
| ADR-0005 | Per-source immutable observations, fact-scoped reconciliation | RECOMMEND CONDITIONAL ACCEPTANCE | Timestamp/generation semantics, freshness, reducer tests |
| ADR-0006 | Bounded evidence intervals, explicit unknown gaps | RECOMMEND CONDITIONAL ACCEPTANCE | Define accounting policy, gap threshold, user terminology |
| ADR-0007 | Owner-scoped PSN and Remote Play credentials | RECOMMEND CONDITIONAL ACCEPTANCE | Concrete store, durability, threat review, Sony permission |
| ADR-0008 | Hybrid Config Entries + Store + SQLite + Recorder | RECOMMEND CONDITIONAL ACCEPTANCE | Confirm HA OS backup behavior, WAL snapshots and migrations |
| ADR-0009 | Native HA config flows, entities and targeted actions | RECOMMEND CONDITIONAL ACCEPTANCE | Pinned HA Core, identity and entity semantics |
| ADR-0010 | One bundled sidebar Web Component and authenticated WS API | RECOMMEND CONDITIONAL ACCEPTANCE | HA panel API, admin ACL, snapshot/delta race, bundle compatibility |

**Meaning:** “Recommend conditional acceptance” is a reviewer recommendation, **not** a status change to ACCEPTED. Final decisions need explicit maintainer approval and evidence where required. Do not overwrite ADR headers automatically.

## 3. Cross-document consistency checks

| ID | Finding / possible contradiction | Severity | Resolution proposal |
| --- | --- | --- | --- |
| REV-001 | ADR-0004 assumes stable `host-id` but SPEC-001/007 show no hardware proof | P0 | Treat `host-id` as candidate, validate uniqueness/stability before durable canonical key |
| REV-002 | Discovery “identity verified” could be misread as cryptographically authenticated | P0 | Separate protocol-validated from pairing-authenticated trust levels; never send keys based only on IP |
| REV-003 | ADR-0005 freshness expiry and ADR-0006 session continuity budget are distinct | P0 | Define two named policies; no implicit equality or common magic timeout |
| REV-004 | ADR-0006 bounded “observed” duration could be interpreted as exact continuous measurement | P0 | Use explicit `bounded_evidence_seconds` label; transition intervals remain uncertain |
| REV-005 | ADR-0007 secret storage may use HA Store, but ADR-0008 does not yet guarantee atomic durable token replacement | P0 | Prototype/verify store semantics; rotation crash window cannot be eliminated |
| REV-006 | ADR-0008 backup proposal relies on an HA backup lifecycle hook not yet confirmed | P0 | Inspect pinned HA OS/Core backup mechanism; prove consistent live WAL snapshot and restore |
| REV-007 | ADR-0009 suggested `power_mode` sensor with unavailable state; ADR-0005 also models UNKNOWN | P1 | Specify difference between a fresh unknown protocol state and stale/unavailable entity |
| REV-008 | ADR-0009 wake/standby button and action both may duplicate command implementation | P1 | One CommandCoordinator, explicit target, no optimistic state, shared permission checks |
| REV-009 | ADR-0010 panel registration lifetime may differ from per-entry lifecycle | P1 | Integration-level singleton; test zero/one/many entries, reload and HACS upgrades |
| REV-010 | PSN account game activity cannot identify physical console or exact play duration | P0 for game attribution | Preserve separate account-scoped DTOs; inference labeled and never double counted |
| REV-011 | PSN OAuth callback desired but no Sony-authorized client/redirect is established | P0 for PSN | Keep SPEC-003 blocked; do not promise automatic capture or redistribute borrowed OAuth client |
| REV-012 | Source-derived PS5 power heuristic maps non-620 to awake | P0 | Reject unsupported status codes; no “no reply means OFF” |
| REV-013 | SPEC-002 wake credential mapping and Remote Play registration bytes incomplete | P0 for Remote Play | Do not expose functioning wake/standby until source vectors and hardware tests pass |
| REV-014 | HA Recorder numeric state classes may be inappropriate for resetting daily counters | P1 | Audit per-entity semantics against pinned HA release; ledger remains source of truth |
| REV-015 | Historical data deletion, account unlink and Recorder retention differ | P1/privacy | Separate explicit privacy policy, admin confirmation and backup disclosures |
| REV-016 | Public HACS capability claims could exceed actual hardware/firmware evidence | P0 release | Gate claims per model/firmware, use SPEC-005/007 evidence |
| REV-017 | Original code uses MQTT and one configured player, incompatible with new modular architecture | P1 | Use `develop` as reference only; no blind port of code or single-user assumptions |
| REV-018 | Status of ADR-0001 source filename must be checked; direct fetch of `docs/decisions/ADR-0001-no-mqtt.md` returned NOT_FOUND | P2 docs | Find actual ADR-0001 path and repair only confirmed broken links; do not invent file |

This review checks written requirements for logical consistency, not an exhaustive audit of every source line or external upstream commit.

## 4. Blocking decisions by release scope

### Common LAN foundation — P0 before implementation of durable identities/history

1. Define canonical console ID and what happens when host ID is absent/changes.
2. Pin supported Home Assistant Core/Python baseline and test custom DHCP flow with multiple entries.
3. Freeze a minimal observation DTO and ordering/freshness semantics.
4. Freeze a bounded session continuity rule or initially ship power observation without historical duration.
5. Choose durable storage path and test HA backup/restore strategy before promising multi-year history.
6. Implement strict access control for the sidebar and any private history APIs.
7. Verify exact supported hardware/firmware before compatibility claims.

### Remote Play extension — independently blocked

- Full registration/crypto byte contract and independent vectors.
- Wake `user-credential` derivation and console-scoped key mapping.
- Safe standby preflight without implicit wake, post-command confirmation.
- User-authorized real PS5 tests, privacy and permissions.

### PSN extension — independently blocked

- Sony client, scopes, redirect and endpoint permission evidence.
- Approved NPSSO/OAuth flow and token storage/refresh.
- Privacy, child accounts, rate limits, DTO schema, game artwork rights.
- No implicit console attribution from cloud presence.

## 5. Proposed architecture boundaries

```text
custom_components/playstation_hub/
  domain/           # pure models, identity, observations, reconciliation
  transport/lan/    # UDP discovery/status, fakeable async interface
  transport/remote_play/ # gated registration/control
  transport/psn/    # gated provider adapters
  persistence/      # abstract repository and reviewed implementations
  api/              # authorized DTO facade and subscriptions
  frontend/         # bundled build output, not a runtime server
  config_flow.py    # HA discovery/reconfigure/reauth
  coordinator.py    # per-entry lifecycle, shared integration owner
```

All paths are conceptual. Code/comment text remains English; frontend text is localized EN/PT-PT. No executable files are created by this review.

## 6. Proposed staged implementation work packages

| Stage | Work package | Entry condition | Exit evidence |
| --- | --- | --- | --- |
| WP-00 | Pin HA Core/Python versions, repo test conventions, ADR decisions | Maintainer approval | Reviewed compatibility and toolchain |
| WP-01 | Pure LAN parser, fake UDP transport and identity resolver | WP-00 | SPEC-001 synthetic tests |
| WP-02 | HA discovery/config entry and stable device registry | WP-01 | Multi-console HA integration tests |
| WP-03 | Observation reducer and native power/reachability entities | WP-02 | ADR-0005 tests, no false OFF |
| WP-04 | SQLite ledger, bounded sessions, backup and restore | WP-03, ADR-0008 decision | Transaction, crash and HA OS restore evidence |
| WP-05 | Bundled sidebar + authenticated WS snapshots and history | WP-03/04 | ACL, pagination, mobile, reconnect tests |
| WP-06 | Remote Play pairing, wake/standby | SPEC-002 blockers resolved | Crypto KAT + real console safety |
| WP-07 | PSN account authentication/presence/catalog | SPEC-003 authorization resolved | Provider permission + privacy/rate tests |
| WP-08 | Release and regression hardening | Applicable WPs | SPEC-005/006/007 gates and sign-off |

WP-04 and WP-05 can be decomposed further after the storage decision. WP-06 and WP-07 are separate branches of capability, not prerequisites for the LAN foundation.

## 7. Release scope recommendation

A **first LAN-focused development milestone** is appropriate to test architecture, not necessarily a public release. The initial private demonstrator should show a verified console in Home Assistant with stable identity, accurate fresh/stale status and no unverified command buttons. Only after storage and backup validation should it claim durable historical statistics. The single sidebar can initially display a bounded read-only status view.

Do not silently downgrade the project's intended final feature set. Remote Play and PSN remain explicit roadmap capabilities, with independent blockers and gates.

## 8. Required next decisions and owners

| Decision | Priority | Suggested owner | Evidence |
| --- | --- | --- | --- |
| Approve canonical identity strategy or an interim safe fallback | P0 | Maintainer | SPEC-001/007 hardware plan |
| Select HA Core stable baseline | P0 | Maintainer + implementation reviewer | Official compatibility docs/tests |
| Accept source-aware state model | P0 | Maintainer | ADR-0005 + reducer fixtures |
| Select accounting continuity and uncertainty labels | P0 for history | Maintainer | ADR-0006 + synthetic timelines |
| Select SQLite/Store backup design | P0 for history | Maintainer | ADR-0008 + HA OS restore proof |
| Approve initial admin-only sidebar permissions | P0 for private UI | Maintainer | ADR-0010 + ACL tests |
| Resolve Remote Play byte gaps | P0 for control | Protocol researcher | SPEC-002 |
| Establish Sony permission basis | P0 for PSN | Maintainer/legal review | SPEC-003 |
| Approve data retention and unlink policy | P1 | Maintainer | ADR-0007/0008 + SPEC-006 |

Do not mark these decisions approved simply because they appear in the review. Track explicit decision date, rationale, version and reviewer.

## 9. Review completion checklist

- [x] Cross-ADR consistency issues recorded.
- [x] LAN, Remote Play and PSN release gates separated.
- [x] Proposed work packages and dependencies recorded.
- [x] Existing accepted product decisions preserved.
- [x] Unverified hardware, Sony permissions and storage clearly labeled.
- [ ] Maintainer approves/rejects conditional ADR recommendations.
- [ ] Canonical console identity proven on hardware.
- [ ] Target HA version pinned and tested.
- [ ] Storage/backup approach approved and demonstrated.
- [ ] Remote Play wire blockers closed.
- [ ] Sony authorization basis established.
- [ ] CI and HA OS tests executed.

## 10. References

- [Cross-protocol review](cross-protocol-review-01-10.md)
- [Compliance matrix](../standards/compliance-matrix.md)
- [ADR-0002](../decisions/ADR-0002-sidebar-panel.md)
- [ADR-0003](../decisions/ADR-0003-persistence-provisional.md)
- [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- [SPEC-001](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md)
- [SPEC-003](../specifications/SPEC-003-psn-authorization-and-availability.md)
- [SPEC-004](../specifications/SPEC-004-psn-presence-game-metadata-dto-mapping.md)
- [SPEC-005](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md)
- [SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md)

**Outcome:** Formal documentation-level review complete, with 18 findings and a conditional decision register. No ADR was accepted, no P0 blocker closed, and no implementation or hardware validation performed.
