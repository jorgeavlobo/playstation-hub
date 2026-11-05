# WP-00 — Implementation readiness and architecture decision closure

**Status:** Proposed planning package; NOT implementation authorization
**Date:** 2026-11-05
**Branch:** Documentation on `main`; new implementation branches will be created from `main` when work begins; `develop` remains legacy reference
**Depends on:** Formal ADR-0004–0010 review, Protocols 01–10, SPEC-001–007, release quality gates
**Outcome required:** An approved, evidence-backed implementation baseline and precise WP-01 entry criteria

## 1. Purpose and boundaries

WP-00 converts extensive research into executable *future* implementation decisions without pretending hardware compatibility, Sony authorization, or SQLite backup reliability have been demonstrated. The full product goal includes native LAN monitoring, optional Remote Play and PSN, multiple consoles/accounts, one HACS integration and one sidebar panel. LAN-first staging does not delete the remaining requirements.

**Approved product invariants:** No mandatory MQTT/broker, no extra HA App/add-on, one sidebar, English code/comments/documentation, extensible modules, independent console/account identities, no secrets in frontend/history, and no power OFF inference from missing LAN packets.

## 2. Decision state vocabulary

- **ACCEPTED:** Maintainer explicitly approves a bounded architectural decision with recorded rationale and date.
- **PROPOSED:** Design documented, but not approved.
- **CONDITIONAL:** Recommended pending named evidence, not equivalent to ACCEPTED.
- **BLOCKED:** Missing permission, security proof or other mandatory prerequisite.
- **DEFERRED:** Explicitly out of initial implementation scope, not impossible.
- **TESTED:** Separate executable evidence, never implied by ACCEPTED.
- **RELEASE_READY:** All applicable SPEC-005–007 gates and reviewer sign-off.

The formal review recommended conditional acceptance of ADR-0004–0010 but did **not** change their statuses. WP-00 must not do so automatically.

## 3. Home Assistant compatibility baseline — decision template

**Official-source checkpoint (2026-11-05):** Home Assistant Core `2026.11.0` is a released stable reference whose official `pyproject.toml` declares Python `>=3.14.2`. This is our **verified research/test baseline**, not yet an approved minimum supported version. Before implementation:
1. Select a currently released, stable Core version as the minimum supported baseline; record exact version and release date.
2. Verify its bundled Python version and dependency constraints from official HA metadata.
3. Check its `ConfigEntry.runtime_data`, `async_step_dhcp`, unique-ID flow, entity registry, coordinator, repairs, WebSocket, panel_custom, static path and storage APIs.
4. Confirm HACS installation requirements and pinned HACS/Hassfest validation tooling.
5. Define a support matrix: minimum stable, latest stable at release and upgrade/rollback test versions.
6. Capture evidence links, API signatures, sample integration tests and reviewer.
7. Record whether a new release changes frontend safe-area behavior or permissions.

**Compatibility record:**
```yaml
status: TBD
ha_core_minimum: null
ha_core_latest_tested: null
python_version: null
hacs_version: null
hassfest_revision: null
frontend_api_baseline: null
source_commit: null
reviewer: null
approval_date: null
```

Do not start production code based solely on an unstable `dev` branch.

## 4. ADR decision closure register

| ADR | Proposed direction | Safe pre-code decision | Evidence still needed |
| --- | --- | --- | --- |
| 0004 | Separate physical console and PSN account entries | Approve conceptual separation only | Stable console ID, multi-entry HA behavior |
| 0005 | Independent source snapshots, pure deterministic reducer | Approve source/fact separation | Ordering, TTL and HA entity semantics |
| 0006 | Bounded session intervals and explicit gaps | Approve conservative accounting principle | Continuity policy, transition intervals, storage |
| 0007 | Per-owner credentials and single-flight token refresh | Approve isolation/no-secret exposure | Store semantics, crash/rotation tests, Sony permission |
| 0008 | Hybrid Config Entries/Store/SQLite/Recorder | Approve responsibilities conceptually | SQLite path, WAL, live backup and restore |
| 0009 | Native entities, discovery and targeted actions | Approve no MQTT and categorical power | Pinned HA APIs, hardware identity |
| 0010 | One bundled sidebar, authorized WS facade | One panel already accepted | ACL, static registration, snapshot race and mobile |

**No ADR is accepted by this table.** Decisions must be explicitly signed off, ideally with a separate ADR status update and linked commit once the maintainer approves.

## 5. Cross-ADR contract freeze candidates

### 5.1 Physical identity

`PhysicalConsoleKey` is an opaque, stable canonical key, **not an IP address, DHCP hostname or friendly name**. `host-id` is a candidate requiring validation. If identity cannot be established, keep the candidate transient; never fabricate a durable key. A second console on the same IP cannot inherit pairing secrets or history.

### 5.2 Observation envelope

Versioned immutable envelope with source, target key, observation ID, run ID, request generation, UTC receipt time, optional provider event time, validity, normalized fact and redacted error. Preserve independent LAN power, PSN account presence and Remote Play command progress. Do not use cross-source last-write-wins.

### 5.3 Console state

Categorical `AWAKE | STANDBY | UNKNOWN` (future explicit OFF only if supported by verified evidence). Reachability, freshness and last-known are separate. Source expiry never fabricates a power transition.

### 5.4 Session accounting

Use half-open UTC intervals and a separately versioned continuity policy. Source freshness TTL and session maximum continuity gap are distinct settings. Between changed-state point samples, exact transition time is unknown. Do not accumulate unlimited time during outages.

### 5.5 Credential ownership

PSN account tokens and Remote Play console pairing keys have independent repositories and owner namespaces. No credentials in logs, entity attributes, frontend, session database or diagnostics. Persist token generation before declaring durable refresh success; acknowledge provider/local crash window.

### 5.6 API/UI

One integration-scope sidebar registration and versioned authenticated WS API; snapshot/delta revisions prevent missed events. Initially recommend admin-only private history and commands pending finer ACL, with server-side checks mandatory.

## 6. Proposed modular dependency graph

```text
domain/models
   ├── domain/identity
   ├── domain/observations
   ├── domain/reconciliation
   └── domain/session_policy
         ↑
transport/lan -> adapters -> coordinator -> HA entities
transport/remote_play (independent gated extension)
transport/psn (independent permission-gated extension)
         ↓
persistence interfaces -> storage implementation
         ↓
api facade -> authenticated WS -> bundled sidebar
```

Dependencies must not point from domain models into Home Assistant, frontend or concrete transport modules. Adapters are fakeable and testable without a console. No empty scaffold files are to be created in WP-00.

## 7. Proposed WP-01 entry checklist

- [ ] Maintainer explicitly approves WP-01 scope and branch policy.
- [ ] HA Core/Python baseline pinned with official evidence.
- [ ] Physical identity provisional policy agreed, including no durable entry on missing identity.
- [ ] UDP discovery/status grammar and pinned upstream provenance recorded.
- [ ] Pure parser and fake transport interfaces reviewed.
- [ ] Deterministic synthetic fixtures and negative-case list approved.
- [ ] Python lint/type/test conventions chosen.
- [ ] No secrets or actual household console IDs in fixtures.
- [ ] No LAN wake, Remote Play pairing or PSN calls in WP-01.
- [ ] Acceptance evidence format agreed (test ID, commit, versions, actual result).
- [ ] Initial directory/module boundaries reviewed.
- [ ] User has explicitly authorized implementation and the purpose-specific branch name.

If any mandatory entry criterion remains open, WP-01 is **NOT_READY**, even if a planning document exists.

## 8. Work-package acceptance plan

| Package | Minimal output | Must not claim |
| --- | --- | --- |
| WP-01 | Pure LAN discovery/status parser and fake transport tests | Actual PS5 compatibility |
| WP-02 | Native HA discovery/config flow and multi-console registry tests | Hardware ID proven stable |
| WP-03 | Reducer, cached native entities and lifecycle tests | PSN presence is physical state |
| WP-04 | Transactional history and tested backup/restore | SQLite safe merely because WAL enabled |
| WP-05 | Bundled panel, authenticated WS, bounded history queries | Panel visibility equals API authorization |
| WP-06 | Validated Remote Play extension | Wake/standby works without byte/hardware proof |
| WP-07 | Sony-permitted PSN adapter and account UX | Community OAuth client is authorized |
| WP-08 | HACS release checks, regression and signed-off evidence | Quality tier or hardware support without tests |

## 9. Open blockers and triage

| ID | Severity | Blocking scope | Required resolution |
| --- | --- | --- | --- |
| BLK-001 | P0 | Multi-console durable identity | Verify host-id stability and collision behavior |
| BLK-002 | P0 | HA runtime | Pin stable Core/Python APIs |
| BLK-003 | P0 | Historical duration | Approve continuity/uncertainty policy |
| BLK-004 | P0 | History release | Prove SQLite live backup and restore |
| BLK-005 | P0 | Remote Play | Wake credential and registration/crypto vectors |
| BLK-006 | P0 | PSN | Sony client/redirect/endpoint permission |
| BLK-007 | P0 | Private panel | Backend ACL and lifecycle tests |
| BLK-008 | P1 | Firmware support | Real model/firmware test matrix |
| BLK-009 | P1 | Data privacy | Retention, export, account unlink |
| BLK-010 | P1 | Supply chain | Dependency license and pinned CI validation |

These blockers have different scopes: BLK-005/006 do not prevent pure synthetic LAN parser research, but BLK-001/002 must be resolved before claiming complete HA discovery compatibility.

## 10. Risk-based implementation rules

- Keep `develop` as read-only legacy reference, never wholesale merge its MQTT, single-player or Lovelace code.
- Keep research documentation on `main` until implementation is authorized; then create a purpose-specific `feature/*` branch from `main`.
- Each future implementation PR must link ADR/SPEC tests and exact supported HA versions.
- Reject unverified default status-code mappings, unbounded retries, raw credentials, optimistic command success and implicit cross-console identity reassignment.
- A capability can be implemented behind a disabled flag for controlled tests but cannot be advertised or enabled without applicable release gates.
- Favor small, reviewed modules and complete-file changes with detailed English comments.

## 11. Acceptance evidence and sign-off template

```yaml
work_package: WP-00
status: PROPOSED
maintainer_approval: null
approval_date_utc: null
architecture_guide_version: "0.40.0"
target_branch_for_implementation: null # create feature/<scope> from main when authorized
ha_core_baseline: null
python_baseline: null
accepted_adrs: []
conditional_adrs: ["0004", "0005", "0006", "0007", "0008", "0009", "0010"]
blocking_issues: ["BLK-001", "BLK-002", "BLK-003", "BLK-004", "BLK-005", "BLK-006", "BLK-007"]
synthetic_tests_run: 0
hardware_tests_run: 0
security_review: NOT_RUN
release_authorization: false
```

This is a documentation template, not a generated approval or an assertion that all other issues are resolved.

## 12. Next research actions

1. Pin official stable Home Assistant Core and Python baseline with source-level API inventory.
2. Review ADR-0004/0005 conceptual choices with maintainer for bounded acceptance.
3. Establish a canonical hardware identity verification procedure and safe interim discovery policy.
4. Investigate HA OS backup hooks and SQLite online snapshot lifecycle in the target release.
5. Complete Remote Play wake/registration byte-level trace separately.
6. Continue Sony authorization research separately; no OAuth-client substitution.
7. Prepare WP-01 test plan and acceptance evidence without writing implementation code.

## 13. References

- [Formal architecture review](formal-architecture-review-adr-0004-0010.md)
- [Cross-protocol review](cross-protocol-review-01-10.md)
- [Compliance matrix](../standards/compliance-matrix.md)
- [Release quality gates](../release/quality-gates.md)
- [SPEC-001](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md)
- [SPEC-003](../specifications/SPEC-003-psn-authorization-and-availability.md)
- [SPEC-005](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md)
- [SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md)
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/development_testing/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://www.hacs.xyz/docs/publish/integration/

**Outcome:** WP-00 readiness criteria, contract freeze candidates, blocker ownership and staging documented. No code, actual tests, hardware verification or maintainer approval was performed.

## Branch strategy revision — 2026-11-05

The maintainer has rejected using an empty permanent `next` implementation branch. Research and architecture documentation remain on `main`; `develop` is retained as a read-only legacy reference. When implementation is authorized, create a short-lived, purpose-specific branch from the current `main` (for example `feature/lan-discovery`), validate through a pull request, and merge reviewed code into `main`. Do not recreate or use `next` as the designated implementation branch. This decision does not authorize deleting any existing remote branch; branch cleanup is a separate explicit action.

## Official-source re-audit alignment (2026-11-05)

The [official HA 2026.11 / Marketplace re-audit](../research/official-source-reaudit-home-assistant-2026-11.md) provides a pinned **research baseline** of Core 2026.11.0 with Python >=3.14.2; final `ha_core_minimum` remains subject to explicit approval and compatibility tests. WP-00 must also validate DeviceInfo dataclasses, one-config-entry-per-device registry ownership, setup/unload/migrate `-> None` or translated errors, explicit `step_id` in flows, in-place entity-ID changes, config-entry-scoped repairs, 2026.11 entity naming, Marketplace `hacs.json.homeassistant`, local branding, custom translations and the new single-panel theme tokens. The validated manifest category candidate is `media_entertainment.gaming`. No implementation was authorized and no readiness gate is marked passed.
