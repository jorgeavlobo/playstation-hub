# Internal applicability matrix — official Home Assistant Core quality rules

**Date:** 2026-11-05  
**Status:** Documented applicability only; **zero tests executed, zero rules proven**  
**Scope:** All **54** official Home Assistant Core quality rules: 20 Bronze, 10 Silver, 21 Gold, 3 Platinum  
**Interpretation:** Voluntary engineering target for our **custom Marketplace integration**, not official Core tier or official Marketplace certification. Marketplace install/catalog checks are a **separate** binding contract.

> An external Core integration quality-scale requirement may not automatically be mandatory for a custom Marketplace project. Core-only requirements such as a `home-assistant.io` documentation PR, Core brands repository or `quality_scale.yaml` metadata must be **adapted**, not copied blindly. The exact `done/exempt/todo` lifecycle is part of Core's quality-scale mechanism, not evidence that this custom project is approved.

## 1. Rule inventory and planned evidence

### Bronze: 20 Core rules

| Core rule | PlayStation Hub applicability | Proposed verification |
| --- | --- | --- |
| `action-setup` | Conditional (RP commands) | Register native HA actions once, not for each console entry |
| `appropriate-polling` | Applicable | Source-specific, measured bounded LAN/PSN cadence; no copied legacy defaults |
| `brands` | Adapt for custom | Ship locally approved brand/icon.png, not assert Core brands repository admission |
| `common-modules` | Applicable | Use coordinator.py/entity.py and independent domain/transport boundaries |
| `config-flow` | Applicable | UI setup for multi-console, stable IDs, data vs options and field descriptions |
| `config-flow-test-coverage` | Applicable | Full manual/DHCP/error/ignore/reauth/reconfigure tests |
| `dependency-transparency` | Applicable | Reviewed license, source, exact pinned packages and reproducible install |
| `docs-actions` | Conditional | Document wake/standby when enabled; no actions invented for LAN-only |
| `docs-conditions` | Conditional | Document only real conditions if shipped |
| `docs-high-level-description` | Applicable | Explain local PlayStation monitoring and optional PSN/RP |
| `docs-installation-instructions` | Applicable | Document prerequisites and current Marketplace setup |
| `docs-removal-instructions` | Applicable | Document credential, history, backup and entity cleanup |
| `docs-triggers` | Conditional | Document only real triggers if shipped |
| `entity-event-setup` | Applicable | Lifecycle listener registration and cleanup |
| `entity-unique-id` | Applicable | Never key unique ID by IP, room or player display name |
| `has-entity-name` | Applicable | Contextual, translated entity naming for HA 2026.11 |
| `runtime-data` | Applicable | Typed per-entry ConfigEntry.runtime_data; shared infrastructure scoped separately |
| `test-before-configure` | Applicable | Validate PlayStation candidate/identity before entry is made |
| `test-before-setup` | Applicable | Runtime setup validates transport and handles typed failures |
| `unique-config-entry` | Applicable | DHCP/manual dedupe and independent same-model PS5s |

### Silver: 10 Core rules

| Core rule | PlayStation Hub applicability | Proposed verification |
| --- | --- | --- |
| `action-exceptions` | Conditional (control) | ServiceValidationError for invalid target and HomeAssistantError for device failures |
| `config-entry-unloading` | Applicable | No cross-entry resource shutdown; idempotent unload/reload |
| `docs-configuration-parameters` | Conditional | Document actual options with units/defaults once implemented |
| `docs-installation-parameters` | Applicable | Document every setup and pairing field |
| `entity-unavailable` | Applicable | Separate stale source health from categorical physical power |
| `integration-owner` | Applicable internally | Document maintainer ownership, issue/security response |
| `log-when-unavailable` | Applicable | One outage/recovery transition per source, no poll log flood |
| `parallel-updates` | Applicable | Explicit per-platform setting; per-console action locks |
| `reauthentication-flow` | Conditional (PSN) | Authorized PSN reauth and stable account identity preservation |
| `test-coverage` | Voluntary stretch | Target >95% **per Python module**, not aggregate count; measured only with tests |

### Gold: 21 Core rules

| Core rule | PlayStation Hub applicability | Proposed verification |
| --- | --- | --- |
| `devices` | Applicable | One physical device per console entry; PSN account service device distinct |
| `diagnostics` | Applicable | Allowlisted redacted entry/device diagnostics, snapshot tests |
| `discovery` | Applicable | Use HA DHCP flow with bounded PlayStation protocol verification |
| `discovery-update-info` | Applicable | Same console new IP updates entry without history reassign |
| `docs-data-update` | Applicable | Explain polling, push, freshness, history checkpoints |
| `docs-examples` | Applicable | Real automation examples with clear uncertainty |
| `docs-known-limitations` | Applicable | List Sony permission, firmware, LAN/offline ambiguity |
| `docs-supported-devices` | Applicable | Evidence-based PS5 family/firmware matrix |
| `docs-supported-functions` | Applicable | List exact shipped entities and actions, not roadmap |
| `docs-troubleshooting` | Applicable | No-response, VLAN, pairing, source/DB/storage errors |
| `docs-use-cases` | Applicable | Multi-console monitoring, history and reports |
| `dynamic-devices` | Adapt for entries | Discover new PS5 through new independent config entry, no forced reload |
| `entity-category` | Applicable | Diagnostic/config category for low-priority sensors |
| `entity-device-class` | Applicable | Use fitting HA device classes, not for ambiguous power |
| `entity-disabled-by-default` | Applicable | Disable noisy diagnostics/statistics as appropriate |
| `entity-translations` | Adapt for custom | Use bundled translations/en.json and locale files rather than Core compile pipeline |
| `exception-translations` | Adapt for custom | Typed translated HA errors supplied by custom integration locale files |
| `icon-translations` | Applicable | Declare appropriate bundled icon translations where valid |
| `reconfiguration-flow` | Applicable | Manual IP/address change with identity verification |
| `repair-issues` | Applicable | Scoped pairing/auth/DB repair issues, no secret leakage |
| `stale-devices` | Adapt for physical host | No automatic deletion on UDP silence; expose user-initiated removal |

### Platinum: 3 Core rules

| Core rule | PlayStation Hub applicability | Proposed verification |
| --- | --- | --- |
| `async-dependency` | Applicable when external adapter used | Async-native protocol transport, nonblocking DB actor |
| `inject-websession` | Conditional HTTP adapters | Use shared HA aiohttp session only for permitted HTTP calls |
| `strict-typing` | Voluntary stretch | Strict typing with scoped immutable DTO/repository protocols |


## 2. Reconciliation with actual project scope

- **LAN-only:** `action-setup`, `reauthentication-flow` and some cloud controls may be exempt/conditional in the first limited release if no actions or PSN are exposed. Nothing should appear as operational unless implemented and tested.
- **Remote Play:** Wake/standby require targeted action permission, serial commands, user-facing typed exceptions and post-command confirmation. Optional feature gates in SPEC-002 remain open.
- **PSN:** Account setup/reauth, cloud presence and catalog depend on SPEC-003 Sony permission; no Core Quality Scale designation can override that requirement.
- **Independent physical devices:** New consoles may need independent *config entries* rather than adding entities to one existing “hub” device; apply the spirit of dynamic-devices while preserving ownership and user confirmation.
- **No device on silence:** A missing UDP status reply is never authoritative deletion or physical power OFF; stale-devices requires explicit safe user removal when absence cannot be proved.
- **One sidebar:** Frontend behavior and private WebSocket ACL are separate from Core quality rules and must pass ADR-0010/SPEC-005 security/UX tests.
- **Source reliability:** For every rule a test/CI evidence link and approved release scope are required. Before that, status remains NOT_IMPLEMENTED / NOT_TESTED.

## 3. Evidence record

For each applicable rule, a future record must contain: official rule URL, exact requirement, implementation file+line, test IDs, HA Core release, Python version, actual result, exception/exemption rationale where legitimate, reviewer/date and change commit. A passing aggregate “80 legacy frontend tests” assertion is **not evidence** of passing per-module Python coverage, current CI or Home Assistant integration quality.

## 4. Official sources

- https://contributors.home-assistant.io/core/quality-scale/rules/
- https://contributors.home-assistant.io/core/quality-scale/
- https://contributors.home-assistant.io/core/quality-scale/quality-scale-file/
- https://contributors.home-assistant.io/core/quality-scale/test-coverage/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/validation/
- [Batch 02 source audit](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md)
- [Release gates](../release/quality-gates.md)

**Outcome:** All 54 current Core rule names mapped to applicability and future tests; no quality tier asserted and no code written.
