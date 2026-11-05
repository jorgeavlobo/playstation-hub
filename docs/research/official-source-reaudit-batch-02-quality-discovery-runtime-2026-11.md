# Official-source re-audit — Batch 02: quality rules, discovery, runtime, diagnostics and Marketplace

**Review date:** 2026-11-05  
**Status:** Source-backed documentation review; no code implemented, no tests run, no accepted ADR status changed  
**Source scope:** Home Assistant Contributors documentation current at review; rules concern primarily **Core integrations** unless expressly described for Marketplace custom integrations  
**Target release reference:** Home Assistant Core `2026.11.0` (research baseline, minimum product version not yet approved)  
**Project branch:** `main` only; `develop` is read-only legacy, purpose-specific feature branch only on later authorization  
**Related:** [Batch 01 official-source audit](official-source-reaudit-home-assistant-2026-11.md), [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md), [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md), [SPEC-005](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md).

> **Evidence classification:** `OFFICIAL_CORE_RULE` = rule applicable to Core quality tiers, adopted as an **internal voluntary design target** for this custom Marketplace integration unless independently required by custom-integration validation; `OFFICIAL_MARKETPLACE_REQUIREMENT` = publishing or install check for a custom repository; `OFFICIAL_API_GUIDANCE` = recommended Home Assistant framework usage; `PROPOSED_PROJECT_POLICY` = project-specific design, not an upstream mandatory rule; `OPEN` = unimplemented, untested or unresolved. Do **not** claim Bronze/Silver/Gold/Platinum certification for a custom integration.

## 1. Findings and immediate architecture corrections

| ID | Priority | Source-confirmed finding | PlayStation Hub action |
| --- | --- | --- | --- |
| OFF2-001 | P0 | Core Quality Scale currently lists **54 rules: 20 Bronze, 10 Silver, 21 Gold, 3 Platinum** | Maintain an applicability/implementation matrix; do not claim an official custom tier |
| OFF2-002 | P0 | Home Assistant's native DHCP/zeroconf/etc. discovery integrations find devices and start config flows | Use HA DHCP matchers/flow; native PlayStation UDP remains *verification/probing*, not a second DHCP lease scanner |
| OFF2-003 | P0 | `ConfigEntry.runtime_data` is recommended per-entry runtime owner; typed config entries | Keep per-console/account coordinators in typed `entry.runtime_data`; separate explicitly owned shared integration service |
| OFF2-004 | P0 | HA `DataUpdateCoordinator` consolidates fetching and error handling; entities read cached state | One source-aware coordinator per console/account where appropriate; no network calls in entity properties |
| OFF2-005 | P0 | Action failures should raise `ServiceValidationError` for caller errors and `HomeAssistantError` for device/transport errors | Preserve typed failure distinctions in HA wake/standby and API; never swallow errors after logging |
| OFF2-006 | P0 | Marketplace rechecks manifest/folder/domain/version and can restore files on post-write failure | Validate manifest/release/version, collisions, rollback and clean install; not just HACS Action |
| OFF2-007 | P1 | Marketplace maximum download/unpacked size is **100 MiB or 50,000 files** | Add artifact size and file-count release gate; bundle frontend without unbounded assets |
| OFF2-008 | P1 | `PARALLEL_UPDATES` should be explicitly set per entity platform in Silver target | Use `0` for coordinator-backed read-only entities; bound physical control per-console separately |
| OFF2-009 | P1 | Coordinators log unavailable once and recovery once; avoid per-poll warning spam | Centralize source failure changes and explain stale/unavailable from ADR-0005 |
| OFF2-010 | P1 | Gold diagnostics exports are redacted; official `async_redact_data` and registry serializers available | Implement per-entry/per-device diagnostics eventually, with conservative denylist **and allowlist**, no raw keys/history |
| OFF2-011 | P1 | `System health` can expose per-integration health; only loaded entries have valid `runtime_data` | Plan optional `system_health.py`, use `async_loaded_entries`, no secrets |
| OFF2-012 | P1 | `reauth` fixes credentials; `reconfigure` fixes host/address; options manage behavior | Keep these workflows separate; account ID mismatch and console ID mismatch must abort |
| OFF2-013 | P1 | Gold stale-devices rule: remove only with **positive authoritative absence**, else support user-managed deletion | Silence/unreachable PS5 must never trigger automatic device or history deletion |
| OFF2-014 | P1 | Gold dynamic-devices rule: new devices after setup appear without reload | For per-physical-console entries, evaluate **new config discovery flow** instead of silently attaching another device to existing entry |
| OFF2-015 | P1 | Core Silver quality target requires **>95% per-module** coverage, not just aggregate suite count | Add per-module coverage target, separately for Python modules; existing 80 legacy JS tests do not establish coverage |
| OFF2-016 | P1 | Core manifest `requirements` should be exact versions; `dependencies` vs `after_dependencies` differ | Declare only genuine mandatory HA dependencies; optional PSN and native LAN must not create MQTT dependency |
| OFF2-017 | P1 | Core config-flow rule distinguishes `ConfigEntry.data` (connection) and `options` (behavior), with translated descriptions | Specify data/options fields, stable unique ID and no arbitrary polling slider without rationale |
| OFF2-018 | P1 | Official user-facing docs rules include installation/removal, features, troubleshooting and supported devices | Create public-documentation acceptance matrix for Marketplace README/docs (do not use core-only website includes blindly) |
| OFF2-019 | P1 | Diagnostics JSON is often posted publicly; `async_redact_data` redacts matching keys but cannot classify unknown personal fields for us | Default to explicitly allowed fields and synthetic snapshot tests; never include private game history or provider payload by default |
| OFF2-020 | P2 | Quality-scale `quality_scale.yaml` is for integrations with a Core tier; not a prerequisite for custom Marketplace admission | Use an internal status matrix in `docs/standards/`; do not add misleading official tier metadata |
| OFF2-021 | P2 | Network-discovery docs recommend using shared HA zeroconf/DHCP services rather than independent duplicate scanners | Reserve directed `SRCH` UDP for PlayStation protocol verification/status, with bounded interface/rate budgets |
| OFF2-022 | P2 | Core exception translation source examples use `strings.json`/translation keys | In custom integration distribute complete `translations/en.json` and locale files, applying equivalent keys without relying on Core translation compilation |

## 2. Quality-scale audit: authoritative rule counts and scope

Official `All rules` currently lists:
- **Bronze:** 20 core rules (setup, unique ID, polling, runtime data, documented install, transparent dependencies and complete config-flow tests).
- **Silver:** 10 core rules (unload, reauth, unavailable state, action errors, per-platform parallel updates, logging, >95% coverage per module).
- **Gold:** 21 core rules (discovery, new/stale device management, diagnostics, repairs, translations, exhaustive user documentation and devices).
- **Platinum:** 3 core rules (async library, injected web session, strict typing).

**Our policy:** Treat these as a voluntary engineering checklist with `APPLICABLE / OPTIONAL / DEFERRED / NOT_APPLICABLE` status, but retain external Marketplace validation as a separate release gate. Official rules that refer to a Home Assistant Core pull request, `home-assistant.io` integration page or `quality_scale.yaml` cannot automatically be imposed as a catalog requirement for a custom HACS repository.

### Quality rule to requirement mapping (selected source-verifiable areas)

| Official rule | Scope for PlayStation Hub | Expected evidence | Current status |
| --- | --- | --- | --- |
| `action-setup` | Optional wake/standby actions | Registered once per integration, no duplicate entry registration | NOT_IMPLEMENTED |
| `appropriate-polling` | LAN and PSN separately | Measured polling cadence; no user-exposed arbitrary default | NOT_TESTED |
| `config-flow` | Physical console and optional PSN | HA UI flow with per-field descriptions and correct data/options | NOT_IMPLEMENTED |
| `config-flow-test-coverage` | LAN/DHCP/manual/reauth | Happy path, duplicate, failure, cancellation tests | NOT_IMPLEMENTED |
| `dependency-transparency` | Optional libraries | Exact pinned third-party packages and license inventory | NOT_SELECTED |
| `runtime-data` | All per-entry runtimes | Typed `ConfigEntry.runtime_data`, unload/reload tests | NOT_IMPLEMENTED |
| `entity-unique-id` | All console/account entities | Stable unique IDs after DHCP IP and name changes | NOT_TESTED |
| `test-before-configure` | Console identity / PSN account | Bounded verification before creating entries | NOT_TESTED |
| `unique-config-entry` | Multiple independent consoles | Same host never duplicated, other host not conflated | NOT_TESTED |
| `action-exceptions` | Wake/standby, admin actions | Typed user vs network vs auth exceptions | NOT_IMPLEMENTED |
| `config-entry-unloading` | Multi-config runtime | Unload one leaves others alive | NOT_TESTED |
| `entity-unavailable` | Source health | Known stale vs UNKNOWN vs unavailable | NOT_TESTED |
| `parallel-updates` | Every entity platform | Explicit setting chosen for coordinator/actions | NOT_IMPLEMENTED |
| `log-when-unavailable` | Each independent source | One lost + one restored log transition | NOT_TESTED |
| `test-coverage` | Pure Python, HA integration | >95% in **every** applicable Python module, not merely overall | NOT_TESTED |
| `diagnostics` | Per entry/device | Sanitized and snapshot-tested JSON | NOT_IMPLEMENTED |
| `discovery` | DHCP/PlayStation verification | Dedicated discovery flow, multiple consoles | NOT_TESTED |
| `discovery-update-info` | IP changes | Reconfigure known physical console without history reassignment | NOT_TESTED |
| `dynamic-devices` | New console after setup | New discovery flow creates independent entry | NOT_TESTED |
| `stale-devices` | Console removal | Explicit user deletion; **no removal on UDP silence** | NOT_IMPLEMENTED |
| `reconfiguration-flow` | Host/network | Reconfigure with verified same physical identity | NOT_IMPLEMENTED |
| `reauthentication-flow` | Optional PSN | Provider identity match and token update | BLOCKED_SONY |
| `repair-issues` | Pairing/auth/storage | Per-entry translated repairs with safe resolution | NOT_IMPLEMENTED |
| `strict-typing` | Python | Mypy strict configuration, typed DTO/repositories | NOT_CONFIGURED |

All 54 rule names are maintained at the upstream `/core/quality-scale/rules/` URL; **this matrix intentionally captures high-impact mappings, not a false claim that 54 checks were executed**.

## 3. Discovery ownership and transport policy

The official discovery guide states that HA's discovery integrations (DHCP, zeroconf, SSDP, etc.) find candidate hosts and dispatch to `async_step_dhcp`/equivalent, with manifest matchers. The unique ID prevents duplicates, including ignored entries. A rediscovered known device with a new address should update the existing configuration rather than create a new identity.

**Native PlayStation UDP is separate:** Protocol 01 `SRCH` and status packets are **device-specific validation and monitoring**, not an alternative DHCP server or a second Home Assistant DHCP scanner. The integration may send directed/bounded probes or use a deliberate protocol discovery window for its own device when needed; network-wide broadcast, repeated scanning and multi-interface behavior require explicit throttling and network API review.

**Design contract:**
```text
HA DHCP discovery event
  -> candidate address / observed DHCP metadata
  -> validated, bounded PlayStation UDP probe
  -> stable host ID candidate + identity checks
  -> existing entry address update OR new confirmation flow
  -> per-console config entry and native HA device
```

**Fallback:** Manual directed IP/hostname verification for networks where broadcast/DHCP matching is unavailable. Do not claim a DHCP matcher identifies a trustworthy physical PS5. Do not assume SSID, IP, MAC OUI or hostname alone proves console identity.

## 4. Typed per-entry runtime vs shared manager

The official Bronze `runtime-data` rule requires runtime data that belongs to a config entry to live in **`entry.runtime_data`**, with a typed config entry; loading/unloading disposes of that data. It discourages `hass.data[DOMAIN]` for *per-entry* state.

The project also needs cross-entry services: one panel registration, shared storage writer and domain registry. **Design tension to resolve rather than hide:** We should not overwrite each console's `runtime_data` with a process-global manager or attach an unrelated account/console to the same device. Prefer:
- Per-console `entry.runtime_data` owning one console coordinator/client/subscriptions.
- Per-account `entry.runtime_data` owning token/rate/coordinator if PSN authorized.
- Separate integration-scope `HubServices` owner with explicit lifetime/refcount for legitimately shared services.
- Audit the **supported API** for sharing integration-level services without the per-entry lint and lifecycle pitfalls; explicit, narrow `hass.data` use may be appropriate for an integration-global singleton, but should not become a dumping ground for entry state.

**Open:** Exact integration-global owner API and cleanup semantics in Core 2026.11.0.

## 5. Polling, source freshness and parallelism

The fetching-data guide favors a coordinator to fetch one device/account snapshot and notify several entities. Read-only coordinator-backed sensors/binary sensors may use `PARALLEL_UPDATES = 0` because property access uses cached coordinator data; **action platforms are different** and need explicit device command throttling, plus the project-level per-console mutex/lock.

Home Assistant's coordinator logs first unavailable and recovery transitions when `UpdateFailed` is used correctly. Do not emit warnings on every failed 30-second poll. A coordinator's default `available` semantics are tied to its fetch health; our richer ADR-0005 status still needs independent current, last-known, unknown protocol value and source-health facts. Do not overwrite a valid last-known historical observation merely because a coordinator changed to unavailable.

**No adopted numerical interval:** The old 30-second legacy session continuity policy and 90-second frontend stale check are not approved source freshness or polling intervals.

## 6. User actions and exception mapping

Official Silver rule `action-exceptions` expects:
- `ServiceValidationError`: caller used an invalid/missing target, invalid field, or requests a capability that is not configured (depending on exact UI semantics).
- `HomeAssistantError`: legitimate action failed due to transport, device or provider issue.
- Typed translated errors rather than plain logs. An action that catches and only logs an error is not considered successful.

**Project-specific third outcome:** `CommandAcceptedButUnconfirmed` is a **domain result** or typed error only after review of how HA services and UI should represent uncertainty. Sending a UDP wake or a TCP standby command is not physical-state confirmation. Do not throw a generic success or set power optimistically on mere socket send.

For custom WS mutations, the same backend CommandCoordinator and permission logic must be used; no duplicate business logic.

## 7. Diagnostics, system health and repairs

**Diagnostics:** Official per-entry/device `diagnostics.py` functions can provide sanitized JSON. `async_redact_data` can mask named keys in nested data, but **allowlist-first** is safer for our multi-player private history, console host IDs, PSN bearer secrets and device identifiers. Do not include raw provider packets, personal timeline, player/child names, OAuth tokens, PINs, or artwork signed URLs. Add snapshot tests and manual inspection before public release.

**System health:** `system_health.py` can expose a read-only availability summary, integration/Core version, storage schema/health and optional PSN rate budget without secrets. Use `hass.config_entries.async_loaded_entries(DOMAIN)`; generic `async_entries(DOMAIN)` may include disabled/unloaded entries lacking `runtime_data`.

**Repairs:** Use per-entry repair issues for pairing invalid, auth required, unsupported firmware, storage problems, with localized issue text and links to actual safe recovery actions. Repair must never silently delete historical usage or credentials of unrelated owners.

**Hardware history:** A PS5 that stops responding is **not an obsolete/deleted device**. The official stale-devices rule explicitly disallows automatic removal without reliable authoritative absence. Provide user-controlled removal and clear history-retention options.

## 8. Reauthentication, reconfiguration and options

- `ConfigEntry.data`: immutable-ish connection identity and data needed to establish a connection; any sensitive data stored here requires security review.
- `ConfigEntry.options`: behavior/settings not required to identify the device or service.
- `async_step_reauth`: account-specific replacement of credentials after a genuine auth failure; verify stable PSN account ID before updating the existing entry.
- `async_step_reconfigure`: change IP/host/connection details of existing physical console; verify stable hardware identity before updating.
- Options flow: independent choices like reporting timezone/retention; the default network probe cadence should be determined by implementation as a tested policy, not an uncontrolled user slider.

The official reauth documentation says `ConfigEntryAuthFailed` triggers reauth when raised from `async_setup_entry` or `DataUpdateCoordinator._async_update_data`; from other contexts, initiate through supported `entry.async_start_reauth(hass)` if needed. These are source API facts, not Sony permission.

## 9. Marketplace validation and release artifact constraints

Two independent validation levels:
1. **HACS Action/Hassfest** in our repository (catalog eligibility), with no ignored checks for Marketplace catalog admission.
2. **Marketplace install-time checks** in Core that validate root `hacs.json`, repository/folder ownership, domain, manifest loadability, compatibility/version and artifact size. Failures can refuse installation; post-write errors can roll files back.

Official limits: total downloaded/unpacked **100 MiB** or **50,000 files**. Check release ZIP, not merely working-tree size. Bundle the one sidebar frontend efficiently, avoid embedding thousands of images in source and keep mutable SQLite outside HACS-managed code.

The `hacs/action` sample uses `@main`, and Hassfest example uses `home-assistant/actions/hassfest@master`; **project policy recommends pinning reviewed immutable commit SHAs for supply-chain integrity**, although upstream examples use moving refs. No actual workflow or action was created.

## 10. Public documentation acceptance matrix

The official Core quality-scale documentation rules expect user-readable descriptions of setup, fields, options, actions/triggers/conditions where offered, known limitations, supported/unsupported devices, troubleshooting, removal, updates, example automations and use cases.

For a Marketplace custom integration, write equivalent content in our own `README.md` and `docs/` rather than pretending we have a Core-hosted `home-assistant.io/integrations/playstation_hub` page. Do not include Core documentation Jinja macros in a plain GitHub Markdown file without a supported renderer. Planned content:
- What the integration actually supports (LAN-only initially, optional gated RP/PSN).
- Which PS5 families and firmware are **tested**, versus untested/deferred (SPEC-007).
- Network prerequisites, multicast/broadcast vs directed probe limitations and setup steps.
- Multi-console discovery/ignore/rename/IP changes and their permissions.
- Entity/action list with precise `unknown` and `unavailable` semantics.
- Config flows, reconfigure, reauth, data/options and translations.
- Storage paths, retention, backup selection and explicit removal/export behavior.
- Privacy of player history, child accounts, PSN optional data, logs and diagnostics.
- Troubleshooting with repair issues and provider-specific errors.
- Actual tested HA/Marketplace release matrix, changelog, rollback and support policy.

These must be populated with **tested facts at release time**, not speculative claims today.

## 11. Source register (official pages reviewed)

| Source ID | URL | Main requirement |
| --- | --- | --- |
| S2-001 | https://contributors.home-assistant.io/core/quality-scale/rules/ | 54 rules and tiers |
| S2-002 | https://contributors.home-assistant.io/core/quality-scale/ | Core tier meaning and minimum |
| S2-003 | https://contributors.home-assistant.io/core/quality-scale/runtime-data/ | Per-entry typed runtime data |
| S2-004 | https://contributors.home-assistant.io/core/quality-scale/parallel-updates/ | Explicit platform concurrency setting |
| S2-005 | https://contributors.home-assistant.io/core/quality-scale/log-when-unavailable/ | One lost/one restored log message |
| S2-006 | https://contributors.home-assistant.io/core/quality-scale/action-exceptions/ | HA service exceptions |
| S2-007 | https://contributors.home-assistant.io/core/quality-scale/test-coverage/ | >95% per module |
| S2-008 | https://contributors.home-assistant.io/core/quality-scale/stale-devices/ | No device deletion from uncertain absence |
| S2-009 | https://contributors.home-assistant.io/core/quality-scale/dynamic-devices/ | New devices handled after setup |
| S2-010 | https://contributors.home-assistant.io/core/integrations/discovery/ | Native HA discovery ownership |
| S2-011 | https://contributors.home-assistant.io/core/integrations/network-discovery/ | Shared network discovery APIs |
| S2-012 | https://contributors.home-assistant.io/core/integrations/fetching-data/ | Data coordinator, polling, parallelism |
| S2-013 | https://contributors.home-assistant.io/architecture/core/data-updates/ | Per-source data freshness, coordinator architecture |
| S2-014 | https://contributors.home-assistant.io/core/integrations/diagnostics/ | Redaction and diagnostics interfaces |
| S2-015 | https://contributors.home-assistant.io/core/integrations/system-health/ | System health loaded entries |
| S2-016 | https://contributors.home-assistant.io/core/integrations/repairs/ | Repair issues |
| S2-017 | https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/ | Reauth/reconfigure/options distinction |
| S2-018 | https://contributors.home-assistant.io/core/integrations/config-flow/ | Data/options, dedupe, flow |
| S2-019 | https://contributors.home-assistant.io/core/integrations/manifest/ | Requirements, dependencies and iot_class |
| S2-020 | https://contributors.home-assistant.io/marketplace/reference/validation/ | HACS Action, Hassfest and install limits |
| S2-021 | https://contributors.home-assistant.io/marketplace/guides/integrations/ | Custom integration packaging |
| S2-022 | https://contributors.home-assistant.io/core/quality-scale/docs-installation-instructions/ | Setup/prerequisites documentation |
| S2-023 | https://contributors.home-assistant.io/core/quality-scale/docs-configuration-parameters/ | Options documentation |
| S2-024 | https://contributors.home-assistant.io/core/quality-scale/config-flow/ | Selectors, translations and fields |
| S2-025 | https://contributors.home-assistant.io/core/quality-scale/entity-translations/ | Translation keys and entity naming |
| S2-026 | https://contributors.home-assistant.io/core/integrations/translations/ | Core translation contract; differentiate custom distribution |
| S2-027 | https://contributors.home-assistant.io/core/quality-scale/quality-scale-file/ | Core tier YAML, not custom certification |
| S2-028 | https://contributors.home-assistant.io/core/integrations/tutorial/ | Reference integration and its test/structure |
| S2-029 | https://contributors.home-assistant.io/core/integrations/network-discovery/ | Shared discovery dependencies and APIs |

**Review result:** 22 high-impact findings, official source links and a proposed implementation/test/documentation mapping. There is no new release, code, test outcome, or accepted ADR. The review applies official Core rules as voluntary targets where appropriate and Marketplace checks as actual distribution constraints.
