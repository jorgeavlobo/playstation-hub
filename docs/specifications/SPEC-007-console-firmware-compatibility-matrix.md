# SPEC-007 — Supported console, firmware and network compatibility matrix

**Status:** Proposed compatibility and evidence specification; no hardware tested  
**Date:** 2026-11-05  
**Branch:** `main` documentation only; `next` and `develop` unchanged  
**Sources:** Protocols 01–07, ADR-0004/0005/0009, SPEC-001/002/005/006, pinned playactor and PS5-MQTT community implementations

> A protocol value found in source code is not proof of support for a retail console, firmware revision, network topology or Home Assistant release. All cells below are **UNTESTED** unless expressly classified as **SOURCE_OBSERVED**. Do not market any model as supported until actual test evidence exists.

## 1. Goals and compatibility vocabulary

The first product target is PlayStation 5 LAN monitoring with optional, independently gated Remote Play wake/standby. PS4 and other Sony devices are research candidates, not a promised first release. This document specifies exactly how hardware variants, firmware, power modes, transports and Home Assistant installation types will be tested and recorded.

**Evidence states:**
- `SOURCE_OBSERVED`: code or published source shows a proposed protocol path, not verified on PlayStation Hub.
- `SYNTHETIC_PASS`: deterministic fixture test passed for a specific implementation revision.
- `HA_OS_PASS`: integration test passed on a specified HA OS/Core build with a fake or physical device clearly indicated.
- `HARDWARE_PASS`: authorized real device and firmware test passed with evidence.
- `HARDWARE_FAIL`: reproducible failure, with environment and symptoms.
- `NOT_TESTED`: no evidence; the default.
- `BLOCKED`: prerequisite (e.g. missing identity, rights or hardware) prevents testing.
- `UNSUPPORTED`: explicitly excluded from the declared release scope, not a claim that the protocol is technically impossible.

`SUPPORTED` is a **release decision** after all applicable capability gates pass, not a test status. Firmware changes may invalidate previous support and require retesting.

## 2. Hardware family inventory

| Hardware family / form | Discovery candidate | Remote Play candidate | Initial release posture | Actual verification |
| --- | --- | --- | --- | --- |
| PlayStation 5 original disc model | PS5 UDP 9302 | PS5 registration/control path | Target candidate | NOT_TESTED |
| PlayStation 5 original Digital Edition | PS5 UDP 9302 | PS5 registration/control path | Target candidate | NOT_TESTED |
| PlayStation 5 revised/slim disc model | PS5 UDP 9302 | PS5 registration/control path | Target candidate | NOT_TESTED |
| PlayStation 5 revised/slim Digital Edition | PS5 UDP 9302 | PS5 registration/control path | Target candidate | NOT_TESTED |
| PlayStation 5 Pro | PS5 UDP 9302 hypothesized from family | PS5 path hypothesized | Candidate; explicit firmware test required | NOT_TESTED |
| PlayStation 4 original | PS4 UDP 987 | PS4-specific protocol variant | Deferred | NOT_TESTED |
| PlayStation 4 Slim | PS4 UDP 987 | PS4-specific protocol variant | Deferred | NOT_TESTED |
| PlayStation 4 Pro | PS4 UDP 987 | PS4-specific protocol variant | Deferred | NOT_TESTED |
| PlayStation Portal | Not established as standalone console target | Remote Play client, not automatically a host | Out of scope pending evidence | NOT_TESTED |
| PlayStation 3 / handheld legacy devices | Not established for this protocol | Not established | Out of scope | NOT_TESTED |
| PC Remote Play client | Not a physical PlayStation console | Client, not a host | Out of scope | NOT_TESTED |

The names above describe broad product families, not Sony chassis codes, exact CFI model IDs or firmware compatibility. Record the exact user-visible model/serial *privately* during hardware validation; publish only redacted model family and firmware. Do not infer PS5 Pro behavior from the original PS5 without tests.

## 3. Protocol-to-family matrix

| Capability | PS5 family | PS4 family | Evidence |
| --- | --- | --- | --- |
| IPv4 UDP discovery `SRCH` | Port 9302, version `00030010` | Port 987, version `00020020` | SOURCE_OBSERVED; Protocol 01 |
| HTTP-like status response | Parsed by community implementation | Source branch exists | SOURCE_OBSERVED; Protocol 02 |
| Standby status code `620` | Community mapping | Requires independent check | SOURCE_OBSERVED, not complete Sony state table |
| Other status codes -> AWAKE | Upstream heuristic only | Upstream heuristic only | NOT an accepted safe mapping |
| Wake `WAKEUP` | UDP 9302 | UDP 987 | SOURCE_OBSERVED; Protocol 03 |
| Registration discovery | `SRC3/RES3`, UDP 9295 | `SRC2/RES2`, UDP 9295 in source | SOURCE_OBSERVED; Protocol 04 |
| Registration HTTP | `/sie/ps5/rp/sess/rgst` | Different path/crypto variant | SOURCE_OBSERVED; PS4 not validated |
| Remote Play crypto | PS5 AES-CFB and source-specific tables | Variant-dependent | SOURCE_OBSERVED; SPEC-002 |
| Session/control | PS5 `:9295` init/control | PS4-specific mapping | SOURCE_OBSERVED; SPEC-002 |
| Wake credential derivation | Unresolved | Unresolved for supported release | BLOCKED |
| Authenticated standby | `0x0050` in source | Not release verified | SOURCE_OBSERVED, HARDWARE NOT_TESTED |
| PSN account activity | Account/platform, not hardware ID | Account/platform, not hardware ID | Permission blocked by SPEC-003 |
| Game artwork/library | PSN account scope | PSN account scope | Permission/rights blocked independently |

**Important:** The PS4 branch may have different registration keys, protocol versions, cryptographic algorithms and firmware behavior. A shared transport abstraction must use explicit `ConsoleProtocolProfile` selected from validated evidence, not a PS5 default applied to PS4.

## 4. Firmware compatibility strategy

Maintain a private test inventory and a public **verified firmware range table** once evidence exists. Do not invent a minimum firmware version or treat “latest” as a precise test environment.

```text
CompatibilityEvidence
  evidence_id: immutable test-run reference
  console_family: PS5_ORIGINAL | PS5_SLIM | PS5_PRO | PS4_ORIGINAL | ...
  model_code_redacted: optional model family/CFI series
  firmware_version: exact reported system software version
  hardware_interface: ethernet | wifi_2_4 | wifi_5 | wifi_6 | unknown
  network_topology: same_subnet | vlan_directed | isolated | ...
  ha_core_version: exact
  ha_os_version: optional exact
  hacs_version: exact
  integration_commit: git SHA
  capability_id: DISCOVERY | POWER | WAKE | PAIR | SESSION | STANDBY
  expected_result / actual_result
  test_status: evidence state
  test_timestamp_utc
  reviewer
  redacted_artifact_reference
```

A firmware update triggers revalidation of at least discovery, status mapping and privileged command safety. A compatibility regression must be reflected in the UI capability flag, changelog and known-issues list. If the firmware cannot be obtained without exposing sensitive device identifiers, record a bounded `unknown` and withhold broad support claims.

## 5. Power-state and availability test matrix

| Test ID | Scenario | Required assertion |
| --- | --- | --- |
| HW-P001 | PS5 awake, LAN responding | Fresh validated awake observation, identity matched |
| HW-P002 | PS5 rest mode, LAN responding | `STANDBY` only on recognized response |
| HW-P003 | PS5 rest mode, no response | `UNKNOWN/UNAVAILABLE`, never automatic OFF |
| HW-P004 | Fully powered off or disconnected | No response does not establish an OFF protocol fact |
| HW-P005 | Console transitioning awake -> standby | Transition detection time distinguished from physical event time |
| HW-P006 | Console transitioning standby -> awake | Wake command success only after fresh state confirmation |
| HW-P007 | Wi-Fi disconnect while console awake | Last-known stale, no invented state change |
| HW-P008 | Console restart/firmware update | Stable identity if evidenced; otherwise mismatch handled |
| HW-P009 | Unknown response status code | Reachable may be true; power UNKNOWN |
| HW-P010 | PSN offline while console awake | Independent account and hardware facts |
| HW-P011 | HA restart during power transition | No fabricated continuous session duration |
| HW-P012 | Two same-model consoles | Separate physical identities and histories |

Record time between probes, poll interval, source status code, freshness TTL and observed latency. **No numeric thresholds are approved yet**; measure before setting defaults.

## 6. Network transport and topology matrix

| ID | Topology | Discovery expectation | Safety requirement |
| --- | --- | --- | --- |
| NET-C001 | HA OS Ethernet + PS5 Ethernet, same subnet | UDP discovery candidate | Deduplicate and validate identity |
| NET-C002 | HA OS Ethernet + PS5 Wi-Fi, same LAN | Discovery where broadcast allowed | No Wi-Fi-specific false assumptions |
| NET-C003 | HA OS Wi-Fi + PS5 Ethernet | Discovery if router allows | Retry/cancellation bounds |
| NET-C004 | Dual-stack IPv4/IPv6 | IPv4 protocol supported candidate | Do not promise IPv6 discovery |
| NET-C005 | VLAN separated, directed routing permitted | Manual IP directed probe | No claim of broadcast across VLAN |
| NET-C006 | VLAN with UDP filtered | Unavailable/manual diagnostics | No false OFF |
| NET-C007 | Wi-Fi client isolation | Discovery/control may fail | Explain topology limitation |
| NET-C008 | Multiple HA interfaces | Probe selected interface and avoid duplicates | No uncontrolled broadcast flood |
| NET-C009 | DHCP address renewal | Same console key | No history/entity ID change |
| NET-C010 | IP reused by different device | Identity mismatch | Block privileged key use |
| NET-C011 | DHCP candidate without valid LAN reply | Unverified candidate | No config entry/commands |
| NET-C012 | Broadcast unavailable, directed works | Manual fallback | No MQTT dependency |
| NET-C013 | Multiple HA instances | No exclusive ownership assumption | Limit simultaneous probes |
| NET-C014 | Console behind NAT/Internet | No unsupported remote LAN promise | No arbitrary public socket probing |
| NET-C015 | Firewall denies UDP 9302 or TCP 9295 | Feature-specific failure | LAN status vs Remote Play independently diagnosed |

Wi-Fi generation, band and Ethernet model are test metadata; none automatically proves a different protocol. Power-saving and router multicast/broadcast settings may affect discovery. Do not require changing home router security settings without explicit user understanding.

## 7. Remote Play compatibility and safety matrix

| Test ID | Requirement | Status |
| --- | --- | --- |
| HW-R001 | Explicit PIN registration on supported PS5 model/firmware | NOT_TESTED |
| HW-R002 | Registration fields validated, keys durable and scoped | NOT_TESTED |
| HW-R003 | Session init nonce and authenticated control socket | NOT_TESTED |
| HW-R004 | Login/passcode handling if console requests it | NOT_TESTED |
| HW-R005 | Heartbeat and bounded session closure | NOT_TESTED |
| HW-R006 | Wake from rest mode with valid pairing | NOT_TESTED |
| HW-R007 | Standby from awake with fresh state | NOT_TESTED |
| HW-R008 | Already-standby request never wakes console | NOT_TESTED |
| HW-R009 | Command sent but state not confirmed -> UNCONFIRMED | NOT_TESTED |
| HW-R010 | Two consoles with distinct keys | NOT_TESTED |
| HW-R011 | Wrong IP/identity cannot receive prior keys | NOT_TESTED |
| HW-R012 | Unpair/re-pair after console reset | NOT_TESTED |
| HW-R013 | Remote Play session conflict with other client | NOT_TESTED |
| HW-R014 | Wi-Fi loss or HA unload during command | NOT_TESTED |
| HW-R015 | Firmware upgrade invalidates or preserves pairing | NOT_TESTED |

All SPEC-002 byte and crypto gates are prerequisites for real command support. Do not use hardware tests to justify skipping source license/credential safety review.

## 8. Home Assistant platform compatibility

The console matrix is independent from Home Assistant compatibility. Each supported product release must record:
- Exact HA Core and HA OS versions and install type.
- HACS version and custom integration manifest schema.
- Python/runtime dependencies and native platform availability.
- DHCP Discovered flow behavior with zero, one and two configured consoles.
- Config Entry unload/reload, entity registry stability, repairs, diagnostics and permission checks.
- Static sidebar asset registration, WebSocket subscription and mobile safe-area behavior.
- SQLite backup/restore and credential reauth after restart.
- Whether the official `playstation_network` integration is present and coexistence behavior.

A successful test against `home-assistant/core dev` does not establish support for a released HA Core version. Test the oldest declared supported stable and the latest supported stable.

## 9. Capability negotiation and user-facing compatibility

A console's supported capability flags should derive from validated protocol profile and live availability, not from model marketing name alone:

```text
ConsoleCapabilities
  lan_discovery: supported | unsupported | unknown
  local_power_observation: supported | unsupported | unknown
  remote_play_pairing: supported | unsupported | unknown
  wake: supported | unsupported | unknown
  standby: supported | unsupported | unknown
  game_attribution: confirmed | inferred | ambiguous | unknown
  provider_presence: optional_account_scope
  firmware_verified: boolean
  capability_evidence_revision: optional
```

**Examples:** A discovered PS5 may expose power observations but show “Pairing not configured” for standby. A model with no tested wake credential must not expose a working Wake action. PSN game reports are account-scoped regardless of the model's marketing name. The sidebar should show firmware/compatibility diagnostics without exposing serial numbers.

## 10. Evidence capture and privacy

Hardware test evidence should contain test ID, model family, firmware, network topology, HA version, integration commit, sanitized packet/status summary, expected and actual results, timestamps and reviewer. Do not commit serial numbers, real MAC/host IDs, account IDs, NPSSO, OAuth tokens, pairing keys, registration PINs, private packet captures or child usage history. Store sensitive raw captures, if ever essential and explicitly authorized, outside the public repo under controlled access with a deletion schedule.

A test with one PS5 cannot automatically certify all original/slim/Pro firmware families. Multiple console testing is required before claiming independent multi-console operation.

## 11. Test execution stages and prerequisites

1. **Research:** Pin upstream source commits and record candidate protocol profile.
2. **Synthetic:** Implement deterministic parser/serializer and crypto known-answer fixtures.
3. **HA integration:** Fake DHCP and fake consoles, multiple entries and lifecycle.
4. **Lab HA OS:** Clean HACS installation, backup/restore, UI and permissions.
5. **Live LAN:** Explicitly authorized console model/firmware, awake/rest discovery and IP changes.
6. **Live Remote Play:** Explicit pairing, key isolation, wake/standby safety, command confirmation.
7. **Regression:** Repeat affected capability matrix after firmware/HA Core upgrades.
8. **Release:** Link all evidence and obtain human sign-off under SPEC-005/006.

No step is marked completed merely because its procedure is written.

## 12. Release compatibility gates

| Gate | Evidence | Status |
| --- | --- | --- |
| COMP-G01 | Supported hardware families selected and declared | NOT_APPROVED |
| COMP-G02 | Exact firmware baseline documented | NOT_TESTED |
| COMP-G03 | PS5 LAN discovery/status hardware tests | NOT_TESTED |
| COMP-G04 | Identity stability across IP/reboot/interfaces | NOT_TESTED |
| COMP-G05 | Multi-console hardware behavior | NOT_TESTED |
| COMP-G06 | Network topology and manual directed fallback | NOT_TESTED |
| COMP-G07 | HA Core/OS/HACS version matrix | NOT_TESTED |
| COMP-G08 | HA entities, actions and sidebar across versions | NOT_TESTED |
| COMP-G09 | Remote Play pairing/crypto compatibility if enabled | BLOCKED/NOT_TESTED |
| COMP-G10 | Wake/standby safe confirmation if enabled | NOT_TESTED |
| COMP-G11 | Firmware update regression policy and tests | NOT_TESTED |
| COMP-G12 | Public compatibility table with evidence and limitations | NOT_APPROVED |

## 13. Known uncertainties and explicit exclusions

- No actual PS5 firmware version has been observed by PlayStation Hub.
- No actual PS5 original/slim/Pro has been tested in this documentation phase.
- The LAN `host-id` stability and relationship to DHCP/Remote Play identifiers remain unknown.
- PS4 support is deferred; a source-observed PS4 UDP path is not a supported release feature.
- PS5 Pro may share PS5-family behavior but has no independent evidence here.
- PS Portal is a Remote Play client and not assumed to expose a PS5 host service.
- Remote Play wake credential derivation and full registration byte contract remain unresolved in SPEC-002.
- A fully powered-off device may be indistinguishable from a disconnected/unreachable device without a separate verified signal.
- Sony PSN APIs remain blocked by SPEC-003 permission gates.
- IPv6-only discovery, cross-Internet console control and untested game launch are not promised.

## 14. Open decisions and approval checklist

- [ ] Confirm v1 supported hardware scope (recommend PS5 family first, PS4 deferred).
- [ ] Obtain actual PS5 model/firmware evidence without publishing sensitive IDs.
- [ ] Select a minimum supported HA Core/OS release.
- [ ] Choose which network topologies are explicitly supported versus best effort.
- [ ] Verify canonical host ID stability and MAC/interface behavior.
- [ ] Decide whether original, slim and Pro require independent certification or a limited family claim.
- [ ] Define numeric LAN and command latency/timeout thresholds from real tests.
- [ ] Resolve SPEC-002 Remote Play byte/crypto blockers.
- [ ] Approve compatibility evidence format, reviewer and regression frequency.
- [ ] Link every claimed capability to passed tests and public limitations.
- [ ] Maintain independent PSN authorization scope and feature flags.
- [ ] Approve the final hardware compatibility table before release.

## 15. References

- [Protocol 01 — LAN discovery](../protocols/01-lan-discovery.md)
- [Protocol 02 — Console status](../protocols/02-console-status.md)
- [Protocol 03 — Wake](../protocols/03-console-wakeup.md)
- [Protocol 04 — Registration](../protocols/04-remote-play-registration.md)
- [Protocol 05 — Cryptography](../protocols/05-remote-play-cryptography.md)
- [Protocol 06 — Session](../protocols/06-remote-play-session.md)
- [Protocol 07 — Commands](../protocols/07-remote-play-commands.md)
- [SPEC-001 — LAN acceptance](SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-002 — Remote Play acceptance](SPEC-002-remote-play-byte-contract-and-safety.md)
- [SPEC-003 — PSN authorization](SPEC-003-psn-authorization-and-availability.md)
- [SPEC-005 — Release quality gates](SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [SPEC-006 — Security threat model](SPEC-006-security-privacy-threat-model.md)
- [ADR-0004 — Identity](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 — State reconciliation](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0009 — Home Assistant integration](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- https://github.com/dhleong/playactor/tree/93ee087445db368acaba9ad50099bce56ca9141d
- https://github.com/FunkeyFlo/ps5-mqtt
- https://developers.home-assistant.io/docs/config_entries_index/
- https://www.hacs.xyz/docs/publish/integration/

**Outcome:** Hardware-family and protocol candidate matrix, twelve power tests, fifteen network cases, fifteen Remote Play tests, HA platform compatibility criteria and twelve unpassed release gates. No hardware or executable test was performed.
