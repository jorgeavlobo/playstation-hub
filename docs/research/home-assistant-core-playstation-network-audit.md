# Home Assistant Core PlayStation Network — deep reference audit

**Date:** 2026-11-05  
**Status:** Research / source audit / architecture inputs; **not** PlayStation Hub implementation  
**Reference:** Home Assistant Core `dev` integration `homeassistant/components/playstation_network/`, reviewed 2026-11-05  
**Project domain:** `playstation_hub` (distinct from Core's `playstation_network`)  
**Scope:** Automatic discovery, configuration, identity, runtime, service and entity architecture, polling, authentication, privacy, tests, shortcomings and decisions for PlayStation Hub.

> **Evidence rules:** `CORE-SOURCE` means behavior visible in the reviewed Home Assistant source; `HA-DOC` means a documented Home Assistant platform contract; `PROJECT-DIRECTION` is a proposed PlayStation Hub design, not a validated implementation; `OPEN` requires implementation-stage confirmation. Review of `dev` is a snapshot in time, not a guarantee for any installed release. The source does not prove live PS5 interoperability or authorize Sony API/client usage.

## 1. Executive overview

Home Assistant Core already ships an official PlayStation Network integration (`playstation_network`), exposed in Devices & services and supporting automatic discovery proposals. Its runtime primarily models **PSN accounts, platform-level presence, social data, games and trophy information** using PSNAWP. It does **not** implement the PlayStation Hub goal of independent LAN power/status control and physically distinct multi-console usage history.

PlayStation Hub is intended to be **one native HACS custom integration with one sidebar frontend**, without required PS5-MQTT, MQTT broker, Home Assistant App/add-on, Node.js service, companion browser or separate container. Its additional product requirements include first-party LAN discovery, Remote Play pairing/control, account-linked PSN enrichment, session accounting, persistent history and robust source reconciliation.

**Critical discovery result:** The official manifest provides DHCP matchers but its reviewed `config_flow.py` does **not** implement `async_step_dhcp`. Home Assistant's base config flow explicitly falls back to the `user` step for a matching discovery source that lacks a specialized step, using a single-flow/no-existing-entry guard for this fallback. This explains an initial **Discovered** proposal without demonstrating per-console repeated discovery. PlayStation Hub should implement a dedicated, verified discovery path for genuinely separate consoles.

## 2. Source inventory / audit traceability

| ID | Upstream file or documentation | Audit focus |
| --- | --- | --- |
| HAPSN-001 | `homeassistant/components/playstation_network/manifest.json` | Domain, discovery rules, package pins, quality tier |
| HAPSN-002 | `config_flow.py` | NPSSO, uniqueness, reauth, reconfigure, friend subentries |
| HAPSN-003 | `__init__.py` | Setup, runtime, platforms, unload, device registration |
| HAPSN-004 | `coordinator.py` | Fetch cadence, blocking call isolation, PSN errors and updates |
| HAPSN-005 | `helpers.py` | PSNAWP calls, identity, presence parsing and game metadata |
| HAPSN-006 | `entity.py` | Service identity and device registry associations |
| HAPSN-007 | `media_player.py` | Platform-derived players, lifecycle and media properties |
| HAPSN-008 | `sensor.py` | Player, trophy and presence sensors |
| HAPSN-009 | `binary_sensor.py` | PS Plus status |
| HAPSN-010 | `image.py` | Avatar, share-profile and game-cover images |
| HAPSN-011 | `notify.py` | PSN direct/group messaging entities and removal |
| HAPSN-012 | `diagnostics.py` | Redaction and diagnostics coverage |
| HAPSN-013 | `const.py` | Domains, supported platforms, Sony NPSSO link |
| HAPSN-014 | `tests/components/playstation_network/test_config_flow.py` | Manual config, duplicates, reauth and failure cases |
| HAPSN-015 | `tests/components/playstation_network/test_init.py` | Setup retry, auth failure, polling and reauth |
| HA-DISC-001 | Home Assistant developer Config Flow documentation | Reserved steps, default dispatch, stable identity and user confirmation |
| HA-DISC-002 | Home Assistant discovery guidance | DHCP/SSDP/zeroconf flow lifecycle and per-device matching |
| HA-DISC-003 | Home Assistant `config_entries.py` | Base `async_step_dhcp` and fallback behavior |
| HA-DISC-004 | Home Assistant DHCP documentation | User-facing Discovered and DHCP Browser |

### Exact source URLs

- https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/manifest.json
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/config_flow.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/__init__.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/coordinator.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/helpers.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/entity.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/media_player.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/sensor.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/binary_sensor.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/image.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/notify.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/diagnostics.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/const.py
- https://github.com/home-assistant/core/blob/dev/tests/components/playstation_network/test_config_flow.py
- https://github.com/home-assistant/core/blob/dev/tests/components/playstation_network/test_init.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py
- https://contributors.home-assistant.io/core/integrations/discovery/
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://developers.home-assistant.io/docs/config_entries_index/
- https://www.home-assistant.io/integrations/dhcp/
- https://www.home-assistant.io/integrations/playstation_network/

All GitHub `dev` links refer to moving branches. Pin exact commit hashes before implementing wire adapters or making compatibility assertions in a release.

## 3. Manifest inspection

### 3.1 Declared capabilities

The official integration declares:

| Key | Reviewed value |
| --- | --- |
| `domain` | `playstation_network` |
| `name` | `PlayStation Network` |
| `config_flow` | `true` |
| `integration_type` | `hub` |
| `iot_class` | `cloud_polling` |
| `connectivity` | `[cloud]` in reviewed Core manifest |
| `quality_scale` | `bronze` in reviewed Core manifest |
| `requirements` | `PSNAWP==3.0.3`, `pyrate-limiter==4.5.1` |
| `dhcp` | Multiple MAC-prefix and hostname matchers |

The DHCP list includes `hostname: ps5-*`, `ps4-*`, `ps3`, and numerous PlayStation-related MAC/OUI prefixes. **Do not blindly transplant this entire list** into the new integration. We must compare changes and potential false positives, distinguish Sony-issued MAC prefixes from device identity, and account for the fact that DHCP visibility and hostname availability vary by network.

### 3.2 Interpreting DHCP evidence

A manifest match means a *potential* integration opportunity, not that the host is an authenticated PS5, belongs to the user, is online now, or supports a specific protocol version. DHCP can be observed indirectly via Home Assistant's network discovery sources; manual IP configuration must remain available when discovery cannot cross VLANs/subnets or when a router suppresses relevant records.

The network stack should never infer a stable PlayStation identifier solely from a mutable IP, hostname, current router label or a MAC-prefix match. MAC itself can be a useful observed attribute but must be reviewed for stability and availability; never use an OUI prefix as a unique ID.

## 4. Why Core appears under Discovered without `async_step_dhcp`

### 4.1 Source-confirmed dispatch

The reviewed Core `PlaystationNetworkConfigFlow` defines `async_step_user`, `async_step_reauth`, `async_step_reconfigure` and friend subentry steps. It does **not** define `async_step_dhcp`.

The Home Assistant base `ConfigFlow.async_step_dhcp` calls `_async_step_discovery_without_unique_id()`, which guards against an existing configured entry / another in-progress flow and delegates to `async_step_user()`. The developer documentation states that if a source-specific discovery step is absent, discovery falls back to the generic user flow; **with an existing entry this generic path ceases to create new discovery flows**.

Therefore the official integration can be proposed on a DHCP match while still asking the user for NPSSO. It does not prove that the official integration identifies, validates, or separately onboards every detected PS5. We must not call this an authenticated PS5 local-discovery flow.

### 4.2 Proposed PlayStation Hub differentiated behavior

1. Home Assistant DHCP produces a candidate `DhcpServiceInfo` (IP, hostname, MAC).
2. Dedicated PlayStation Hub `async_step_dhcp` receives and validates discovery data.
3. A bounded PlayStation-specific LAN query attempts to confirm a compatible console; do not rely on the OUI alone.
4. Normalize a stable source-derived physical-console identity when genuinely provided. Determine fallback behavior **explicitly** if the protocol does not provide an acceptable stable ID.
5. Deduplicate the same console across DHCP, LAN scans, manual setup and concurrent flows, and avoid notifying on already configured or ignored devices.
6. Present a **user confirmation** before creating the config entry; discovery must not silently add an entity/configuration.
7. Associate the confirmed device with a per-console setup or an appropriate integration-level hub entry; choose config-entry boundaries in an ADR before implementation.
8. When discovery is unavailable, provide an explicit manual IP/hostname search with protocol validation; never make cloud PSN mandatory merely to configure LAN-only functionality.

**OPEN:** Verify the full Home Assistant Core DHCP integration invocation and custom integration discovery timing against the declared minimum supported release. Review supported `DhcpServiceInfo` use, fallback and ignore behavior. The source inspection confirms the base flow behavior but is not a real HA discovery acceptance test.

### 4.3 Discovery topology considerations

- DHCP-based discovery may be unavailable across VLAN boundaries or on networks where HA cannot observe DHCP.
- A direct LAN probe may use UDP discovery messages and must respect route, broadcast and network isolation.
- A PS5 in standby may advertise differently from an awake PS5; discover and represent uncertainty separately.
- Discovery results may arrive repeatedly, out of order, or with stale DHCP data.
- IP can change after the user has accepted setup; update the reachability address without changing the persistent device identity.
- Store source timestamps and confidence; do not turn `not seen` into `powered off`.
- Do not repeatedly scan a network aggressively; bound concurrency, broadcast frequency and timeouts.
- IPv4 LAN discovery currently has source evidence; IPv6 capabilities must be separately researched rather than inferred.

## 5. Configuration, authentication and account uniqueness

### 5.1 Official Core flow

`config_flow.py` invokes `parse_npsso_token` on user input, constructs the PSN helper, resolves `psn.user(online_id="me")`, and calls `async_set_unique_id(user.account_id)`. It aborts duplicates and blocks creating an account that was already present in certain friend subentries.

The `ConfigEntry.data` stores `CONF_NPSSO` and the entry title uses the online ID. Reauthentication and reconfiguration require an NPSSO and verify that the returned provider account ID matches the previously linked unique ID. Incorrect credentials, missing account and connection problems are mapped into distinct user-visible flow errors.

The Sony NPSSO URL is `https://ca.account.sony.com/api/v1/ssocookie`; the user signs into Sony in their own browser. Core does not implement automatic cross-origin cookie capture or a PSN OAuth callback.

### 5.2 Friend subentries

The `FriendSubentryFlowHandler` offers friend account IDs from the current friend list and creates config subentries with their own IDs. The code prevents conflicts with existing account entries and duplicate friend subentries; its data source may not be available while the main config entry is unloaded.

**Project direction:** PSN account entries, friends and console configuration must be carefully separated. A friend represented by a subentry must not become a credential owner or a physical-console device. Multi-account associations must use provider-stable identity, not editable PSN online names.

### 5.3 Security implications

Do not expose passwords, NPSSO, access/refresh tokens or OAuth codes via entity attributes, debug events, logs or frontend. Core's use of a config entry is persistence, not proof of at-rest encryption. Distinguish Sony credential lifecycle from Remote Play pairing credentials. Full OAuth callback requires a provider-sanctioned client registration/redirect; a reverse-engineered OAuth exchange is not authorization to reuse a third-party mobile client ID.

See [Protocol 08](../protocols/08-psn-authentication.md) for full token concurrency, refresh, persistence and account-linking audit.

## 6. Runtime / coordinator architecture

### 6.1 Official integration setup

`__init__.py` declares `BINARY_SENSOR`, `IMAGE`, `MEDIA_PLAYER`, `NOTIFY`, `SENSOR` platforms, creates a single `PlaystationNetwork` helper for an account, starts relevant coordinators, constructs runtime data, registers a service-level account device in the HA device registry, forwards setup to entity platforms, and installs an update listener for reloading configuration when required. `async_unload_entry` unloads these platforms.

The coordinator design uses `DataUpdateCoordinator` and executor-backed calls for blocking PSNAWP operations, which prevents direct blocking network calls on the HA event loop.

### 6.2 Observed schedules and update purposes

| Coordinator | Reference schedule | Notes |
| --- | --- | --- |
| User data | 30 seconds | Profile/presence/trophy summary and active PSN sessions; rate-limit implications |
| Trophy titles | 1 day | Refresh title lists, then request related data refresh |
| Friends list | 3 hours | Resolve friend IDs; refresh user display |
| Groups | 3 hours | Group list and metadata; forbidden errors may create repair issues |
| Friend data | `max(9 * subentries, 180)` seconds | Per friend subentry, scaled to group size |

These intervals are implementation observations, not proof of Sony-approved request budgets. The helper initializes a PSNAWP client with a rate limiter; per-function policies and total cross-account pressure must be researched for our own polling schedule. Core may also do additional queries during startup.

The official coordinator propagates `PSNAWPAuthenticationError` into `ConfigEntryAuthFailed` and handles generic API/client/server failures through setup retry or update failure paths. Emkraan additionally handles string-valued OAuth `invalid_grant` errors and guards concurrent refresh-token rotation.

**Project direction:** Use account-scoped, serialized token refresh with bounded timeouts and rate control; allow PSN-derived state to become stale without corrupting live LAN power observations or accounting. Expose operational availability by source.

## 7. PSNAWP helper and PSN state interpretation

`helpers.py` builds `PlaystationNetworkData` containing user account ID and online name, presence, profile, trophies, registered platforms, active-session summaries and profile links. It resolves registered device types, presence `basicPresence.primaryPlatformInfo`, `gameTitleInfoList` and the current title ID/name/artwork.

Observed game metadata fields include `npTitleId`, `titleName`, `format`, `conceptIconUrl` (preferred in this helper), and `npTitleIconUrl` (fallback). Legacy PS3/PS4/PS Vita data comes through additional profile APIs and title-artwork fallback logic.

**Critical distinction:** `primaryPlatformInfo` and PSN active sessions identify **presence on a platform**, not necessarily a particular physical console. PSN visibility/privacy and last-used-device semantics limit player attribution. Never manufacture certainty or retroactively assign session time to a specific PS5 without compatible, fresh evidence.

`get_game_title_info` takes the first item in a game list where present; it does not provide proof that every reported title or platform maps to an independently observable console. Platform membership and PSN account lists are distinct from LAN hardware inventory.

## 8. Home Assistant entity inventory

### 8.1 Media player

The official `media_player.py` defines a mapping of platform types (PS5, PS4, PS3, Vita, PC) into platform media players, modeled as receiver devices. Entity IDs/unique IDs include PSN account ID plus platform identifier. Media state becomes `PLAYING` when the relevant PSN session reports online with title ID, `ON` when online without title ID, and `OFF` otherwise. Media content is classified as a game with optional ID/title/artwork.

**Project limitation:** This media-player `OFF` is a PSN-session mapping, not independent proof of the physical console's electrical power state. PlayStation Hub must publish separate physical power, connectivity and PSN-presence signals and fuse them conservatively.

The media-player platform dynamically creates entities when previously unseen supported platforms occur in user data. Existing registered platform devices are recreated at setup so entity continuity is preserved across restarts.

### 8.2 Sensor platform

The official sensor module defines these reported sensor keys:

- `trophy_level`
- `trophy_level_progress`
- `earned_trophies_platinum`
- `earned_trophies_gold`
- `earned_trophies_silver`
- `earned_trophies_bronze`
- `online_id`
- `last_online`
- `online_status`
- `now_playing`

The module creates account and, where applicable, configured-friend views. It uses translated entity descriptions and data-derived getters. Percent/progress and trophy counts are account-level PSN data, not physical-console measures. Home Assistant state class metadata is present for some metrics; treat lifetime counters with appropriate statistics semantics in the new integration.

### 8.3 Binary sensor

`binary_sensor.py` exposes `ps_plus_status` from profile `isPlus`, dependent on provider response and privacy/availability. Absence of data is not logically equivalent to a confirmed false; test edge cases and availability policy.

### 8.4 Image entities

`image.py` defines `avatar`, `share_profile`, and `now_playing_image` variants, using remote PSN links for current avatars/game artwork. It invalidates its cached image on changed URL and updates the image timestamp. The new integration should separately validate remote URLs, handle cache/expiration, observe licensing/privacy rules, and keep image loading outside the domain data model.

### 8.5 Notify entities

`notify.py` implements group and direct messages; dynamic entities are added as group/friend lists change. It maps forbidden, missing-target and service failures to HA-visible errors, including disabling some entities by default. This illustrates HA's notify entity platform and registry lifecycle but adds external side effects and a broad permission/privacy surface.

**Product scope decision to make:** Whether sending messages is in PlayStation Hub v1. It is not automatically required merely because Core implements it. Do not silently add messaging or notification actions during monitoring setup.

### 8.6 Device registry hierarchy

Core registers a **service** device for the account, with Sony manufacturer, and platform/game-related devices linked by `via_device_id`. Friend subentries have their own account-linked devices. This is an account/platform-centric hierarchy, not physical hardware registration. For PlayStation Hub, evaluate separate console hardware devices and PSN account service identities; account-to-device associations should be explicit and updateable.

## 9. Domain-model comparison

| Dimension | Official `playstation_network` | PlayStation Hub target |
| --- | --- | --- |
| Principal data source | PSN cloud | LAN status + optional Remote Play + optional PSN |
| Discovery trigger | DHCP candidate rules | DHCP + verified PlayStation LAN discovery |
| Initial authentication | Manual NPSSO | Assisted NPSSO initially; provider-approved automatic OAuth if feasible |
| Device model | Account and platform views | Physical consoles plus separately modeled PSN accounts |
| Per-console local power | Not shown in audited PSN source | Proposed, only when confirmed by LAN |
| Wake / standby | Not shown in audited PSN source | Proposed, explicit pairing/authorization |
| Presence | Account/platform | Account/platform with attribution confidence |
| Game metadata | PSN active game info and remote artwork | Normalized title catalog with provenance and cache |
| Historical usage | HA entities/Recorder, not a private detailed session ledger in audited source | Detailed application-owned session accounting, storage ADR pending |
| Dashboard | Standard HA entities | Dedicated multilingual sidebar panel plus HA entities |
| Runtime dependency | PSNAWP/cloud | First-party protocols, audited dependencies if approved; no MQTT/add-on |

**Design principle:** PlayStation Hub must not claim a superset of Core functionality at release until each capability has independently passed implementation/compatibility and authorization gates. Document unavailable features explicitly.

## 10. Identified risks and opportunities

1. **Discovery without stable identity:** DHCP candidate only is insufficient for durable per-console config entries. Validate Sony protocol identity and the HA unique-ID source requirements.
2. **Generic discovery fallback:** Core's no-`async_step_dhcp` path is essentially a one-entry discovery prompt; unsuitable as sole mechanism for multi-console onboarding.
3. **Sony/PSN cloud not equivalent to console state:** Presence `offline`, blocked profile and API timeout are not confirmed `PS5 OFF`.
4. **Same PSN account on multiple devices:** A per-account-per-platform entity cannot distinguish multiple physical PS5 consoles.
5. **Rate limits:** PSNAWP refresh/poll concurrency may cause token rotation errors; centralize token lifecycle, heed provider limits.
6. **HTTP error classification:** `invalid_grant` must not be treated like generic loss of internet; avoid process-wide library monkey patches.
7. **Entity creation/removal:** Dynamic entities must preserve IDs and ensure unsubscribing listeners on unload.
8. **No secret leakage:** NPSSO and tokens must remain backend-only; diagnostics must redact all credential and personal data.
9. **Images/social features:** Cover URLs and profile assets may be unavailable, time-limited or restricted; avoid leaking credentials in URL requests.
10. **Coexistence:** Both `playstation_network` and `playstation_hub` might be installed. Use a distinct domain, stable device identifiers, and investigate how to avoid duplicate physical hardware representations/confusing Discovered prompts; do not overwrite Core config entries.
11. **Security and consent:** Neither the official HA Core source nor other community software grants Sony OAuth client permissions to our independent product.
12. **Future changes:** The reviewed `dev` branch may change. Pin and compare before release.

## 11. Proposed PlayStation Hub discovery/registration contract (not implemented)

### 11.1 Config flow states

`IDLE -> CANDIDATE -> PROBING -> IDENTIFIED -> USER_CONFIRMATION -> PAIRING_OPTIONAL -> CONFIGURED`

Error/alternative branches: `PROBE_TIMEOUT`, `NOT_PLAYSTATION`, `UNSUPPORTED_MODEL`, `DUPLICATE`, `UNREACHABLE`, `MANUAL_ADDRESS`, `USER_CANCELLED`. A discovered candidate never creates an entry without confirmation. Show the evidence and uncertainty, not a guessed unique ID.

### 11.2 Candidate record (proposed)

```text
DiscoveryCandidate
  source: dhcp | lan_probe | manual
  address: str
  mac_address: optional[str]
  hostname: optional[str]
  discovered_at_utc: datetime
  verified_protocol: optional[str]
  stable_console_id: optional[str]
  model: optional[str]
  confirmation_state: candidate | verified | rejected | indeterminate
```

Do not store user-facing strings in domain code. MAC addresses and console IDs may be privacy-sensitive in exports. If a unique, reliable console ID is not available, use a documented fallback policy rather than the current IP as a unique ID.

### 11.3 Test requirements

- [ ] DHCP matcher recognized on supported HA OS/Core; **Discovered** card appears after integrating a valid candidate.
- [ ] Generic Core fallback behavior reproduced in a synthetic unit test, with no custom DHCP step.
- [ ] Explicit PlayStation Hub `async_step_dhcp` handles multiple consoles, including when one config entry already exists.
- [ ] User must confirm before any config entry is created.
- [ ] Duplicate discoveries from DHCP and LAN scan collapse to one console identity.
- [ ] Two consoles of the same model/account are onboarded independently if stable identity exists.
- [ ] MAC OUI match but unsupported/unrelated host is rejected without false console identification.
- [ ] PS5 standby versus awake: absence of a reply is not called `OFF`.
- [ ] IP lease change or hostname rename preserves stable entity/device IDs.
- [ ] Manual IP setup works if DHCP/broadcast visibility is missing.
- [ ] Different VLAN, broadcast filtering and wireless isolation produce useful error reporting.
- [ ] Reboot, config reload, remove, ignore and rediscovery do not leak tasks or duplicate entities.
- [ ] Installation alongside official PlayStation Network does not mutate or reuse its domain/entries.
- [ ] No Sony auth/PSN network access is necessary for local LAN discovery.
- [ ] Discovery probes obey timeout, cancellation, safe payload parsing and rate limits.
- [ ] New PSN account authentication enriches existing console state without re-creating physical device identity.
- [ ] Account removed while game is running: maintain LAN state; mark PSN-only fields unavailable.
- [ ] Multiple PSN users on a console: do not assign gaming time to a player without sufficiently fresh evidence.
- [ ] Home Assistant runtime update and dependency compatibility tests precede release.

## 12. Project decisions versus open questions

### Established project direction

- One native HACS integration, distinct domain `playstation_hub`.
- One multilingual sidebar panel; HA-native entities and actions for interoperability.
- Independent local LAN monitoring is operationally meaningful without Sony cloud.
- Discover automatically where supported; manual configuration remains available.
- Do not depend on the official PSN integration, PS5-MQTT or Mosquitto.
- Support multiple physical consoles and optional multiple PSN accounts; do not conflate account/platform/device identity.
- Follow Home Assistant config-flow, device-registry, coordinator, translation and unload conventions.
- Research and documentation in `main`; implementation planned on `next`, legacy reference on `develop`.

### Open architecture decisions / validation gates

- Definitive multi-console config entry boundary (one entry per device versus discovery hub).
- Stable physical-console identifier obtainable for each console generation/firmware.
- Supported release and whether custom integration DHCP manifest matchers yield identical behavior to Core under HA OS.
- Source-specific `async_step_dhcp`, probe scheduling, ignore and in-progress dedupe implementation.
- Supported LAN discovery across subnets and IPv6, optional network permissions and minimal scan load.
- Whether notify messaging/social friend entities are included in the initial release.
- Entity naming/translation and account-to-device representation.
- PSN credential storage, token refresh and Sony endpoint/client authorization (see Protocol 08).
- History database and backup/restore ADR.
- Hardware/device tests and formal release quality gates.

## 13. Suggested implementation-stage source checks

- Re-read the then-current `homeassistant/config_entries.py` and `homeassistant/components/dhcp` dispatch and discovery tests for the minimum supported HA Core release.
- Review Home Assistant's current discovery documentation and stable-unique-ID rules. DHCP `DhcpServiceInfo` contains lowercase hostname, lowercase unseparated MAC and IP, but the information is **not** equivalent to a console proof.
- Review `homeassistant/components/playstation_network` test fixtures and coverage for platform entity creation and reauth.
- Confirm `PSNAWP` version/API behavior and package licenses without copying community client secrets.
- Create synthetic, non-sensitive fixtures for DHCP candidate, LAN verification, mixed PSN/console state and duplicate/restore/reload scenarios.
- Test local/manual and auto discovery with actual Home Assistant OS when implementation starts; report exact release, network topology and PS5 firmware.

**Research checkpoint:** This document records the official Core component's integration anatomy in detail and resolves why the official integration can appear under Discovered without a custom DHCP step. Nothing in this review constitutes working PlayStation Hub discovery or permission to reuse private Sony OAuth mechanisms.
