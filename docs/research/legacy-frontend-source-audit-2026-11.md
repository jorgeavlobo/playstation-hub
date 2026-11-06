# Legacy frontend source audit — verified `develop` branch

**Date:** 2026-11-05  
**Status:** Source-backed audit; code and tests read, **not executed or modified**  
**Repository:** `jorgeavlobo/playstation-hub`  
**Reference branch:** `develop` (read-only legacy implementation)  
**Documentation branch:** `main`  
**Current product architecture:** one native Home Assistant sidebar panel, no parallel Lovelace card, no mandatory MQTT/App, multiple consoles and optional independently scoped PSN accounts.

> **Correction of previous review:** The earlier [frontend availability note](legacy-frontend-inventory-and-panel-ux-review-2026-11.md) incorrectly concluded that `develop/frontend` was inaccessible. The GitHub connector's `fetch_file` is for **files**, not directories; attempting a directory with it returns NOT_FOUND. The approved GitHub `fetch` action on the REST Contents/Tree API confirmed `frontend/` on `develop`, and individual source files were then fetched successfully. That **tooling mistake is now closed**. The previous note is retained only as an audit trail and points here for authoritative results.

## 1. Branch and source verification

The remote repository has `main` and `develop`; the maintainer deleted `next`. The `develop` root contains `backend/` and `frontend/` directly. The source tree was enumerated from:

- [GitHub Contents API for `develop` root](https://api.github.com/repos/jorgeavlobo/playstation-hub/contents?ref=develop)
- [`develop/frontend` contents](https://api.github.com/repos/jorgeavlobo/playstation-hub/contents/frontend?ref=develop)
- [Frontend tree at SHA `f4a8b76c5c0221fb3cd3671a4c631f5d275beb96`](https://api.github.com/repos/jorgeavlobo/playstation-hub/git/trees/f4a8b76c5c0221fb3cd3671a4c631f5d275beb96?recursive=1)

**Verified file inventory:** 21 files: 1 dashboard card, 2 reusable components, 7 services, 1 CSS file, 10 JavaScript tests.

```text
frontend/
  ps5-dashboard-card.js                  # Legacy Lovelace custom card v1.1.2
  components/
    ps5-game-library.js
    ps5-history-chart.js
  services/
    ps5-daily-history-client.js
    ps5-first-row-metrics.js
    ps5-formatters.js
    ps5-history-client.js
    ps5-history-index-client.js
    ps5-history-navigation.js
    ps5-live-client.js
  styles/
    ps5-game-library.css
  tests/
    ps5-card-navigation.test.mjs
    ps5-daily-history-client.test.mjs
    ps5-first-row-metrics.test.mjs
    ps5-formatters.test.mjs
    ps5-game-library.test.mjs
    ps5-history-client-v11.test.mjs
    ps5-history-client.test.mjs
    ps5-history-index-client.test.mjs
    ps5-history-navigation.test.mjs
    ps5-live-client.test.mjs
```

The old `develop/README.md` reports a private operational snapshot, v1.1.2 frontend and 80 locally passing frontend tests. The source tree actually contains 80 declarations using `test(...)` across ten files. **Counting test declarations is not executing tests**, and the README's historical “passing locally” statement was not revalidated in this audit.

## 2. Verified functional inventory: what the old card actually implements

| Component | Source | Confirmed behavior |
| --- | --- | --- |
| Dashboard root | [`ps5-dashboard-card.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js) | Custom element `PS5DashboardCard`, Shadow DOM, `setConfig`, HA `hass` setter, first-row hero and metrics, monthly history, chart tabs, game rankings/library |
| Current live-state client | [`ps5-live-client.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-live-client.js) | Subscribes to an MQTT topic **via HA's existing authenticated WebSocket**, validates payload and generation, rejects old observations, releases subscription |
| Month history client | [`ps5-history-client.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-client.js) | MQTT history request/response using generated random request ID, monthly validation, response correlation, cancellable pending requests |
| 36-month index | [`ps5-history-index-client.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-index-client.js) | Retained MQTT 36-month index, calendar-window validation and navigation target extraction |
| Month navigation | [`ps5-history-navigation.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-navigation.js) | Only navigates valid calendar months containing recorded gaming activity, with current-month fallback |
| Daily history | [`ps5-daily-history-client.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-daily-history-client.js) | Bounded 1–31-day requests, schema validation, request/response correlation, out-of-order page assembly and cancellation |
| Usage metrics | [`ps5-first-row-metrics.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-first-row-metrics.js) | Comparison of gaming durations and aggregation of daily session totals |
| Date/duration formatting | [`ps5-formatters.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-formatters.js) | Duration, sensor-hour and calendar-period helpers |
| Annual chart | [`ps5-history-chart.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/components/ps5-history-chart.js) | Validates a 12-month dataset, calculates SVG chart dimensions and renders bars |
| Game library | [`ps5-game-library.js`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/components/ps5-game-library.js) | Sorts games by observed duration, displays title image, duration, session count and proportional progress |
| Styles | [`ps5-game-library.css`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/styles/ps5-game-library.css) | Styling for game-library content; main card also embeds an extensive `STYLES` CSS string |

**Important nuance:** The old frontend does **not** open its own MQTT broker connection. It uses the authenticated Home Assistant WebSocket's MQTT subscription command and the `mqtt.publish` service. Thus its client connection mechanics offer valuable event-handling patterns, but its runtime still **depends on HA MQTT and an external producer**, contrary to the new first-party integration architecture.

## 3. Source-confirmed behavior worth retaining conceptually

### 3.1 Correlated, cancellable requests

The history client generates request IDs using `crypto.getRandomValues`, validates calendar periods, subscribes before publishing, matches responses to requests and handles cancellation/timeouts. The daily client assembles out-of-order paginated responses and handles duplicates. **Keep** correlation IDs, validation, pagination and cancellation; **replace** MQTT topics, waiting periods and publish/subscribe request routing with namespaced Home Assistant WebSocket commands and async backend service contracts (ADR-0010).

### 3.2 Robust subscription and connection replacement

The live client tracks a `generation`, rejects older/stale events and disposes its HA WebSocket subscription. The dashboard detects HA connection replacement and resets different data clients. **Keep** generation fencing, listener cleanup and reconnect/resync, but have one shared backend snapshot/subscription architecture rather than one per widget/topic.

### 3.3 Incremental updates and avoidance of invented time

The dashboard updates current hero/metrics in place for ordinary HA changes and avoids rebuilding the entire Shadow DOM on every update; it uses generation-controlled async history loads. The live view explicitly prints placeholder marks for session start and real-time duration because backend observations do not confirm those values. **Keep** this conservative honesty rather than synthesizing fake session start/duration from receipt time.

### 3.4 Activity navigation and meaningful data views

The 36-month index supports skipping inactive months, an accessible concept for activity navigation, with calendar rollover handling. The UI includes week/month/6-month/12-month/2-year/3-year chart ranges; the monthly report contains console/gaming time, sessions, game counts and ranked titles. The single-panel UX can reuse these information needs while adding multi-console filters, source freshness and unknown coverage.

### 3.5 Safer text handling

The game library assigns provider title names using `textContent`, not `innerHTML`; images include alt text and use lazy loading. **Keep** escaped text and lazy images. A string merely matching `https://` is not complete artwork provenance, content safety or permission validation.

## 4. Evidence-based risks and modernization gaps

| ID | Priority | Actual source evidence | Future improvement (not a code change yet) |
| --- | --- | --- | --- |
| UI-001 | P0 | [Card lines 52–62](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js#L52-L62) hardcode `sensor.ps5_monitoring_service_ps5_...` entities | Dynamic canonical device IDs and HA registry-aware inventory for multiple consoles |
| UI-002 | P0 | [History client](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-client.js) and [daily client](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-daily-history-client.js) use MQTT request topics/service | Replace with authorized `playstation_hub/*` backend WS API; no MQTT dependency |
| UI-003 | P0 | [Card lines 530–566](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js#L530-L566) maps `!console_active` to “Consola desligada” | Only assert AWAKE/STANDBY with source confirmation; otherwise UNKNOWN or stale |
| UI-004 | P0 | Old live DTO reports single player gaming and title without provenance | Separate LAN physical power vs PSN account activity and ambiguous attribution |
| UI-005 | P1 | [Card line 64 onward](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js#L64-L122) contains large hardcoded dark CSS/color overrides | Theme-aware tokens and modular scoped CSS; adaptive 2026.11 panel backgrounds |
| UI-006 | P1 | Mixed Portuguese and English literals directly in [card render](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js#L915-L1090) | Full EN/PT-PT i18n, accessibility and error-code translations |
| UI-007 | P1 | [`getCurrentPeriod`](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-formatters.js) and 36-month index use browser local `new Date()` | Define reporting IANA timezone from backend/HA user; consistent UTC boundaries and DST |
| UI-008 | P1 | Month history response and game list depend on source schema and single period | Versioned DTOs, scope, source/coverage, cursor pagination for multi-year queries |
| UI-009 | P1 | Historical request clients insert a [2-second subscribe delay](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-client.js#L325-L327) for MQTT compatibility | Eliminate empirical delay; use atomic subscribe-with-snapshot or revision catchup |
| UI-010 | P1 | [Live client](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-live-client.js) uses 90s `STALE_MS`; dashboard also uses 90s | Derive per-source freshness policy from reconciler, not duplicated frontend magic constants |
| UI-011 | P1 | Covers accepted if URL string starts with https; [library component](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/components/ps5-game-library.js#L86-L103) | Separate approved artwork host/rights/cache/referrer policy, backend-safe proxy if permitted |
| UI-012 | P1 | Card rebuilds `shadowRoot.replaceChildren()` for history and whole view updates | Preserve focus, scroll and screen reader announcement; component-level updates and virtual/bounded lists |
| UI-013 | P1 | History chart uses fixed SVG colors and visual bars | Theme-aware, screen-reader accessible chart plus equivalent data table and reduced motion |
| UI-014 | P2 | JS import and CSS paths carry literal `?v=1.1.2`, some service imports `?v=1.0.5` | Reproducible content-hashed bundling tied to Python release, cache mismatch handling |
| UI-015 | P1 | `getMonth`/daily calendar parsing uses local browser date assumptions | Explicit `timezone` and half-open request ranges; backend validates calendar boundaries |
| UI-016 | P2 | One large card class (approx. 1,261 lines), long inline CSS | Split PanelShell, ConsoleCard, HistoryChart, GameLibrary, shared state and API client |
| UI-017 | P1 | Separate subscriptions for history index/live and request clients | Share a single subscription manager/store to avoid per-view polling or event leaks |
| UI-018 | P1 | Public/local panoramic images keyed by hardcoded title ID | Optional licensed artwork, fallback and bounded cache; no hardcoded game catalog |
| UI-019 | P1 | Existing frontend tests mock HA WebSocket/MQTT and fake DOM, not a running native panel | Adapt behavioral tests, add browser/mobile integration, accessibility, theme and WS ACL checks |
| UI-020 | P1 | README calls frontend a private snapshot not yet imported even though source exists | Correct branch documentation references; do not expose private operational data |

**Evidence classification:** A code pattern is verified by source inspection; whether it causes a bug or regression is **not proven** until a reproducible test fails. UI-003 is a semantic conflict with new architecture, not proof that the legacy display was wrong for its own MQTT payload.

## 5. Existing test suite inventory (80 test declarations, unexecuted)

Ten test files contain **80** source declarations of the form `test(...)`. This independently corroborates the legacy README's count but **not** its historical “all pass” claim.

| File | Test declarations | Domains |
| --- | ---: | --- |
| `ps5-card-navigation.test.mjs` | 20 | Month navigation, rollover, stale responses, chart mode, hero behavior |
| `ps5-daily-history-client.test.mjs` | 8 | Day validation, request correlation, paging, cancellation, errors |
| `ps5-first-row-metrics.test.mjs` | 6 | Comparison and daily totals |
| `ps5-formatters.test.mjs` | 5 | Period and duration format |
| `ps5-game-library.test.mjs` | 6 | Collection, sorting, artwork, durations, progress |
| `ps5-history-client-v11.test.mjs` | 5 | Subscription reuse, concurrent correlation, cancellation, malformed response |
| `ps5-history-client.test.mjs` | 3 | Subscribe-before-publish, filtering, invalid period |
| `ps5-history-index-client.test.mjs` | 11 | Index validation, calendar, subscription lifecycle |
| `ps5-history-navigation.test.mjs` | 10 | Adjacent activity period and navigation |
| `ps5-live-client.test.mjs` | 6 | Payload validation, generation filtering, disposal/reconnect |
| **Total** | **80** | **No tests executed in this audit** |

The tests are reusable as **design intent and behavior specifications**, not as a testing certificate for the new Home Assistant Core 2026.11 integration or a multi-console setup.

## 6. Source-to-target component map

| Legacy source | New panel/service target (proposed) | Reuse | Don't port |
| --- | --- | --- | --- |
| `ps5-dashboard-card.js` | `PanelShell`, `ConsoleOverview`, `ActivityOverview` | Hero layout intent, in-place state updates | Lovelace `setConfig`, hardcoded entities, one-player assumptions |
| `ps5-live-client.js` | Shared `ApiClient` / `SubscriptionManager` | Generation/version checks and unsubscribe discipline | MQTT topic and 90s magic TTL |
| `ps5-history-client.js` | `HistoryApiClient` | Request IDs, validation, cancellation | MQTT publish and 2-second subscribe delay |
| `ps5-daily-history-client.js` | `DailyHistoryQuery` | Bounded ranges, paging, cancellation | MQTT response topic and fixed report calendar |
| `ps5-history-index-client.js` | `HistoryCoverageIndex` | Activity-aware navigation, 36-month overview | Retained MQTT payload as source of truth |
| `ps5-history-navigation.js` | Pure domain/frontend date navigation helper | Adjacent nonempty periods | Browser-local timezone assumption |
| `ps5-history-chart.js` | Accessible theme-aware `UsageChart` | Dataset validation and SVG concepts | Fixed colors/no accessible data alternative |
| `ps5-game-library.js` | `GameLibraryView` | Sorting, textContent, lazy images | Direct unapproved image URLs/one-month-only scope |
| `ps5-first-row-metrics.js` | `UsageComparisonService` / presentation | Pure comparison functions | Unclear time source/coverage |
| `ps5-formatters.js` | Shared locale/timezone formatter | Simple duration/period formatting | Hardcoded PT/English and browser timezone |
| `ps5-game-library.css` + inline CSS | Versioned module CSS/theme tokens | Some visual ideas | Static overrides incompatible with HA 2026.11 themes |

New panel features absent from original one-console UI must be added deliberately: multi-console chooser, per-account PSN scope and permissions, explicit source status, unknown gaps and attribution confidence, storage-health diagnostics, accessible admin settings and backend command confirmation.

## 7. Security and privacy considerations

**Positive evidence:** Most content text is assigned through `textContent`; no direct evidence of unsafe `innerHTML` use was found in the reviewed components. Explicit HTTPS image checks and `referrerPolicy = "no-referrer"` on library images are useful partial controls. The client uses HA's authenticated WebSocket rather than opening a separate broker socket or storing MQTT credentials.

**Remaining risks:** Provider image URLs are untrusted network destinations; string prefix checks cannot substitute for source/domain policy, license review or safe backend image fetching. Browser image privacy differs from backend SSRF (do not conflate). Mixed language literals and extensive inline CSS harm localization and theme consistency. Frontend code's use of HA state does not prove authorization for future private per-account history; backend must validate ACL in the future `playstation_hub/*` API.

## 8. Documentation corrections required

1. Replace the incorrect statement that `develop/frontend` does not exist. It exists, and all 21 frontend source/test files listed above were enumerated by the GitHub tree API.
2. Mark previous `UX-001: source unavailable` as **RESOLVED — tool-directory lookup limitation**, replaced by implementation/new-panel verification gaps.
3. Do not claim the 80 test cases pass today; only test declarations were counted, and a past README statement was read.
4. Update `ARCHITECTURE_GUIDE.md`, `docs/standards/review-history.md`, `docs/standards/compliance-matrix.md`, `docs/architecture/system-overview.md` and ADR-0010 links.
5. Retain historical notes with a correction banner for traceability.
6. Update stale legacy README only as a separate explicitly approved change to `develop`; do not mutate the historical branch as part of documentation review.

## 9. Next documentation-only investigations

- **UX-DOC-001:** Source-annotated UI design taxonomy and mobile layout improvements.
- **UX-DOC-002:** Exact old MQTT request/response schema -> proposed versioned WebSocket DTO migration table.
- **UX-DOC-003:** Timezone/DST and pagination edge-case matrix spanning the 36-month index and SQLite.
- **UX-DOC-004:** Accessibility/theme audit against pinned Home Assistant 2026.11 frontend APIs.
- **UX-DOC-005:** Security/image rights model and authenticated asset strategy.
- **UX-DOC-006:** Map all 80 legacy tests to keep/adapt/retire/rewrite and future HA integration tests.

No new frontend JS, CSS, test files, feature branch or working sidebar panel has been created.

## 10. Sources

- [GitHub develop/frontend source](https://github.com/jorgeavlobo/playstation-hub/tree/develop/frontend)
- [Frontend tree metadata](https://api.github.com/repos/jorgeavlobo/playstation-hub/git/trees/f4a8b76c5c0221fb3cd3671a4c631f5d275beb96?recursive=1)
- [Legacy README](https://github.com/jorgeavlobo/playstation-hub/blob/develop/README.md)
- [Earlier research note (corrected/superseded)](legacy-frontend-inventory-and-panel-ux-review-2026-11.md)
- [ADR-0002 accepted sidebar panel](../decisions/ADR-0002-sidebar-panel.md)
- [ADR-0010 proposed panel/WebSocket contract](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- [Official 2026.11 Home Assistant source re-audit](official-source-reaudit-home-assistant-2026-11.md)

**Conclusion:** The old frontend is genuinely present on `develop` and its source/test inventory is verified. Multiple architectural improvements can be documented without programming. All executable changes and test runs remain pending separate authorization.


## 11. Explicit Lovelace and old MQTT monitor entity cutover contract — 2026-11-06

[New legacy backend/frontend migration evidence](legacy-develop-to-native-migration-provenance-audit-2026-11.md), [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) and [SPEC-019](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md) connect the old dashboard source directly to historical data migration. The old card uses hardcoded monitor entity ID prefix sensor.ps5_monitoring_service_ps5_ and History/Live clients use mqtt/subscribe and MQTT publish over Home Assistant's WebSocket. Actual installed entity IDs, automations and user-customized cards have NOT been inspected. The backend publisher creates ten synthetic monitor MQTT Discovery sensors with unique_id ps5_monitor_<key> and a synthetic device identifier, none of which establishes physical PlayStation identity.

The native integration's one sidebar should retain conceptual navigation, historical charts, game lists and 36-month browsing; source snapshots and imported legacy sessions remain physically LEGACY_UNATTRIBUTED unless separately proven. The old 36-month index is a UI window, not a deletion policy for raw history. Retiring the Lovelace card, old MQTT retained Discovery configs and any old monitor automations is a **separate owner-approved live cutover** after verified backups and full registry/dependency mapping. The third-party PS5-MQTT activity sensor and power switch are NOT among the old monitor publisher's ten sensors and must not be removed under this migration. No frontend code/registry data/MQTT broker was modified and no test run.
