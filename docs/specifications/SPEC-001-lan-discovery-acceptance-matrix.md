# SPEC-001 — LAN discovery acceptance matrix and multi-console onboarding

**Status:** Proposed research specification; no executable implementation or live device validation  
**Date:** 2026-11-05  
**Primary inputs:** Protocol 01, Protocol 02, ADR-0004, ADR-0005, ADR-0009, official Home Assistant discovery/config-flow guidance  
**Branch:** `main` documentation only; `next` implementation and `develop` legacy reference unchanged  
**Test philosophy:** Deterministic synthetic packets and fake HA discovery services first; real Home Assistant OS and user-authorized console tests later.

## 1. Scope and acceptance objective

The PlayStation Hub shall detect candidate consoles on a supported IPv4 LAN, validate actual PlayStation discovery responses, establish a defensible stable physical-console identity, offer Home Assistant **Settings > Devices & services > Discovered** where DHCP discovery is available, and allow independently configured multiple consoles. Manual directed discovery must remain available for networks without broadcast/DHCP visibility. The feature shall not depend on PSN, NPSSO, MQTT, Remote Play pairing, a Supervisor App or a separate server.

**A discovery event is a candidate, not proof of hardware identity or power.** No console entry, credentialed command or user history assignment may be created from a Sony MAC prefix or hostname alone.

## 2. Evidence and wire contract

| Property | Upstream research reference | Acceptance treatment |
| --- | --- | --- |
| IPv4 UDP discovery | Protocol 01; playactor discovery UDP implementation | Test datagram send, response parser, timeouts, cancellation |
| PS5 discovery destination | UDP 9302 in reviewed playactor | Source-observed; verify on actual PS5 firmware |
| PS4 discovery destination | UDP 987 in reviewed playactor | Future optional; never assume v1 support |
| PS5 discovery protocol version | `00030010` | Synthetic fixture and compatibility test |
| PS4 discovery protocol version | `00020020` | Synthetic fixture and future-scope gate |
| Discovery method | `SRCH` | Exact message formatting and safe bounded parser |
| Broadcast destination | `255.255.255.255` in upstream | Test interface routing; directed address fallback |
| UDP source bind | Ephemeral in upstream | Avoid fixed-port conflicts; verify response routing |
| `host-id` | Returned by upstream response parser | Candidate stable ID; uniqueness and persistence **unverified** |
| `host-type`, `host-name`, `system-version` | Source-observed response fields | Validate and display only supported parsed values |
| Status response | Protocol 02 | Reachability and known awake/standby where recognized; no silence=OFF |
| Upstream discovery retry/timeout | 5-second retry / 30-second total in reference | Do not adopt as universal product defaults without measurement |

**Source URLs:**
- https://github.com/dhleong/playactor
- https://github.com/FunkeyFlo/ps5-mqtt
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/manifest.json
- https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py
- https://developers.home-assistant.io/docs/config_entries_index/
- https://www.home-assistant.io/integrations/dhcp/

### 2.1 Synthetic request fixture

```text
SRCH * HTTP/1.1
device-discovery-protocol-version:00030010
```

Transport encoding, line endings, trailing newline behavior and case sensitivity must be tested against the pinned playactor source and actual console response. Do not infer that the HTTP-like UDP format is an HTTP server or that an unauthenticated response proves ownership.

### 2.2 Synthetic response fixture policy

Create fixtures with clearly fictional `host-id`, `host-name`, `host-type`, `system-version`, and source addresses. Store positive awake/standby, unknown code, missing host ID, invalid encoding, duplicate fields, oversized packet, conflicting identity, truncated datagram, delayed response and hostile text variants. **No real household MAC, host ID, account ID, pairing key or LAN capture belongs in public fixtures.**

## 3. Discovery entry points and architecture

```text
Home Assistant DHCP candidate ------+
                                     |
Directed/manual IPv4 address --------+--> DiscoveryCandidate
                                     |         |
Scheduled bounded LAN scan ----------+         v
                                     Validated UDP probe
                                             |
                                  Canonical identity resolver
                                             |
                                Duplicate / collision / ignore check
                                             |
                                  User confirmation config flow
                                             |
                                Console config entry + HA device
```

- The integration domain is `playstation_hub`, not the official `playstation_network`.
- Use a dedicated `async_step_dhcp` rather than the built-in PSN integration's generic fallback, which is insufficient for multi-console onboarding.
- Discovery does **not** pair Remote Play, wake hardware or authenticate to Sony.
- One physical console gets one stable config entry (preferred ADR-0004 option, still unapproved).
- Address, hostname, MAC and source interface are locators/diagnostic hints; do not treat them as immutable keys.
- An IP now returning a different verified console identity must not inherit the old console's credentials or history.

## 4. Proposed candidate and validation state machine

```text
RECEIVED -> SANITIZED -> PROBING -> RESPONSE_PARSED
 -> IDENTITY_VERIFIED -> DEDUPLICATED -> AWAITING_CONFIRMATION
 -> CONFIGURED

RECEIVED/SANITIZED/PROBING -> REJECTED | TIMEOUT | CANCELLED
RESPONSE_PARSED -> UNVERIFIED_IDENTITY | UNSUPPORTED_MODEL
IDENTITY_VERIFIED -> EXISTING_ENTRY | IGNORED | IDENTITY_COLLISION
```

`IDENTITY_VERIFIED` means a *validated protocol-level identifier and matching response*; it is not a cryptographic proof against an active LAN attacker. Document the network trust boundary and revalidate before privileged Remote Play actions. If a trustworthy persistent ID cannot be established, no permanent hardware identity should be fabricated.

## 5. Acceptance matrix — packet parsing

| Test ID | Scenario | Expected result | Gate |
| --- | --- | --- | --- |
| LAN-001 | Well-formed PS5 response with supported protocol and stable candidate host ID | Parsed typed candidate, no side effects | Unit |
| LAN-002 | Missing host ID | Unverified identity; no permanent config entry | Unit |
| LAN-003 | Empty/whitespace host ID | Rejected, never coalesced to one fake ID | Unit |
| LAN-004 | Unsupported protocol version | Capability unknown/unsupported; no credentialed action | Unit |
| LAN-005 | Unknown status code with valid host identity | Reachable, power UNKNOWN; no OFF inference | Unit |
| LAN-006 | Invalid UTF-8 / control characters | Safe parser failure and sanitized diagnostic | Unit |
| LAN-007 | Oversized UDP datagram | Bounded reject without memory amplification | Unit |
| LAN-008 | Repeated/conflicting response fields | Deterministic reject or explicit safe policy | Unit |
| LAN-009 | Header capitalization/ordering differences | Follow tested protocol rules, no speculative leniency | Unit |
| LAN-010 | Embedded newline or malicious hostname text | Escape UI, prevent log/HTML injection | Unit |
| LAN-011 | Truncated response | No partial trusted identity | Unit |
| LAN-012 | Multiple valid packets from same host ID | One candidate, updated last seen | Unit |
| LAN-013 | Same host ID from conflicting simultaneous addresses | Collision/quarantine, no blind merge | Unit |
| LAN-014 | IP changed, same validated identity | Same device/entry, new locator | Integration |
| LAN-015 | Same IP, different validated identity | Block old credentials and history reassignment | Integration |
| LAN-016 | Unsolicited response from unknown sender | Source validation; no automatic entry | Unit |
| LAN-017 | Valid response during standby | Standby when protocol explicitly confirms; otherwise UNKNOWN | Hardware |
| LAN-018 | No response to query | Timeout/unavailable, never confirmed OFF | Unit |

## 6. Acceptance matrix — Home Assistant discovery and config flows

| Test ID | Scenario | Expected result | Gate |
| --- | --- | --- | --- |
| HA-001 | DHCP match on fresh unconfigured integration | Candidate probed; Discovered prompt only if verified | HA |
| HA-002 | Existing console A, new console B discovered | B gets independent flow and entry | HA |
| HA-003 | DHCP candidate is not PlayStation | No confirmed entry, no misleading prompt | HA |
| HA-004 | Same console via DHCP and manual input | One canonical unique ID and entry | HA |
| HA-005 | Concurrent discovery flows for one console | One accepted flow, others aborted/deduplicated | HA |
| HA-006 | User rejects/ignores discovery | No entry; ignore respected on rediscovery | HA |
| HA-007 | User cancels while UDP probe pending | Cancel sockets/tasks; no ghost flow | HA |
| HA-008 | Manual IP on network with no DHCP visibility | Directed probe works if reachable | HA |
| HA-009 | VLAN/broadcast filtered, directed route allowed | Manual fallback; no blanket failure | HA |
| HA-010 | Home Assistant restart with existing entries | No duplicate entities/prompts | HA |
| HA-011 | Reconfigure address with matching host ID | Preserve entry, unique IDs, history | HA |
| HA-012 | Reconfigure address with mismatched host ID | Reject and require explicit recovery | HA |
| HA-013 | Two PS5 of same model and PSN account | Two physical entries, no merged identity | HA/hardware |
| HA-014 | Official `playstation_network` also installed | Independent domains; no modification of official entries | HA |
| HA-015 | No Sony login or Remote Play pairing | LAN-only setup still succeeds | HA |
| HA-016 | Custom integration DHCP matcher on supported HA Core | Actual Discovered behavior verified on clean HA OS | HA OS |
| HA-017 | Disabled/removed console entry | Clean runtime unload and scoped rediscovery behavior | HA |
| HA-018 | New model/firmware unsupported | Clear diagnostic and no unsupported commands | HA/hardware |

## 7. Acceptance matrix — network topology and reliability

| Test ID | Scenario | Expected result |
| --- | --- | --- |
| NET-001 | Single interface, one console | Bounded discovery, one verified candidate |
| NET-002 | Multiple HA network interfaces | Correct interface/broadcast behavior, no duplicate identity |
| NET-003 | Ethernet HA with Wi-Fi console | Works when LAN permits; no assumed L2 topology |
| NET-004 | Multiple subnets/VLANs | Report limitations; directed manual fallback |
| NET-005 | Router hides DHCP lease information | Manual/direct LAN discovery remains possible |
| NET-006 | IPv4 DHCP lease renewal | Stable console identity and entity IDs |
| NET-007 | Console asleep/standby | Status depends on actual response, no forced OFF |
| NET-008 | Console fully off/unreachable | UNKNOWN/UNAVAILABLE, not falsely confirmed OFF |
| NET-009 | UDP packet loss, jitter and reorder | Bounded retries, generation-safe results |
| NET-010 | High packet rate / many discovered hosts | Concurrency and per-interface rate limits |
| NET-011 | HA shutdown during scan | Prompt cancellation and socket cleanup |
| NET-012 | Two HA instances on same LAN | No unsafe assumptions about exclusive ownership |
| NET-013 | IPv6-only environment | Explicitly unsupported/unknown until separate protocol proof |
| NET-014 | DHCP hostname absent or inaccurate | Protocol confirmation, not hostname, determines identity |
| NET-015 | Host ID spoofed by hostile LAN endpoint | No claim of cryptographic authentication; privileged actions require pairing and target validation |

## 8. Identity acceptance and migration contract

Preferred `host-id` normalization must be defined from observed byte format and validated across:
- Standby -> awake -> standby
- Console reboot
- Home Assistant restart
- DHCP address change
- Wired versus wireless interface, if available
- Firmware update
- Console factory reset and re-pairing
- Two same-model consoles and two PSN accounts
- Hardware replacement at previously used address

**No automatic migration** from IP/name/MAC to a new physical identity without explicit mapping and user confirmation. A factory reset might change an identifier; treat as an open test question. The local `DeviceInfo.identifiers` and entity `unique_id` must be stable under address/name changes and must not expose raw private IDs in public diagnostics.

## 9. Security and privacy gates

- Never send Remote Play pairing keys, NPSSO or OAuth tokens in discovery UDP.
- Never trigger wake, standby, pairing or Sony login from a passive DHCP event.
- Do not log unbounded raw datagrams or private host IDs.
- Validate source address and destination before directed privileged operations.
- Reject or quarantine identity collision and suspicious changes.
- Do not let user-controlled hostname/metadata become HTML, shell or SQL input.
- Limit UDP payload size, parsing complexity, retries, timeouts and concurrent sockets.
- Treat `host-id` as unauthenticated device assertion until a stronger pairing trust check exists.
- Honor Home Assistant admin/config-flow permissions and prevent duplicate flow abuse.

## 10. Proposed test harness and fixtures

**Pure Python parser tests:** synthetic datagram byte fixtures and parameterized malformed variants; no HA imports in core protocol parser.

**Fake UDP transport:** deterministic clock, send capture, injected timeouts/packet loss/out-of-order replies, cancellation and interface selection.

**Fake HA discovery/config flow:** mock `DhcpServiceInfo`, unique-ID handling, ignored entries, existing entries and in-progress flows. Assert no extra config entries or background task leaks.

**Integration test:** pinned supported HA Core, manifest discovery setup, entity/device registry behavior, reload/remove, IP changes, two devices and official PSN coexistence.

**Live hardware:** user-authorized PS5(s), model/firmware recorded, LAN topology recorded, status in standby and awake, and at least one network lease change. Never commit real console IDs or network captures.

## 11. Evidence gates and sign-off

| Gate | Required proof | Status |
| --- | --- | --- |
| G1 — Parser contract | Pinned upstream packet grammar and synthetic fixture pass | Research only |
| G2 — Identity | Real host-id uniqueness/stability across lifecycle | Not tested |
| G3 — HA discovery | Actual HACS custom integration appears under Discovered | Not tested |
| G4 — Multi-console | Two independently configured physical devices | Not tested |
| G5 — Address changes | Same identity, stable HA device/entity history | Not tested |
| G6 — No cloud dependency | LAN-only config/monitor works without PSN | Not implemented |
| G7 — Security | Malformed packet, collision and credential target tests | Not implemented |
| G8 — Runtime lifecycle | Clean cancellation/unload/reload without leaked tasks | Not implemented |
| G9 — Release | HA version matrix, HACS/Hassfest and actual hardware tests | Not implemented |

**Acceptance rule:** A source-observed behavior or documented test plan does not count as a passed test. Do not mark any G1–G9 complete until executable test evidence, versions, expected/actual results and reviewer sign-off are recorded.

## 12. Open decisions

1. Approve or amend ADR-0004 one-config-entry-per-console proposal.
2. Verify stable canonical host ID and define normalization.
3. Select supported PS5 firmware/PS4 scope.
4. Select HA Core minimum version and supported discovery API.
5. Decide safe default retry interval, total scan timeout and concurrency limits from tests.
6. Decide how to handle an otherwise valid response without stable identity.
7. Determine whether directed scanning may occur automatically after startup, and on which interfaces.
8. Define source verification and local-network trust assumptions.
9. Specify ignored candidate retention and removal/reconfiguration behavior.
10. Finalize compatibility and diagnostics reporting without leaking identifiers.

## 13. Source register

- [Protocol 01](../protocols/01-lan-discovery.md)
- [Protocol 02](../protocols/02-console-status.md)
- [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [Home Assistant Core PSN audit](../research/home-assistant-core-playstation-network-audit.md)
- [Cross-protocol architecture review](../architecture/cross-protocol-review-01-10.md)
- https://github.com/dhleong/playactor
- https://github.com/FunkeyFlo/ps5-mqtt
- https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/manifest.json
- https://developers.home-assistant.io/docs/config_entries_index/
- https://www.home-assistant.io/integrations/dhcp/

**Research outcome:** Discovery acceptance is defined with synthetic/HA/hardware matrices and nine release gates. No implementation, live test or automatic discovery result is claimed.
