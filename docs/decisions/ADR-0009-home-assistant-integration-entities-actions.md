# ADR-0009 — Home Assistant integration, discovery, entities and actions

**Status:** Proposed; not accepted, implemented or tested in Home Assistant OS  
**Date:** 2026-11-05  
**Domain:** `playstation_hub` — distinct from built-in `playstation_network`  
**Inputs:** ADR-0004 identity, ADR-0005 observations, ADR-0006 sessions, ADR-0007 credentials, ADR-0008 persistence, Protocols 01–10  
**Next:** ADR-0010 panel and authenticated backend API  
**Branch:** Documentation on `main` only; `develop` and `next` untouched

> This ADR is a design proposal. It does not demonstrate a working Home Assistant custom integration, console compatibility, permission to use Sony PSN APIs or successful discovery on a real network. Verify Home Assistant APIs against a pinned supported Core version before implementation.

## 1. Purpose and scope

Specify the native Home Assistant interface of a single HACS PlayStation Hub integration: configuration/discovery, device and entity registries, commands, availability, repairs, diagnostics, reload/unload, user permissions, translations and test/release gates. LAN monitoring must function without Sony login, Remote Play pairing, MQTT or a separate App. A single sidebar panel will consume backend data as defined separately in ADR-0010.

## 2. Decision options

| Option | Benefits | Drawbacks | Decision direction |
| --- | --- | --- | --- |
| Pure sidebar with no entities | Simple UX | No HA automations, poor ecosystem integration | Reject |
| One MQTT device/switch | Familiar legacy pattern | Requires broker and external app; violates ADR-0001 | Reject |
| One generic media player representing everything | Compact | Confuses physical power with PSN activity, misleading actions | Reject |
| Native physical-console devices plus optional PSN service devices and distinct entity domains | Correct semantics and HA automations | More code and lifecycle coordination | **Preferred, proposed** |
| Depend on official `playstation_network` for cloud | Less API code | Optional feature depends on separately installed integration | Reject as required dependency |

## 3. Home Assistant integration package and manifest

Proposed `custom_components/playstation_hub/` layout: `manifest.json`, `__init__.py`, `config_flow.py`, `const.py`, `coordinator.py`, `entity.py`, optional `sensor.py`, `binary_sensor.py`, `button.py`, `switch.py`, `media_player.py`, `image.py`, `diagnostics.py`, `repairs.py`, `strings.json`, `translations/`, `services.yaml`, `domain/`, `transport/`, `persistence/`, and panel assets only when supported by ADR-0010. **These are candidate modules, not files to create prematurely.**

Manifest:
- `domain=playstation_hub`, `name=PlayStation Hub`, `config_flow=true`, appropriate `integration_type`, `iot_class` and `connectivity` values **as supported by the selected HA release**.
- Declare only genuine dependencies; no required MQTT, Mosquitto, PS5-MQTT, Node.js, separate Docker or official PSN integration.
- Conservative DHCP matchers as **candidates**; use a dedicated `async_step_dhcp` and validated LAN discovery.
- Do not copy all Sony MAC prefixes without false-positive analysis. Validate manifest schema with Hassfest and HACS requirements.
- Specify minimum HA Core/Python versions, dependency pins and runtime features after compatibility research. Avoid assuming the `dev` branch equals installed stable.
- Keep all mutable data outside HACS-managed code.

## 4. Config Entry architecture

Preferred but unapproved ADR-0004: one config entry per **validated physical console** and separate config entries for **authorized PSN accounts**, both under the same integration domain, distinguished by a versioned `entry_kind` discriminator.

**Setup flow:**
1. `async_step_user` offers Add Console or Link PSN Account; cloud linking optional.
2. `async_step_dhcp` receives HA DHCP candidate, performs bounded safe protocol verification and resolves a stable identity before proposing a new console entry.
3. `async_step_confirm` asks user confirmation. No automatic pairing, wake or credential submission from passive discovery.
4. `async_step_reconfigure` handles address/options with identity revalidation.
5. `async_step_reauth` handles account credentials, rejects account ID mismatch, preserves console history.
6. Separate user-initiated Remote Play pairing flow or secure options/repair flow; exact supported HA flow method to be selected.
7. All flows deduplicate by stable validated unique ID and active flow state, including manual/discovered races.

**Critical upstream nuance:** Built-in `playstation_network` declares DHCP matchers yet its reviewed config flow has no dedicated `async_step_dhcp`. Home Assistant's inherited generic DHCP fallback may show an initial Discovered card but does not provide our required per-console discovery after an entry already exists. PlayStation Hub needs an explicit multi-console discovery handler, verified with HA integration tests.

**When identity is unavailable:** Do not manufacture a unique ID from a mutable IP, Sony OUI or hostname. Present a safe pending/manual setup or supported error, not a fake permanent console entry. If the same IP later reports a different console identity, block privileged commands and protect history.

## 5. Device Registry model

- Physical device: one `DeviceInfo` per validated console with `identifiers={(DOMAIN, canonical_console_key)}`; manufacturer, model and software version only when actually confirmed.
- Optional PSN account service device: separate identifier namespace `psn:<account_id>`, never merged with hardware.
- `via_device` or `via_device_id` is not automatically appropriate between PSN account and console; a many-to-many relation is not a parent-child hardware bus.
- `config_entry_id`, `device_id` and user-facing `entity_id` are Home Assistant-local identifiers, not canonical historical keys.
- Friendly names and rooms may be edited without changing the unique ID.
- Two PS5s of the same model must have independent device entries and actions.
- Account unlink does not delete physical console devices; console removal does not delete unrelated PSN service entries.
- Coexistence with official `playstation_network` must not modify its config entries, unique IDs or device registry records.

## 6. Entity model and proposed entity matrix

**Entity semantics first:** Do not use `binary_sensor` or `switch` to represent three-state power (awake/standby/unknown). `OFF` is not established by silence. Use `available` independently from state value and preserve last-known time in a separate diagnostic when useful.

| Scope | Platform | Suggested key | Meaning / source | Availability |
| --- | --- | --- | --- | --- |
| Physical console | `sensor` | `power_mode` | `awake/standby/unknown` from fresh validated LAN status | Source-specific freshness; stale -> unavailable |
| Physical console | `binary_sensor` | `lan_reachable` | Last verified network reachability, not power | Unknown/unavailable on missing evidence |
| Physical console | `sensor` | `last_seen` | Timestamp of last accepted local response | Historical timestamp remains valid |
| Physical console | `sensor` | `model` or diagnostic attributes | Confirmed hardware/firmware | Static, not a power source |
| Physical console | `button` | `wake` | Explicit action; requires pairing/credential if protocol demands | Disabled/unavailable when unpaired |
| Physical console | `button` | `standby` | Explicit action via verified Remote Play capability | Unavailable when unpaired/unsupported |
| Physical console | `sensor` | `command_status` | Requested/sent/verifying/confirmed/failed/unknown | Independent of power sensor |
| Physical console | `sensor` | `observed_awake_today` | Bounded, durable usage from ADR-0006 | Unavailable/degraded on ledger failure |
| Physical console | `sensor` | `observed_awake_total` | Monotonic lifetime bounded usage, subject to reset/migration policy | Must choose valid `state_class` |
| Physical console | `sensor` | `history_coverage` | Complete/partial/interrupted/unknown | Diagnostic by default |
| PSN account | `sensor` | `online_status` | PSN account reported presence | Cloud source freshness/permissions |
| PSN account | `sensor` | `now_playing` | PSN-reported game title; not console identity | Optional, cloud-only |
| PSN account | `sensor` | `last_online` | Provider-reported timestamp | Historical, may be private |
| PSN account | `image` | `now_playing_artwork` | Licensed/permitted provider artwork | Optional; fallback on failure |
| PSN account | `sensor` | `trophy_level` | PSN profile aggregate | Optional cloud feature |
| PSN account | `binary_sensor` | `ps_plus_status` | Provider-confirmed subscription flag | Unknown if private/missing |
| PSN account | `media_player` | `psn_activity` | **Optional** account/platform media view | Must not claim physical power |
| PSN account | `notify` | `psn_message` | **Future/conditional** explicit message sending | Permission/legal scope and opt-in |

All keys, names and exact domains are **proposed**. Avoid exposing sensitive account identifiers or large arrays in `extra_state_attributes`. Entity descriptions, `entity_category`, `device_class`, `state_class` and `suggested_display_precision` must be chosen according to HA platform contracts.

### 6.1 Why a switch is not the default power entity

A switch normally implies a controllable boolean state. The observed local state includes at least `AWAKE`, `STANDBY`, `UNKNOWN`; remote wake and standby have distinct credentials and verification. A switch that optimistically flips `on`/ `off` after sending a packet would misrepresent the console. Prefer explicit wake/standby buttons or targeted actions, and consider a switch only if future protocol validation proves reliable, reversible state and appropriate HA switch semantics. Existing legacy `switch.playstation_5_power` is not a reason to repeat a misleading model.

### 6.2 Native HA statistics

The ledger is authoritative for bounded session time; selected cumulative duration sensors may be exposed for HA Recorder/long-term statistics with correct unit, `state_class` and reset behavior. Daily resetting counters should not be blindly marked `total_increasing`. HA Recorder purge must not remove our own historical ledger. The panel's full history comes from the backend API, not giant sensor attributes.

## 7. Entity identity, naming and lifecycle

Proposed stable entity unique IDs: `<canonical_console_key>:<semantic_key>` and `psn:<account_key>:<semantic_key>` scoped to domain/platform. Do not use current IP, online name, friendly device name or user-edited entity ID.

- Device and entity registry additions must be idempotent on setup/reload.
- A change in discovered IP must not duplicate entities or reset Recorder history.
- A title/game change changes entity **state**, not its unique ID.
- Dynamic PSN account/platform/friend entities must be created/removed safely with subscriptions and cancellation.
- Disabled-by-default diagnostics/social entities should follow HA registry practices.
- Entity removal and historical data retention are distinct; do not assume deleting an entity erases Recorder data.
- Use `async_added_to_hass` and `async_will_remove_from_hass` for listener registration/cleanup where supported.

## 8. Coordinator and runtime ownership

**Proposed architecture:**
- One integration-scope `HubRuntime` owns shared storage, identity/association registry, panel registration and common dispatch.
- Each console entry owns `ConsoleRuntime` with its own LAN coordinator, per-console command lock, pairing and discovery address.
- Each PSN account entry owns `PsnAccountRuntime` with its token manager, cloud rate budget and PSN coordinator.
- HA entities subscribe to immutable cached domain snapshots, never perform I/O in properties.
- Account cloud outages must not prevent LAN console entries from loading.
- Unloading one console cannot close shared SQLite or remove the global panel if other entries remain.
- One account's refresh cannot rotate another account's tokens.
- Avoid global monkey-patches and mutable process-global singleton objects.

The exact `hass.data` / `entry.runtime_data` and lifecycle owner APIs must be verified against the minimum supported HA Core version.

## 9. Actions, commands and permissions

Actions must be explicitly targeted to a validated physical console. No command may default to the first detected PS5 or use a stale IP without identity revalidation.

**Proposed actions:**

| Action | Input | Behavior | Confirmation |
| --- | --- | --- | --- |
| `playstation_hub.wake` | Target console entity/device | Validate target, pairing and credential scope; send permitted wake | Subsequent valid awake observation or proven ack |
| `playstation_hub.standby` | Target console entity/device | Start bounded Remote Play control session and request standby | Subsequent valid standby observation or proven ack |
| `playstation_hub.refresh_status` | Target console | Bounded directed LAN query | Fresh accepted observation, not forced power |
| `playstation_hub.refresh_psn` | Target account | Respect provider rate/authorization | Updated account snapshot or typed error |
| `playstation_hub.repair_pairing` | Selected console | Explicit interactive flow, not silent re-pair | Durable credential commit |

**HA service registration:** Review current Home Assistant guidance for `async_setup`-level service registration, `services.yaml` descriptions and supported entity/device target resolution. Commands should be cancellable, idempotent where meaningful and concurrency-serialized per console. An action being accepted or a UDP packet sent does not establish a physical transition.

**Authorization:** Panel visibility is not sufficient. Validate authenticated user and action permissions using supported HA service/WebSocket APIs. Restrict secret/pairing/administrative operations. Do not assume HA permissions automatically cover every custom API route. If a platform lacks appropriate fine-grained permissions, expose only safe capabilities or require administrator approval as permitted.

## 10. Discovery and Home Assistant integration lifecycle

### 10.1 DHCP/Discovered

- Manifest DHCP matchers identify **candidates**.
- Explicit `async_step_dhcp` verifies protocol identity and avoids generic fallback's one-entry behavior.
- Use HA unique-ID and in-progress flow mechanisms to deduplicate across DHCP, manual and directed discovery.
- Support user ignore/dismissal without repeated notification spam.
- Multiple consoles can appear independently; user confirmation required before entry creation.
- Manual IP/hostname directed setup is a first-class fallback for VLAN/broadcast limitations.
- IP changes update reachability metadata, not canonical console identity.
- Test HACS custom integration discovery under the chosen HA Core version; built-in integration success alone does not prove custom integration parity.

### 10.2 Setup/unload/remove

- `async_setup`: register integration-scope infrastructure and supported services/panel hooks once.
- `async_setup_entry`: dispatch by validated `entry_kind`; create per-console or per-account runtime and forward only relevant entity platforms.
- `async_unload_entry`: cancel/await entry tasks, unload platforms, unsubscribe listeners, release owner references.
- `async_remove_entry`: remove scoped credentials and associations according to approved retention policy; do not silently erase history.
- `async_migrate_entry`: versioned migration for entry schema, preserving unique IDs.
- Reload/reconfigure: identity checks, no unnecessary token-only reload, and no duplicate socket binding or DB owner.
- Setup failure: distinguish `ConfigEntryNotReady` for temporary network problems from `ConfigEntryAuthFailed` for genuine auth failures. LAN-only entries should not fail due to optional PSN outage.
- On last entry removal, shared panel/storage lifecycle is controlled by the integration owner, not an arbitrary entry's unload callback.

## 11. Diagnostics, repairs and observability

- Sanitized diagnostics per console/account: model, supported capability flags, last successful probe, source freshness, retry status, database schema version and health.
- Redact NPSSO, OAuth tokens, Remote Play keys, sensitive account IDs, exact private history and signed artwork URLs.
- HA Repairs issues (where supported): pairing invalid, PSN reauth required, storage corrupted, identity collision, unsupported firmware, missing permissions.
- Repairs should link to actionable config/reconfigure flows; never trigger credential reset or deletion without explicit consent.
- Limit log volume and avoid raw packet dumps by default.
- Distinguish cloud degraded from local console unavailable in user-facing error messages.

## 12. Translations and accessibility

Use English for source code, comments and documentation; user-visible text must support translations. Minimum planned locales: English and Portuguese (Portugal), with expandable locale catalog. Use Home Assistant `strings.json` and `translations/<locale>.json` for config flows, entities, errors, services and repairs according to the target Core API. Frontend i18n is addressed in ADR-0010.

Avoid embedding fixed English/Portuguese strings in entity logic, and never use PSN game names or user nicknames as translated unique IDs. Use accessible state labels and localized date/time/units. Mobile Home Assistant UI must remain usable.

## 13. Coexistence with official PlayStation Network integration

- Keep `playstation_hub` domain distinct from `playstation_network`.
- Do not import runtime state, tokens or config entries from the official integration.
- Both may match the same DHCP host; duplicate **discovery proposals** may appear and are not necessarily preventable across independent integrations.
- Use clear integration/device naming to avoid confusion; only one physical-console device should be created by PlayStation Hub per canonical ID.
- Avoid trying to hide, delete or disable the official integration's discovery automatically.
- The built-in integration's account/platform media players are not evidence of physical hardware identity.

## 14. Security and privacy

- PSN features remain subject to the unresolved Sony client/endpoint authorization gate.
- Remote Play actions only after explicit pairing and validated console target.
- Do not expose credentials in frontend bundles, WebSocket responses, entity attributes, events, logs or diagnostics.
- Prevent malformed LAN payloads from becoming unrestricted network destinations.
- User commands must not wake or pair a device during background discovery.
- Respect PSN account visibility/privacy, including child accounts.
- Keep long-term history private; authenticated export/deletion policy belongs to ADR-0008/0010.
- Do not assume local HA users have identical access rights or that a sidebar panel automatically provides authorization.

## 15. Error taxonomy

| Error | Home Assistant response |
| --- | --- |
| `console_not_identified` | Setup form error; no unsafe entry |
| `duplicate_console` | Abort discovery and link existing device |
| `console_unreachable` | Mark source unavailable or retry setup |
| `unsupported_firmware` | Show capability unavailable, not generic OFF |
| `remote_play_unpaired` | Action unavailable; pairing prompt |
| `command_unconfirmed` | Do not optimistically change power state |
| `psn_auth_required` | Account-specific reauth/repair |
| `psn_rate_limited` | Backoff and cloud degraded; LAN continues |
| `storage_unavailable` | Mark history unsaved; protect existing data |
| `identity_mismatch` | Block privileged action, request rediscovery |
| `permission_denied` | Explicit auth error; no side effect |
| `unsupported_entry_schema` | Migration/repair, not silent reset |

## 16. Acceptance and integration test matrix

### Discovery/configuration
- [ ] HACS install and HA restart load integration and manifest correctly.
- [ ] DHCP candidate creates a Discovered prompt only after validated identity.
- [ ] A second and third console are discoverable with existing config entries.
- [ ] Same console from DHCP/manual/LAN scan yields one entry.
- [ ] User confirmation/ignore, changed IP, VLAN/manual setup and identity collision tested.
- [ ] Console-only configuration succeeds without PSN or Remote Play pairing.

### Device and entities
- [ ] Two consoles yield separate stable device/entity IDs.
- [ ] Rename/IP change preserves IDs and Recorder continuity.
- [ ] Unknown/unavailable never becomes false OFF.
- [ ] PSN account status and physical power are separate entities.
- [ ] No network I/O from entity getters; listeners cleaned up.
- [ ] Correct state classes for durable cumulative usage, resettable counters and units.
- [ ] Disabled diagnostics and entity removal handled.
- [ ] Official `playstation_network` can coexist.

### Actions/security
- [ ] Targeted wake/standby never defaults to another console.
- [ ] Unpaired/identity mismatch denies privileged commands.
- [ ] Send success without observed state yields unconfirmed command.
- [ ] Concurrency locks and cancellation prevent duplicate operations.
- [ ] HA user permissions checked on custom services/API.
- [ ] No credential leaks through logs, diagnostics, entity attributes or translations.

### Lifecycle/compatibility
- [ ] `async_setup`, setup entry, unload, remove, reconfigure, reauth and migration are idempotent.
- [ ] Unloading console A leaves console B, account C, storage and panel operational.
- [ ] PSN token refresh does not reload all entries.
- [ ] Home Assistant restart recovers durable history but current source state remains stale until observed.
- [ ] HACS validation, Hassfest, pytest, type checks and translation validation pass on pinned Core baseline.
- [ ] Tests distinguish unit/source-derived behavior from actual PS5/PSN live validation.

## 17. Decisions pending acceptance

- [ ] Approve one config entry per physical console and separate PSN account entries (ADR-0004).
- [ ] Verify stable host ID and custom DHCP flow on target HA release.
- [ ] Choose exact physical power/status entity types and supported platforms.
- [ ] Decide whether wake/standby are buttons only or also targeted services; recommendation: both if supported and useful.
- [ ] Decide whether account-level media players and notify entities are in v1; recommendation: defer notify.
- [ ] Confirm HA Core baseline, dependency pins and quality gates.
- [ ] Finalize permissions and admin-only operations.
- [ ] Approve entity unique-ID namespaces and migration strategy.
- [ ] Finalize shared runtime owner and entry removal semantics.
- [ ] Confirm statistics state classes and retention.
- [ ] Resolve PSN authorization and Remote Play live compatibility before claiming support.
- [ ] Align frontend and backend event/command contracts with ADR-0010.

**Recommendation:** Use native HA device/entry/entity/action semantics, with distinct hardware and PSN service identities, explicit per-console controls and no MQTT dependency. Maintain `Proposed` until reviewed and validated.

## 18. Sources

### Internal
- [ADR-0004 Identity](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 Observation](ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 Sessions](ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007 Credentials](ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008 Storage](ADR-0008-storage-persistence-and-backup.md)
- [Official PSN integration audit](../research/home-assistant-core-playstation-network-audit.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

### Home Assistant
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/data_entry_flow_index/
- https://developers.home-assistant.io/docs/core/device_registry_index/
- https://developers.home-assistant.io/docs/core/entity/
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://developers.home-assistant.io/docs/core/entity/button/
- https://developers.home-assistant.io/docs/core/entity/switch/
- https://developers.home-assistant.io/docs/dev_101_services/
- https://developers.home-assistant.io/docs/integration_fetching_data/
- https://developers.home-assistant.io/docs/integration_setup_failures/
- https://developers.home-assistant.io/docs/core/diagnostics/
- https://developers.home-assistant.io/docs/core/platform/repairs/
- https://developers.home-assistant.io/docs/internationalization/core/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network
- https://www.hacs.xyz/docs/publish/integration/

**Outcome:** Detailed proposed Home Assistant native integration contracts, device/entity/action semantics, lifecycle, discovery and tests. No code or live HA installation was changed.

## 19. Home Assistant Core 2026.11 compatibility overlay (2026-11-05)

See the [current official-source re-audit](../research/official-source-reaudit-home-assistant-2026-11.md), including official references OS-016–OS-023. Core 2026.11.0 requires Python >=3.14.2; this is a **research baseline candidate**, not an approved minimum supported release. DeviceInfo/ChildDeviceInfo are dataclasses: use typed construction, attributes and `as_dict()` instead of TypedDict assumptions; DeviceEntry is owned by one config entry and at most one subentry. This reinforces distinct physical-console and PSN account service ownership.

Prefer modern config-entry `async_setup_entry`, `async_unload_entry` and `async_migrate_entry` returning `None` and raising translated ConfigEntry exceptions; custom integrations can still return booleans. Always supply `step_id` in forms, menus, progress and external steps, anticipating the 2027.5 requirement. Core 2026.11 changes entity IDs in place; listener keys must handle `async_entity_id_changed`, and `async_on_remove` should clean up callbacks for partial add failures. Entity display names should be translated and context-free; canonical unique IDs remain stable. Per-entry repairs can use `config_entry_id` and the issues-refresh helper.

The candidate Marketplace manifest category is `media_entertainment.gaming`; this is optional for custom integrations but recommended for discoverability and to avoid an HACS Action warning. No source compatibility tests or native entities were implemented.

## 20. Official discovery, coordinator, actions and device lifecycle re-audit (2026-11-05)

The [second official-source audit](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md) adds current guidance from Home Assistant's discovery, runtime, quality-scale and diagnostics documents:

- **Discovery ownership:** Let HA's `dhcp` integration detect candidates and start a dedicated `async_step_dhcp`; directed PlayStation UDP probes validate the candidate and monitor local state. Do **not** implement an alternative DHCP lease scanner or a redundant network-wide discovery daemon. A bounded protocol broadcast can be investigated separately only as explicit PlayStation transport behavior.
- **Identity/retention:** Set a stable unique ID and deduplicate manual/DHCP flows; rediscovery of a validated known console at a new IP must update the same entry. Never delete an unreachable PS5 from the HA device registry merely because there is no UDP response; provide supported user-requested removal. For independently configured PS5s, a new discovery candidate creates a separate config flow/entry rather than automatically merging multiple physical consoles into a single device.
- **Runtime:** Per-entry `ConfigEntry.runtime_data` owns one typed console/account coordinator and its resources. The application-wide panel, shared history writer and association registry require a separately justified shared owner; do not store per-entry client state in unrestricted `hass.data[DOMAIN]`.
- **Coordinator and concurrency:** Entities read cached coordinator snapshots, without transport I/O in properties. Each entity platform sets `PARALLEL_UPDATES` explicitly; coordinator-backed read-only sensors may use `0`, but control actions still require per-console serialization. Coordinator `UpdateFailed` can log outage/restoration once rather than on every failed poll.
- **Actions:** Raise `ServiceValidationError` for invalid targets/inputs and `HomeAssistantError` for transport or device failures. Apply the same typed failure policy to button actions and custom WebSocket mutations. A command sent but not confirmed is not success.
- **Diagnostics/repairs:** Future per-entry/device `diagnostics.py` exports must use allowlisted sensitive-data-safe fields and snapshot tests. A system health view may use `async_loaded_entries(DOMAIN)`; unloaded/disabled entries cannot be assumed to have runtime data. Pairing, credential and storage repair issues must be scoped to the correct config entry.
- **Flows:** Connection identity belongs in `ConfigEntry.data`, behavior options in `ConfigEntry.options`; `reauth` and `reconfigure` are distinct, and reauth/reconfigure should update the **same entry** only after stable identity matches.

**Current status:** All are additional implementation/test requirements; they have not been implemented or proven by this documentation. Core Quality Scale is an internal voluntary engineering target for the custom integration, not an officially awarded tier.

## 21. Multi-console runtime ownership: official Core 2026.11 deep audit

See [source-pinned runtime investigation](../research/ha-core-2026-11-multi-console-runtime-source-audit.md) and [SPEC-008](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md). An ordinary DataUpdateCoordinator only schedules periodic work while at least one listener is registered; therefore dashboard/entity visibility alone cannot own a continuously collected history stream.

**Preferred unapproved architecture:** One independently entry-owned LAN monitor per physical console with bounded probes, generation fencing and safe shutdown; a push-only DataUpdateCoordinator distributes accepted snapshots using `async_set_updated_data` without duplicate polling. The alternate is a single polled coordinator with a deliberate internal lifetime listener and transactional ledger ingest. Choose exactly one after tests. `entry.async_create_background_task` is source-confirmed, scoped to entry unload; `entry.async_on_unload` supports callbacks and failed-setup cleanup. The pinned implementation waits up to 10 seconds for pending unload tasks, so cancellation-safe network cleanup remains an explicit requirement.

The config flow validates physical identity and confirms new consoles; later restart of an already identified sleeping PS5 can load in a deliberately degraded state instead of losing the entry. `async_config_entry_first_refresh` raises `ConfigEntryNotReady` if a required first read fails; `async_refresh` is an official allowed approach for often-offline devices, but requires entities to handle `None`/stale data safely. Respect `entry.pref_disable_polling` in any independently scheduled monitor and show historical coverage gaps on pause. Physical power, source health, HA entity availability and historical last-known values must not be conflated. These are proposed contracts, not executed HA OS tests.


## 22. Boot-time Recovery Hold, platform setup and native Config Entry states — 2026-11-06

**ADR-0009 technical implementation remains PROPOSED.** [Pinned HA Core lifecycle + worker source audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md), and [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md) refine setup under a damaged or partially promoted history ledger. Core 2026.11 invokes domain async_setup before enabled Config Entry setup, has entry-local locks and distinct native LOADED/SETUP_RETRY/SETUP_ERROR/MIGRATION_ERROR states. A Hub entry may be LOADED with an internal RECOVERY_HOLD and a restricted admin panel while the history writer is denied, but this is a **project proposal** rather than a new Core state. Do not raise ConfigEntryNotReady from Hub setup solely because admin intervention is required for recoverable historical storage: that may hide the recovery interface; genuine missing dependency/migration errors must remain honest.

All entry platform forwarding must be awaited and typed runtime_data populated beforehand. Each console/account entry remains independent, but cannot bypass global DENY_WRITE with its own SQL connection; optional SOURCE_ONLY_UNSAVED LAN monitoring requires a separate capability from persisted history leases. One global Repair issue is independent of a removable physical console entry. A platform-level setup error need not retry the entire entry, so essential recovery preflight and state validation belong to integration-level ownership, not buried in sensor platform setup. No code, tests or hardware verification occurred.
