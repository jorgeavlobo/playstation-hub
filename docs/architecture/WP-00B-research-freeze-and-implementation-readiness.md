# WP-00B — Research freeze, architecture closure and implementation-readiness decision

**Date:** 2026-11-06  
**Status:** PRE-IMPLEMENTATION RESEARCH BASELINE DOCUMENTED / PROPOSED FREEZE / NOT IMPLEMENTATION AUTHORIZATION  
**Inputs:** [Architecture Guide v0.57.0](../../ARCHITECTURE_GUIDE.md), [WP-00](WP-00-implementation-readiness-and-decision-closure.md), [WP-00A](WP-00A-home-assistant-baseline-and-lan-contracts.md), [ADR-0021](../decisions/ADR-0021-observation-to-session-reducer-and-temporal-coverage.md), [ADR-0022](../decisions/ADR-0022-deterministic-replay-and-versioned-corrections.md), [SPEC-021](../specifications/SPEC-021-observation-to-session-state-machine-and-replay.md), [SPEC-022](../specifications/SPEC-022-replay-correction-and-crash-boundary-acceptance.md).  
**Scope boundary:** New PlayStation Hub integration only. The old `develop` App and fake SQLite records are never deployed and never migrated.

> This document exists to **prevent open-ended research**. It is a decision register and bounded handoff, not an additional workstream that automatically demands another ADR/SPEC. Future implementation is separate and requires user authorization.

## 1. What "done" actually means

**Architecture documentation sufficiently scoped:** YES, for a proposed greenfield, LAN-first modular architecture and test plan, subject to the explicit selection/approval register below. The 22 ADR numbers and SPEC-001–022 are reference identifiers, not a requirement to produce further numbered documents. Several historic sections are superseded; they must not be resurrected as blockers.

**Architecture technically proven:** NO. A review of web docs, third-party protocol sources, and hypothetical tests does not prove PlayStation firmware, Sony permission, HA OS backup behavior, actual SQLite C version, Home Assistant integration runtime or worker/thread safety.

**Ready to start *limited* implementation:** CONDITIONAL. WP-01 can reasonably begin once its narrow baseline and explicit authorization are approved. Unrelated optional PSN, Remote Play and production history restore questions should **not** block building a pure, testable LAN parser against synthetic fixtures.

**Ready to release:** NO. Requires executed device tests, crash/backup/restore and privacy/release checks, not merely documentation.

## 2. Frozen product expectations, already established

1. One packaged Home Assistant Marketplace/HACS integration `playstation_hub`, one bundled sidebar panel, native Home Assistant Config Entries/entities/actions; no mandatory App, MQTT broker or other service.
2. One logical Hub/Archive Config Entry for persistent history access, additional physical console and optional PSN account entries; one shared controller and ledger writer, not one database per console. ADR-0011 product concept accepted.
3. LAN-first monitoring; optional independently gated Remote Play and PSN modules (no undocumented Sony service access implied).
4. Preserve physically verified console identity independent of account, game, DHCP IP, HA entity_id and display names.
5. Current power sample, source availability/freshness, account presence, source health and historical duration are separate concepts. Unknown/offline must not invent OFF or continuous gameplay.
6. New SQLite ledger from scratch, no old develop migration or MQTT cutover; immutable normalized accepted source facts, versioned interpretations, idempotent atomic writes, conservative UNKNOWN coverage.
7. Crash-safe recovery/backup is a release requirement for durable history; recovery must never erase or silently replace missing/divergent historical data.
8. English code, comments and repo documentation; modular, expandable components and reproducible tests.
9. No code, DDL, test fixture or deployed integration currently exists under the new `main` architecture.

## 3. Small bounded decision-closure table

| # | Decision to approve before relevant work | Preferred architecture | Implementation stage | State |
| --- | --- | --- | --- | --- |
| D01 | Core baseline and minimum supported HA/Python | Source-reviewed Core 2026.11.0 / Python >=3.14.2; final declared support matrix at coding/release | WP-01 | PENDING_SELECT |
| D02 | Physical identity trust | Accept only validated hardware candidate, never IP/name; mark ambiguous until proved | WP-01–02 | PENDING_FIXTURES |
| D03 | One source/identity/lifecycle policy | Per-console owned polling, immutable normalized observations, no last-write-wins | WP-01–03 | PENDING_APPROVAL |
| D04 | Conservative history semantics | Two compatible points -> bounded inference, change/failure -> UNKNOWN; B versioned/calibrated | WP-03–04 | PENDING_APPROVAL_AND_MEASUREMENT |
| D05 | SQLite v1 logical shape | One application-owned 12-entity normalized ledger, with policy/correction provenance | WP-04 | PENDING_SCHEMA_PROOF |
| D06 | Durable transactions/recovery | One writer, generation fencing, explicit receipts, safe staged restore/promotion, no silent reset | WP-04 | PENDING_HA_OS_FAULT_TESTS |
| D07 | Report/replay/corrections | Read-only verify, no automatic historic rewrite, explicit audited admin rebuild | WP-04–05 | PENDING_APPROVAL |
| D08 | Panel and access policy | One sidebar, backend WebSocket ACL; recovery UX possible with no console | WP-05 | PENDING_HA_TESTS |
| D09 | Optional Remote Play | Separate authenticated module, no optimistic power state after sending command | WP-06 | DEFERRED_UNTIL_VALIDATED |
| D10 | Optional PSN | Separate account presence/title metadata; physical attribution not automatic; Sony API permission gate | WP-07 | DEFERRED_UNTIL_PERMITTED |

**Important:** D01–D03 and explicit user instruction are the only *architecture entry* requirements for **narrow WP-01 parser/fake-transport coding**. D04–D10 do not preemptively block safe WP-01 work; they block only the dependent features. Technical ADRs remain PROPOSED until approved, even when strongly recommended.

## 4. Explicit next work: bounded 8-package implementation path

| Package | Deliverable | Exit evidence |
| --- | --- | --- |
| WP-01 | Pure LAN discovery/status parser + fake transport and protocol fixtures | Deterministic parsing tests pass, malformed/unknown codes handled, no real PSN/Remote Play |
| WP-02 | Config Flow, canonical multi-console registry and discovery handling | 2-console simulated tests and one validated hardware identity fixture; no IP-based silent reassignment |
| WP-03 | Entry-owned monitor, observation envelope/reducer and native current-state entities | Tested HA update/unload/reload, stale/unknown semantics, bounded state machine |
| WP-04 | Greenfield SQLite v1 schema, serialized worker and historical intervals + backup/replay tests | Actual linked SQLite/HA OS, injected COMMIT/recovery/restore and idempotency proof |
| WP-05 | One bundled sidebar, scoped WebSocket API, Reports/Repairs, and admin correction preview | ACL and report consistency tests; no remote power by hiding button |
| WP-06 | Optional Remote Play control, pairing and key isolation | Sony/version-specific wire and command-confirmation tests |
| WP-07 | Optional PSN adapter, profiles/title metadata and privacy-aware attribution | Explicit legal/provider permission and integration tests or feature stays deferred |
| WP-08 | CI, HACS/Marketplace packaging, reliability, firmware matrix, documentation release | Actual quality, privacy, restore, regression and release check evidence |

This is sequencing, not permission to create those implementations. No `next` branch; when implementation is specifically approved create `feature/<scope>` from main.

## 5. What is and is not a true blocker right now

### Blocks starting narrow WP-01 code
- No explicit authorization to leave documentation-only mode.
- Exact HA/Python coding baseline and language/tooling review must be recorded before first tests.
- Pure LAN adapter/reducer boundaries and parser fixture contracts to be chosen from existing Protocol 01/02 and WP-00A proposals; source packet may be treated as synthetic until hardware validation.

### Blocks production durable-history WP-04, **not** the LAN parser
- Real SQLite linked runtime/WAL fix and worker terminal proof.
- Safe immutable snapshot/backup/restore and metadata/ledger identity divergence control on HA OS.
- Final DDL, observation retention sufficient for replay, policy-version and break-event source.
- Approved duration B, actual poll cadence, fault injection and no-overlap tests.

### Blocks optional features only
- Sony source/provider authorization, account privacy and PSN title semantics: WP-07.
- Remote Play byte/crypto/registration proof and real firmware: WP-06.

### Not a blocker at all
- Importing, converting, uninstalling or cleaning up the old **never-deployed** develop prototype.
- Inventing 80 additional NOT_RUN scenarios per research topic.
- Proving optional PSN and Remote Play before writing a LAN-only parser.
- Running 36-month performance tests before the first domain/parser modules exist.

## 6. Documentation freeze / STOP policy

**Recommended freeze scope:** Documentation in ARCHITECTURE_GUIDE + ADR-0001–0022 + SPEC-001–022, except the retired legacy migration track ADR-0019/SPEC-019. Older superseded advice must not be interpreted as current requirements.

- Do not create ADR-0023/SPEC-023 automatically.
- Future source research requires a named contradiction, a changed official API, a new requested feature, or a failing test. Capture findings as a focused amendment to existing records.
- Prioritize actual running tests and source fixtures over hypothetical test-count growth; the number of planned cases is **not** a quality metric.
- Keep a small release evidence register marking each item SOURCE_CONFIRMED, DESIGN_APPROVED, TESTED, BLOCKED or DEFERRED; do not equate these terms.
- If a test exposes a conflict, revise the closest existing ADR/Spec and update the Bible. A document can change without needing a new document number.
- A user request to "document and advance" authorizes research/docs, **not** autonomous implementation or deciding blocked Sony permission details.

## 7. Acceptance criteria for WP-00B research freeze

- [x] Greenfield/no-legacy migration policy recorded.
- [x] Supported conceptual separation of LAN, PSN, console identity, physical power and history documented.
- [x] SQLite logical, temporal, recovery, replay, admin-archive and crash safety requirements described.
- [x] Test catalogues and source limitations clearly identified, with no claim of tests run.
- [x] WP-01..08 stages, dependencies and evidence-based exits listed.
- [x] No further *scheduled* numbered source-audit/research follow-ups required by default.
- [ ] Maintainer chooses whether to approve the narrow architecture freeze.
- [ ] Exact WP-01 baseline and explicit authorization to implement.
- [ ] Run actual WP-01 tests (only after implementation begins).

### Suggested maintainable next-turn options

- **Option A — Freeze research (recommended):** approve the proposed baseline and choose WP-01 implementation task. This moves toward tangible working software.
- **Option B — Documentation-only:** keep the baseline marked PROPOSED, but stop generating open-ended ADRs; use next interaction to resolve at most the small D01–D03 pre-code decisions, not restart wide source sweeps.
- **Option C — Narrow targeted research:** only if the maintainer identifies a specific genuine blocker to WP-01 or changes the product scope.

**Outcome:** This is the handoff point. Research stage is sufficiently mapped, not implementation-proven, and no further ADR-series is presumed.

## Targeted upstream-source exception — LAN title metadata (2026-11-06)

The maintainer explicitly requested deeper analysis of existing upstream code rather than more SQLite-backup speculation. The new [commit-pinned upstream source audit](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md) is an **allowed targeted research exception** under this freeze, not permission to continue endless ADR/SPEC creation. It identified a previously underexplored optional `running-app-titleid` / `running-app-name` in Chiaki-ng's LAN discovery parser and corrected the candidate code map to `200` READY/`620` STANDBY/other UNKNOWN. It also identified PS5-MQTT multi-NIC broadcast and first-awake-device PSN attribution heuristics, potential sequential polling starvation, playactor command/state bugs and legal/version drift in candidate dependencies.

**Update WP-01 parser targets, without implementing now:** allowlisted status parsing, optional local app metadata fields, network interface discovery with safe bounds, host-ID collision checks, independent source/freshness dimensions and real-device validation matrix. Real PS5 metadata semantics are still a WP-02/03 empirical gate; PSN authorisation and external GPL/AGPL copy/link licensing remain later-feature gates. A running-app response field must not be counted as verified uninterrupted gameplay. Keep existing package sequence and research stopping rules intact; revise the existing Protocol 01–05/07/09/10, ADR-0005/0020/0021 and Bible rather than creating ADR-0023 or SPEC-023.

## Second targeted upstream audit — stronger testable LAN evidence (2026-11-06)

The maintainer requested deeper reference-repository investigation. [Protocol triangulation and LAN title forensics](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) is a **focused exception** to the research freeze, adding source-level corroboration and bugs without spawning ADR-0023/SPEC-023. Examined archived pyremoteplay (2022), a newer playactor-based Python port (2026), PS5-specific PS5-Wake C, Chiaki-KM's input-profile feature and existing playactor/PS5-MQTT/Chiaki-ng modules.

**WP-01 parser first:** candidate 200/620/UNKNOWN states; no non-620 => awake; first-colon and CRLF-safe headers, bounded UTF-8 input, identity conflicts, absent versus empty optional app metadata, no automatic history from `running-app`; repeated same-state accepted observations despite unchanged HA entity. **WP-02/03 hardware checks:** actual PS5 game/media/background/rest and firmware semantic validation, multi-NIC replies and owner stability. **WP-06 commands:** verify fresh 200 after WAKEUP and fresh 620 after standby, never infer from TCP close, library success or swallowed timeout. No optional cloud, SQLite/backup or crypto licensing issue should block safe synthetic WP-01 parser development, which still requires explicit authorization. 20 source trace IDs live in the research audit and are linked into existing SPECs; they are **not executed cases** or another numbered SPEC.

## Final PSN upstream source follow-up — 2026-11-06

The same [second triangulation research §11](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md#11-deeper-psn-runtime-source-audit--token-rotation-provider-title-selection-and-independent-failures) compared PSNAWP, Emkraan, HA Core 2026.11 and psn-api source methods. Optional WP-07 PSN requires per-account single-flight refresh and durable rotation/reauth semantics, typed flat/nested auth error, independent quota/privacy failure, source list preserving multiple presence-title candidates (HA Core first-title = UI projection) and version-sensitive persisted GraphQL queries. These gates must **never block WP-01 LAN parser or future passive LAN_RUNNING_APP source**. No API/credential/wheel/runtime test was executed. Continue the documented research stop policy: only actual contradictions, new capabilities or test failures justify further upstream source investigation.

## MAINTAINER REQUIREMENT OVERRIDE — full first-party implementation without new runtime packages (2026-11-06)

The maintainer now explicitly requires **all PlayStation-specific protocols and behavior to be implemented by PlayStation Hub itself**: no runtime playactor, PS5-MQTT, Chiaki, PSNAWP, pyremoteplay, playdirector or other external PlayStation libraries. This is a genuine new product constraint and **supersedes any earlier work package wording that assumes selecting/depending on those packages**. Canonical new [first-party dependency sovereignty policy](first-party-dependency-sovereignty-policy.md) and [technical native HA/stdlib source audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md) record accepted rules versus unresolved technical exceptions.

**WP-01 can still be fully independent:** own Python asyncio UDP SRCH/response parser, use native HA \`network.async_get_ipv4_broadcast_addresses(hass)\` (not netifaces) and source-validated 9302/00030010 PS5 candidate, retain optional DDP app header and strict 200/620/UNKNOWN. **WP-02/03:** own identity, per-console polling, event/session reducer, native HA entities. **WP-04/05:** stdlib sqlite3 owned worker and vanilla JavaScript dashboard with HA WebSocket. **WP-06:** code framing can be first-party but encrypted registration/standby remains **BLOCKED_CRYPTO_BACKEND**; stdlib does not provide general-purpose AES-CFB/CBC, and handmade AES is prohibited. **WP-07:** own HTTP logic via HA-managed client, but Sony PSN authorization remains a separate gate.

Do not start programming or spawn a new feature branch on the basis of this documentation alone. Do not automatically expand the speculative test inventory; existing SPECs receive targeted dependency, parser and crypto feasibility acceptance checks. The previous research freeze never restricted an **explicit new maintainer architecture constraint**.

## Candidate preinstalled secure AES primitive — not an approved external-library exception (2026-11-06)

HA Core 2026.11.0 itself requires PyCA \`cryptography==50.0.2\` and the package exposes a legacy CFB mode under its Decrepit compatibility namespace. This **could** satisfy \`manifest.requirements=[]\` for first-party Remote Play orchestration without installing an extra pip package, but a direct import would still be a third-party cryptographic library. Under the maintainer's no-external-library rule it remains **NOT APPROVED**. Record a small explicit decision: allow the already-included PyCA AES primitive as a narrow audited exception, or defer Remote Play cryptographic features entirely. The code must never implement AES independently, reuse third-party proprietary key tables or perform unsafe OpenSSL ABI calls. See [policy §7](first-party-dependency-sovereignty-policy.md#7-platform-preinstalled-cryptography-clarification--candidate-only) and [source audit §11](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md#11-newly-verified-ha-core-platform-aes-candidate--zero-additional-pip-packages-but-still-third-party-code). This is a future WP-06 gate and never blocks WP-01 native LAN.

## DDP request correlation and source/heartbeat correction (2026-11-06)

[First-party DDP wire/temporal audit](../research/lan-ddp-wire-and-temporal-correlation-audit-2026-11-06.md) documents a concrete newly identified implementation contract rather than reopening broad research. The inspected PS5 SRCH packet contains no request ID/nonce echo, so **local scan generation is not physical proof of causality**; window-associated replies must remain labelled temporally uncertain. Python's datagram \`sendto\` queues bytes without guaranteed delivery; Chiaki maintains per-host last-ping receipt on unchanged samples but emits only change callbacks; the independent PlayStation Hub history monitor must not depend on sparse HA entity transitions. A real PS5 scan must validate NUL/no-NUL, local ephemeral/source port options, optional app fields and strict 200/620/unknown.

**WP-01 future tests:** pure parser and mock UDP lifecycle for packet/window/identity quality, no PlayStation libraries. **WP-02/03:** actual firmware and native HA interface/host-ID provenance, independent source heartbeats and multi-console fairness. No new ADR/SPEC; no code created; current implementation authorization unchanged. This is fully within the accepted dependency sovereignty policy.
