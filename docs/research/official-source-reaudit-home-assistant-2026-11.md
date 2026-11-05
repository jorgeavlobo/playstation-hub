# Official-source re-audit — Home Assistant 2026.11, Marketplace, HACS and PlayStation Hub

**Review date:** 2026-11-05  
**Status:** Research and documentation correction; no implementation or integration validation  
**Repository:** `jorgeavlobo/playstation-hub`, `main`  
**Primary artifact audited:** `ARCHITECTURE_GUIDE.md` version 0.40.2 (2,663 lines; approximately 257k characters before this audit)  
**Baseline verified:** Home Assistant Core **2026.11.0**, released **2026-11-04**; official pinned `pyproject.toml` requires **Python >=3.14.2**  
**Sources:** Official Home Assistant release notes, the unified Contributors site, official Marketplace/HACS publishing references and pinned Core 2026.11.0 code. Third-party PlayStation repositories are **not** official Sony protocol or licensing sources.

> **Evidence policy:** A source inspection proves only the published documentation or code at the stated version. It does not prove that PlayStation Hub is functional, compatible with an actual PS5, authorized by Sony, installed in Marketplace, or capable of reliable backup/restore. This review preserves the historical DOC-001–DOC-080 record and adds a current, prioritized corrective overlay.

## 1. Executive result

The Bible remains architecturally useful and unusually detailed, but its earlier chapters and some review entries mix past assumptions with later decisions. **Do not rewrite historical source audit conclusions as if they never happened**; mark the current binding choices and replace outdated *active instructions*. The review identifies **18 actionable findings** across Marketplace distribution, Python/API baseline, DeviceInfo, entity naming, lifecycle, config flows, frontend compatibility, backup, translations, persistent data and branch policy.

### High-impact discoveries

1. On **2026-11-04**, Home Assistant **2026.11.0** introduced the **Marketplace** as an integrated HACS experience under Settings, across installation types. The new Marketplace contributor documentation is the primary current developer source; `hacs.xyz` remains relevant as a compatibility/reference resource.
2. The official Core 2026.11.0 `pyproject.toml` pins `requires-python = ">=3.14.2"`. **Research baseline**: 2026.11.0/Python 3.14.2. Whether that becomes the **minimum supported** HA version remains an explicit project decision.
3. Core 2026.11 changes DeviceInfo/ChildDeviceInfo from TypedDict to dataclass; use typed construction, attributes, `.as_dict()` and `UNDEFINED` handling appropriate to the pinned version.
4. Core 2026.11 config entry lifecycle methods return `None` or raise translated `ConfigEntry*` exceptions for core integrations; **custom integrations may still return booleans**, but new code should prefer the modern pattern.
5. Flow form/menu/progress/external-step results should explicitly pass `step_id`. It becomes mandatory for custom integrations in **2027.5.0**, while 2026.11 gives a deprecation warning for omissions.
6. 2026.11 entity naming composes context around device and entity names, preserving existing entity IDs. Use standalone translated entity names instead of embedding console/friendly device names in every entity.
7. 2026.11 can rename entity IDs **in place**. Listeners keyed on `entity_id` require `async_entity_id_changed` rather than assuming remove/add hooks always run.
8. Devices belong to **one config entry** (with at most one subentry) in the modern HA registry. Distinct physical-console and optional PSN account entries must avoid sharing a single physical DeviceEntry across multiple entries.
9. New repairs can be linked to `config_entry_id` and refreshed without delete/recreate churn; useful for per-console pairing and per-account reauth warnings.
10. The Marketplace guide explicitly documents manifest `categories`, `persistent_directory`, local `brand/icon.png`, release-tag/version alignment, immediate first-install config flow, and restart behavior on updates/removals.
11. The official category **`media_entertainment.gaming`** matches this integration. The category key is optional for custom integrations but omission is a HACS action warning; invalid categories fail it.
12. The Home Assistant 2026.11 frontend removed some older web components/CSS tokens; full-page custom panel theme handling gained `--ha-panel-background` and related variables. Avoid hardcoded opaque panel backgrounds.
13. **Custom integrations** ship fully generated `translations/en.json` (required, complete) and localized files. They should **not depend on Core's `strings.json` compile/Lokalise process**, and translation references `[%key:...%]` are not resolved in custom integration JSON.
14. Home Assistant has a supported backup platform pre/post hook, as the Bible's pinned 2026.11 backup manager audit already established. The unresolved question is PlayStation Hub's **consistent SQLite snapshot/restore implementation**, not whether the mechanism exists.
15. The `next` branch is obsolete and was deleted by the maintainer. Feature branches should be created **on demand** from `main`; `develop` is legacy reference.
16. Official Marketplace release rules distinguish **installing a custom repo** from **catalog admission**; full GitHub release and clean HACS Action/Hassfest are catalog gates, not universally necessary for development installs.
17. The Marketplace supports `hacs.json.persistent_directory` for data inside the integration directory, but our preferred application data path **outside HACS-managed source** remains safer as a design direction pending HA backup tests.
18. The official integration quality scale **does not assign formal tiers to custom integrations**. Use its rules as voluntary engineering quality standards without claiming Gold/Platinum certification.

## 2. Findings with severity, evidence and action

| ID | Priority | Existing issue or opportunity | Source-backed correction | Verification plan |
| --- | --- | --- | --- | --- |
| OFF-001 | P0 documentation | Older first chapters still prescribe `next` | Current policy: `main` + on-demand `feature/*`; `develop` reference | GitHub branch strategy review |
| OFF-002 | P0 deployment | Guide presents standalone HACS as the default present-day install | Lead with 2026.11 integrated Marketplace, retain older HACS compatibility note | Clean HA OS 2026.11 Marketplace install |
| OFF-003 | P0 runtime | HA and Python baselines unpinned | Core 2026.11.0/Python >=3.14.2 source baseline, minimum support TBD | Pin versions and matrix |
| OFF-004 | P0 API | DeviceInfo may be treated as dict | Use 2026.11 dataclass/attributes/as_dict; handle UNDEFINED | Device registry tests |
| OFF-005 | P0 ownership | Multi-entry device ownership not explicit enough | One physical device belongs to one console entry; account entries own separate service device | HA multi-entry registry tests |
| OFF-006 | P1 flow | Flow result `step_id` missing from implementation checklist | Always supply step_id for form/menu/progress/external; mandatory 2027.5 | Config-flow tests |
| OFF-007 | P1 setup | Old boolean return pattern | Prefer `-> None` + translated ConfigEntry exception; custom bool still allowed | Setup/unload/migration tests |
| OFF-008 | P1 entities | Pre-2026.11 naming/context assumptions | Use has_entity_name/translation keys and context-aware display; don't rely on friendly_name | HA naming and i18n tests |
| OFF-009 | P1 lifecycle | Entity renames assumed remove/add | Use entity_id_changed callback for keyed listeners, async_on_remove for cleanup | Runtime rename tests |
| OFF-010 | P1 repairs | Per-entry repairs cleanup manual | Use config_entry_id scoped issues and refresh helper | Unlink/reload/delete tests |
| OFF-011 | P1 manifest | No selected Marketplace category | Propose `media_entertainment.gaming`; validate exact manifest | HACS Action/hassfest |
| OFF-012 | P1 packaging | Brand placement and persistence described as open | Local `custom_components/playstation_hub/brand/icon.png`; no mutable DB there by default | Clean install/upgrade asset check |
| OFF-013 | P1 frontend | 2026.11 theme/component changes absent | Use current CSS tokens, avoid old ha-md-list/ha-formfield, preserve panel background | Browser light/dark/mobile tests |
| OFF-014 | P1 translations | Old references to `strings.json` may mislead | Custom `translations/en.json` complete, `pt.json` localized, no unresolved reference syntax | Hassfest, locale tests |
| OFF-015 | P1 storage | Backup hook source evidence sometimes called unresolved | Pinned 2026.11 manager hook invocation verified; **snapshot consistency still open** | HA OS WAL backup/restore |
| OFF-016 | P1 releases | HACS vs Marketplace catalog rules can be conflated | Separate custom repo installation, Marketplace catalog entry, releases and validation gates | Release/install smoke test |
| OFF-017 | P2 information architecture | Historical DOC-001–080 can look equally current | Add binding-authority banner and current review index; retain provenance | Markdown/link audit |
| OFF-018 | P2 future compatibility | Upcoming 2026.12 UNDEFINED change may affect design | Watchlist only; not a 2026.11 required migration | Recheck after 2026.12 stable |

## 3. Recommended support baseline — decision proposal

**Official pinned fact:** `home-assistant/core` tag `2026.11.0`, `pyproject.toml`, `requires-python = ">=3.14.2"`.

**Candidate implementation baseline (NOT YET APPROVED):**
- Start source/API reconnaissance and first integration tests against **Core 2026.11.0** using its compatible Python 3.14.2+ environment.
- When choosing minimum supported HA version, compare the costs of 2026.11-only targeting against an earlier stable 2026.10 installation. Do not advertise earlier support until tested.
- Define `hacs.json.homeassistant` **only after approving** that minimum version; Marketplace checks it for repositories with releases. Do not invent `manifest.json` as the sole place to declare the Marketplace's minimum version.
- Distinguish the Python host runtime supplied by Home Assistant from the Python version used in external development/CI.
- Pin a supported release tag, not just `dev`, when inspecting APIs and writing test expectations.
- Trigger regression testing on new HA stable and beta releases.

## 4. Marketplace distribution refresh

**Source precedence:**
1. `contributors.home-assistant.io/marketplace/` and official 2026.11 release notes are authoritative for the integrated Marketplace.
2. `hacs.xyz` remains useful to document HACS compatibility and existing catalog submission rules.
3. `home-assistant/core` pinned tags supply executable API signatures; mutable `dev` is research only.
4. Sony/community PlayStation code is not a substitute for provider authorization.

**Packaging and metadata proposal:**
```text
playstation-hub/
  hacs.json                       # Marketplace/HACS metadata
  README.md
  LICENSE
  custom_components/
    playstation_hub/
      __init__.py
      manifest.json               # categories, version, required HA manifest keys
      config_flow.py
      translations/
        en.json                   # required complete fallback for custom integration
        pt.json                   # Portuguese (Portugal); test locale mapping
      brand/
        icon.png                  # local integration icon
      frontend/
        ...                       # built assets; no runtime Node.js
```

**Proposed `manifest.json` metadata (illustrative only, not ready-to-use manifest):**
```json
{
  "domain": "playstation_hub",
  "name": "PlayStation Hub",
  "config_flow": true,
  "categories": ["media_entertainment.gaming"],
  "version": "0.1.0"
}
```
Other mandatory manifest fields, requirements and product support metadata are intentionally omitted from this *fragment*; do not copy it as a complete manifest.

**Marketplace `hacs.json` proposal (not created):**
```json
{
  "name": "PlayStation Hub",
  "homeassistant": "2026.11.0"
}
```
The `homeassistant` value here is a **candidate**, not an approved minimum. Keep release version and tags aligned, and avoid adding `persistent_directory` merely for convenience; our preferred history DB is outside the managed integration directory.

### Integration catalog admission

The current official Marketplace contributor guide confirms the familiar `hacs/default` process:
- Public GitHub repository; issue tracker, README, license, description and topics.
- HACS Action with **no ignored checks**, and Hassfest for integrations.
- **Full GitHub release** after passing actions for catalog application; merely pushing a tag is insufficient.
- PR against `hacs/default`'s `integration` list, sorted, created from a branch forked from that repository's `master`; this refers to **hacs/default**, not our `playstation-hub` branch strategy.
- Brand icon in integration `brand/`; manifest domain must not conflict with official Core domain; owner/maintainer reviews apply.
- Standard custom-repository installation has different, less stringent publishing prerequisites, but should still pass our internal CI before public distribution.

**Marketplace behavior:** A config-flow integration can be offered for setup immediately after its initial install; updates/removal of loaded integrations require restart and Marketplace creates a repair. Test these flows on a clean 2026.11 HA OS environment.

## 5. Native integration and entity API changes

### 5.1 DeviceInfo / ChildDeviceInfo

For the Core 2026.11 API, construct `DeviceInfo(identifiers=..., name=...)` and access fields by attributes. A missing field reads as `UNDEFINED` (not necessarily `None`); check explicitly. Use `.as_dict()` when JSON-serializing or storing device information. The old mapping compatibility layer is not a forward-compatible implementation strategy.

**Device registry constraint:** A device is owned by exactly one config entry and at most one subentry. Our physical console key must map to the console's entry, while a PSN account service device must be distinct. Never merge a many-to-many console/account association by attaching a single DeviceEntry to multiple config entries. Avoid deprecated `DeviceEntry.config_entries` / `primary_config_entry`, old `via_device` and deprecated default-name fields. Prefer `via_device_id` only when a true parent/child hardware relation exists, not for accounts.

### 5.2 Config Entry methods and flow results

Prefer for new code:
```python
async def async_setup_entry(
    hass: HomeAssistant,
    entry: PlayStationHubConfigEntry,
) -> None:
    """Set up one PlayStation Hub config entry."""
    ...
```
Failures raise appropriate translated `ConfigEntryNotReady`, `ConfigEntryAuthFailed`, or `ConfigEntryError`. Use current unload APIs such as `async_unload_platforms_or_raise` when supported. **Qualification:** The 2026.11 change is enforced for core integrations; custom integrations still support boolean returns, so this is a forward-looking code-style choice, not a current custom integration hard failure.

Pass explicit `step_id` to `async_show_form`, `async_show_menu`, `async_show_progress` and `async_external_step`. This is a best practice now and becomes mandatory for custom integrations in 2027.5.0.

### 5.3 Entity naming and lifecycle

- Use context-free translated entity descriptors: a console device named `PS5 — Living Room` has an entity named `Power mode`, not `PS5 Living Room Power mode` as the entity's literal own name.
- Preserve stable `unique_id` and respect user-edited `entity_id` / display names; Home Assistant 2026.11 composes names with context and does not rewrite existing entity IDs.
- Mark the one primary entity only where appropriate according to current entity naming rules; do not assume each console requires a media_player main entity.
- Explicitly test `async_entity_id_changed` and use `async_on_remove` for cleanup that must survive partial add failures or renamed entities.
- Never store device identity based on user-facing device/entity name.

### 5.4 Per-entry repairs

Use `config_entry_id` when creating a device-specific pairing issue or account reauth issue. That ties issue lifecycle to the config entry, avoiding manual deletes on reload. Consider `async_refresh_issues` for condition-based sets without re-notifying users who dismissed unchanged issues. Future subentry-specific issue support in 2026.12 is not required at the 2026.11 baseline.

## 6. Sidebar frontend compatibility — 2026.11

The new frontend documentation specifies:
- `ha-md-list` and `ha-md-list-item` removed; use supported `ha-list-base`, `ha-list-item-base` or `ha-list-item-button`.
- `ha-formfield` removed; `ha-switch` and `ha-checkbox` accept labels in their own content slot.
- Old Material/MDC chip, outlined-button and typography CSS tokens are being replaced by `--ha-*` tokens.
- Theme panel backgrounds are now painted centrally. A custom panel should not cover them with an unconditional host `background-color: var(--primary-background-color)`.
- Use `--ha-panel-background`, `--ha-panel-toolbar-background` and `--ha-data-table-background` when relevant, with fallbacks for older versions only if those versions are supported.

**Recommendation:** Avoid undocumented internal HA component assumptions where simple Web Components/CSS are sufficient. Validate laptop/tablet/mobile companion webviews, accessibility, keyboard focus, light/dark theme and safe areas. One sidebar panel remains the approved product design; the frontend has not been written.

## 7. Translations, brands and quality scale

**Custom integrations:** Complete `translations/en.json` and localized `translations/pt.json` are supplied in our own release; no `strings.json` compilation or Lokalise translation infrastructure is automatically available. Test PT-PT locale behavior and placeholder parity with English. Translation references of the `[%key:...%]` form are not resolved for custom integration files; write full strings. Keep application-owned frontend translations separately versioned and consistent.

**Branding:** Since HA 2026.3 custom integrations can ship `custom_components/playstation_hub/brand/icon.png`, with optional logo/dark/high-res variants per official brand size and licensing rules. Do not use Sony's protected logos without permission, or official Home Assistant brand assets.

**Quality scale:** The official Core Integration Quality Scale does not award Bronze/Silver/Gold/Platinum tiers to custom integrations. We may voluntarily apply applicable rules, but must not claim an official quality certification.

## 8. Persistence and backup — corrections, not premature approval

The Bible already performed a source-verified check of `homeassistant/components/backup/manager.py` at `2026.11.0`, confirming registered pre/post backup actions and finally-handled post actions, with caveats for cancellation/crash. **Preserve that finding** and stop treating the mere existence of backup hooks as unknown.

Remaining requirements before accepting ADR-0008:
- Decide private SQLite data path outside HACS-managed code and confirm archive coverage.
- Test SQLite WAL active transactions and a consistent snapshot under the native HA backup lifecycle.
- Test all files selected for backup, snapshot high-water mark, recovery and HA OS restore.
- Confirm secret-store permissions and backup encryption, plus stale Sony token reauth.
- Avoid duplicate archive growth when including both raw live database/WAL and a backup snapshot.
- Compare `hacs.json.persistent_directory` as a known update-preservation mechanism, but do not conflate it with transactionally safe backup or an approved app-owned DB path.

The HA 2026.11 release adds the ability to use internal or USB local disks for backup storage and optimizes restore copying; this is an operational capability, not proof our SQLite is consistent.

## 9. Branching, historical notes and precedence

The maintainer deleted the obsolete `next` branch. Current plan:
- `main`: research/documentation now; reviewed release branch once product code exists.
- `feature/<scope>`: on-demand implementation branch created only when explicitly authorized.
- `develop`: frozen previous MQTT/App/Lovelace implementation for research only.
- No permanent empty development branch, no automatic background implementation.

**Document precedence:** Current explicit user decisions > new binding architecture-guide sections and accepted ADRs > proposed ADRs > historical DOC-001–DOC-080 notes. Historic assumptions about `next`, “MQTT and/or”, Lovelace alternatives, `strings.json` for custom integrations and standalone HACS installation are not active requirements.

## 10. Source register (official documents opened or source inspected)

| ID | Official current source | Date / result |
| --- | --- | --- |
| OS-001 | https://www.home-assistant.io/blog/2026/11/04/release-202611 | 2026-11-04; integrated Marketplace, entity naming, backup changes |
| OS-002 | https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml | Pinned Core; Python >=3.14.2 |
| OS-003 | https://contributors.home-assistant.io/marketplace/ | New official Marketplace documentation index |
| OS-004 | https://contributors.home-assistant.io/marketplace/guides/integrations/ | Custom integration manifests, translations, branding, persistence and restart rules |
| OS-005 | https://contributors.home-assistant.io/marketplace/guides/catalog/ | HACS/default catalog entry process and action/release requirements |
| OS-006 | https://contributors.home-assistant.io/marketplace/reference/repository-structure/ | One custom integration, package file placement |
| OS-007 | https://contributors.home-assistant.io/marketplace/reference/hacs-json/ | Minimum HA version, persistent_directory, version keys |
| OS-008 | https://contributors.home-assistant.io/marketplace/reference/validation/ | Categories, HACS Action and Hassfest |
| OS-009 | https://www.hacs.xyz/docs/publish/integration/ | Compatible historic HACS publishing rules |
| OS-010 | https://www.hacs.xyz/docs/publish/include/ | Old catalog flow, currently consistent with OS-005 |
| OS-011 | https://www.hacs.xyz/docs/publish/action/ | HACS Action, ignored checks, validation triggers |
| OS-012 | https://contributors.home-assistant.io/core/integrations/manifest/ | Manifest categories, config flow and integration types |
| OS-013 | https://contributors.home-assistant.io/core/integrations/categories/ | Gaming category `media_entertainment.gaming` |
| OS-014 | https://contributors.home-assistant.io/core/integrations/brands/ | Local brand image placement and dimensions |
| OS-015 | https://contributors.home-assistant.io/core/integrations/translations/ | Custom integration en.json, no references, localization |
| OS-016 | https://www.home-assistant.io/blog/2026/11/03/naming-things-in-home-assistant/ | Entity/device naming in 2026.11 |
| OS-017 | https://contributors.home-assistant.io/blog/2026/10/13/device-info-class/ | DeviceInfo/ChildDeviceInfo dataclasses |
| OS-018 | https://contributors.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/ | Modern async_setup/unload/migrate -> None |
| OS-019 | https://contributors.home-assistant.io/blog/2026/10/23/flow-results-require-step-id/ | step_id required later, warning now |
| OS-020 | https://contributors.home-assistant.io/blog/2026/10/12/new-entity-lifecycle-hooks/ | In-place renaming and cleanup hooks |
| OS-021 | https://contributors.home-assistant.io/blog/2026/10/28/issue-registry-refresh/ | Per-config-entry repair issue and refresh helper |
| OS-022 | https://contributors.home-assistant.io/blog/2026/08/24/device-registry-follow-up-changes/ | Single config entry ownership/deprecation |
| OS-023 | https://contributors.home-assistant.io/blog/2026/09/15/device-entry-config-entries-deprecation/ | DeviceEntry.config_entry_id policy |
| OS-024 | https://contributors.home-assistant.io/blog/2026/10/28/frontend-component-updates-2026.11/ | Panel CSS, component removals |
| OS-025 | https://contributors.home-assistant.io/frontend/custom-ui/panel/ | Supported custom panel frontend contract |
| OS-026 | https://contributors.home-assistant.io/core/integrations/backup/ | Backup platform contract and agents |
| OS-027 | https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py | Pinned backup hook ordering reviewed in prior Bible section |
| OS-028 | https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/storage.py | Pinned Store atomic_writes/private/options code |
| OS-029 | https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/panel_custom/__init__.py | Pinned panel_custom API |
| OS-030 | https://contributors.home-assistant.io/blog/2026/11/01/undefined-helper/ | Future 2026.12 Undefined deprecation; watchlist |
| OS-031 | https://developers.home-assistant.io/docs/core/integration-quality-scale/ | Core quality scale, not official custom integration tier |
| OS-032 | https://www.home-assistant.io/common-tasks/general/backups | User backup selection and restore, distinct from SQLite snapshot reliability |

**Link caveat:** Old `developers.home-assistant.io` URLs commonly redirect to `contributors.home-assistant.io`. Maintain canonical new locations while retaining original URLs in historical DOC entries as provenance. URLs above are a curated official reference register, not proof each individual integration quality rule or all Sony legal pages has been re-audited.

## 11. Recommended implementation gates after this audit

1. Decide whether `2026.11.0` is the minimum supported Core version, record Python >=3.14.2 and Marketplace `hacs.json.homeassistant`.
2. Accept the logical multi-console Config Entry plan and verify new DeviceInfo/registry behavior.
3. Design flow results with `step_id`, modern ConfigEntry exceptions and clean entity rename lifecycle.
4. Add `media_entertainment.gaming`, `brand/icon.png` and full `translations/en.json` to the future implementation checklist.
5. Write CI for HACS Action, Hassfest and the current Core device/entity API contracts.
6. Validate a read-only single-panel frontend against 2026.11 themes, routes and authenticating WS.
7. Prove HA OS backup/restore with the actual proposed SQLite location and concurrent writes before promising historical data retention.
8. Keep SPEC-002 Remote Play byte gaps and SPEC-003 Sony permission blockers unchanged; no capability enablement without evidence.
9. Update architecture guide active sections and references, and re-run a documentation-link audit at the next release.
10. Record approval separately from source research and test evidence.

## 12. Disposition

**Review complete at source/document level.** The audit justifies multiple targeted improvements to the Bible and development checklist. It does **not** approve a production Python baseline, resolve Sony API permissions, implement code or close hardware/SQLite tests.

**Next review event:** Home Assistant 2026.12 beta or stable, significant HACS Marketplace changes, or before first implementation branch.
