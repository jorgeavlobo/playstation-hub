# WP-00A — Home Assistant Core baseline and LAN-first interface contracts

**Status:** Technical design frozen for review; NOT implementation authorization, not an accepted ADR, not hardware-validated  
**Date:** 2026-11-05  
**Repository:** `jorgeavlobo/playstation-hub`  
**Target:** One custom integration, `playstation_hub`, distributed via built-in Marketplace/HACS, with one sidebar panel  
**Branch:** `main` research/documentation; feature branches on demand only after explicit authorization; `develop` is legacy reference; obsolete `next` deleted  
**Inputs:** Official Home Assistant 2026.11 source re-audit; ADR-0004–0010; Protocols 01–02; SPEC-001 and SPEC-005–007; WP-00.

> This work package deliberately separates (a) **source-verified capabilities** of Home Assistant Core 2026.11.0, (b) **recommended project contracts**, and (c) **unperformed tests and approvals**. A frozen proposal can guide development without declaring hardware compatibility, SQLite backup safety or Sony API authorization.

## 1. Baseline selection recommendation

**Recommended first development baseline:** **Home Assistant Core 2026.11.0** on its supplied **Python 3.14.2 or newer compatible patch version**.

**Pin evidence:** Core source tag `2026.11.0` identifies package version `2026.11.0` and `requires-python = ">=3.14.2"` in `pyproject.toml`. Release announcement dated 2026-11-04 confirms integrated Marketplace. This is a concrete, released test target, **not an assertion that earlier Core versions cannot technically work**.

**Recommendation for first supported minimum:** `2026.11.0`, because it gives one coherent Marketplace, DeviceInfo dataclass, device ownership and entity naming baseline without compatibility shims. **Formal minimum-version decision remains pending maintainer approval and actual install tests.** Older versions, including 2026.10, can be evaluated later if there is a user need; no backward compatibility is promised or ruled out on assumption alone.

The Marketplace `hacs.json.homeassistant` value is release-specific, read when releases are installed; no implementation/manifest file should be created in WP-00A.

### Version matrix (source, design, tests)

| Dimension | Source-confirmed reference | Proposed first target | Evidence still required |
| --- | --- | --- | --- |
| Core | `2026.11.0` (released) | `2026.11.0` | Clean HA OS install and integration smoke test |
| Python | Core `requires-python >=3.14.2` | Python 3.14.2+ compatible with selected Core | Local dev/CI interpreter, dependency wheels |
| Marketplace | Built in from 2026.11 | One integration under `custom_components/playstation_hub/` | Test manual custom repository installation/upgrade |
| Minimum HA in `hacs.json` | Supported `homeassistant` key | Proposed `2026.11.0` *once approved* | Release-tag behavior in Marketplace |
| Future HA | Unpinned | Latest stable release at release time | Regression test on supported matrix |
| HACS standalone | Historical external integration | Not a mandatory runtime dependency on 2026.11+ | Only if supporting older Core |
| PS5 firmware | No real device tested | Not set | SPEC-007 hardware evidence |
| PSN | Sony client/endpoint basis unverified | Disabled in LAN milestone | SPEC-003 legal/permission evidence |

## 2. Exact Core source references inspected

All source-code findings below were read from **GitHub tag `2026.11.0`**, not the moving `dev` branch.

| API/source | Concrete source fact | Project consequence |
| --- | --- | --- |
| `pyproject.toml` | Python >=3.14.2 | Dependency and CI runtime baseline |
| `homeassistant/config_entries.py` | `ConfigFlow.async_step_dhcp(DhcpServiceInfo)` has generic fallback to `_async_step_discovery_without_unique_id` | Define dedicated per-console DHCP flow |
| `homeassistant/helpers/device_registry.py` | `DeviceInfo` / `ChildDeviceInfo` are dataclasses with `UNDEFINED` defaults | Use typed construction; don't treat as old TypedDict |
| `homeassistant/helpers/device_registry.py` | `DeviceEntry` belongs to a config entry with scoped subentry | Do not bind multiple PSN entries to one physical console DeviceEntry |
| `homeassistant/data_entry_flow.py` | `async_show_form(step_id: str | None = None)` warns on omission | Supply step_id explicitly |
| `homeassistant/helpers/entity.py` | `async_entity_id_changed` and `async_on_remove` lifecycle hooks | Rebind keyed listeners, clean partial-add resources |
| `homeassistant/components/websocket_api/__init__.py` | `async_register_command` supports typed handler / schema | Backend-owned namespaced commands and ACL |
| `homeassistant/components/panel_custom/__init__.py` | `async_register_panel` supports module_url, admin restriction and handle_safe_area | Single native sidebar panel, no external web host |
| `homeassistant/components/knx/websocket.py` | Production example of static path + panel + authenticated WebSocket commands | Source-grounded architecture, not PlayStation proof |
| `homeassistant/helpers/storage.py` | `Store` has `private=False`, `atomic_writes=False` constructor defaults | Do not assume secret encryption or disk-write atomicity |
| `homeassistant/components/backup/manager.py` | Official backup platform pre/post hook protocol | Hook exists; PlayStation Hub consistent SQLite restore still untested |
| `homeassistant/components/playstation_network/config_flow.py` | Native PSN config flow accepts user NPSSO and uses stable account ID | Reference only; no Sony client rights transferred |

**API drift rule:** Each source fact is pinned to tag 2026.11.0. Only compatible public APIs should be used. Source-level support does not replace a test under the installed HA Core and frontend.

## 3. Current binding architecture constraints

1. One Marketplace/HACS integration, no required MQTT broker, PS5-MQTT add-on, Node runtime, external cloud service or separate database server.
2. One sidebar panel with bundled static assets; panel navigation visibility never grants permission for private API calls.
3. LAN discovery and local physical state operate independently of Sony credentials and Remote Play pairing.
4. Multiple independently owned physical-console entries; PSN account entries separate if enabled and authorized.
5. Raw LAN evidence is not trusted account identity or cryptographic pairing identity.
6. Console state and reachability, observation freshness, command progress and account activity are different facts.
7. History is conservative and must not count time across unobserved gaps.
8. Mutable history/credentials must live outside the Marketplace-managed code path unless a separately approved persistence mechanism proves safe.
9. All implementation source, comments, schemas and documentation in English; user UI localization EN and PT-PT.
10. No runtime code is authorized or created by this design checkpoint.

## 4. WP-01 scope — LAN-only protocol foundation

**In scope after approval:**
- Pure UDP datagram builder/parser for PlayStation LAN discovery and status.
- Typed immutable synthetic `DiscoveryCandidate` / `LanObservation` / `ConsoleStatus` models.
- Injected UDP transport interface with directed/broadcast probes, bounded timeouts and cancellation.
- Dedicated identity candidate validation; no pairing/security credential association.
- Pure source-aware state reducer and tests for stale/reordered observations.
- Unit tests and deterministic protocol fixtures only, with no actual network traffic required in CI.

**Out of scope:** Sony sign-in, NPSSO, PSN calls, Remote Play PIN/pairing/wake/standby, physical power OFF inference, long-term SQLite storage, live user history, dashboard data charts, production HACS release, live console scanning without further permission.

A later WP-02 brings the parser into Home Assistant DHCP/ConfigEntry flows and device registry. Pure protocol code should not directly import Home Assistant.

## 5. Contract A — normalized discovery response

Proposed immutable record (conceptual fields, not a Python file):

```text
LanDiscoveryCandidate
  schema_version: 1
  protocol_family: PS5 | PS4 | UNKNOWN
  response_type: DISCOVERY | STATUS
  candidate_host_id: opaque string | null
  host_type: optional validated string
  host_name: optional sanitized string
  system_version: optional opaque string
  discovery_version: optional opaque string
  source_ipv4: validated IPv4 address
  source_interface: optional interface identifier
  raw_status_code: optional three-digit string
  received_at_utc: timezone-aware timestamp
  received_monotonic: in-process monotonic instant
  probe_request_id: unique request identifier
  runtime_generation: incremented run identifier
  parse_status: VALID | INCOMPLETE | REJECTED | UNSUPPORTED
  evidence_level: PROTOCOL_ASSERTION
```

**Ownership:** Transport produces candidates. The identity resolver consumes them; only the resolver may propose a canonical console key. Never use the mutable IP, DHCP hostname, Sony OUI or display name as an immutable history key.

**Parser invariants:** Bounded byte input, strict text control character handling, deterministic duplicate-field policy, normalized header names, supported start-line validation, no raw packet logging, source-address correlation, and no inferred registration or command side effects.

## 6. Contract B — discovery wire inputs and version profile

Protocol 01's upstream reference uses:

```text
SRCH * HTTP/1.1
device-discovery-protocol-version:00030010
```

This is source-derived PS5 IPv4 UDP discovery on destination port **9302**. PS4 candidate support uses UDP **987**, version **00020020**, but is not part of the initial validated release target. Exact newline and terminating newline encoding must match source-pinned fixtures; do not normalize HTTP-like UDP messages into an unrelated HTTP request implementation.

The reviewed playactor discovery retry/timeout settings (5 seconds / 30 seconds) are **reference defaults**, not adopted WP-01 production values. Define independent per-probe timeout, overall discovery deadline, cancellation and traffic budget after synthetic and HA OS measurements.

## 7. Contract C — power and reachability observations

```text
LanStatusObservation
  schema_version: 1
  console_key: canonical key | null until identity verified
  candidate_host_id: opaque ID | null
  source: LAN_DISCOVERY
  source_status_code: opaque status string | null
  power_state: AWAKE | STANDBY | UNKNOWN
  reachability: REACHABLE | UNREACHABLE | UNKNOWN
  received_at_utc
  probe_request_id
  runtime_generation
  observation_id
  valid_until_monotonic: derived if policy known
```

**Source-derived:** Upstream parser maps `620` to STANDBY and all other responses to AWAKE as a heuristic. **PlayStation Hub decision:** `620` is a candidate recognized standby value; other status codes should only become AWAKE after a reviewed allowlist and evidence from source/hardware. Unknown codes remain UNKNOWN rather than defaulting to AWAKE. A valid but unrecognized response may establish network reachability while leaving power unknown.

**No-response:** Packet loss, full power-off, disconnected Wi-Fi, wrong IP, firewall or VLAN limitation are indistinguishable without additional evidence. Use UNKNOWN/unavailable, not physical OFF. Preserve last-known separately and mark staleness. A fresh confirmed STANDBY can be REACHABLE.

## 8. Contract D — identity resolution and multi-console ownership

```text
IdentityResolution
  result: CONFIRMED_CANDIDATE | UNVERIFIED | COLLISION | EXISTING | REJECTED
  candidate_key: optional namespaced candidate host ID
  stable_console_key: optional durable key only after approved verification
  observation_source: probe correlation
  reason_code: safe diagnostic category
```

The `host-id` field is a source-observed *candidate*, not cryptographic proof. Must be validated across awake/standby, reboot, DHCP renewals, network interfaces, firmware changes, and two same-model consoles. A known host ID presented from two unrelated simultaneous addresses is a collision, not immediate merge. An old IP now showing another identity may not inherit keys, power actions, entities or sessions. Until stability is established, synthetic WP-01 tests should avoid persisting arbitrary “stable” keys.

## 9. Contract E — observation ordering and freshness

Required metadata: observation ID, runtime generation, probe request ID, source, source address, receipt UTC and monotonic clock, and scope/identity.

- A later probe generation cannot be overwritten by an earlier delayed response.
- Stale after-restart callbacks cannot write to a new runtime generation.
- Freshness is a per-source policy, independent of ADR-0006's durable session continuity budget.
- Last-known state and current availability remain separate, including during HA restart.
- Transport timeout is a probe outcome, **not** evidence that the console changed power state.
- Use monotonic time for in-process elapsed deadlines; UTC for persisted timestamps.
- Source-specific failures never mutate an unrelated console or PSN account state.

## 10. Contract F — fakeable transport interface

```text
LanTransport (abstract)
  discover(request: DiscoveryRequest) -> async collection[DatagramObservation]
  probe(target_ipv4, interface?, timeout, request_id) -> DatagramObservation | Timeout
  close() -> async resource cleanup

DiscoveryRequest
  family: PS5
  target: broadcast | explicit_ipv4
  interface: optional
  deadline_monotonic
  max_retries
  cancellation_token / task cancellation

DatagramObservation
  payload: bounded bytes
  source_ipv4
  received_at_utc
  received_monotonic
  request_id
```

The implementation should inject an async UDP adapter and a fake adapter with controllable clock and packet queue. No direct Home Assistant event loop calls from parser/model logic. Never allocate per-browser or per-entity transport loops; shared per-console coordinators are future HA integration responsibilities.

## 11. Contract G — Home Assistant ConfigEntry/device lifecycle (WP-02 design gate)

**Future dedicated flow**: `async_step_dhcp(DhcpServiceInfo)` validates candidate via bounded directed UDP probe; the generic fallback in Core 2026.11.0 is insufficient to create independent multi-console entries after the first configuration. Manual IP setup remains supported.

**Entry strategy (conditional ADR-0004):** One physical console entry with its own DeviceEntry; optional PSN account entry with separate service device, never shared hardware device ownership. A physical DeviceEntry has one config entry and possibly one subentry; do not assume the old multi-entry API.

**Entity strategy:** Use DeviceInfo dataclass with `UNDEFINED` defaults; stable `unique_id` not derived from IP/name; contextual translated entity names. Use `async_entity_id_changed` for keyed listeners and `async_on_remove` for cleanup. Prefer `-> None` setup/unload and translated errors; all flow forms/menus/progress explicitly supply `step_id`.

**Test gate:** Two PS5 candidates of same model yield independent flows and entries, only after validated identity; duplicate manual/DHCP candidates dedupe; missing identity never creates a durable entry; refresh/reload/unload cancels queued transports.

## 12. Contract H — sidebar and API constraints (WP-05 design gate)

Pinned Core 2026.11.0 supports `panel_custom.async_register_panel` parameters including `frontend_url_path`, `webcomponent_name`, `module_url`, `require_admin`, and `handle_safe_area`. The KNX integration demonstrates a static path plus custom panel and WebSocket handlers.

**Future initial policy:** One global registration, admin-only private panel pending finer per-user permissions; backend checks permissions per endpoint regardless of panel visibility. Source state snapshots contain no keys, OAuth tokens, raw credentials, unbounded game history or arbitrary user data. WebSocket subscriptions require version/revision gap recovery, bounded page limits and cleanup on disconnect. No API/JS code is written in WP-00A/WP-01.

## 13. Contract I — persistence and backup constraints (WP-04 design gate)

Core 2026.11.0 `Store` has `private=False` and `atomic_writes=False` defaults: it does not automatically encrypt secrets or make every write atomic. HA backup platform pre/post hooks are source-confirmed, but PlayStation Hub SQLite location, WAL live snapshot, archive inclusion and restored session correctness are untested. No database or storage hook is included in WP-01.

Before WP-04, decide the HistoryRepository interface and retention, test SQLite backup high-water mark under active writes, corruption handling, two-console concurrency, credentials stored separately, and HA OS restore.

## 14. Proposed files and responsibilities for future WP-01

```text
custom_components/playstation_hub/
  domain/
    lan_models.py             # Immutable candidate/status records, enums
    identity.py               # Candidate ID policy, collision detection
    observations.py           # Ordering, freshness, source provenance
  transport/
    lan/
      protocol.py             # Pure encoding/decoding; no HA imports
      udp.py                  # Async IO adapter
      interface.py            # Abstract transport and request contract
  const.py                    # Domain and protocol constants, once approved

tests/
  unit/lan/
    test_protocol.py
    test_identity.py
    test_observations.py
  integration/lan/
    test_fake_transport.py
```

Names are **proposals**. Avoid creating empty scaffold files, runtime dependencies or large one-file implementations in advance. English documentation/comments in implementation, modular code, explicit types and comprehensive negative tests.

## 15. Deterministic WP-01 acceptance matrix

| ID | Input / condition | Required result |
| --- | --- | --- |
| BASE-001 | Pin Core 2026.11.0 source version | Exact tag and Python requirement documented |
| LAN-001 | Valid PS5 SRCH request | Exact known bytes and UDP port |
| LAN-002 | Proper response with host-id | Valid typed candidate |
| LAN-003 | Missing or empty host-id | Candidate unverified; no permanent identity |
| LAN-004 | Truncated / oversized / invalid text | Rejected safely |
| LAN-005 | Duplicate or conflicting headers | Deterministic policy and test |
| LAN-006 | Status 620 on validated candidate | STANDBY candidate |
| LAN-007 | Unknown status code | UNKNOWN, not AWAKE or OFF |
| LAN-008 | Missing response/timeout | UNREACHABLE/UNKNOWN source, no OFF |
| LAN-009 | Changed IP / same candidate ID | Candidate resolution without destructive merge |
| LAN-010 | Same IP / changed candidate ID | Identity mismatch blocks associations |
| LAN-011 | Late response from prior probe generation | Ignored |
| LAN-012 | Prior runtime generation after reload | Ignored |
| LAN-013 | Two consoles, one unavailable | Independent source states |
| LAN-014 | Cancel during wait | Bounded cleanup/no sockets leaked |
| LAN-015 | Fake UDP loss/reorder/duplicate | No duplicate current-state mutation |
| LAN-016 | Unrelated source IP datagram | Rejected as candidate for target |
| LAN-017 | No PSN and no RP pairing | LAN parser/transport usable |
| LAN-018 | Unexpected large hostname/HTML | Sanitized, no injection |
| LAN-019 | No Home Assistant import in pure parser | Domain-level test passes |
| LAN-020 | Repeated fake probes | No unbounded tasks or memory growth |

**No test above has been run**. Tests become PASS only with a reproducible CI run or manually recorded evidence; a green synthetic parser suite still does not prove firmware support.

## 16. Acceptance and owner decisions to close WP-00

| Decision | Recommended choice | State |
| --- | --- | --- |
| Research target | Core 2026.11.0 / Python >=3.14.2 | SOURCE_VERIFIED |
| First minimum supported Core | 2026.11.0 | RECOMMENDED, awaiting approval |
| Marketplace distribution | One bundled custom integration | Accepted product design, validation pending |
| LAN first developer milestone | Pure parser / fake transport without PSN/RP | RECOMMENDED |
| Canonical console ID | Derived from validated physical identity, not IP | Proposed; hardware proof pending |
| Unknown power status | Explicit UNKNOWN, no inferred OFF | Established safety requirement |
| Historical source accounting | Separate future stage | Proposed; tests pending |
| Remote Play | Separate feature after byte/crypto proof | Blocked for shipping |
| PSN | Separate feature after Sony authorization | Blocked for shipping |
| Implementation branch | `feature/<scope>` from `main` on demand | Current policy; no branch created |
| First code authorization | Explicit maintainer approval | NOT GIVEN by creating this document |

**WP-00 documentation readiness:** Complete for a *proposed* Core 2026.11 baseline and WP-01 LAN contracts.  
**WP-00 implementation readiness:** **NOT_READY** until maintainer approval of the minimum version/scope, dependency/toolchain choice, and implementation branch creation.  
**WP-01 tests and hardware compatibility:** NOT_STARTED.

## 17. Implementation discipline and test methodology

- Always make test fixtures synthetic; never publish console IDs, IPs, MACs or user network captures.
- No secrets, pairing keys or Sony account data in tests or logs.
- Enforce Python type checking, linting, fake UDP and deterministic clock.
- No network calls in Home Assistant entity getters.
- Revalidate HA APIs when target version changes; don't import moving private Core internals.
- Test clean install, two-console discovery, HA restart, reload and unload only in WP-02 and later.
- Record known fixture provenance from pinned upstream playactor tree and exact expected bytes.
- Use standalone source-focused code reviews before integrating transport and HA.
- Protect `main` with reviewed pull requests for executable changes; no direct source implementation in research phase.

## 18. Official source register

- [Core 2026.11.0 pyproject](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml)
- [Core 2026.11.0 Config Entries](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py)
- [Core 2026.11.0 device registry](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/device_registry.py)
- [Core 2026.11.0 data entry flow](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/data_entry_flow.py)
- [Core 2026.11.0 entity](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity.py)
- [Core 2026.11.0 panel_custom](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/panel_custom/__init__.py)
- [Core 2026.11.0 KNX websocket panel](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/knx/websocket.py)
- [Core 2026.11.0 Store](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/storage.py)
- [Core 2026.11.0 backup manager](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py)
- [Core 2026.11.0 built-in PSN reference](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/config_flow.py)
- [Official release announcement](https://www.home-assistant.io/blog/2026/11/04/release-202611)
- [Marketplace how it works](https://contributors.home-assistant.io/marketplace/how-it-works/)
- [Marketplace version requirements](https://contributors.home-assistant.io/marketplace/guides/releases/)
- [Marketplace hacs.json](https://contributors.home-assistant.io/marketplace/reference/hacs-json/)
- [SPEC-001 LAN acceptance](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-005 Release testing](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [WP-00 readiness](WP-00-implementation-readiness-and-decision-closure.md)
- [Official-source Bible re-audit](../research/official-source-reaudit-home-assistant-2026-11.md)

**Outcome:** Specific source-pinned Core/Python baseline recommendation and pure LAN contracts recorded. No executable implementation, tests, Home Assistant installation, live PS5, PSN login, release or permanent feature branch was created.
