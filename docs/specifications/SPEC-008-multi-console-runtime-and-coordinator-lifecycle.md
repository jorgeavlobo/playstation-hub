# SPEC-008 — Multi-console runtime, Config Entry and coordinator lifecycle contracts

**Status:** Proposed architecture/test specification; nothing implemented or approved  
**Date:** 2026-11-05  
**Official Core reference:** `home-assistant/core` tag `2026.11.0`  
**Primary research:** [Core multi-console source audit](../research/ha-core-2026-11-multi-console-runtime-source-audit.md)  
**Inputs:** Protocol 01/02, ADR-0004/0005/0006/0008/0009/0010, WP-00A, SPEC-001/005/006/007  
**Scope:** Multi-console LAN monitoring and native Home Assistant lifecycle, including future account isolation; no MQTT, PS5-MQTT, extra app or external database server  
**Working branch:** Research documentation on `main` only; legacy `develop` untouched.

> **Important:** A test defined here is not a passed test. This document formalizes the consequences of the official coordinator's listener-driven polling behavior. It does not authorize building a monitor, a Config Flow, a database, a panel or any other executable source.

## 1. Intended guarantee

For every **configured and validated physical PlayStation** with monitoring enabled, the integration should independently make bounded LAN observations and conserve the resulting durable evidence even if:
- the sidebar panel is closed;
- its power sensor is disabled by the user;
- the HA frontend client disconnects;
- another configured console becomes unreachable;
- a PSN account is unlinked or its authentication fails;
- a separate config entry is removed or reloaded.

Exceptions: the HA user intentionally disables polling/monitoring, the Home Assistant process is stopped, the network is inaccessible, or persistence cannot safely accept evidence. These conditions must create explicit historical coverage gaps rather than fabricated minutes.

## 2. Recommended dependency layout (conceptual)

```text
Home Assistant DHCP discovery
    -> PlayStation UDP candidate verification
    -> PhysicalConsoleConfigEntry A/B/C (separate unique IDs)
          -> ConsoleRuntime per entry
               -> LanMonitor (single probe owner per console)
               -> StateReducer + immutable accepted snapshot
               -> Push DataUpdateCoordinator (no periodic poll of its own)
               -> Entity Registry projections (sensor/binary_sensor/etc)
               -> Shared HistoryRepository lease
    -> Optional PsnAccountConfigEntry per authorized account
          -> AccountRuntime / scoped PSN coordinator and token manager
    -> HubSharedServices (single integration-level lifecycle)
          -> Bounded history writer
          -> Identity and account association registry
          -> Authenticated WebSocket facade
          -> One sidebar panel
```

The preferred scheduling design is a **single entry-owned LanMonitor as the probe producer**, publishing accepted results to a push-only DataUpdateCoordinator. An alternative is a single polling coordinator held alive by a deliberate internal lifetime listener. Both are **unimplemented**, and choosing one requires review and synthetic lifecycle tests. They are alternatives, **not two pollers to run together**.

## 3. Entry identity contract

| Field | Type/provenance | Mutability |
| --- | --- | --- |
| Entry kind | `console` or `psn_account` | Immutable after creation |
| Canonical console ID | Stable, validated physical identifier | Immutable; physical stability requires hardware proof |
| Candidate `host-id` | LAN response assertion | Not proof of cryptographic identity |
| Current IP | Verified locator | Can change with DHCP |
| Hostname/MAC | Discovery hints | Not immutable canonical keys |
| Friendly name | User-editable label | Never in unique ID |
| Home Assistant `entry_id` | Native internal ID | Different namespace from canonical console |
| PSN account ID | Provider identity | Independent from console key and nickname |

A physical console Config Entry should own the associated native DeviceEntry. Account entries, when authorized, own separate service entities and may have an account-level service device only if there is a supported use case; never merge physical device ownership through a PSN association.

## 4. Dedicated config-flow contract

**Discovery step:** `async_step_dhcp(DhcpServiceInfo)` receives a HA DHCP candidate, performs a safe bounded PlayStation UDP directed probe, validates a source-asserted ID, sets the reviewed unique ID, deduplicates concurrent flows, then asks the user to confirm. An unanswered packet does not create a permanent entry or an OFF assertion.

**Configured device rediscovery:** If a validated known console reports from a new address, use the documented unique-ID update-and-abort behavior to refresh its locator while preserving entry/device/history identity. Do not use `_abort_if_unique_id_configured` to “fix” a collision between different physical consoles.

**Manual setup:** Same parser/identity resolver and deduplication; neither an IP nor user-provided nickname is a permanent ID.

**Races and ignores:** Concurrent DHCP and manual attempts for the same hardware yield one confirmation/entry. Ignored device behavior uses a stable unique ID when available. Multiple different candidate IDs for one console may require explicit matching-flow logic. No background flow may automatically pair, wake, send Sony credentials, or create a new Config Entry without user confirmation.

## 5. Runtime ownership and invariant matrix

| Object | Owner | Lifetime | Cleanup |
| --- | --- | --- | --- |
| LAN UDP adapter | Console Entry A | A loaded | Close socket; invalidate pending generation |
| Per-console monitor task | Console Entry A | A loaded, monitoring enabled | Entry-owned cancellation and explicit bounded cleanup |
| Console state reducer | Console Entry A | A loaded | Drop callbacks and cached live state safely |
| Push-only coordinator | Console Entry A | A loaded | `entry.async_on_unload(coordinator.async_shutdown)` built in if config_entry provided |
| Console HA entities | Console Entry A | Forwarded platform scope | Await platform unload, remove listeners |
| PSN OAuth/refresh tasks | Account Entry C | C loaded and authorized | Scoped cancellation and token lock |
| Shared history writer | Integration-wide owner | While any required owner/queries active | Reference-counted/serialized shutdown |
| Sidebar registration | Integration-global singleton | Explicit zero-entry policy | Never one per console; no duplicate registration |
| WebSocket subscriptions | Authenticated user connection | Socket/session lifetime | Unsubscribe and revoke on disconnect/unlink |
| Historical data | User-authorized persistent owner | Independent of entry runtime | Explicit archive/export/delete policy |

`entry.runtime_data` should be a typed container, not a free-form global dictionary. Any `hass.data[DOMAIN]` use must be reserved for a documented integration-global service, with source-compatible lifecycle and quality-lint review.

## 6. Monitor scheduling policy and the no-listener problem

### Source-confirmed limitation

In Core 2026.11.0, `DataUpdateCoordinator.async_add_listener` schedules periodic refresh for the first listener; removing the last unschedules the next refresh. A normal polling coordinator on its own **does not guarantee continuous history collection** when nobody listens. `async_set_updated_data` is the native way to publish externally acquired data to entities without having the coordinator initiate another poll.

### Recommended B — background producer, push projection

1. On successful entry setup, create one monitor task using `entry.async_create_background_task` or an equivalent proven entry-owned scope.
2. The monitor owns all automatic and manually coalesced LAN probes to that physical console.
3. The transport is bounded for timeout, cancellation, source address and resource use.
4. Valid observations go through the per-console reducer and ordered ledger write contract.
5. The current snapshot is published to the push coordinator and backend WS state stream, including durability flag.
6. The monitor continues while configured/loaded even if zero HA entity listeners or browser subscribers remain.
7. On polling disabled, stop automatic probing and close or mark uncertain intervals conservatively. Do not silently override HA's user setting.
8. On unload, fence generation, cancel task, close sockets, stop coordinator, release shared lease, and invalidate in-flight reads.

### Alternative A — coordinator polling plus owned internal listener

An entry-scoped subscription may keep the coordinator's periodic scheduler active even with no entity listeners, with the ledger committed in `_async_update_data`. This is a viable candidate only if lifecycle, write durability, no-duplicate-facts and cancellation behavior are explicitly tested. Do not create a no-op listener without documenting why it owns continual monitoring.

### Explicit rejection

Do **not** enable both a polling coordinator and a second monitor timer on one console. Do not use browser presence, enabled sensors, or Recorder inclusion as the sole monitoring on/off switch.

## 7. Runtime state machine

```text
ENTRY_CREATED
  -> SETUP_VALIDATING
  -> RUNTIME_INITIALIZING
  -> ACTIVE_FRESH | ACTIVE_DEGRADED
  -> MONITORING_PAUSED (user-disable)
  -> ACTIVE_FRESH on re-enable / valid observation
  -> UNLOADING
  -> STOPPED

SETUP_VALIDATING -> SETUP_RETRY | SETUP_ERROR
RUNTIME_INITIALIZING -> FAILED_SETUP_CLEANUP
ACTIVE_* -> IDENTITY_CONFLICT (privileged control disabled)
ACTIVE_* -> HISTORY_UNSAVED (LAN may remain usable)
```

**Already validated console asleep at restart:** A full setup may remain loaded with unavailable sensors/known stale state when the policy permits. The official `test-before-setup` guidance allows `async_refresh` rather than a failing `async_config_entry_first_refresh`; entity code must tolerate no initial data. Do not mark the saved `last_known_power` as a fresh status. A new, never identified candidate still must not gain a permanent ID by guessing.

## 8. Observer envelope and data durability

Proposed per-console event:

```text
LanObservation
  observation_id
  console_id
  runtime_generation
  probe_request_id
  source_address
  received_utc
  received_monotonic
  source_status_code
  accepted_physical_power
  reachability
  freshness_expiry
  protocol_confidence
```

The reducer rejects older generations, unexpected source/physical identity and out-of-order accepted observations. A fresh status response is not exact physical transition time. Shared writer commits evidence and checkpoint (when approved) with idempotency keys. Publish `history_persistence_status` separately so dashboard stats never silently include uncommitted minutes. When persistence fails, current LAN status can still show as observed, but historical coverage becomes incomplete.

## 9. Entity projection contract

Console physical power, LAN reachability, last seen, command progress, historic last-known and persistence health are separate dimensions. Physical power may be `UNKNOWN` while the last-known power remains `AWAKE`, and the console may be `STANDBY` yet reachable.

- Coordinator receives immutable snapshots and entity getters read only cached data.
- Some entities may become unavailable when source health is degraded, while a last-seen diagnostic remains a valid historical timestamp.
- `CoordinatorEntity.available` must incorporate per-fact freshness where necessary, not only coordinator's global `last_update_success`.
- A push coordinator's `async_set_updated_data` can mark successful *delivery* without implying a newly successful LAN probe; snapshots need explicit source health.
- Use stable unique IDs independent of IP and friendly name; entity ID rename must not trigger additional UDP workers.
- `PARALLEL_UPDATES=0` is a candidate for read-only cached sensor platforms; action concurrency requires separate policy.

## 10. API, panel and shared-resource independence

The sidebar and its authenticated WebSocket API consume the domain snapshots and paged database reports, not direct console pollers. Two browsers displaying the same console must not double its polling frequency. Disconnection of all browsers must not stop history while monitoring remains enabled.

The optional PSN account may report online activity without proving which physical PS5 is in use. An account unlink cannot unload other physical console entries or alter their LAN power state. Console A's unload must not unregister the shared panel or close SQLite while console B's lease remains.

## 11. Network, fairness and backpressure

- Limit outstanding probes and socket count per console.
- Bound total concurrent probes across consoles to avoid congesting HA/network on restart.
- Apply jitter and backoff, with source-specific deadlines and no unbounded memory queue.
- Manual refresh joins or queues behind the existing per-console probe owner.
- One unreachable console must not delay all other console probes.
- Respect HA's `pref_disable_polling` if an independent monitor is chosen; surface pause in history coverage.
- Avoid polling every game/PSN metadata endpoint from each entity or browser.
- A history writer slowdown must have bounded queue behavior and clear UNSAVED/degraded state.

## 12. Acceptance matrix — config flows and identity (all NOT_RUN)

| ID | Scenario | Expected behavior |
| --- | --- | --- |
| MC-CF01 | First PS5 candidate from HA DHCP | Dedicated directed probe; user confirmation |
| MC-CF02 | Second PS5 after first configured | Independent confirmation and Config Entry |
| MC-CF03 | Same console via DHCP and manual flow | One unique ID, no duplicate device |
| MC-CF04 | Two concurrent DHCP candidate flows for same host | Deduped safely |
| MC-CF05 | User ignores a discovered host | No repeated prompts with stable ID |
| MC-CF06 | Candidate with no host-id | No unsafe permanent entry |
| MC-CF07 | Unsupported/malformed UDP response | Rejected or unverified, no auto-pair |
| MC-CF08 | Known console reappears at new IP | Existing entry updates with same canonical ID |
| MC-CF09 | New console at old IP | No history/credential reassignment |
| MC-CF10 | Same model and PSN account, two PS5s | Separate physical entries |
| MC-CF11 | Reconfigure address with mismatched ID | Abort with explicit identity conflict |
| MC-CF12 | Official `playstation_network` installed | Distinct domains and entry/registry ownership |

## 13. Acceptance matrix — coordinator and observation lifecycle (all NOT_RUN)

| ID | Scenario | Expected behavior |
| --- | --- | --- |
| MC-MON01 | One console, three read-only entities | One network probe per interval |
| MC-MON02 | Ten UI subscribers | Still one probe per console |
| MC-MON03 | All HA entities disabled | Monitoring continues if enabled and permitted |
| MC-MON04 | All browser panels closed | Monitoring continues independent of panel |
| MC-MON05 | All entity listeners removed from a normal polling coordinator | Test demonstrates scheduler stops (Core behavior) |
| MC-MON06 | Push coordinator without update_interval | No duplicate automatic polling |
| MC-MON07 | User disables HA polling | Automatic monitor pauses, gaps explicit |
| MC-MON08 | User re-enables polling | Resume with new observation, no gap backfill |
| MC-MON09 | Console A offline, B fresh | B monitoring and entity state unaffected |
| MC-MON10 | Late UDP response from previous generation | Rejected |
| MC-MON11 | Repeated identical status observation | Evidence checkpoint bounded; avoid duplicate UI state spam |
| MC-MON12 | Unknown status code with valid identity | Reachability may be true, power UNKNOWN |
| MC-MON13 | Standby still responds | Power STANDBY, reachable |
| MC-MON14 | Timed-out probe | Source degraded; last-known retained; no OFF |
| MC-MON15 | Manual refresh during scheduled probe | Coalesced; no second socket flood |
| MC-MON16 | Runtime reconfigured while probe pending | Old callback fenced, new target validated |
| MC-MON17 | No current data on setup | Entities tolerate null/stale and recover later |
| MC-MON18 | Push coordinator receives failed-source snapshot | Physical availability reflects source, not just coordinator success |

## 14. Acceptance matrix — unloading, shared services and history (all NOT_RUN)

| ID | Scenario | Expected behavior |
| --- | --- | --- |
| MC-LC01 | Unload console A while B loaded | A stops; B and panel continue |
| MC-LC02 | Remove PSN account entry | Token tasks stop; LAN monitors continue |
| MC-LC03 | Reload same entry 100 times | One active monitor/socket and one device instance |
| MC-LC04 | Failed partial entry setup after socket open | `async_on_unload` cleans source tasks/socket |
| MC-LC05 | Background task ignores cancellation | Detect excessive cleanup, no silent success |
| MC-LC06 | Unload during pending history write | No wrong-owner commit; safe drain/error |
| MC-LC07 | Database writer error | Current LAN independent; historical data flagged unsaved |
| MC-LC08 | HA shutdown with two active consoles | Both cancel, shared resources close after last lease |
| MC-LC09 | Remove last config entry | No orphaned pollers; panel policy explicit |
| MC-LC10 | User deletes a console but retains history | Data retained under approved policy |
| MC-LC11 | Reassign IP/rename console | Same historical key and entity unique IDs |
| MC-LC12 | Repeated observation ID from retry/reload | Idempotent ledger; no double seconds |
| MC-LC13 | Restore old backup and restart | Last-known stale, unknown gap; no fabricated duration |
| MC-LC14 | 20-console synthetic stress case | Bounded global concurrency and queue |
| MC-LC15 | Permission-denied manual refresh/action | No side effect on underlying LAN transport |
| MC-LC16 | Registry listener renamed entity ID | Rebinding without duplicate monitor or stale listener |

**Total: 46 newly enumerated test cases (12 ConfigFlow, 18 monitor, 16 lifecycle)**. All remain **NOT_RUN**. Overlap with SPEC-001/005 is intentional and should be deduplicated in a later executable test catalog.

## 15. Acceptance and approval gates

| Gate | Required evidence | State |
| --- | --- | --- |
| MC-G01 | Decision on polling coordinator + owned listener vs entry-owned monitor + push coordinator | PROPOSED |
| MC-G02 | Stable console ID/unique-ID hardware verification | BLOCKED_HARDWARE |
| MC-G03 | DHCP + manual multi-console flow tests | NOT_RUN |
| MC-G04 | No-listener monitoring tests and disabled polling semantics | NOT_RUN |
| MC-G05 | One probe owner per console, fair concurrent multi-console behavior | NOT_RUN |
| MC-G06 | Safe setup of sleeping/offline previously registered PS5 | NOT_RUN |
| MC-G07 | Typed per-entry runtime and global shared service lease | NOT_RUN |
| MC-G08 | No task/socket/listener leak on unload/reload/failed setup | NOT_RUN |
| MC-G09 | Physical/PSN state and unknown/unavailable separation | NOT_RUN |
| MC-G10 | Durable history and source snapshot consistency | BLOCKED_STORAGE |
| MC-G11 | Backend private API permissions and no browser-induced polls | NOT_RUN |
| MC-G12 | HA Core version, HACS/Hassfest and multi-console release validation | NOT_RUN |

**Approval distinction:** This document can be accepted as a *test plan* without accepting all underlying ADRs as implemented or passed. No gate is closed because upstream source has been inspected.

## 16. Implementation constraints preserved in documentation

- No code in `next`; branch deleted by the maintainer. No feature branch is created until implementation is authorized.
- Current research changes only `main`, no modifications to legacy `develop`.
- Pure LAN transport and identity logic remain fakeable and independent of Home Assistant imports.
- Per-entry monitor and coordinator must not produce duplicate network probes.
- Home Assistant entities never query transport directly.
- A missing packet never proves OFF; PSN offline never proves physical console OFF.
- No raw console ID, PSN token or Remote Play key in public diagnostics or test fixtures.
- Shared history storage outside integration code and verified backup strategy remain separate approvals.
- Future source code and comments must be English, modular and fully documented.

## 17. References

- [Pinned Core 2026.11 multi-console source audit](../research/ha-core-2026-11-multi-console-runtime-source-audit.md)
- [WP-00A baseline and LAN contract](../architecture/WP-00A-home-assistant-baseline-and-lan-contracts.md)
- [SPEC-001 LAN discovery](SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-005 CI/release](SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [SPEC-006 threat model](SPEC-006-security-privacy-threat-model.md)
- [ADR-0004 identity](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 source observations](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 sessions](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0008 storage](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009 HA entities/lifecycle](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [ADR-0010 sidebar API](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/update_coordinator.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://contributors.home-assistant.io/core/integrations/fetching-data/
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/

**Result:** A source-pinned multi-console architecture plan, competing scheduler designs, explicit runtime ownership and 46 deterministic tests with 12 unpassed approval gates. No executable implementation was started.


## 18. Shared manager and SQLite lifetime follow-up (2026-11-06)

This specification's 46 NOT_RUN tests and 12 open gates remain unchanged. [SPEC-009](SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md) adds **56** targeted concurrency, shared-resource, SQL, panel, backup and restore tests with 12 additional gates. The [source audit](../research/ha-core-2026-11-shared-services-lifecycle-and-sqlite-audit.md) establishes that per-Config-Entry setup locks do not serialize a process-global writer. Use manager-owned single-flight setup, generation-fenced leases and ordered cleanups, including FAILED_UNLOAD behavior. Backup hooks in generic Core do not yet prove HA OS Supervisor backup correctness. SPEC-009 elaborates (not supersedes) MC-LC01/03/04/05/06/07/08/09/12/13/14. No tests were executed and no implementation was authorized.


## 19. Optional logical Hub/Archive entry and storage-root lifecycle — 2026-11-06

[SPEC-011](SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) adds 64 NOT_RUN cases and 16 OPEN gates; [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md) remains PROPOSED. The preferred archive-UX candidate is a separate user-confirmed logical Hub entry, not a new physical console and not the owner of another writer. Hub-only setup may register one panel and accept bounded history queries but must never start LAN monitors or PSN token jobs. Dedicated DHCP flows are necessary to discover additional consoles even when a Hub entry exists; the generic first-integration fallback is insufficient. The Hub and all independently configured physical/account entries must share exactly one process-global controller. Removing the Hub while physical consoles remain cannot unload their monitors or writer. No existing SPEC-008 case is marked passed.


## 20. Recovery-Hold preflight before multi-entry historical monitoring — 2026-11-06

This document's 46 cases remain NOT_RUN. The maintainer ACCEPTED logical Hub/Archive Config Entry product architecture in [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06), which supersedes the earlier historical "ADR-0011 remains proposed" statement in §19. The actual entry/runtime and storage mechanics are not implemented.

[Source-pinned boot/worker research](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md), and [SPEC-016](SPEC-016-recovery-hold-boot-order-and-worker-termination.md) distinguish native Home Assistant ConfigEntry LOADED from **internal** Hub RECOVERY_HOLD. A globally constructed HubController must set DENY_WRITE before any entry-owned monitor can submit historical evidence, and per-entry runtime_data is prepared before awaited platform forwarding. In RECOVERY_HOLD, no source entry receives a durable writer lease; optional SOURCE_ONLY_UNSAVED LAN state requires a separate approved capability and cannot buffer unbounded historical time. Hub-only setup may remain LOADED with restricted admin panel and global Repair, instead of using ConfigEntryNotReady for an administrator-resolvable SQL failure. True PS5 offline/PSN authentication errors remain source-scoped. A cancel/timeout of any historical worker does not prove the SQLite connection closed. These requirements are NOT tested, and no code change occurred.


## 21. Per-console degraded capabilities and backend command guard — 2026-11-06

[New source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) and [SPEC-017](SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) distinguish per-entry source freshness, canonical identity, global ledger health and specific operation permissions. A console entry LOADED is not necessarily capable of writing durable history. Under global RECOVERY_HOLD a separately authorized OBSERVATION_ONLY current LAN projection may be shown as UNSAVED, with bounded state and no historical backfill; default physical-control policy denies wake/standby/Remote Play pending approval. An identity conflict blocks all physical controls and new attribution even if the entity reports available. HA service/automation, entity method and WebSocket handlers must recheck the same backend capability/generation at execution.

Each per-console LAN monitor remains entry-owned, and Hub/Archive never becomes a PS5 monitor or another SQL writer. PSN account source/refresh permissions remain independently scoped from physical consoles and historical data; during storage hold they are conditional and not automatically enabled. The SPEC-008 46 cases remain NOT_RUN, while SPEC-017 adds 80 explicit capability/worker tests and 20 OPEN gates. ADR-0011 is ACCEPTED at product architecture level; all new technical operation policies remain proposals.


## 22. Legacy single-console App history cannot inherit native physical ownership — 2026-11-06

[Actual develop source audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md), [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) and [SPEC-019](SPEC-019-legacy-history-migration-and-mqtt-retirement.md) reveal that legacy events/sessions/checkpoints are globally scoped to one monitored App source/player but have no canonical immutable physical PS5 key. Proposed historical importer must keep legacy records in a separate LEGACY_UNATTRIBUTED archive scope, not automatically assign them to new per-console Config Entries, reuse old synthetic MQTT monitoring device ID or authorize PSN account tokens. New physical-console runtime starts only at fresh native evidence boundary; migration must not replay old sparse MQTT state events as direct LAN observations. The source contains one single-console MQTT topic; this is not proof of actual historical physical identity after hardware replacement. No live database, broker or device inspected and no original SPEC-008 tests executed.
