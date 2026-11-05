# ADR-0010 — Single sidebar panel, authenticated backend API and frontend delivery

**Status:** Proposed — research-backed architecture, not approved or implemented  
**Date:** 2026-11-05  
**Domain:** `playstation_hub`  
**Scope:** One multilingual Home Assistant sidebar panel, embedded frontend packaging, WebSocket read/subscription/mutation APIs, authorization, pagination, caching, lifecycle, performance, accessibility and privacy  
**Depends on:** ADR-0002 (one sidebar panel, accepted); ADR-0004 (identity, proposed); ADR-0005 (observation semantics, proposed); ADR-0006 (session ledger, proposed); ADR-0007 (credentials, proposed); ADR-0008 (storage, proposed); ADR-0009 (entities/actions, proposed)  
**Implementation:** Not started; no frontend bundle or production WebSocket endpoint exists  
**Research scope:** Documentation in `main` only. The legacy Lovelace card on `develop` is a behavioral reference, **not** frontend code to merge.

> **Evidence levels:** Home Assistant source/API documentation establishes the relevant **platform mechanisms**, not compatibility of our unimplemented panel. Names, event frames, message fields, limits and permissions below are **PlayStation Hub proposals**, not existing Home Assistant APIs. Verify against a pinned HA Core/frontend release and test on Home Assistant OS/mobile before approving.

## 1. Objective and non-negotiable requirements

Deliver exactly **one full-page sidebar panel**, as approved by ADR-0002, installed together with the Python HACS integration. It must support multiple physical PlayStation consoles and optional PSN accounts, instant rendering from **locally cached backend state**, durable statistics and historical queries, game artwork/library, direct user-initiated control, configuration-status links, localization and useful diagnostics. It must not require a Lovelace custom card, custom dashboard, separate frontend repository, MQTT broker, Node.js server at runtime, Home Assistant App/add-on or external web service.

No frontend component shall:
- Receive or store NPSSO, OAuth access/refresh tokens, Remote Play pairing keys, PINs or raw credentials.
- Call internal Sony account APIs, send console UDP/TCP packets or open/read SQLite directly.
- Treat cloud PSN state as proof of physical power or attribute a game to one console without evidence.
- Bypass backend authentication/authorization simply because the sidebar menu is visible.
- Fire provider/network queries on every render or on each widget refresh.
- Persist raw personal history to browser `localStorage` or URL query strings.
- Display cached restored data as current without source freshness labels.

Code, comments, schemas and documentation will use English. UI strings must be localized, including English and PT-PT at minimum, with extensible locale loading.

## 2. Alternatives evaluated

| Architecture | Benefit | Cost/problem | Direction |
| --- | --- | --- | --- |
| Lovelace card as sole UI | Quick integration with dashboard | Contradicts approved one-panel product scope, spreads layout/config | Rejected |
| Home Assistant App/Ingress | Strong standalone app UI | Adds container/App and separate runtime dependency | Rejected |
| Static frontend hosted by external server | Independent deployment | Requires extra service, origin/cookie/security complexity | Rejected |
| Custom sidebar Web Component + HA static asset serving + HA WebSocket | Native HA navigation/auth transport, deploys inside one HACS integration | Need registration lifecycle, frontend compatibility and ACL | **Preferred proposal** |
| Large HA entity attributes replacing backend APIs | Cheap initial read | Recorder/state size, sensitive data leakage, poor query semantics | Rejected |
| Direct Sony fetch from browser | No Python adapter | CORS, exposed tokens, privacy and provider limitations | Rejected |

## 3. Source-confirmed Home Assistant integration mechanisms

Reviewed Home Assistant Core `dev` source and official developer guidance on 2026-11-05:

1. `homeassistant/components/panel_custom/__init__.py` exposes `async_register_panel` with a `webcomponent_name`, `frontend_url_path`, `module_url`, `embed_iframe`, `require_admin` and other panel metadata. Exact signatures may change.
2. `homeassistant/components/knx/websocket.py` registers a production KNX panel using `hass.http.async_register_static_paths([StaticPathConfig(...)])`, `panel_custom.async_register_panel(...)`, a stable route and WebSocket commands. It uses `async_panel_exists` to avoid duplicate registration.
3. Home Assistant developer documentation, **Extending the WebSocket API**, prescribes validated command types/schemas, `websocket_api.async_register_command`, decorated handlers, `@websocket_api.async_response` for asynchronous work, and connection `send_result`/`send_error` patterns. Subscription commands need explicit listener cleanup on connection close.
4. Current HA frontend changes may affect panel safe-area behavior and UI component internals. Avoid relying on undocumented internal component contracts without a compatibility test.
5. Official HA **Integration service actions** guidance recommends registering actions in `async_setup`, not per config entry; a command sent from a sidebar must use the same authorization and operational policy as the equivalent HA action.

**Do not promise** that `panel_custom`, static path signatures, WebSocket subscription helpers or HA user-permission APIs are identical across all releases. The minimum supported HA Core version must be established and pinned as an implementation gate.

## 4. Proposed frontend/backend architecture

```text
Home Assistant sidebar
  -> playstation-hub-panel Web Component (versioned static JS/CSS)
      -> HA authenticated WebSocket connection
          -> playstation_hub/* command schema + authentication/authorization
              -> HubApiFacade (DTOs, filtering, pagination, generation)
                  -> ConsoleRegistry / account-scoped runtime
                  -> ReconciledSourceState (ADR-0005)
                  -> SessionReportService (ADR-0006)
                  -> Catalog / ArtworkService (P10)
                  -> CommandCoordinator / HA service actions (P03-P07)
                  -> CredentialService: status only, NO secrets (ADR-0007)
                  -> HistoryRepository (ADR-0008)
      <- Snapshot and bounded event subscriptions, sanitized DTOs
```

**Architecture rule:** Pure domain models are independent of HA and browser. The API facade owns authorization, version translation, filtering and response-size caps; transport adapters/SQLite never directly construct frontend state. All provider I/O is backend-controlled and cached or scheduled. One integration-scope runtime owns the panel and WebSocket command registration, not the first console config entry.

### 4.1 Frontend module decomposition (design, not files to create)

- `PanelShell` — sidebar page root, navigation, locale/theme and connection status.
- `ApiClient` — thin wrapper on HA authenticated WebSocket, version handshake, request IDs and typed errors.
- `SubscriptionManager` — connection lifecycle, one shared state stream per panel, sequence checking and reconnect/resync.
- `ConsoleOverview` — devices, current fresh/stale mode, source health and bounded usage.
- `ConsoleDetail` — selected console, paired capabilities, commands and recent history.
- `PsnAccountOverview` — authorized account status and provider-reported games with provenance.
- `GameLibrary` — titles, scopes, cover references, filter/pagination and stale metadata.
- `StatisticsView` — day/week/month/year/rolling windows, coverage and comparison.
- `TimelineView` — bounded timeline of observed/unknown/inferred segments.
- `SettingsStatusView` — links or supported UI flows for configuring consoles, PSN account authorization, diagnostics and retention.
- `Localization`, `ThemeAdapter`, `ErrorPresenter` and shared reusable components.

Frontend framework choice (plain Web Components vs selected build system) is open. No runtime Node.js requirement means bundling assets at build/release time, not prohibiting developer build tools.

## 5. Panel registration, asset serving and lifecycle

### 5.1 Registration proposal

During integration-scope setup, establish a stable route like `/playstation-hub` with `frontend_url_path` and a uniquely named Web Component `playstation-hub-panel`; register the static asset directory via the supported HA HTTP static-path API. Register once only and do not register identical panels per console entry. The supported Home Assistant route/panel names must be checked for collision and any reserved paths.

**Security default proposed:** Register the panel as **administrator-only** initially, until backend historical/read and command ACL has been explicitly designed and tested for non-admin HA users. This restricts visibility but **does not replace API-level permission checks**. More granular read-only access may be a future product feature.

Asset paths should be immutable/versioned (e.g. distribution build hash) and remain served from the installed HACS package, with consistent `manifest.json`/frontend release version. Avoid timestamps/random URL cache busters that change every reload; prefer deterministic content hashes or release versions. Ensure stale chunks from a previous version cannot render against an incompatible backend. Fail safely if frontend and backend protocol versions cannot negotiate.

### 5.2 Static file and cache rules

- Do not serve arbitrary paths or directories beyond explicitly bundled frontend assets.
- Never place mutable DBs, `.storage` secrets, source maps with sensitive values, build credentials or user exports under public static paths.
- Restrict static responses to intended MIME types, immutable hash-chunk caching and no-store for any dynamic private JSON.
- Strictly control image references as per Protocol 10; remote image caching/rights and authenticated image proxy remain open.
- No public `/api/playstation_hub/export` route unless a separately authorized, expiring download and anti-leak design is approved.
- A HACS update must not silently leave two active panel registrations or duplicate WebSocket command handlers.
- On teardown/uninstall: remove listeners/panel safely using supported HA APIs. Exact static-path unregistration behavior must be investigated; do not promise a nonexistent `unregister_static_paths` call.
- A dashboard browser refresh must create no extra Remote Play/PSN polling workers.

## 6. WebSocket API contract and version negotiation

**All message types below are proposed**, namespaced under `playstation_hub/`, not built into Home Assistant.

### 6.1 API information and snapshots

| Proposed type | Arguments | Response / semantics |
| --- | --- | --- |
| `playstation_hub/get_capabilities` | None or client protocol version | Schema versions, supported features, enabled modules, limits, minimum client version |
| `playstation_hub/list_consoles` | Filters, page/cursor | Stable console IDs, names, model, bounded source status, capabilities |
| `playstation_hub/get_console` | Canonical console ID | One sanitized current/last-known state and command capability summary |
| `playstation_hub/list_accounts` | Page/cursor | PSN account display and auth state (no tokens) |
| `playstation_hub/get_account` | Account ID | PSN presence, last-known title, freshness, privacy flags |
| `playstation_hub/get_usage_summary` | Scope, IANA timezone, half-open period | Bounded coverage and account/game statistics per ADR-0006 |
| `playstation_hub/get_sessions` | Console/account/title, period, cursor, size | Paged durable segments with evidence/uncertainty |
| `playstation_hub/get_games` | Scope, query/filter, cursor, size, locale | Paged title/catalog metadata with rights and staleness |
| `playstation_hub/get_diagnostics` | Config entry/target, admin required | Sanitized per-source and storage health |

### 6.2 Subscriptions

- `playstation_hub/subscribe_state` — sends a bounded initial snapshot plus incremental delta events for requested authorized console/account scopes.
- `playstation_hub/subscribe_operation` — progress of a specific command whose authorization is verified.
- `playstation_hub/unsubscribe` or the Home Assistant standard subscription unsubscribe semantics — design based on official supported HA WS APIs.

**Lifecycle:** On client disconnect/cancel, server unregisters that connection's listeners. A subscription does not spawn a separate LAN/PSN fetch loop. A frontend navigation transition should not leak subscriptions.

### 6.3 Mutating commands

Prefer registered HA services for `wake`, `standby`, `refresh_status` etc. The sidebar may invoke a capability-checked service via HA's authenticated service machinery; if a custom WS mutation command is needed for progress or application-specific behavior, its handler delegates to the same CommandCoordinator and server-side ACL. **No duplicated command implementation**.

Administrative commands such as pairing initiation, PSN linking/reauth, history deletion, ownership changes or exports must use supported HA config-flow/service APIs with explicit admin authorization, confirmation, validation, and audit. **Do not put NPSSO or pairing keys into a generic WebSocket update message.**

## 7. Proposed envelope for all responses

```json
{
  "schema_version": 1,
  "snapshot_revision": 42,
  "generated_at_utc": "2026-11-05T12:00:00Z",
  "source_state": {
    "freshness": "fresh",
    "last_observed_at_utc": "2026-11-05T11:59:59Z"
  },
  "data": {},
  "next_cursor": null
}
```

Synthetic payload for schema illustration only.

**Common contract:** All API results have a schema version, source/source-timestamp where relevant, explicit durability/uncertainty and bounded JSON shape. Never include provider tokens, raw private packet bodies or unrestricted nested objects. Null/unknown is **not** 0/off. IDs use canonical namespaces from ADR-0004; only authorized targets are returned.

**Version behavior:** Backend owns supported major/minor schema versions; optional fields must be backward-compatible inside the approved range. A client with unsupported major version shows a localized refresh/update requirement instead of misinterpreting statuses. Avoid global API version increments for mere artwork changes unless contract incompatible.

## 8. Incremental updates, ordering and reconnect

**Proposed snapshot-and-delta flow:**

1. Frontend connects through the existing authenticated Home Assistant WebSocket.
2. Frontend requests capabilities and full authorized snapshot, recording a server boot ID and monotonically increasing revision.
3. Frontend establishes a subscription; the backend either atomically attaches subscription with snapshot or provides a cursor/revision replay contract to avoid a lost update between initial list and subscribe.
4. Each delta carries `boot_id`, `revision`, target ID, changed fields, scope/source and timestamp. Never allow a stale source delta to overwrite a newer accepted ADR-0005 observation.
5. A duplicate/old revision is ignored. A revision gap, boot ID change or incompatible schema triggers a full resynchronization.
6. If WebSocket disconnects, mark connection offline without pretending hardware is OFF; reconnect with bounded exponential backoff and resubscribe.
7. Pending mutating operations must not be automatically resent after reconnect: their outcome may be unknown; fetch operation status / allow user retry explicitly.
8. Keep bounded server-side event buffering or deliberately require resync; never store indefinite per-browser event queues.

### Snapshot race example

Bad: request snapshot at revision 10; event revision 11 happens; client subscribes too late and never sees it. Correct: subscribe-with-snapshot atomic mechanism **or** revision-based subscribe/replay with resync on gaps. This is an implementation acceptance test, not yet a finalized API.

### Rate and rendering policy

Coalesce bursty observations into a minimal UI update cadence without dropping meaningful state changes; domain ledger persists according to its own transaction policy. Browser tabs and widgets must consume cached shared subscriptions and not multiply provider polling. Pause expensive charts/animations when panel is not visible, without changing backend monitoring.

## 9. Pagination, filtering and performance

All list/history endpoints require:
- Server-enforced max page size, default page size and total query time budget, **not merely client-controlled** `limit`.
- Bounded half-open `[start_utc,end_utc)` periods and a justified maximum time span for each endpoint, plus role-based authorization.
- Stable deterministic sort, opaque next cursor including sort position/snapshot revision and validated filters (or equivalent robust pagination scheme).
- Protection from unbounded scans, huge JSON, expensive group-by or user-chosen wildcards.
- Cancelable async/executor read jobs so one browser's request cannot monopolize SQLite or block HA.
- Separate caching rules for summaries, game catalog, artwork and durable session lists.
- Explicit reported `data_as_of_utc`, `completeness` and `persistence_health`, not optimistic “realtime” claims.

**Initial suggested limits for design review (not adopted):** 100 session records/page, 100 games/page, 366 local calendar days for one daily chart request and bounded concurrency per connection. Set limits after performance tests.

## 10. Security, authorization and privacy model

### 10.1 Authentication is not authorization

Home Assistant's websocket connection is authenticated, but custom endpoints **must** check the current HA user's authorization for each target and operation. A sidebar with `require_admin=True` is an initial defense, not a reason to omit command-specific checks.

**Proposed initial scope:** All custom historical/private endpoints and pairing/account mutations are administrator-only until a precise HA ACL model and comprehensive non-admin tests are approved. HA native read-only entity state has its own permission semantics; don't infer that those permissions authorize private per-player history.

- Verify ownership/visibility for every console/account identifier requested; never trust a frontend-supplied `config_entry_id` or `device_id` without resolving it server-side.
- Exports, deletion, secret changes and external messaging require explicit permission and user confirmation.
- Do not return the full private history by default on panel load.
- Sanitize translated exceptions and avoid reflecting account/player text into HTML without escaping.
- Limit request rate and query size; avoid a crafted request exhausting CPU, memory or disk.
- Image proxy, if implemented, must verify host/IP/redirect/MIME/size and must not forward Sony bearer headers to arbitrary hosts.
- Keep every frontend asset public only when it contains **no user data**; dynamic account/history data is served over authorized HA APIs.

### 10.2 Client-side storage and privacy

Prefer in-memory UI state only. Avoid `localStorage` for personal history, PSN identifiers or secrets; if harmless theme/layout preferences are cached, document exactly what is stored. Never use NPSSO in URL fragments/query parameters, browser console logs, DOM data attributes or analytics. On logout/reauth, invalidate local account data and unsubscribe. Security policy must account for public/shared household tablets and browsers.

## 11. UX and information architecture

### 11.1 One-panel navigation

Proposed sections within **one sidebar route**:
1. **Overview:** all consoles, physical source freshness and current command status.
2. **Console detail:** power, last observed, pairing, controls, activity, timeline.
3. **Statistics:** daily, weekly, monthly, annual, 12-/36-month windows, unknown coverage and per-console/account scope.
4. **Game library:** PSN-reported current/recent/played, digital entitlement and local observed history clearly separated.
5. **Accounts:** optional PSN linking status, presence, privacy/reauth status, associations.
6. **Settings & diagnostics:** entry links, connection health, safe storage state, export/retention action entry points.

**No parallel Lovelace card**. Internal tabs/routes inside the single panel are allowed and should preserve browser back/forward navigation only with non-sensitive route parameters.

### 11.2 Semantic status examples

| Fact | Suitable label | Avoid |
| --- | --- | --- |
| Valid LAN AWAKE | “Console awake” | “Player is playing” |
| Valid LAN STANDBY | “Rest mode” | “Completely powered off” |
| LAN unavailable | “Console status unavailable — last confirmed awake at …” | “OFF” |
| PSN current game | “PSN reports playing [title]” | “PS5 in the living room is running [title]” without attribution |
| Ambiguous account/device | “Device attribution uncertain” | Automatic exact player timer |
| Standby sent, no confirmation | “Command sent; final state not confirmed” | “Standby successful” |
| DB unsaved | “Current status available; history could not be saved” | Normal-looking persisted chart |
| Provider library game | “In PSN digital library” | “Permanently owned / installed” |

### 11.3 Accessibility and responsive design

Keyboard navigation, visible focus, correct roles/labels and screen-reader descriptions for controls and charts, sufficiently large touch targets, theme responsiveness, contrast, reduced-motion preference, loading/error/empty states, mobile portrait/tablet/desktop layouts, safe-area insets. Home Assistant's 2026.8 frontend changed custom-panel safe-area handling; inspect the installed version and avoid duplicate padding. Avoid reliance on undocumented Lit/HA internal classes; favor stable Web Component interfaces. A nonvisual accessible history table should accompany graphs.

## 12. Localization and date/time behavior

- English is source code/text translation key language; include PT-PT and extensible dictionaries for frontend.
- Home Assistant's current `hass.language`/locale/timezone capabilities must be verified for the chosen frontend version. Apply tested fallback to English.
- All backend instants are UTC, frontend renders in the configured HA/user-selected IANA timezone; calendar report requests send an explicit timezone and unambiguous date range.
- Day/month/year and ISO week boundaries must be consistent with ADR-0006, including DST and partial periods.
- Numeric formatting, decimal separators, relative timestamps, units and accessibility strings use locale-aware APIs.
- Avoid user-facing strings embedded in domain logic or server error messages; map stable error codes to localized UI text and HA translation keys.
- Game titles from providers remain content data, not translated identifiers.

## 13. Frontend bundle/versioning, build and HACS distribution

- The released HACS integration includes built JS/CSS/static assets alongside Python code in the same GitHub release/tag.
- Source may be modular TypeScript/JavaScript; Node.js tooling is allowed during development/CI but **not required at Home Assistant runtime**.
- A shared semantic release version and API compatibility metadata are generated reproducibly; no manual random cache busters.
- Static asset packaging must preserve correct relative URL paths for code-split chunks and images.
- Evaluate CSP compatibility (no inline `eval` or untrusted HTML), use sanitization and dependency/license audits.
- Do not ship source maps with secrets, private paths or sensitive build configuration; sourcemaps may be generated for controlled CI debugging if separately approved.
- HACS integration distribution has different requirements from HACS frontend resource packages; verify packaging of bundled JS and manifest behavior on clean install/upgrade.
- CI release checks: Python tests/type checks/lint, frontend unit and E2E browser tests, translation validation, Hassfest, HACS validation, locked dependency scan, reproducible build artifact inventory.
- Test a clean HA OS installation and one upgrade/rollback, including cache mismatches, old browser tabs and API schema change.

## 14. Backend integration lifecycle

Integration-level initialization owns:
- WebSocket command registration once.
- Shared authorized query facade and subscriptions.
- Registration of static assets/panel once.
- Shared read-only access to initialized repository/services, without owning individual console tasks.

Entry lifecycle:
- Adding console entry updates panel's authorized inventory, not the panel registration itself.
- Removing console closes only its transport and entity runtime; the global panel remains when other relevant entries exist.
- Unlinking PSN account removes that account's private frontend data and emits a safe removal event.
- HA restart first makes historical last-known data available, then overlays fresh observations; never claim stale stored state is live.
- During unload, cancel connection-bound listeners and ongoing reads; reject late callbacks using generation/run ID.
- If all entries are removed, choose panel visibility/registration policy explicitly (leave a useful setup screen vs unregister panel). No source currently establishes one correct answer for custom integration lifecycle.
- Registering WebSocket command handlers may be non-reversible under some HA APIs; do not assume arbitrary unregister exists. Handle integration not-loaded safely and avoid duplicate registration rather than relying on cleanup functions that are not supported.

## 15. Error contract, diagnostics and observability

Proposed sanitized error envelope:

```json
{
  "schema_version": 1,
  "code": "history_unavailable",
  "category": "persistence",
  "retryable": true,
  "correlation_id": "synthetic-request-001",
  "user_action": "retry",
  "details": null
}
```

The backend owns source and retryability. It should not serialize exception tracebacks, OAuth/Remote Play credentials, raw HTML, arbitrary server error bodies or personal account IDs. The frontend renders localized user remedies and keeps a bounded, private diagnostic view. Network health, database health, auth status, last refresh, queue depth and protocol capability status can be provided when authorized.

An API failure must not blank the entire panel when independent LAN or cached historical functionality is available. Use per-section error states. Distinguish auth required, source unavailable, privacy restricted, rate limited, schema unsupported, identity mismatch, command unconfirmed, storage failure and permission denied.

## 16. Test matrix

### Panel registration and lifecycle
- [ ] On supported HA Core, static asset and sidebar route register once per integration.
- [ ] Multiple console entries never duplicate routes, static paths or WebSocket commands.
- [ ] Browser reload creates no extra backend LAN/PSN polling workers.
- [ ] HACS install/upgrade/rollback handles bundle version, hashed assets and missing/cached chunks.
- [ ] Panel unload/entry unload removes connection listeners and stale callbacks safely.
- [ ] Verify exact supported iframe/non-iframe rendering and safe-area behavior, including 2026.8+.

### WebSocket API and security
- [ ] Every handler has validated schema and bounded payload.
- [ ] Admin and non-admin users receive only their authorized data; unauthorized mutation fails without network effect.
- [ ] Arbitrary console/account IDs, oversized periods and pagination tokens are rejected.
- [ ] Unknown schema major version yields explicit compatibility error.
- [ ] No tokens, session keys, raw provider bodies or secrets in WebSocket, static JS, logs or diagnostics.
- [ ] Proper cancellation, response delivery and error categories for long-running history queries.
- [ ] Two concurrent browsers receive consistent snapshots with no extra provider polls.
- [ ] Snapshot-to-subscribe race cannot lose a transition.
- [ ] Reconnect/replay/delta revision gap triggers resync, not stale overwrite.
- [ ] Pending control commands are not automatically resent after socket reconnect.
- [ ] XSS tests against malicious game titles/online names and artwork URLs pass.

### History and statistics
- [ ] Half-open time-range pagination and local timezone/DST match ADR-0006.
- [ ] Large 36-month history yields bounded query and response.
- [ ] Missing/unknown intervals remain distinct from actual off/inactivity.
- [ ] PSN provider lifetime duration is never summed into local observed time.
- [ ] One account on two PS5s produces ambiguous attribution, not duplicated game time.
- [ ] DB migration/read failure shows localized partial error without blocking live LAN panel.
- [ ] Export/privacy retention operations require explicit confirmation and admin permission.

### UI accessibility and localization
- [ ] English and PT-PT complete, tested fallbacks; no untranslated backend error keys.
- [ ] Keyboard-only navigation, screen readers, focus after route changes and reduced motion.
- [ ] Home Assistant light/dark theme, narrow phone, tablet and widescreen layouts.
- [ ] Safe-area/notch behavior, Android/iOS companion webview and touch targets.
- [ ] Console unknown/standby/off and account online/offline remain semantically distinct.
- [ ] Stale history and provider data visibly labeled with timestamp and source.

## 17. Open questions / approval gates

- [ ] Pin minimum supported HA Core/frontend version and supported Python runtime.
- [ ] Approve Web Component vs iframe approach, static registration, route and safe-area handling.
- [ ] Approve initial admin-only private panel; define later fine-grained per-user ACL if desired.
- [ ] Approve API command taxonomy, version strategy, page limits and subscription semantics.
- [ ] Determine whether HA service actions or custom WS commands are best for each mutation.
- [ ] Finalize integration-wide panel registration and end-of-life behavior with zero config entries.
- [ ] Decide frontend framework/build tool and lockfile policy, without runtime Node.js.
- [ ] Approve exact database/credential storage and backup APIs (ADR-0007/0008).
- [ ] Decide game artwork proxy/caching/licensing and safe image URL design.
- [ ] Approve data retention, browser privacy and any optional export feature.
- [ ] Validate Home Assistant permissions, panel visibility and custom WebSocket endpoints in tests.
- [ ] Resolve optional PSN Sony client/API authorization blocker before enabling provider features.
- [ ] Verify with real HA OS, desktop/mobile browsers and live PS5 as implementation proceeds.
- [ ] Maintain ADR-0002 decision of one panel/no Lovelace card.

**Preferred proposal:** One HA custom sidebar panel, static bundled frontend assets, a versioned authenticated WebSocket facade for bounded reads/subscriptions, HA service actions or explicitly authorized WS mutations for controls, and strong source/ACL/privacy boundaries. This ADR remains **Proposed** until approved and tested.

## 18. Sources

### Home Assistant Core implementation inspected
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/panel_custom/__init__.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/knx/websocket.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/http/__init__.py

### Official Home Assistant developer documentation
- https://developers.home-assistant.io/docs/frontend/extending/websocket-api
- https://developers.home-assistant.io/docs/dev_101_services/
- https://developers.home-assistant.io/blog/2026/07/31/frontend-component-updates-2026.8/
- https://developers.home-assistant.io/docs/core/entity/
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/core/diagnostics/
- https://developers.home-assistant.io/docs/internationalization/core/
- https://www.hacs.xyz/docs/publish/integration/

### Internal project documents
- [ADR-0002 — One sidebar panel](ADR-0002-sidebar-panel.md)
- [ADR-0004 — Identity and multi-console](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 — Observation and state reconciliation](ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 — Sessions and statistics](ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007 — Credentials](ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008 — Storage](ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009 — HA entities/actions](ADR-0009-home-assistant-integration-entities-actions.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)
- [Legacy frontend](https://github.com/jorgeavlobo/playstation-hub/tree/develop/frontend)

**Outcome:** Sidebar delivery, WebSocket boundary, authorization, state subscriptions, query contracts, i18n, responsive UX and test gates are documented in depth. No executable code was produced; compatibility and security must be demonstrated in later implementation.

## 19. Home Assistant 2026.11 frontend/Marketplace overlay (2026-11-05)

The [official-source re-audit](../research/official-source-reaudit-home-assistant-2026-11.md) confirms that Home Assistant 2026.11 embeds HACS as the **Marketplace**. The project remains one custom integration package with bundled frontend assets, local `brand/icon.png` and full custom `translations/en.json` plus PT-PT localization. The single custom sidebar panel decision remains unchanged.

The 2026.11 frontend removed `ha-md-list`, `ha-md-list-item` and `ha-formfield`. Use supported list/input elements and current `--ha-*` CSS tokens instead of old Material CSS names. The frontend paints backgrounds behind all panels; avoid forcing a custom-panel host `background-color: var(--primary-background-color)` and honor `--ha-panel-background`, `--ha-panel-toolbar-background` and `--ha-data-table-background`. Verify safe areas, mobile WebViews, user authentication and authorization against the pinned Core/frontend build. No JavaScript bundle or running panel was created.

## 20. Legacy frontend source audit and reuse boundary (2026-11-05)

The [verified `develop` frontend audit](../research/legacy-frontend-source-audit-2026-11.md) corrects the original incomplete investigation: the actual branch contains 21 frontend files, including a v1.1.2 Lovelace card, live/history/index/daily MQTT-over-HA-WebSocket clients, SVG chart, game library, styles and ten test files comprising 80 test declarations. The tests were counted, not executed. Good patterns to preserve conceptually are authenticated HA WebSocket use, request ID correlation and cancellation, source event generation fencing, month navigation, safe `textContent`, lazy images and incremental updates.

The new single sidebar Web Component must **not** reuse legacy hardcoded `sensor.ps5_monitoring_service_ps5_*` entity IDs, MQTT topics or publish requests, single-console account assumptions, browser-local date boundaries, legacy 90-second frontend freshness magic values or misleading “Consola desligada” based solely on `!console_active`. Replace them with canonical physical-console IDs, source-aware state, per-user timezone, backend-owned freshness, versioned `playstation_hub/*` WebSocket API, bounded queries, accessible theme-aware components and separated PSN account facts. Exact migration maps remain design proposals and are not implemented.
