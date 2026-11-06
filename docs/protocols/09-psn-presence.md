# Protocol 09 — PlayStation Network presence and activity attribution

**Status:** Detailed source-derived research specification; not validated by PlayStation Hub on a real account or console  
**Reviewed:** 2026-11-05  
**Implementation:** Not started  
**Primary proposed module:** `custom_components/playstation_hub/transport/psn/presence.py`  
**Related domain module:** `custom_components/playstation_hub/domain/presence_reconciler.py` (proposed, not implemented)  
**Reference trees from protocol index:** `psn-api` `1e9d9a806fcd884a4ddee8086bfe92594611da9f`; `PS5-MQTT` `7ab3075d276f3eeecd81a3322c72231af8cd51bd`. Current default-branch files were also inspected on the review date; pins do not imply those files match current heads.

> **Evidence boundary:** `SOURCE-CONFIRMED` means behavior visible in identified upstream source; `OFFICIAL` refers to Home Assistant or Sony's published documentation about their own services and privacy; `DESIGN DIRECTION` is a PlayStation Hub proposal; `UNVERIFIED` requires testing and possibly Sony authorization. The reverse-engineered PSN interface is not a publicly guaranteed or licensed Sony third-party API. Protocol 08's client/endpoint authorization blocker still applies.

## 1. Objective and boundaries

Obtain fresh PSN account presence and optionally current game details without relying on PS5-MQTT, an MQTT broker or the built-in Home Assistant `playstation_network` integration. The adapter must serve account-specific observations to the PlayStation Hub domain; it must not directly create Home Assistant entities, operate physical console power, infer a local console's identity, or write game sessions without a separate reconciliation decision.

Presence answers questions about a **PSN account**. LAN discovery/status (Protocols 01–02) answer questions about a **physical console**. Remote Play (Protocols 04–07) handles authenticated console control. Game metadata (Protocol 10) enriches titles. These are deliberately distinct.

**Design invariants:**

1. `PSN online` **does not imply** that a particular local PS5 is awake.
2. `PSN offline` **does not imply** that the physical console is off; the user may be hidden, disconnected from PSN, using another account, or the source may be stale.
3. A PSN platform value (`PS5`, `ps4`, `PSPC`, etc.) is not a stable physical device identifier.
4. `gameTitleInfoList` describes game context visible to the requester, not guaranteed controller ownership, exclusive activity, physical console identity or exact session duration.
5. A missing game does **not** prove zero play time.
6. Account privacy and permissions are authoritative restrictions: do not attempt to bypass them.
7. A failed PSN request never rewrites a fresh, independently confirmed LAN power observation.
8. Timestamp returned from Sony and local retrieval time are different facts; record both when present.

## 2. Source and evidence inventory

| ID | Source | Classification | Finding |
| --- | --- | --- | --- |
| PRES-01 | `psn-api/src/user/getBasicPresence.ts` | SOURCE-CONFIRMED | Authenticated per-account `basicPresences?type=primary` GET, error-object rejection. |
| PRES-02 | `psn-api/src/user/getBasicPresence.test.ts` | SOURCE-CONFIRMED | Synthetic `basicPresence` with `primaryPlatformInfo` and `gameTitleInfoList`, plus error-response tests. |
| PRES-03 | `psn-api/website/docs/api-docs/users.md` | COMMUNITY-DOCUMENTED | Basic presence fields and privacy restrictions. |
| PRES-04 | `PSNAWP/src/psnawp_api/models/user.py` | SOURCE-CONFIRMED | `User.get_presence()` reads primary presence, requests platforms and own game title information, with forbidden-error semantics. |
| PRES-05 | `PSNAWP/src/psnawp_api/models/client.py` | SOURCE-CONFIRMED | `Client.get_presences(account_ids)` supports a batch query with `accountIds` and platform filters. |
| PRES-06 | `PS5-MQTT/ps5-mqtt/server/src/psn-account.ts` | SOURCE-CONFIRMED | Uses account-specific basic presence and first `gameTitleInfoList` entry to derive current activity; returns undefined on failure/no game. |
| PRES-07 | HA Core `playstation_network/helpers.py` and `coordinator.py` | SOURCE-CONFIRMED | Profile/presence aggregation, account/platform session models and 30-second main polling. |
| PRES-08 | HA Core `playstation_network/sensor.py`, `media_player.py`, `image.py` | SOURCE-CONFIRMED | Entity-level status, current title, cover art and presence-based platform media players. |
| PRES-09 | Home Assistant PlayStation Network documentation | OFFICIAL (HA) | 300 requests / 15 minutes is an integration-documented PSN limit; data refresh 30 seconds; last-used device limitation. |
| PRES-10 | Sony PlayStation account privacy documentation | OFFICIAL (SONY) | Users control visibility of online status, current game, gaming history and other profile details. |
| PRES-11 | Home Assistant data update coordinator guidance | OFFICIAL (HA) | Poll once per source, propagate data to entities, mark stale/unavailable instead of inventing freshness. |

See the complete source register in section 17. Community type declarations and fixtures are **not** a commitment by Sony that all fields always exist.

## 3. Observed transport and request semantics

### 3.1 Single account

The community `psn-api` implementation builds:

```text
GET https://m.np.playstation.com/api/userProfile/v1/internal/users/{accountId}/basicPresences?type=primary
Authorization: Bearer {access_token}
```

The request is made by the authenticated backend on behalf of an explicitly authorized account. The `internal` URL component and use of mobile-app OAuth context are further reasons to treat this endpoint as **community-observed, not public Sony API documentation**. Exact account identifier and token formatting must be validated; do not expose the bearer token in source, logs, URL query parameters or frontend.

The `psn-api` adapter calls its authenticated `call` wrapper and rejects responses containing a top-level `error` object, including an HTTP 200 carrying an API error. The upstream unit tests verify both a structured error message and a missing-message fallback. Error status alone is insufficient: validate body shape and content.

### 3.2 PSNAWP single and batch

The reviewed `User.get_presence()` requests `type=primary`, platform filter `PS4,PS5,MOBILE_APP,PSPC`, and `withOwnGameTitleInfo=true`. The method documents `PSNAWPForbiddenError` when privacy prevents observing the requested account. The `Client.get_presences(account_ids)` requests `accountIds` as a comma-joined list with corresponding filters. The exact response schema and maximum supported batch size **require tests**; do not assume batching gives one result per requested account or bypasses visibility rules.

The standalone `psn-api` request and PSNAWP query are not identical: `psn-api` uses `type=primary` without the additional filters in the inspected file. Protocol adapter implementations must identify which query variant they implement and test its expected response. Do not silently combine parameters from different library versions.

### 3.3 PS5-MQTT behavior

PS5-MQTT retrieves an account's basic presence with a bearer token, examines `basicPresence.gameTitleInfoList`, takes the **first** game record, normalizes the recorded platform/launchPlatform, and returns an optional title ID, name and image. When the response indicates an error or the game list is empty, the adapter returns no activity.

**Improvement needed:** An empty list should produce `game_unknown_or_not_visible` / `no_reported_game`, not automatically `console_off` or `gaming_seconds=0`. Discarding other records can be misleading; preserve the full normalized list or explicitly record the first-record selection policy and uncertainty.

## 4. Observed response schema

The documented `basicPresence` object may contain:

| Field | Example or type | Semantics and precautions |
| --- | --- | --- |
| `availability` | `availableToPlay`, `unavailable` | PSN account availability; not physical console power. |
| `lastAvailableDate` | ISO date/time string | Provider-reported availability history; not a session start. |
| `onlineStatus` | `online`, `offline` | Account-level online status; optional, privacy-dependent. |
| `lastOnlineDate` | ISO date/time string | Last provider-seen online time; not a current-sample timestamp. |
| `platform` | `PS5`, `ps4` in documented examples | Current account platform when reported; not a hardware ID. |
| `primaryPlatformInfo` | Object | Reported primary platform, onlineStatus and lastOnlineDate. |
| `gameTitleInfoList` | Array | Potentially zero/multiple visible game titles. |
| `npTitleId` | String | Provider game title identifier; retain as an opaque string. |
| `titleName` | String | Display string; may vary by localization and edition. |
| `format` | `PS5` / `ps4` | Game-format platform. |
| `launchPlatform` | `PS5` / `ps4` | Platform used to launch title; distinct from game format. |
| `npTitleIconUrl` | Optional URL | Remote title artwork; validate/cache separately. |
| `conceptIconUrl` | Optional URL | Alternative artwork identifier. |

Fields are optional or may be absent, null, malformed, differently cased or expanded in future responses. The parser must not crash on missing nested keys or future enum values. Preserve unknown raw values as sanitized diagnostics metadata if necessary, not unbounded arbitrary JSON.

### Synthetic normalized example (NOT a real account response)

```json
{
  "basicPresence": {
    "availability": "availableToPlay",
    "onlineStatus": "online",
    "primaryPlatformInfo": {
      "onlineStatus": "online",
      "platform": "PS5"
    },
    "gameTitleInfoList": [
      {
        "npTitleId": "SYNTHETIC_GAME_ID",
        "titleName": "Example Game",
        "format": "PS5",
        "launchPlatform": "PS5",
        "conceptIconUrl": "https://example.invalid/cover.png"
      }
    ]
  }
}
```

This fixture expresses **one possible shape** and must not be mistaken for a guaranteed Sony response. Real user fixtures, account IDs and tokens must never enter the repository.

## 5. Separate account online status, availability, game and physical power

Four independent dimensions should be represented:

1. **Account online status:** online, offline, away, mobile-app-only, unknown, or future provider value.
2. **Account availability:** available to play, unavailable, unknown.
3. **Reported game activity:** game entries, no reported game, unavailable/private/unknown.
4. **Console hardware status:** awake, standby, off, unavailable/unknown, from LAN/Remote Play evidence only.

The official Home Assistant PlayStation Network documentation exposes user-facing statuses including **Online**, **Offline**, **Away**, **Online on PS App**. Do not assume the `onlineStatus` wire field alone maps to all these human-readable categories; inspect the Core sensor value function and its locale translations during implementation. Preserve provider raw state separate from normalized UI state.

**Crucial cross-source rule:** PSN reporting `offline` is never sufficient to close a local physical-console session; LAN status remains independently evaluated.

## 6. Stable identity and attribution limits

### Account identity

Use PSN provider-resolved `account_id` as the stable account key; `online_id` is presentation metadata and can change. Account identity is per-user and can be linked to multiple consoles. Reauthentication with another account ID must not silently reassign historical data.

### Console identity

Physical console records must be keyed by independently validated LAN/registration identity (see Protocols 01–04), **not** by PSN account ID, `PS5` platform, hostname, or DHCP IP. An account/platform pair cannot distinguish two PS5 units.

### Play attribution

Assign a game session to a specific person/physical console only when independently supported by sufficiently fresh, compatible evidence. A PSN game title plus one known PS5 may support an **inferred** relation, but not a `confirmed` physical device/user assignment without a trusted signal.

For local home-monitoring statistics, maintain independent metrics:

- **Console-use time:** locally confirmed hardware awake/active interval.
- **PSN-account reported activity:** provider-sampled online and title observation, with privacy uncertainty.
- **Attributed player gaming time:** time for a named player only if attribution policy is satisfied; do not count ambiguous time into a specific player's total.
- **Unattributed/uncertain activity:** keep separately if user wants visibility; never silently fabricate exact time.

## 7. Provider freshness and timeline accounting

Provider presence is typically polled and represents a point-in-time **observation**. It is not a start/stop event feed. If a user starts a game after polling at T0 but before T1, exact start is unknown. If the next observation at T2 disappears, exact end is unknown. Do not infer game duration as precisely T2–T1 without an explicit documented estimation policy.

### Observation envelope (proposed)

```text
PsnPresenceObservation
  account_id: stable provider id
  requested_at_utc: UTC instant
  received_at_utc: UTC instant
  provider_last_online_at_utc: optional UTC instant
  source: psn_basic_presence
  fetch_generation: monotonic integer
  validity: fresh | stale | unavailable
  online_state: normalized + original provider value
  availability: normalized + original provider value
  platform: optional normalized + provider raw
  titles: immutable tuple of observed game candidates
  privacy_visibility: visible | restricted | unknown
  correlation_id: sanitized local request correlation value
```

- Use received-at for local freshness calculation; `lastOnlineDate` describes a different provider event.
- Use monotonic elapsed time for in-process TTL; persist canonical UTC timestamps for history.
- Do not accept stale late responses over a newer account generation.
- The exact TTL must be set from observed polling and reliability tests, not chosen as a Sony specification.
- If source updates fail, mark PSN availability false/unknown after TTL, but preserve the last-known title separately as historical display, explicitly labeled stale.
- A game title switch across polls is observed within an interval, not at an exact provider-confirmed transition instant.
- Do not backfill offline periods as known game play or mark an hour of unknown state as measured session duration.

## 8. State reconciliation policy (proposed)

Inputs: latest LAN console state(s); any Remote Play pairing/command-confirmation observations; latest PSN presence for one or more associated accounts; explicit account-to-console relationships; timestamps and source health.

| LAN evidence | PSN evidence | Safe interpretation |
| --- | --- | --- |
| Console awake, fresh | PSN reports account online and game | Console awake **confirmed**; game/account relation **candidate/inferred** unless other evidence binds them. |
| Console awake, fresh | PSN offline | Console awake confirmed; PSN account not currently reported online; no forced power-off or session close. |
| Console standby, fresh | PSN online | Preserve standby observation; account may be online elsewhere or reports may differ in time. |
| Console unavailable | PSN online with game | Account activity reported; **unknown local power**; do not claim this specific device is gaming. |
| Multiple PS5 awake | One account online, one game | Ambiguous physical-device attribution; no confident per-device session attribution. |
| LAN awake and PSN API 403 | PSN privacy restriction | LAN state unaffected; redact unavailable account details. |
| LAN awake and PSN API 429/timeout | PSN service unavailable | Preserve LAN state and history; no optimistic PSN activity. |
| LAN unavailable and no PSN data | No signals | Unknown; do not report OFF by default. |

### Confidence classification (project direction)

- `confirmed`: observation directly and freshly establishes exactly the asserted fact (e.g. LAN confirms console awake, PSN confirms account-level game list).
- `inferred`: association is consistent with multiple observations, but not directly proven.
- `ambiguous`: multiple equally plausible consoles/accounts or conflicting evidence.
- `unknown`: evidence missing, expired, hidden or unavailable.

Do not show a single numerical confidence percentage without empirically calibrated evidence. For UI labels, prefer clear categories and source attribution. Keep source-specific facts accessible so troubleshooting can explain an inference.

## 9. Architecture and dependencies

```text
Home Assistant config entry (per PSN account, TBD)
  -> Protocol 08 account-scoped Token Manager
  -> Protocol 09 PSN Presence Adapter
       -> Account-scoped scheduler / rate budget
       -> Schema parser and typed error normalization
       -> Last fresh provider observation
  -> Domain Presence Reconciler
       <- LAN console status adapter (Protocols 01–02)
       <- Remote Play control observations (Protocols 04–07)
       <- Explicit account/console association registry
  -> Domain session/event accounting (subject to storage ADR)
  -> Home Assistant entities and sidebar panel
       -> No direct PSN network calls from entity getter or frontend
```

The adapter must be independently testable with deterministic fake HTTP responses. The domain reconciler must be independently testable without Home Assistant imports and must avoid coupling the player/game data model to a particular PSN implementation.

### Proposed interfaces (conceptual, not code)

- `PsnPresenceAdapter.fetch_presence(account_id) -> PsnPresenceObservation`
- `PsnPresenceAdapter.fetch_batch(account_ids) -> account-keyed observations` (only if the library and privacy semantics are reviewed)
- `PsnPresenceReconciler.reconcile(lan, psn, associations) -> ReconciledDomainState`
- `PresenceErrorClassifier.classify(error) -> typed category`
- `PsnPresenceScheduler`: account-specific pacing, limits, backoff and cancellation

These names are proposed boundaries, not final Python signatures.

## 10. Polling, rate limits and concurrency

The official Home Assistant PlayStation Network page documents a **300 requests per 15 minutes** PSN allowance and states its own main integration refreshes every **30 seconds**, with friend presence about every **180 seconds** and adjustments for more than 20 friends. Treat this as a published limit for that integration's reference use, **not** a universal contractual Sony rate-limit guarantee for all endpoints/scopes/accounts.

A single 30-second request loop creates 30 polling cycles in 15 minutes, but each cycle can contain several HTTP calls. The official HA page reports **three requests per 30-second data update**, approximately 90 in 15 minutes for its main account polling alone; friends, other actions, multiple accounts and refresh may consume additional capacity. This estimate is for planning only.

**Design direction:**

1. Begin with a conservative configurable cadence; don't lock 30 seconds into every PSN adapter.
2. Centralize provider request budgeting per account (and potentially globally across accounts, pending measured limits).
3. Differentiate slow-changing profiles/trophies from high-frequency current presence.
4. Deduplicate simultaneous fetches for identical account IDs and context.
5. Batch account IDs only if the response and permission contract supports it; restrict fan-out and batch size.
6. Respect HTTP 429, credible `Retry-After`, 5xx backoff, cancellation and safe timeouts.
7. Coordinate presence polling with Protocol 08 token refresh; one account must have a single in-flight refresh.
8. Avoid demand-driven frontend polling multiplication: a dashboard with five users must not trigger five overlapping PSN calls per render.
9. Evaluate `DataUpdateCoordinator` and changed-data equality semantics in HA to limit unnecessary entity updates.
10. Do not emit a false `OFF` or `not playing` state during a network outage or 403 error.

Exact frequency, TTL, batching and concurrency will be benchmarked during implementation, using real provider permissions and documented rate limit behavior.

## 11. Privacy, children and permissions

Sony's official privacy controls let users restrict who can view their online state, current game, gaming history and social details. For child accounts, a family manager may control visibility and restrictions. Respect all privacy settings; do not turn `403` or missing values into a technical reason to bypass restrictions, enumerate alternate accounts or probe hidden information.

**Security requirements:**

- PSN access tokens and refresh tokens stay backend-only; never leak them into entity attributes, diagnostics, browser JS, log exceptions or remote artwork URLs.
- Do not persist sensitive friend lists by default or export social data without explicit user intent.
- Avoid publishing detailed player availability/activity in publicly exposed entities if not needed; consider explicit opt-in for tracking other accounts and retention controls.
- User-visible labels in the Home Assistant panel must be localized. Source technical documents and Python code/comments stay in English.
- Separate remote profile photographs/artwork from personally identifying IDs and unbounded provider responses.
- Keep an audit of what information we collect, how long we retain it, and what delete/unlink does; do not claim Sony-side data deletion.

## 12. Error model and lifecycle

| Error category | Trigger | Required handling |
| --- | --- | --- |
| `authentication_required` | Expired/revoked credentials, confirmed provider auth error | Delegate to Protocol 08 reauth; preserve LAN state and history. |
| `privacy_restricted` | Forbidden/private presence or blocked relationship | Suppress inaccessible fields; no bypass or automatic account probing. |
| `rate_limited` | HTTP 429 | Bounded backoff and optional Retry-After; no rapid retries. |
| `provider_unavailable` | 5xx/service outage | Mark PSN transport unavailable, retain last-known stamped data. |
| `transport_error` | DNS/TLS/timeout/cancel | Retry safely as appropriate; never equate to account offline. |
| `invalid_schema` | Missing/invalid nested JSON structures | Reject malformed data without overwriting fresh accepted observation. |
| `unsupported_platform` | Unknown platform code | Preserve raw value for diagnostics, show unknown platform safely. |
| `account_not_found` | Explicit provider not-found response | Distinguish nonexistent account from hidden/private when possible; avoid overclaim. |
| `identity_mismatch` | Response key unexpectedly maps to another linked account | Reject, report sanitized error, maintain correct account association. |
| `stale_observation` | Expired TTL, delayed prior request | Do not override newer observation or report old data as current. |

On setup: PSN is optional; do not prevent LAN-only integration from loading. On unload: stop scheduled polls, cancel/await tasks, release transport/session state and prevent late callbacks from resurrecting removed accounts. On reauth: preserve account identity and history. On account unlink: remove credentials/associations according to privacy policy and let physical devices continue locally.

## 13. Home Assistant entity and UI model (proposed)

Do not blindly mirror every official `playstation_network` entity into PlayStation Hub; prefer entities with clear state semantics and stable identities.

Suggested account-level entities:

- `sensor` for account presence status, current title and last PSN online date (when allowed).
- `image` for game artwork/avatar, subject to URL security and availability.
- `binary_sensor` only for genuinely boolean, unambiguous properties.
- `media_player` if reporting current media/game state improves HA automations, with clear platform-vs-hardware semantics.
- `diagnostics` indicating PSN authentication / refresh / last successful observation, without tokens.

Suggested console-level entities remain driven by locally confirmed LAN state, not PSN alone. Game/title and account associations should be represented as inferred or unconfirmed where appropriate rather than hidden behind authoritative-looking entity names.

The sidebar UI may display `Last observed` and `Source: PlayStation Network` with an `unavailable`/stale indication, and separate locally confirmed console state. Friends' presence should be opt-in and access-controlled.

## 14. Suggested synthetic fixtures and tests

### Provider protocol

- [ ] Account online on PS5 with one title, both artwork URL variants and valid timestamps.
- [ ] Online without game list; absent game list; empty list; multiple game records.
- [ ] Offline with lastOnlineDate; availability unavailable; mobile-app-only or away.
- [ ] Unknown new platform and online status without crashing.
- [ ] Missing `primaryPlatformInfo`, partial `gameTitleInfoList`, null titles, invalid timestamps, malformed JSON, top-level error object within HTTP 200.
- [ ] HTTP 401/403/404/429/500 and transport timeouts; different handling for auth/privacy/not found.
- [ ] Single-account `psn-api` query and PSNAWP `withOwnGameTitleInfo`/platform query do not assume identical schemas.
- [ ] Batch API returns missing, reordered, private or duplicate users; no identity leakage or mismatching.
- [ ] Inaccessible child/friend account respects Sony privacy.

### Freshness and reconciliation

- [ ] Late response from an older generation cannot override newer state.
- [ ] PSN online with LAN standby does not wake console or rewrite hardware state.
- [ ] PSN offline while local PS5 is awake does not close console usage.
- [ ] Two local PS5 consoles and one PSN account produce ambiguous association instead of invented assignment.
- [ ] PSN title switch between two polls produces bounded uncertainty, not fabricated exact timestamps.
- [ ] 403/429/timeout do not create a false gameplay-ended event.
- [ ] Game activity disappears while local console stays awake: separate no-reported-title from confirmed idle.
- [ ] Restored stale PSN cache is not published as current after HA restart.
- [ ] Internet outage preserves local device control and recorded history.
- [ ] Account reauth and unlink do not corrupt historical console sessions.

### Home Assistant runtime

- [ ] One coordinator refresh fans out to many entities without duplicate provider calls.
- [ ] Startup, load, reload, unload and reconfigure leave no orphan tasks.
- [ ] Polls and token refreshes are serialized appropriately per account.
- [ ] Rate limit and backoff are enforced across concurrent frontend subscribers.
- [ ] Multiple PSN accounts have independent credentials and identity mapping.
- [ ] HA Recorder/history entity semantics reflect unknown/unavailable source, not stale current values.
- [ ] Sensitive identifiers/credentials are omitted from diagnostics and public exports.

## 15. Implementation and live validation gates

1. Resolve Protocol 08's authorized-client, scopes, third-party API usage and security gate.
2. Choose and pin an audited PSNAWP/API adapter version, or implement a narrowly scoped permitted protocol client; do not mix undocumented versions.
3. Specify the concrete response DTO schema from synthetic fixtures and allowed real-device observations.
4. Determine polling interval/TTL from actual endpoint behavior and account limits, not guesses.
5. Approve player/physical-console attribution policy and storage model (including ambiguous activity).
6. Confirm Home Assistant entity presentation, localization and privacy expectations.
7. Validate with a consenting PSN test account on supported console firmware; record endpoint status and privacy settings.
8. Document any compatibility gaps before claiming automatic player attribution or accurate gaming hours.

## 16. Open research and decisions

- **BLOCKED:** Sony-approved PSN client authorization and permitted use of internal presence endpoints.
- **OPEN:** Best supported source interface (PSNAWP single, PSNAWP batch, narrowly scoped client) and future library compatibility.
- **OPEN:** Exact provider response behavior for away, mobile-app-only, multiple platforms, multiple games and hidden visibility.
- **OPEN:** PSN association with two PS5 consoles using the same account; available direct confirmation signal.
- **OPEN:** Whether actual game sessions should require a direct source identity match, or inferred accounting is opt-in with explicit uncertainty.
- **OPEN:** Rate budgets across several accounts, friend monitoring and multiple HA dashboards.
- **OPEN:** Privacy/retention/deletion of social and child-account activity.
- **OPEN:** How to show PSN account service devices versus physical console devices in HA, avoiding duplication with the official `playstation_network` integration.
- **OPEN:** Firmware/region compatibility and account behavior when appearing offline.

## 17. Source register

### Sony official policy

- https://www.playstation.com/en-us/support/account/privacy-settings/
- https://www.playstation.com/en-ie/support/account/privacy-settings-psn/

### Home Assistant official documentation and source

- https://www.home-assistant.io/integrations/playstation_network/
- https://contributors.home-assistant.io/architecture/core/data-updates/
- https://contributors.home-assistant.io/core/integrations/fetching-data/
- https://contributors.home-assistant.io/core/entities/state-updates/
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/helpers.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/coordinator.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/sensor.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/media_player.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/image.py

### Community implementations (not Sony-authorized API specifications)

- https://github.com/achievements-app/psn-api/blob/main/src/user/getBasicPresence.ts
- https://github.com/achievements-app/psn-api/blob/main/src/user/getBasicPresence.test.ts
- https://github.com/achievements-app/psn-api/blob/main/website/docs/api-docs/users.md
- https://github.com/isFakeAccount/psnawp/blob/master/src/psnawp_api/models/user.py
- https://github.com/isFakeAccount/psnawp/blob/master/src/psnawp_api/models/client.py
- https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/psn-account.ts

### Related PlayStation Hub documents

- [Protocol 01 — LAN discovery](01-lan-discovery.md)
- [Protocol 02 — Console status](02-console-status.md)
- [Protocol 08 — PSN authentication](08-psn-authentication.md)
- [Protocol 10 — Game metadata](10-game-metadata.md)
- [Official Core PlayStation Network deep audit](../research/home-assistant-core-playstation-network-audit.md)
- [Communication architecture](../architecture/communication-architecture.md)
- [Security architecture](../architecture/security-architecture.md)

**Research checkpoint:** Presence transport and field-level semantics, privacy limitations, polling, source separation, reconciliation, error handling and test gates are documented. No PSN network access or real-user authentication has been attempted. Source-derived behavior is not evidence of approved Sony third-party API access or PlayStation Hub interoperability.

## 18. Source-pinned account-to-console attribution limitation (2026-11-06)

The [PS5-MQTT v1.8.1 matching saga](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/update-account.ts) sorts optional preferred consoles, selects the **first** physical device in AWAKE with matching platform, then modifies its activity and active player list. This is a best-effort **presentation heuristic**, not hardware evidence. It can be wrong when multiple PS5s are awake, account data lags or the provider's last-used platform differs from the actual LAN device. Never count such output as source-confirmed local game time.

The [official HA Core 2026.11 PSN component](https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network) keys its root service device by PSN account ID and creates platform-oriented media players; [HA PSN documentation](https://www.home-assistant.io/integrations/playstation_network) explicitly notes last-used-device active-state limitations. [psn-api device listing](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/user/getAccountDevices.ts) yields provider-associated devices, not verified physical LAN observations or per-minute game sessions. Treat account status, provider title and local PS5 activity as independent scopes.

**New alternative source for future validation:** LAN discovery responses may contain `running-app-titleid` and `running-app-name` recognized by [chiaki-ng `discovery.c`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L115-L135). If a real PS5 emits meaningful and fresh fields, a directly observed `LAN_RUNNING_APP` candidate may provide console-scoped title metadata **without** PSN; it still cannot prove player identity or uninterrupted gameplay and must pass firmware/semantics testing. See [deep source audit](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md).

## 19. Why LAN application metadata must not inherit account attribution (2026-11-06)

The [source-triangulation audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) identified a PS5-specific C tool, [ps5-wake](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L100-L113), as another parser recognizing local `running-app-*` headers, and a [Chiaki-KM user-interface consumer](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/inputprofile.cpp) interpreting them independently of PSN presence. Neither source confirms that a PSN account/player caused that running app. A physical reported-title fact may ultimately support local-title visibility without a PSN account, but account/title/console mapping needs a separate signal and a namespaced ID crosswalk (CUSA/PPSA/provider IDs).

Therefore `PSN_ACCOUNT_TITLE` and `LAN_RUNNING_APP` are independent evidence scopes; neither may silently override the other. The current PS5-MQTT first-awake-console matching is a visualization heuristic, not evidence of who played what for a historic time interval. No Sony provider endpoint is authorized by this source audit.

## 20. Source-level HA provider projection and token isolation (2026-11-06)

[HA Core 2026.11.0 helpers.py](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/helpers.py#L86-L138) retrieves provider account devices and presence, then uses `next(iter(gameTitleInfoList), {})` to choose a **first game title** for its primary-platform `active_sessions` projection. This is a reasonable UI selection but does **not** prove there was only one returned title, a single physical PS5, or continuous gameplay. Preserve a bounded provider title candidate list, explicit account ID, platform, privacy, source timestamp and selection policy; keep this separate from optional `LAN_RUNNING_APP` and hardware-origin observations.

[PSNAWP's refresh function](https://github.com/isFakeAccount/psnawp/blob/fcd7e8334495585b5a8d7502b3b527f34f9d7777/src/psnawp_api/core/authenticator.py#L177-L211) can be entered by multiple callers unless externally serialized; [Emkraan's HA variation](https://github.com/Emkraan/homeassistant-playstationnetwork/blob/aecbd580c39cc00692f06cec80df4b17c02e1e63/custom_components/playstation_network/compat.py#L74-L118) provides a source-visible lock workaround. For PlayStation Hub, each PSN account's auth/refresh/429/403 state is independent of the LAN service; no PSN refresh can falsely set a physical console to OFF or erase its last-known local title. Source details and qualitative future tests: [triangulation §11](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md#11-deeper-psn-runtime-source-audit--token-rotation-provider-title-selection-and-independent-failures).
