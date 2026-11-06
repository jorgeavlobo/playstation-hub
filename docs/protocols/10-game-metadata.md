# Protocol 10 — Game identity, metadata, digital library and artwork

**Status:** Detailed source-derived research specification; Sony third-party API and artwork usage authorization remain unverified  
**Reviewed:** 2026-11-05  
**Implementation:** Not started; no PSN account, store or physical-console validation  
**Proposed modules:** `custom_components/playstation_hub/transport/psn/metadata.py`, `domain/games.py`, `domain/game_identity.py`, `domain/game_catalog.py` (planning only)  
**Historical pinned reference trees:** `PS5-MQTT` `7ab3075d276f3eeecd81a3322c72231af8cd51bd`, `psn-api` `1e9d9a806fcd884a4ddee8086bfe92594611da9f` (from protocol index). Files were also reviewed from current upstream default branches; pins and moving heads must not be conflated.

> **Evidence boundary:** `SOURCE-CONFIRMED` means inspected community/HA source behavior, not Sony endorsement. `SONY-OFFICIAL` refers to Sony's product descriptions and terms, not an approved API. `DESIGN DIRECTION` is PlayStation Hub's proposed contract. `BLOCKED` means a release gate. All API uses involving Sony OAuth/GraphQL/internal catalog endpoints and content must pass the Protocol 08 authorization and terms review before implementation or distribution.

## 1. Purpose and precise data boundaries

Provide a modular, account-aware and console-aware catalog of PlayStation games, with titles, identifiers, platform/edition information, remote artwork references, and optional enrichment from permissible provider sources. Preserve observations and provenance. Game metadata **must not** be obtained by Home Assistant entity property getters or frontend components performing Sony API calls.

Distinguish six concepts from day one:

1. **Currently reported game** — a game visible in a fresh PSN presence observation (Protocol 09).
2. **Recently played games** — a cloud account list, not a timeline of precisely measured local sessions.
3. **Played-games history** — account-level provider history, potentially including provider-reported play duration/count and last-played dates.
4. **Digital library/entitlements** — games associated with account entitlements, including bought, redeemed, subscription and possibly never-played titles; **not proof of permanent ownership or local installation**.
5. **Game catalog metadata** — localized name, artwork, description, publisher, genre, edition and platform supplied by a metadata provider.
6. **Home Assistant-owned monitored sessions** — separately observed console/player activity, stored by our domain/session engine, not automatically interchangeable with PSN lifetime playtime.

Do not equate a PSN account entitlement with a game being installed, currently playable, currently running or owned as a permanent standalone purchase. Disc-based games may be absent from digital-purchase API views. A PS Plus catalog entry can cease being available despite having been in the account's library.

## 2. Evidence inventory

| ID | Reference | Classification | Finding |
| --- | --- | --- | --- |
| GAME-01 | `psn-api/src/user/getBasicPresence.ts`, `PS5-MQTT/server/src/psn-account.ts` | SOURCE-CONFIRMED | Presence `gameTitleInfoList` exposes `npTitleId`, name, game format, launch platform and optional artwork URLs; PS5-MQTT chooses its first item. |
| GAME-02 | Home Assistant Core `playstation_network/helpers.py`, `image.py`, `media_player.py` | SOURCE-CONFIRMED | HA uses `conceptIconUrl` or `npTitleIconUrl`, current title and image entities; platform media players are account views. |
| GAME-03 | `psn-api/src/user/getUserPlayedGames.ts` | SOURCE-CONFIRMED | Played-game list for an account: `/:accountId/titles`, categories and pagination options. |
| GAME-04 | `psn-api/src/graphql/getRecentlyPlayedGames.ts` | SOURCE-CONFIRMED | Uses persisted GraphQL query `getUserGameList`, categories `ps4_game,ps5_native_game` by default, and a configurable limit. |
| GAME-05 | `psn-api/src/graphql/getPurchasedGames.ts` | SOURCE-CONFIRMED | Uses persisted GraphQL query `getPurchasedGameList`, platform filters, active state, pagination and membership options. |
| GAME-06 | `psn-mcp/src/psn/api.ts` | SOURCE-CONFIRMED | Combines purchased titles and played-game lists, matching by exact `titleId`; can add playtime to library display but handles missing playtime explicitly. |
| GAME-07 | PSNAWP `models/game_title.py` | SOURCE-CONFIRMED | Separates title ID, platform and trophy `np_communication_id`; supports detail queries and legacy PS3/PS4 icon retrieval. |
| GAME-08 | PSNAWP `models/trophies/trophy_titles.py` | SOURCE-CONFIRMED | Trophy title models expose title name, icon, supported platforms, and trophy communication IDs. |
| GAME-09 | Sony PlayStation Plus catalog/support | SONY-OFFICIAL | Subscription library access depends on tier/subscription and titles can leave the catalog. |
| GAME-10 | Sony PlayStation Terms of Service (Portugal, April 2026) | SONY-OFFICIAL | Restricts unauthorized methods, IP/content reuse and certain automated interactions. Must review applicability to metadata/artwork before release. |
| GAME-11 | Home Assistant image entity source | HA-SOURCE | Entity images and cache invalidation are supported; remote artwork ownership and safe fetching remain integration responsibilities. |

## 3. Upstream source: currently playing game

A PSN `basicPresence.gameTitleInfoList` may contain title candidates:

| Wire field | Meaning | Risk |
| --- | --- | --- |
| `npTitleId` | Title identifier | Opaque; do not parse or infer edition solely from its prefix. |
| `titleName` | Provider-supplied human-readable name | Localized, mutable, may differ by edition; not a unique key. |
| `format` | Game software format | May be PS4 while running on PS5; not physical hardware. |
| `launchPlatform` | Platform launching the title | Distinct from format; still not a unique device ID. |
| `npTitleIconUrl` | Optional title image URL | Availability, dimensions, access and license not guaranteed. |
| `conceptIconUrl` | Optional concept image URL | May represent related product/concept across versions; not a game identity. |

PS5-MQTT uses `npTitleIconUrl ?? conceptIconUrl` in its reviewed account module; Home Assistant Core's PSN helper and image entity often prefer `conceptIconUrl` first. **There is no universal source-confirmed priority policy**, so choose by expected asset type and quality during tests, not by one borrowed order.

Presence may return empty, multiple, unavailable or privacy-restricted lists. Do not claim any returned title is currently running on a particular LAN PS5 without the evidence required by Protocol 09's reconciler.

## 4. Played-games history

`psn-api.getUserPlayedGames(authorization, accountId, options)` builds a request for a provider account's titles and accepts pagination options (`limit`, `offset`) and `categories`. The `psn-mcp` example uses a `/gamelist/v2/users/{accountId}/titles` path with `ps4_game,ps5_native_game,pspc_game` categories.

**Information types observed in community consumers:** `titleId`, optional display title, platform category, `playDuration`, `playCount`, `firstPlayedDateTime`, `lastPlayedDateTime`. Exact units, consistency, visibility and limits must be verified against pinned DTOs and permitted test fixtures; do not assume `playDuration` is a duration in seconds or that every title has a value.

A provider lifetime duration may include play on multiple consoles or historical periods before installation of PlayStation Hub. It must not be added directly to our locally measured active-session totals. Maintain independent provenance, scope, units and last-updated timestamps. A field absent from an API is `unknown`, **not zero**.

Privacy restrictions can hide other accounts' played games. Never scrape around restrictions or silently reassign history to a user's account.

## 5. Recently played games

The community `getRecentlyPlayedGames` implementation requests a persisted GraphQL `getUserGameList` operation with categories and a limit (default 50) and checks for `data.gameLibraryTitlesRetrieve`. This query supports recent activity not necessarily tied to trophies.

GraphQL operation hashes are **version-sensitive implementation details**, not an official stable interface. A changed persisted-query hash can break the integration even if authentication remains valid. Never hardcode unpinned hashes into a production release without a permitted API strategy, compatibility fixture and explicit failure handling.

A recently played title is not proof of physical-console identity, disk installation, digital ownership, exact playing interval or parental authorization.

## 6. Digital library and entitlements

The community `getPurchasedGames` function queries `getPurchasedGameList` through a persisted GraphQL operation, with defaults equivalent to `isActive=true`, `platform=[ps4,ps5]`, `size=24`, `start=0`, sorting by activation date descending, and optional membership filtering.

The reviewed `psn-mcp` implementation demonstrates:
- Pagination across digital entitlements.
- Optional membership-related filtering.
- Optional enrichment with played-history `playDuration`, `playCount`, first/last played information by matching the exact `titleId`.
- Explicitly reporting a failure to enrich playtime without treating purchased games as absent.
- Local `NONE` membership filtering in its own implementation because the upstream filter reportedly returns empty results.

**Critical distinctions:** `purchased` is the community API label, not a guarantee that a title was bought permanently, still licensed, installed, eligible to launch or playable without subscription. Free purchases, PS Plus claims, subscriptions, preorders and region restrictions require different semantics. The Sony PS Plus documentation confirms entitlements and access can change as subscriptions expire or catalog games leave. Do not display `Owned` solely because an item appears in the purchased-title response.

The digital library is account-specific; it is not the complete local list of disc games, other users' titles, installed software, or all games that have ever run on a console. Distinguish `entitlement_active`, `entitlement_source`, `downloadable`, `installed` and `ownership_type` only when an authorized source actually confirms each property.

## 7. Game and product identifier taxonomy

| Identifier | Purpose | Relationship |
| --- | --- | --- |
| `npTitleId` / `titleId` | Title identifier supplied by PSN | Primary provider title key, scoped and validated; not a product ID. |
| `npCommunicationId` | Trophy set communication identifier | Separate namespace; cannot be assumed equal to title ID. |
| `conceptId` | Store/catalog game concept (when returned) | May group related platform versions/products; mapping requires evidence. |
| `productId` / SKU | Store offer/product identifier | Can vary by edition, region, currency and entitlement; not title identity. |
| `entitlementId` | Account-rights/entitlement identifier | Account-specific; not proof of permanent purchased ownership. |
| `platform` / `format` / `launchPlatform` | Classification and runtime context | Never a physical console ID. |
| `onlineId` | PSN account display name | Never a game identifier, nor a stable account key. |

**Identity rule:** Do not use normalized title text, marketing cover, game genre, `conceptId` or a trophy set ID alone to collapse two titles. Treat provider identifier + explicit namespace/platform/context as the starting key. Crosswalks must include evidence/source and support one-to-many mapping, corrections and invalidation.

### Platform and edition edge cases

- PS4 game launched on PS5: `format` and `launchPlatform` differ; count the same title on a different hardware type only with appropriate attribution.
- PS4/PS5 dual entitlement: may expose separate title IDs or one shared concept; never merge implicitly.
- Standard/deluxe/ultimate editions: can share a concept but differ in entitlement or extras; preserve product-level distinctions.
- DLC/add-ons and separate trophy groups: not necessarily a playable standalone title.
- Remakes/remasters and different regions: similar names are not proof of one game.
- Disc versus digital: digital entitlements cannot establish what is physically inserted or installed.
- Demos/trials/betas: may report title IDs and partial access, requiring separate flags if known.
- Game-streaming/cloud sessions: provider activity and platform may not map cleanly to a local PS5.

## 8. Provider enrichment and localization

The PSNAWP `GameTitle.get_details(country, language)` implementation requests game concept details using explicit country (ISO alpha-2) and language (BCP 47) parameters. It describes fields such as full title, summary, genre and promotional media. The method is separate from the title/trophy ID crosswalk and uses a provider endpoint from PSNAWP's source. Presence title names should not be overwritten permanently by an unrelated region/edition name.

**Proposed metadata precedence:**

1. Display the best current, directly sourced title for the context the user is viewing.
2. Enrich with explicitly matched catalog metadata for the configured region/language.
3. Cache previous verified details with source, locale and expiry provenance.
4. If enrichment fails, keep the directly reported title/name/ID rather than dropping the game.
5. If neither is available, show a localized neutral placeholder, not a fabricated product name.

Keep a metadata record per provider+ID+locale+edition scope; expose alternative titles when validated, and avoid mixing display language with stable identity.

## 9. Artwork source, priority, caching and security

Possible image sources: `conceptIconUrl`, `npTitleIconUrl`, trophy title icon, catalog product icon, user-provided art (if separately supported). They are *distinct assets* with different quality, crop, aspect ratio, expiry and rights. Store original source attribution and asset role (`cover`, `icon`, `hero`, `avatar`) rather than one unconditional image URL.

**Design direction:** Choose context-specific artwork (e.g. icon for current-game entity, portrait cover for game library), never blindly fetch every large image at startup. The frontend may use a backend-authorized artwork URL or a safe, cache-controlled HA image entity endpoint only after security/API reviews. Do not embed PSN bearer tokens in image URLs.

### SSRF and remote image validation

- Accept only HTTPS, with a maintained allowlist of trusted asset hosts or provider-controlled hostnames once confirmed by source evidence.
- Reject embedded credentials, localhost, link-local, multicast, RFC1918/private addresses and URLs that resolve to internal hosts. Revalidate redirects and DNS-resolved addresses for server-side fetches.
- Restrict response size, MIME type, dimensions, redirect count and timeouts; protect against decompression bombs and SVG/script surprises.
- Never log full URLs when they may contain sensitive query parameters; never send PSN authorization headers to third-party CDN domains unless a trusted provider contract explicitly requires them.
- Use bounded LRU+TTL caches, an image negative-cache for 404 failures, deduplicated concurrent fetches, and cancellation-safe cleanup.
- Treat remote URL as changeable; if it changes, invalidate only the corresponding artwork cache, not the game identity.
- Expose visible fallback artwork when images are unavailable/offline; don't delete the associated game metadata or history.
- Store no unaudited copyrighted binaries in the public GitHub repository; external live URL embedding, proxying, caching and redistribution require a separate rights/terms assessment.

### Licensing and IP restrictions

Sony's [Portugal Terms of Service](https://www.playstation.com/pt-pt/legal/terms-of-service/) (April 2026) includes restrictions on unauthorized means, IP/content use and certain automated activity. Sony's PS Plus support explicitly distinguishes entitlement from continuing access. **BLOCKED:** Review permitted automated metadata requests and image display/proxy/cache/redistribution terms before shipping. Source-visible artwork links are not a reusable artwork license.

## 10. Proposed domain models (conceptual only)

```text
GameTitleIdentity
  provider: playstation_network
  namespace: title
  title_id: opaque string
  platform_scope: optional normalized platform
  external_ids: optional source-annotated mappings

GameMetadata
  identity: GameTitleIdentity
  localized_name: optional string
  locale: optional string
  description: optional string
  genre: optional list[string]
  publisher: optional string
  edition: optional string
  artwork_candidates: immutable list[ArtworkCandidate]
  source: metadata/presence/library/trophy
  observed_at_utc: UTC
  freshness: fresh/stale/unavailable

ArtworkCandidate
  role: cover/icon/hero/unknown
  url: HTTPS validated remote reference
  source: provider and field
  priority: context-specific
  verified_at_utc: optional UTC
  content_type: optional string
  license_status: unknown/approved/restricted

AccountGameRecord
  account_id: stable provider account identifier
  identity: GameTitleIdentity
  relationship: observed_played/recent/digital_entitlement/unknown
  entitlement_status: optional
  play_duration: optional provider-valued duration with units and scope
  play_count: optional nonnegative integer
  first_played_at: optional UTC
  last_played_at: optional UTC
  retrieved_at_utc: UTC
  privacy_visibility: visible/restricted/unknown

LocalGameSession
  independently tracked Home Assistant session ID
  physical_console_id: stable local identifier, if confirmed
  player_account_id: optional
  player_attribution: confirmed/inferred/ambiguous/unknown
  title_identity: optional
  started_at_utc: observed/estimated boundary
  ended_at_utc: observed/estimated boundary
  provenance: one or more evidence records
```

No Python classes, DB migrations or frontend components have been implemented. Names and exact types are **proposed** and must be finalized with Protocol 09 and the storage ADR.

## 11. Proposed module boundaries and API contracts

- `PsnGameMetadataAdapter.fetch_title(title_identity, locale)`: optional catalog enrichment, typed errors, bounded network I/O.
- `PsnLibraryAdapter.fetch_recent(account_id, page)`: recent games; distinct from purchases.
- `PsnLibraryAdapter.fetch_played(account_id, page)`: account-level played game list and provider playtime.
- `PsnEntitlementsAdapter.fetch_library(account_id, page, filters)`: digital entitlements for authorized account, not all installed games.
- `GameIdentityResolver`: explicitly evidenced title/concept/product/trophy crosswalk and corrections.
- `GameCatalogRepository`: optional cache/snapshot store for normalized metadata, independent of session history or secret storage.
- `ArtworkService`: validates assets, rights/cache policy, provides safe UI references and placeholders.
- `GameSessionReadModel`: joins already stored local sessions with optional metadata; metadata refresh may not rewrite authoritative session timestamps/owners.
- `PsnRateBudget`: shared request budget with Protocols 08–09, including concurrent accounts and 429 backoff.

Return immutable typed records with source, retrieved-at and stale status. Do not let UI or HA entity attributes call the provider directly or call token management internally. Account metadata work is optional and cannot block a fresh LAN power update.

## 12. Data and persistence policy

- Persist a compact normalized catalog or cache **only if** user value justifies storage volume and a dedicated ADR approves the schema; the definitive historical SQLite choice is still open.
- Separate durable game identity/crosswalk, account entitlements, current/provider presence, local session history and temporary image cache. Each has different retention and deletion expectations.
- Use canonical UTC for observation/history, explicit locale for localized names, and stable title IDs; avoid changing historical titles retroactively without recording source corrections.
- Provider playtime may be lifetime/aggregate from multiple devices; store it as a snapshot, never double-add it to measured local session durations.
- For daily or monthly statistics, count only independently accepted sessions and label estimated durations as such.
- A user who unlinks their PSN account may choose appropriate retention/deletion of account-specific library/social data; do not delete unrelated local console sessions without an explicit policy.
- On backend restart, previously cached catalog records can be shown as stale/offline reference, never presented as freshly observed currently playing activity.
- Maintain migrations, indexing, backup/restore and storage-size budgets without storing unrestricted raw provider bodies.

## 13. Polling and cache policy

Use distinct refresh profiles, rather than fetching entire libraries whenever the player starts a game:

| Dataset | Suggested cadence | Status |
| --- | --- | --- |
| Current game | As supplied by Protocol 09 presence polling | Source-dependent; no additional mandatory request |
| Game metadata | On first known title and when stale or requested | Design direction; choose TTL by measured stability |
| Recent games | Infrequent / on account library view | Design direction; not same as active-presence polling |
| Played-game history | Scheduled low-frequency refresh or user request | Design direction; provider aggregated values may lag |
| Digital entitlements | Explicit sync or infrequent background update | Design direction; may be large and privacy-sensitive |
| Artwork | Lazy, cached, per visible item | Rights-dependent; no bulk download by default |

Implement request coalescing, bounded concurrency, pagination validation (strictly increasing offset or stable continuation key), maximum page/record counts, cancellation, exponential backoff with jitter and trustworthy Retry-After. Avoid infinite loops on empty/non-advancing pages. A failed metadata request must not repeatedly query every dashboard render.

## 14. Error taxonomy

| Error | Meaning | Safe reaction |
| --- | --- | --- |
| `auth_required` | Token expired/revoked | Delegate to Protocol 08; LAN remains available. |
| `forbidden_or_private` | Provider denies profile/library visibility | Respect privacy; no bypass or alternate account probe. |
| `not_found` | Missing title/product | Keep known title ID and existing cached metadata. |
| `rate_limited` | 429 or policy limit | Shared bounded backoff, no reload/retry storm. |
| `provider_unavailable` | 5xx/timeouts | Keep last-known catalog visibly stale. |
| `schema_changed` | GraphQL operation/schema mismatch | Mark provider adapter degraded; no invented fields. |
| `invalid_pagination` | Repeated cursor/offset, malformed count | Abort bounded sync, preserve prior good data. |
| `ambiguous_identity` | Multiple editions/IDs might match | Keep multiple records; no automatic merge. |
| `artwork_blocked` | Rights or host policy fails | Placeholder only; metadata/session still usable. |
| `invalid_artwork` | Unsafe URL, redirect or binary | Refuse remote fetch; do not leak internal networks. |
| `unknown_play_duration_units` | Numeric aggregate of unknown units | Preserve as raw typed snapshot only if safe; do not convert or add. |
| `not_in_digital_library` | No digital entitlement observed | Do not assume game was never played or isn't installed. |

## 15. Synthetic and integration test matrix

### Identity and metadata

- [ ] Same title ID and edition across two PSN accounts maps to one catalog identity but separate account records.
- [ ] Same name with different PS4/PS5 title IDs remains distinct until source evidence proves mapping.
- [ ] One concept with multiple product editions maps one-to-many without collapsing entitlements.
- [ ] Trophy `npCommunicationId` remains separate from title ID.
- [ ] PS4 title launched on PS5 preserves both `format` and `launchPlatform`.
- [ ] DLC, demo, beta, remake, remaster, deluxe edition and cross-generation upgrade are not silently merged.
- [ ] Locale/region name changes do not change identity or override verified title ID.
- [ ] Empty/missing/partial game title responses do not crash parsing or erase historical sessions.
- [ ] Last-good metadata is shown as stale if provider fails.
- [ ] Unknown platform, game ID or art field falls back safely.

### Library and usage

- [ ] Purchased titles but never played: no invented game session/playtime.
- [ ] Played disc title absent from digital entitlements: retain played-game record.
- [ ] PS Plus catalog entitlement removed or subscription expired: distinguish current access from historical library entry.
- [ ] Pagination follows increasing offsets, terminates on empty/last page and rejects loops.
- [ ] Provider play duration absent is unknown, not zero; known provider total is not added to locally measured sessions.
- [ ] Recent games, played history and digital library are independently modeled and cached.
- [ ] Two linked accounts and two physical consoles keep account/library/session records separate.
- [ ] A provider game's title change updates catalog display, not historical game/account identifiers.
- [ ] Account unlink/relink and backup restore preserve permitted history without retaining unauthorized private records.

### Artwork and security

- [ ] HTTPS allowed source, approved rights status, valid PNG/JPEG/WebP returns image with bounded size.
- [ ] Non-HTTPS, localhost, private IP, loopback, DNS rebinding and redirect to internal address are rejected.
- [ ] Content-type mismatch, broken image, oversized response, decompression bomb and corrupt binary yield placeholder.
- [ ] Asset changes invalidate image cache without changing game identity.
- [ ] Cache evictions do not delete durable metadata.
- [ ] No PSN OAuth token, NPSSO, auth header or sensitive URL query appears in entity attributes or logs.
- [ ] Browser/media requests never carry PSN bearer token to a generic third-party CDN.
- [ ] Artwork use/display rights are reviewed before any release.

### Home Assistant lifecycle

- [ ] Metadata fetch cannot block the HA event loop.
- [ ] Multiple widgets requesting one cover trigger at most one in-flight fetch.
- [ ] No network calls from frontend, entity getters or pure domain models.
- [ ] Coordinator unload cancels tasks, clears pending requests and does not break LAN state.
- [ ] Only licensed/permitted provider adapters are enabled by default, and forbidden ones are not silently used.
- [ ] HACS packaging and frontend cache version align with one integration release.

## 16. Release and compliance gates

1. **BLOCKED:** Determine if Sony authorizes the required account API calls, GraphQL operations, client identifiers and request volume. Public community source does not establish permission.
2. **BLOCKED:** Review artwork copyright, trademarks, CDN access and whether linking, proxying or local caching is allowed for our distributed integration. Comply with relevant law and provider terms.
3. **OPEN:** Decide exact release scope: current game image only, recent/played history, purchased digital library, rich catalog enrichment, store browsing, trophies and installation status.
4. **OPEN:** Pin actual provider response models, GraphQL query operation versions and hash compatibility; never rely on an unverified moving branch.
5. **OPEN:** Determine supported locale/country, user consent and privacy retention for purchased libraries and child accounts.
6. **OPEN:** Confirm identifiers and source-backed mapping between editions and trophy sets; source may vary with region/platform.
7. **OPEN:** Resolve storage ADR, image cache limits and safe HA frontend/image API semantics.
8. **OPEN:** Determine whether provider playtime is actually comparable across accounts, title variants and local timestamps.
9. **OPEN:** Confirm exact feature compatibility through synthetic fixtures, authorized Sony account testing where permitted, Home Assistant OS tests and legal review.

**Design decision:** PlayStation Hub must remain fully functional for LAN discovery and local power/status without metadata/cloud availability. Game names and images enhance monitoring; they are not prerequisites for the console's device entry, state machine or historical session persistence.

## 17. Source register

### Sony product behavior and applicable terms (official, not API licensing)

- https://www.playstation.com/pt-pt/support/subscriptions/ps-plus-game-catalog/
- https://www.playstation.com/pt-pt/ps-plus/games/
- https://www.playstation.com/pt-pt/legal/terms-of-service/

### Home Assistant Core

- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/helpers.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/media_player.py
- https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/image.py
- https://www.home-assistant.io/integrations/playstation_network/
- https://developers.home-assistant.io/docs/core/entity/image/

### Community source (reverse-engineered and not officially supported by Sony)

- https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/psn-account.ts
- https://github.com/achievements-app/psn-api/blob/main/src/user/getBasicPresence.ts
- https://github.com/achievements-app/psn-api/blob/main/src/user/getUserPlayedGames.ts
- https://github.com/achievements-app/psn-api/blob/main/src/graphql/getRecentlyPlayedGames.ts
- https://github.com/achievements-app/psn-api/blob/main/src/graphql/getPurchasedGames.ts
- https://github.com/achievements-app/psn-api/blob/main/src/graphql/operationHashes.ts
- https://github.com/isFakeAccount/psnawp/blob/master/src/psnawp_api/models/game_title.py
- https://github.com/isFakeAccount/psnawp/blob/master/src/psnawp_api/models/trophies/trophy_titles.py
- https://github.com/tmrp/psn-mcp/blob/main/src/psn/api.ts

### Related PlayStation Hub architecture

- [Protocol 08 — PSN authentication](08-psn-authentication.md)
- [Protocol 09 — PSN presence](09-psn-presence.md)
- [Home Assistant Core PSN audit](../research/home-assistant-core-playstation-network-audit.md)
- [Communication architecture](../architecture/communication-architecture.md)
- [Security architecture](../architecture/security-architecture.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

**Research checkpoint:** Title field discovery, identifier namespaces, recently played/played/purchased distinctions, PSNAWP metadata and artwork sources, identity mapping, localization, caching, security, legal constraints, persistence boundaries and synthetic tests are specified. No live PSN or console interoperability is claimed, and no authentication or executable integration code was produced.


## Greenfield game-title identity and SQLite v1 optional metadata separation — 2026-11-06

[Official SQLite/HA v1 schema research](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md), [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md) and [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md) refine Protocol 10's title dimensions into one core game_titles stable key defined by explicit provider namespace, title namespace, provider title ID and platform scope; all unique tuple components must be nonnull. A PSN title, trophy communication ID, concept/edition, localized display name and source artwork URL are not automatically equivalent keys. A crosswalk between genuine identities requires separate provenance and confidence evidence, not title-string matching.

Optional game_metadata_locales and game_title_crosswalk may be added after source rights and authorization review. Account-level entitlement and cumulative played-game duration are optional snapshots with exact provider scope/units, never counted as our locally observed console or player game seconds. Changing title names, artwork or metadata rights cannot change historical session identity/duration, and LAN-only usage works without PSN metadata at all. The proposed schema is greenfield with no old fictional App imports; no API authorization, title mapping, database or test has been proven.

## 18. Discovery-based local application metadata — important new source audit (2026-11-06)

**New possible LAN-only capability:** [Chiaki-ng discovery](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L115-L135) recognizes optional `running-app-titleid` and `running-app-name`. [playactor's `device.extras`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L115-L126) can preserve additional headers even when not explicitly modeled. [playdirector v0.3.0](https://pypi.org/project/playdirector/0.3.0/) documented similarly named LAN running-app fields; its current `0.4.2` is an incompatible API/licensing generation and must not be inferred equivalent.

**Candidate model:** `LAN_RUNNING_APP` is an optional source-scoped physical-console observation with `console_id`, `requested_at/received_at`, `header_present`, `title_id?`, `app_name?`, normalized source protocol version, validity and freshness. Do not misclassify `title_id` as `npTitleId` without verified namespace mapping; avoid merging titles by name. Do not associate PSN account/player based solely on this value. The reported app may be running/background/suspended or a non-game application; absence can mean field not emitted or private/unsupported, not proof of no game. A title/app change sampled at T1 cannot prove exact user gameplay transition time.

**Required future fixture matrix:** standby/home, PS5-native game, PS4-on-PS5 game, media app, game switch, suspend/resume, PSN offline, incomplete headers, firmware variant and title ID crosswalk. If proven reliable, this source can support a local **title-reported** timeline without mandatory PSN and improve source attribution beyond PSN-only platform heuristics. A real console is required before claiming it works for PlayStation Hub.

**Further PSN source distinctions:** [PS5-MQTT `update-account.ts`](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/update-account.ts) selects the first awake console matching the PSN activity platform, optionally prioritizing a preferred device; this is a best-effort UI heuristic, **never evidence of hardware-specific gameplay duration**. [HA Core PlayStation Network](https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network) remains account-centric and its own documentation warns that active state may only be reported for the last-used device. No local game attribution by this provider method is automatic.

**Complete evidence:** [Deep source audit](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md).

## 19. Cross-repository title-ID namespace and absence semantics (2026-11-06)

The [second upstream triangulation audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) confirmed optional DDP `running-app-titleid/name` support in the PS5-specific [PS5-Wake C parser](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L100-L113), older [pyremoteplay](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py#L100-L145), and [Chiaki-ng](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L115-L135). This independently motivates a LAN-only reported-app display but does NOT establish firmware availability or accurate game-usage time.

[Chiaki-KM's profile matching](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/inputprofile.cpp#L35-L49) recognizes certain `CUSA` PS4 title IDs on a PS5 running a backward-compatible game. A title key must preserve **origin + ID namespace + platform context**, and never equate a CUSA ID, PPSA ID, PSN `npTitleId` or concept ID merely because the game name appears to match. Record app field ABSENT versus EMPTY versus VALUE as separate states; no empty title may be inferred from an absent response header.

An optional `LAN_RUNNING_APP` entry in the v1 observations model should be a **source-specific console-scoped sample**, not a hard requirement for the LAN-only feature and not proof of player identity. Confirm foreground/background behavior, menu, media apps, suspend and cross-generation titles with direct hardware fixtures before creating per-title historical usage totals.

## 20. Cloud provider query and display-selection limitations (2026-11-06)

[psn-api's `operationHashes.ts`](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/graphql/operationHashes.ts) describes reverse-engineered persisted-query hashes extracted from Sony's web application. Their validity is version-sensitive, not a stable public contract. `getUserPlayedGames`, `getRecentlyPlayedGames`, `getPurchasedGames`, and `getBasicPresence` are **different provider questions**, not equivalent to what a local PS5 is playing or which title is installed. A provider-failure or changed hash must degrade a **cloud-only** feature, never local LAN status or optional `LAN_RUNNING_APP` metadata.

[HA Core `helpers.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/helpers.py#L110-L138) projects only the first `gameTitleInfoList` record for its account/platform active session. That is a display simplification, not exhaustive game evidence. PlayStation Hub should preserve source-scoped title candidates and explicit title IDs/namespaces, with no automatic CUSA/PPSA/npTitleId/conceptId crosswalk by name. Full analysis and future source trace cases: [upstream triangulation §11](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md#11-deeper-psn-runtime-source-audit--token-rotation-provider-title-selection-and-independent-failures).

## 21. Own source-specific title metadata adapter, without cloud SDKs (2026-11-06)

The [first-party requirement](../architecture/first-party-dependency-sovereignty-policy.md) now excludes all external PlayStation runtime parsers and Sony metadata SDKs. Implement source-scoped console DDP \`running-app-titleid\`/name normalization ourselves, if firmware tests validate those optional fields. Treat namespaced LAN title keys, Sony PSN identifiers and game artwork references separately; do not infer equivalence or game seconds by display name. The optional catalog client cannot use \`psn-api\`, \`PSNAWP\`, a Node service or an undocumented client credential taken from another application, and must remain unavailable if Sony permission is absent. No third-party frontend framework is needed merely to display localized game names or optional images.

## 22. First-party DDP title field parsing versus optional empty header (2026-11-06)

The [latest DDP wire/parser audit](../research/lan-ddp-wire-and-temporal-correlation-audit-2026-11-06.md) inspected [Chiaki \`http.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/http.c#L27-L86) and found its parser rejects explicitly empty HTTP-like header values. Therefore our proposed \`ABSENT\`/\`EMPTY\`/\`VALUE\`/\`INVALID\` app metadata classification is **our robustness/semantic design**, not existing cross-source proof that Sony emits present-but-empty \`running-app-name\` or \`running-app-titleid\`. Hardware fixtures must determine whether EMPTY is valid for that version or must be parsed INVALID. Header absence cannot prove no game; a title name is not a player or measured foreground gameplay period.

The same source study establishes that DDP search traffic lacks a demonstrated on-wire request nonce/timestamp, so \`received_at\` is **only reception time** and \`WINDOW_ASSOCIATED_UNVERIFIED\` timing quality applies even if the packet contains a valid title ID. A source-specific locally reported app at T is not verified title-start time or a cryptographically authenticated host. Game-duration ledger remains separately gated.
