# Legacy frontend inventory and sidebar UX research

**Date:** 2026-11-05  
**Status:** Documentation-only investigation; frontend source not available at expected paths in accessible `develop` tree  
**Repository:** `jorgeavlobo/playstation-hub`  
**Branches:** `develop` read-only legacy; `main` documentation only  
**Product decision:** One native Home Assistant sidebar panel, no Lovelace card, no MQTT or separate App.

## 1. Evidence and limitations

The `develop/README.md` describes a private operational snapshot with a Lovelace card v1.1.2, an App backend v0.5.0, and 80 frontend tests passing **locally**. It explicitly says the private snapshot must never be published, and describes transferring sanitized backend and frontend code to `develop` as a future task. The README is evidence of a claimed private snapshot, **not proof that its frontend files are currently present in this Git repository or that we have inspected its components/tests**.

At this review, fetching `develop/frontend`, `develop/frontend/package.json`, `develop/frontend/README.md`, `develop/frontend/src/main.ts`, `develop/frontend/index.html`, and several likely card entry filenames returned NOT_FOUND. The GitHub file search tool indexes the default `main` branch rather than `develop`, so its lack of frontend results is not independent proof of the `develop` tree contents. A complete Git tree listing or a verified sanitized source artifact is required before claiming a full legacy frontend source audit.

**Conclusion:** The current investigation can define UX migration requirements and a source acquisition plan, but cannot legitimately claim to have audited the old Lovelace card's actual rendering, DOM structure, tests, accessibility or performance.

## 2. Verified references

- [Legacy README](https://github.com/jorgeavlobo/playstation-hub/blob/develop/README.md): private snapshot description, claimed versions and frontend tests, future import plan, security warning.
- [ADR-0002](../decisions/ADR-0002-sidebar-panel.md): accepted single sidebar panel.
- [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md): proposed panel structure, WebSocket and permissions.
- [Legacy backend code review](legacy-code-review-and-refactoring-blueprint-2026-11.md): actual inspected backend files.
- [Official Home Assistant 2026.11 source re-audit](official-source-reaudit-home-assistant-2026-11.md): frontend/theme/Marketplace changes.
- [Home Assistant panel documentation](https://contributors.home-assistant.io/frontend/custom-ui/panel/): native panel contract.

## 3. UX feature inventory to verify against actual legacy source

| Area | Proposed migration target | Actual old UI code verified? |
| --- | --- | --- |
| Dashboard overview | Multi-console tiles, status freshness and navigation | No |
| Power/status | Separate LAN power, availability, command confirmation | No |
| Current game | PSN account-sourced game with provenance and stale state | No |
| Player usage | Per-console observed time and ambiguous account attribution | No |
| Historical charts | Day/week/month/year, gaps and DST-aware labels | No |
| Game ranking | Stable title IDs, no name-based accidental merges | No |
| Artwork | Rights-checked provider references and safe fallbacks | No |
| Mobile | Narrow portrait, safe areas, dark/light themes | No |
| Loading/error | Independent source failures and cached last-known state | No |
| Localization | English/PT-PT and extensible translations | No |
| Accessibility | Keyboard, focus, screen reader, reduced motion | No |
| Security | No secrets, XSS-safe text and backend authorization | No |
| Performance | Shared subscriptions, bounded history queries, lazy views | No |

Do not represent this list as observed legacy features. It is a checklist of what the **new** product should support or inspect in a sanitized legacy artifact.

## 4. New single-panel information architecture (design proposal)

```text
PlayStation Hub sidebar
  Overview
    Console cards: power, reachability, freshness, current game source
    Account cards: optional PSN presence, credential status
    Quick links: details, diagnostics
  Consoles
    Console details, timeline, pairing status, safe command controls
  Activity
    Historical intervals, coverage/unknown gaps, comparisons
  Games
    Recent/played/entitled tabs, provenance, platform and editions
  Accounts
    Provider identity, privacy and reauth status
  Settings & Diagnostics
    Config flow links, health, retention, backup and permissions
```

One sidebar route may contain internal subnavigation; this does not imply multiple HA sidebar entries. Console and account views must not merge provider online status with physical power.

## 5. Proposed UI state contract

Every view should consume a backend DTO with:
- `schema_version`, `snapshot_revision`, `boot_id` and authorized target scope.
- `data_as_of_utc`, per-source last observed and freshness/availability.
- Explicit `AWAKE/STANDBY/UNKNOWN` rather than a misleading optimistic Boolean.
- Separate account presence and current title assertions, including uncertain physical attribution.
- Optional command status: `pending/sent/confirmed/unconfirmed/failed`.
- Historical totals with coverage, unknown gaps and distinct provider lifetime time.
- Pagination and query bounds for history, library and game art.
- Stable sanitized error codes for localization.

These are proposals from ADR-0010, not existing backend endpoints.

## 6. Component and test inventory to perform once source is available

1. Obtain an exact Git commit or sanitized frontend package path; confirm provenance and that it contains no private snapshots, tokens, MACs or account identifiers.
2. Inventory all HTML/JS/CSS components, module dependencies and bundling assumptions.
3. Identify all frontend reads from MQTT, HA entity attributes and old App endpoints; record each with line references.
4. Map each view to a future versioned backend WebSocket DTO.
5. Inspect historical chart timezone, sorting, number formats, negative/unknown durations and cache behavior.
6. Audit DOM construction for XSS, HTML injection and image URL validation.
7. Audit accessibility (keyboard, focus, screen readers, contrast, reduced motion), responsive behavior and theme tokens against HA 2026.11.
8. Read existing frontend tests and classify reusable behavior tests versus obsolete Lovelace/MQTT tests.
9. Check performance: subscriptions, event handlers, timers, history pagination and unbounded DOM nodes.
10. Publish a source-backed component-by-component audit with precise file/line citations; do not claim completion until this is done.

## 7. Design improvements independent of the legacy card

- Show source freshness beside every console and PSN status, not only a global “connected” indicator.
- Distinguish `no data`, `restricted`, `offline account`, `unknown hardware`, and `stale` states.
- Keep user-initiated wake and standby separate from live state; require backend confirmation and authorization.
- Support multiple consoles with clear owner labels and avoid automatic game attribution from one PSN account.
- Display historical *observed/bounded* duration and unknown coverage separately.
- Build accessible chart tables, responsive layouts and keyboard navigation from the beginning.
- Use the current HA panel background/theme CSS and avoid removed HA frontend components.
- Fetch heavy historical data only when its view opens, with server-side pagination and cancellation.
- Keep all PSN-linked screens behind SPEC-003 permission gates; LAN-only UI must be useful on its own.

## 8. Source access blocker and resolution

**Blocker UX-001:** The actual legacy frontend source files were not accessible at the expected `develop/frontend` paths during this review. A full frontend code review remains **NOT_STARTED**, even though a UX requirements audit has been documented.

**Recommended resolution:** First inspect the exact repository tree/commit using a GitHub tree API or obtain the previously described **sanitized source-only** frontend package. Never import or publish the private operational snapshot. Until then, focus on native Home Assistant panel research and specification improvements, not invented code findings.

## 9. Status

- Actual legacy frontend components inspected: **0**.
- Actual frontend tests executed: **0**.
- Verified private snapshot contents: **none**.
- UX/architecture checklist: documented.
- Code changes: **none**.
- New implementation branch: **none**.
- Decision status: ADR-0002 accepted, ADR-0010 proposed.
