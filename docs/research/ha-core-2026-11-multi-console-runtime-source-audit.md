# Home Assistant Core 2026.11.0 — Multi-console Config Entries and coordinator source audit

**Review date:** 2026-11-05  
**Status:** Source-pinned research and architectural recommendations; no integration code, executable tests or live PS5 validation  
**Source pin:** `home-assistant/core` Git tag `2026.11.0` (not `dev`)  
**Project:** One `playstation_hub` Marketplace custom integration, independent physical-console entries, optional PSN account entries, native LAN monitoring and one sidebar panel  
**Authoritative project design status:** ADR-0004, ADR-0005, ADR-0006, ADR-0008, ADR-0009 and ADR-0010 remain proposed; any choices introduced here are review recommendations, not implemented/accepted decisions.

> **Evidence classification:** `CORE_SOURCE` means directly inspected pinned official source; `OFFICIAL_GUIDANCE` means published Home Assistant contributor documentation; `PROPOSAL` means PlayStation Hub contract still subject to approval; `OPEN` means source/hardware/implementation verification incomplete. Cite precise upstream files instead of transferring requirements from current `dev` into 2026.11 without evidence.

## 1. The central finding: UI listeners are not a reliable historical monitoring owner

In pinned `homeassistant/helpers/update_coordinator.py`, `DataUpdateCoordinator.async_add_listener` schedules periodic refresh when the **first** listener arrives; removal of the **last** listener cancels periodic refresh and pending debounced refresh. In `_async_refresh`, another poll is scheduled only while there are listeners. The official [Fetching data](https://contributors.home-assistant.io/core/integrations/fetching-data/) documentation explicitly says the coordinator polls while at least one entity listens.

**Consequence:** A history recorder that depends only on entity listeners may stop taking console observations when all relevant entities are disabled/unloaded or otherwise no listeners remain. A browser panel is not the correct owner for LAN observation cadence. Durable history must have an explicitly integration-owned observation source independent of dashboard visibility.

### Alternatives (both plausible, not yet tested)

| Option | How one probe is owned | Advantages | Risks |
| --- | --- | --- | --- |
| A — One polling coordinator with **deliberate internal lifetime listener** | The per-console coordinator performs probes and has one entry-scoped internal history subscription even with no entity listeners | Reuses HA scheduler, retries, logging and `pref_disable_polling` | A hidden listener is an implicit liveness mechanism; ledger commits must be guaranteed before accepted observation; retention/cancellation need explicit proof |
| B — One **entry-owned background LAN monitor** feeding a **push-only** DataUpdateCoordinator | A single per-console monitor owns periodic probes and ordered durable evidence; coordinator only projects accepted snapshots using `async_set_updated_data` | Monitoring lifecycle and history ownership explicit; UI/entity listeners never decide whether the monitor is alive | Must implement well-governed scheduling, jitter, `pref_disable_polling` handling, retry/backoff and shutdown; avoid double polling |
| C — Coordinator polling only with HA entity listeners | Poll stops when nobody listens | Simple UI entity behavior | **Reject as sole owner** if user expects continuous history |
| D — Each entity or browser widget polls | Many independent fetches | Little architecture effort initially | **Reject:** duplicate packets, races, unbounded load and inconsistent history |

**Preferred design direction for a multi-year history product: B**, subject to WP-00/ADR approval. The coordinator would be created with **no `update_interval`** and receive accepted domain snapshots through `async_set_updated_data`. The per-console monitor is attached to Config Entry lifecycle via supported `entry.async_create_background_task` or an equivalent owned task. There is **exactly one UDP probe owner per configured console**, not a polling monitor **plus** a polling coordinator.

**Alternative A remains legitimate** if an internal listener/atomic ledger contract is formally approved and tested. Neither alternative is implemented. Do not claim HA's coordinator inherently monitors a console with no listeners.

## 2. Core source evidence: coordinator scheduling

| Pinned source behavior | Verified location | Implication |
| --- | --- | --- |
| First listener starts refresh | `update_coordinator.py` `async_add_listener` ~178–190 | Entity subscription can start polling |
| Last listener unschedules refresh and cancels debouncer | `update_coordinator.py` ~194–205 | No guaranteed continuous monitoring without an explicit owner |
| `_schedule_refresh` checks `update_interval` and `entry.pref_disable_polling` | ~260–275 | A custom monitor must respect the user's polling preference |
| Scheduled refresh uses entry-scoped `async_create_background_task` | ~288–312 | Native example of lifecycle-owned work |
| `async_config_entry_first_refresh` requires `SETUP_IN_PROGRESS` | ~332–373 | Call only during entry setup; raises `ConfigEntryNotReady` on initial failure |
| `async_refresh` does not raise for ordinary transient failures | ~430–435 | May allow offline devices to load in degraded state |
| `always_update=False` suppresses unchanged *poll* listener notifications | ~600–614 | Useful for immutable comparable snapshots |
| `async_set_updated_data` pushes data and notifies listeners | ~634–652 | Supported bridge from a background monitor to HA entities |
| `async_set_update_error` marks error and notifies listeners | ~617–633 | Distinguish source failure from a successful normal snapshot |
| Coordinator registered to Config Entry uses `entry.async_on_unload(self.async_shutdown)` | ~154–156 | Built-in cleanup for coordinator scheduler |

**Nuance:** The push method `async_set_updated_data` notifies listeners directly; unlike the polled `_async_refresh` path, it does not perform the same `always_update=False` equality gate. **Producer-side snapshot deduplication** may be needed to avoid emitting identical state repeatedly, while the persistence ledger still records bounded evidence according to ADR-0006. Do not infer data was durably written merely because a coordinator accepted a snapshot.

## 3. Core source evidence: Config Entry background tasks and cleanup

`homeassistant/config_entries.py` in `2026.11.0` exposes:
- `entry.async_create_background_task(hass, coroutine, name, eager_start=True)`, which attaches a background task to that entry; the method's source says it is cancelled when the entry unloads, does not block startup and does not count toward `async_block_till_done`.
- `entry.async_create_task` for setup/lifecycle-related tasks with different waiting semantics.
- `entry.async_on_unload(callback)` for synchronous or asynchronous cleanup; the coordinator registers its `async_shutdown` this way.
- `_async_process_on_unload` invokes callbacks and cancels background tasks, then waits **up to 10 seconds** for tasks to settle; it warns about pending tasks. **Ten seconds is a current pinned implementation detail, not a guarantee every arbitrary task has stopped.**
- `async_forward_entry_setups` must be **awaited during setup**, before the setup lock releases; Core explicitly detects incorrect unawaited usage.
- `async_unload_platforms_or_raise` raises `ConfigEntryError` when platform unloading fails.

**Implication:** Do not build an untracked `asyncio.create_task` polling loop in module-global state, and do not rely only on GC/disposal when the last panel closes. Design cancellation-safe monitor shutdown, explicit socket close, outstanding probe generation invalidation, drain-or-fail history writes and separate shared-database lease release. In testing, an uncooperative cancelled coroutine can exceed Core's 10-second wait; a correct implementation must terminate itself promptly and report a leak rather than silently claim clean unload.

### Failure/cleanup distinctions

- When entry setup fails after allocating a socket, cleanup registered through `entry.async_on_unload` must cover the partial setup; official [Config entry unloading](https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/) states these callbacks are also invoked on failed setup.
- When unloading a platform fails, the overall entry may remain loaded and the integration must not close shared runtime prematurely; follow the supported lifecycle and error policy.
- A shared integration-wide SQLite writer and sidebar must not be closed when console A unloads while console B/account C still hold leases.
- Entry removal is not synonymous with deleting private historical data. Protect optional user-managed archival and purge semantics.

## 4. Native DHCP discovery, stable identity and multi-console setup

The pinned `homeassistant/config_entries.py` `ConfigFlow.async_step_dhcp` default delegates to generic `_async_step_discovery_without_unique_id`, which eventually offers the user step only under the generic integration conditions. The official [Config flow](https://contributors.home-assistant.io/core/integrations/config-flow/) and [Discovery](https://contributors.home-assistant.io/core/integrations/discovery/) documents require a unique stable ID and user confirmation for each discovered new device.

The built-in `playstation_network` `manifest.json` includes DHCP MAC/hostname matchers, but its `config_flow.py` has **no dedicated `async_step_dhcp`**; it is an NPSSO account flow. This is a concrete reason to implement a PlayStation Hub-specific per-console discovery step rather than inherit its behavior.

**Proposed flow:**
1. HA's shared DHCP integration detects MAC/hostname candidate from conservative matchers; no custom DHCP lease scanner.
2. `async_step_dhcp(DhcpServiceInfo)` probes candidate via bounded directed PlayStation LAN UDP, not Remote Play pairing or wake.
3. Parser rejects malformed payload and records protocol-asserted `host-id`, source IP, generation and host type.
4. Until hardware stability/uniqueness is validated, `host-id` remains a **candidate**; never silently treat IP/MAC/hostname as canonical immutable identity.
5. With a reviewed stable ID: `await async_set_unique_id(...)` and `_abort_if_unique_id_configured(updates={CONF_HOST: verified_ip})`, subject to current API and identity validation. This can update a known entry's address without creating another entry.
6. For unknown candidate: show a user confirmation flow and do not create an entry automatically.
7. Manual directed setup uses the **same** probe, parser, identity service and deduplication logic, preventing one device from registering twice through different sources.
8. Account registration, if Sony authorizes it, is a **distinct flow discriminator and unique-ID namespace**; never duplicate physical-console identity or attach two owners to the same DeviceEntry.

**Additional official nuance:** `ConfigFlow.is_matching` and `hass.config_entries.flow.async_has_matching_flow(self)` can be needed when multiple discoveries have **different provisional IDs but refer to the same candidate**. Ignored entries also use stable IDs. The correct cross-source race handling must be validated rather than assuming one call to `async_set_unique_id` solves every identity-collision case.

### Identity and network caveats

- Do not indiscriminately copy the complete official PSN DHCP OUI list: the official list is only a **candidate matcher**, not proof every device using an OUI is our supported console.
- Detecting a different verified physical identity at the previous IP **blocks credentialed control and cross-device historical reassignment**.
- A MAC can change between Wi-Fi/Ethernet; `host-id` stability across those interfaces remains hardware-unverified.
- New compatible hardware discovered when one console is already configured must still produce an independent flow.
- Background observation of a physical console during standby may be unavailable; that alone does not indicate an invalid Config Entry or prove the console is OFF.

## 5. Conceptual typed ownership architecture

```text
                         Home Assistant Core 2026.11
                                  |
                  shared DHCP discovery flow manager
                                  |
                   PlayStation candidate validator
                                  |
               stable physical-console identity resolver
                                  |
                           config entries
                 +----------------+----------------+
                 |                |                |
            PS5 Living         PS5 Bedroom       PSN Account
            Entry A            Entry B           Entry C
                 |                |                |
          entry.runtime_data  entry.runtime_data  entry.runtime_data
                 |                |                |
           ConsoleRuntime A  ConsoleRuntime B   AccountRuntime C
             |         |       |         |         |
         LAN Monitor  State   LAN Monitor State   PSN adapter
         (one probe   Push    (one probe Push    (permission
          owner)      Coord.   owner)     Coord.   gated)
             |         |         |         |
             +---------+---------+---------+
                       |
             HubSharedServices (separate integration-level owner)
                HistoryRepository / identity associations
                 Authorized API facade / one sidebar
```

**Entry ownership rule:** Per-console state, transport, monitor task and coordinator belong to the console entry; per-account state and token refresh belong to the account entry. The shared writer, API facade and single panel have a separate integration-scope lifecycle. `entry.runtime_data` must not be repurposed as a global mutable dictionary. Exact integration-global registry/storage owner location is an **OPEN** API/design decision: narrowly scoped shared state may need an explicit `hass.data` holder, but Core's runtime-data lint rules discourage putting per-entry state there.

**Device Registry:** A physical DeviceEntry belongs to one console config entry; optional PSN service entities may be grouped by account without merging the physical console's DeviceEntry. Many-to-many console/account links belong in project domain models, not in HA's device ownership structures.

## 6. Shared service lifecycle (proposed, not official HA algorithm)

```text
HubSharedServices
  state: NEW | INITIALIZING | ACTIVE | DEGRADED | CLOSING | CLOSED
  acquire(owner_entry_id) -> Lease
  release(owner_entry_id) -> None
  active_owner_count
  global_panel_registered
  history_repository_health
  domain_dispatcher
```

**Leases are design concepts, not HA built-in functionality.** The service must be created only once through serialized integration-level setup, and no module-level unguarded mutable global state may own it. Acquiring a second console must reuse the same shared object. Unloading one entry releases only that entry's lease, stops only that entry's LAN monitor, and preserves other console/account APIs and history.

**Additional challenge:** The sidebar route may remain installed even when no console is configured, to show a setup screen; or it may be removed when there are zero entries. This must be decided deliberately. Core 2026.11 `frontend.async_remove_panel` exists, but does not by itself establish asset/static-path unregistration behavior. Panel and registered WebSocket commands must tolerate a not-ready/empty integration without leaking private data.

**Transaction boundary:** The monitor's accepted observation and durable checkpoint must reach the ledger through a serialized writer; UI state is published only with an explicit `persistence_status` to prevent suggesting unsaved minutes were recorded. Shared writer failure degrades historical coverage but does not require the LAN transport to lie about power.

## 7. Setup and offline state design

Official [Test before setup](https://contributors.home-assistant.io/core/quality-scale/test-before-setup/) explicitly recognizes devices that are intentionally offline. The usual `await coordinator.async_config_entry_first_refresh()` raises `ConfigEntryNotReady` if the first fetch fails. It is only valid while the entry is in `SETUP_IN_PROGRESS`. For sleeping/unresponsive hardware, `await coordinator.async_refresh()` may allow setup to finish with unavailable entities; the data can initially be `None`, so entity properties and DeviceInfo must tolerate that.

**Recommended split for PlayStation Hub:**
- **During config flow:** Require a verified console identity before creating a permanent entry, unless a separately approved safe manual recovery path is available.
- **During subsequent setup/restart:** A previously identified console may be in standby, fully off or disconnected. Do **not** force reauthentication or delete its Config Entry solely because a probe times out. Allow a degraded runtime and unavailable physical-power sensor while preserving last-known and historical evidence.
- **If the identity suddenly changes:** Block privileged Remote Play commands and relevant historical attribution; show a repair/identity-mismatch state.
- **Initial push coordinator:** May start with a typed `UNKNOWN/STALE` snapshot from last-known storage, rather than `None`, if authorized by the history policy; call `async_set_updated_data` on accepted source observations. This is a **project choice**, not proof of a successful fresh probe. Any unavailable physical-state entity must explicitly account for source freshness, not only `coordinator.last_update_success`.
- **Transient transport problems:** Source health fails with retry/backoff; preserve entry, last-known timestamp, and ensure one log on outage and one on recovery.

The exact policy for setup on first-run identity validation versus restart transient failure must be encoded into a state machine and tests before implementation.

## 8. Polling disabled by user: a critical special case

Pinned Core 2026.11 coordinator `_schedule_refresh` returns without scheduling when `self.config_entry.pref_disable_polling` is set. If PlayStation Hub uses its **own** entry-owned monitor, it must honor the same user preference or document why an independent monitoring feature intentionally persists, which would be surprising.

**Proposed rule:** When the HA user disables polling for that console entry, stop scheduled LAN probing, retain last-known historical state with a stale label, close any continuous observed interval conservatively at its last durable checkpoint and inform the user that monitoring/history accumulation is paused. Do **not** backfill inactivity or gaming duration when polling resumes. A manual explicit probe action may remain possible if the user triggers it and permissions allow it.

**OPEN:** Confirm exact user-facing disable-polling semantics in the selected Core release and whether a distinct PlayStation Hub monitoring option is needed. This scenario requires an HA OS test, not only a pure Python test.

## 9. Freshness, unknown, and HA entity availability

Separate:
1. `physical_power`: `AWAKE | STANDBY | UNKNOWN` based on fresh recognized protocol response.
2. `reachability`: `REACHABLE | UNREACHABLE | UNKNOWN` based on probe evidence.
3. `source_health`: `HEALTHY | DEGRADED | DISABLED` with last error and timestamp.
4. `freshness`: `FRESH | STALE | NO_EVIDENCE`; monotonic in-process TTL, UTC for display.
5. `last_known_power`: historical last recognized value; never automatically becomes current on restart.
6. `history_persistence`: `DURABLE | UNSAVED | UNAVAILABLE` (source snapshot independent).
7. `command_result`: `NOT_REQUESTED | SENT | VERIFYING | CONFIRMED | UNCONFIRMED | FAILED`.

A `CoordinatorEntity.available` decision may need a targeted override rather than relying exclusively on `last_update_success`. For example, a valid response with unknown status code can establish LAN reachability without establishing the power mode; physical-power entity may show `UNKNOWN` as a genuine fresh protocol result. After a timeout/stale deadline, the power entity may become unavailable while a timestamp diagnostic remains valid. **No UDP response does not prove physical OFF.** Source health/availability does not turn a PSN account offline either.

## 10. Concurrency, idempotency and rate governance

- One per-console probe lane / semaphore: no overlapping periodic and manual probe to the same address unless explicitly designed and safe.
- Across consoles: bounded parallel probes, per-interface network rate budgets and deterministic jitter; one problematic PS5 must not stall the rest.
- Shared SQLite: one writer queue/transaction owner, bounded memory and explicit error handling. Per-console event streams must preserve order and identity independently.
- Every request uses `runtime_generation` and probe ID; reject stale callbacks from old entry instances and reused IP addresses.
- Operation commands (Remote Play wake/standby later) have their own per-console command lock, independent of status probe cadence, with explicit fresh identity revalidation.
- Manual refresh from HA service/panel is a **coalescible request** to the existing probe owner; it must not spawn a second transport worker.
- Source timeouts are bounded; auto-retries have ceilings/backoff; avoid a “thundering herd” on restart, including across multiple HA installations on the same LAN.
- Any concurrency limits are planning values until measured; do not copy PS5-MQTT or legacy 30/90-second defaults as proved safe.

## 11. Domain snapshot/notification contract

```text
ConsoleDomainSnapshot
  schema_version
  canonical_console_key
  runtime_generation
  accepted_observation_revision
  physical_power
  reachability
  last_seen_utc
  freshness
  source_health
  last_error_code?
  history_persistence_status
  sampled_at_utc
  last_known_power?
```

All fields are proposed. The reducer merges source evidence atomically, then the projection notifies HA entities/WS subscriptions. A change in `sampled_at_utc` every poll need not force every sensor to write state to Recorder; keep time-based evidence and meaningful entity state changes distinct. History commits and UI notifications must indicate durability high-water mark or explicitly flag delayed/failed persistence.

**Push coordinator semantics:** `async_set_updated_data` marks coordinator update success; if the snapshot represents a failed probe, the domain must still carry `source_health=DEGRADED` and `freshness=STALE`, and entity `available` must use the correct meaning. Consider `async_set_update_error` where suitable, but avoid using coordinator-success alone as physical-power accuracy evidence.

## 12. Device Registry, account associations and removal

One physical DeviceEntry per validated console Config Entry. No IP, human room name, online PSN display name or title ID in canonical entity unique ID. A PSN account Config Entry, if Sony features are authorized, may have separate service entities or an optional service device; **do not force a synthetic account DeviceEntry solely for symmetry**. Decide entity grouping using actual HA device-registry conventions and tests.

When a console is removed:
- Unload its monitor/coordinator, cancel probes, unsubscribe HA listeners, release shared lease.
- Remove its active entities according to HA lifecycle and user choices.
- Do not silently erase multi-year historical sessions, account associations or other consoles.
- Explicit user-authorized export/archive/purge decisions live in ADR-0008.
- Do not let a removed console's late probe or command response recreate entities.
- Deleting the last Config Entry must not leave background LAN loops.

When one account unlinks: stop that account's cloud polling and remove scoped secrets, leaving independent LAN monitors intact.

## 13. Decision register and conflicts to resolve

| Decision | Preferred direction | Status / evidence |
| --- | --- | --- |
| Per-console Config Entry | Yes | Proposed ADR-0004, hardware identity unverified |
| Per-account Config Entry | Yes if Sony authorized | Proposed; account service DeviceEntry optional |
| HA DHCP ownership | Use shared HA DHCP matcher + dedicated config flow | Official guidance + pinned fallback source |
| One probe owner per console | Mandatory invariant | Architecture contract, not implemented |
| Historical observation when no entity listeners | Must continue if configured and polling permitted | Official coordinator behavior requires explicit owner |
| Monitor scheduling | Entry-owned background producer + push coordinator | Preferred proposal, not approved |
| Coordinator with internal lifetime listener | Alternate HA-native design | Needs lifecycle/ledger test before accepting |
| Always-on monitoring vs `pref_disable_polling` | Respect user preference and mark historical gap | Proposed, HA OS test required |
| Setup of an already configured sleeping console | Degraded/unknown, don't drop entry | Official permitted pattern, not tested |
| Initial first refresh | Only during SETUP_IN_PROGRESS; may raise ConfigEntryNotReady | Source verified |
| Shared history repository | Single application-scoped owner + leases | Proposed ADR-0008, backup untested |
| Panel lifecycle with zero entries | Setup screen vs removal open | Explicit decision pending |
| Physical status after no response | UNKNOWN/unavailable, last-known preserved | Safety rule; hardware mapping unverified |
| Optional PSN status | Separate account fact and flow | Sony authorization blocked |

## 14. Official source register — pinned and published

### Pinned Home Assistant Core 2026.11.0

- [ConfigEntry lifecycle, task ownership, setup/unload, DHCP fallback](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py)
- [DataUpdateCoordinator listener scheduling, push and first refresh](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/update_coordinator.py)
- [DHCP integration watcher and flow dispatcher](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/dhcp/__init__.py)
- [Discovery flow helper](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/discovery_flow.py)
- [DeviceRegistry unique ownership](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/device_registry.py)
- [Entity platform concurrent update limits](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py)
- [Official PSN manifest with DHCP candidate matchers](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/manifest.json)
- [Official PSN account config flow (no explicit DHCP step)](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/config_flow.py)
- [Official Shelly integration: per-entry runtime/coordinator pattern](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/shelly/__init__.py)
- [Official Shelly config flow: stable ID and host update](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/shelly/config_flow.py)
- [Official panel and removal APIs](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/frontend/__init__.py)

### Official contributor documentation

- https://contributors.home-assistant.io/core/integrations/discovery/
- https://contributors.home-assistant.io/core/integrations/network-discovery/
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/integrations/fetching-data/
- https://contributors.home-assistant.io/core/quality-scale/runtime-data/
- https://contributors.home-assistant.io/core/quality-scale/test-before-setup/
- https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/
- https://contributors.home-assistant.io/core/quality-scale/discovery-update-info/
- https://contributors.home-assistant.io/core/quality-scale/parallel-updates/
- https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/

## 15. Research status and next requirements

**Completed:** Exact Core source reconnaissance and a proposed independent monitoring ownership/lifecycle model; comparison of HA native scheduler vs entry-owned monitor; concrete multi-console/config-flow and first-refresh risk identification.

**Not completed:** Live HA OS setup/unload, no-listener monitoring, disabled polling behavior, hardware host-id, source status codes, SQLite durability, PSN authorization or a working WebSocket/Sidebar. No code was modified or created.

**Next:** Create an independent SPEC-008 with test IDs, expected outcomes and approval gates, then align ADR-0004/0005/0009, WP-00A, compliance matrix and the Architecture Guide. None of these steps authorizes implementation.
