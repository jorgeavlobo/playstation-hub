# SPEC-004 — PSN presence and game metadata DTO mapping

**Status:** Proposed, source-derived specification; no Sony API permission, live provider tests or implementation  
**Date:** 2026-11-05  
**Scope:** Protocols 08–10; ADR-0004/0005/0006/0007/0008/0009/0010; SPEC-003 authorization gate  
**Branch:** `main` documentation only. No executable code changes on `next` or `develop`.

> **Evidence boundary:** A DTO described by community code is not a stable Sony public contract. Every field must carry source, scope and uncertainty. All PSN adapters remain release-disabled until SPEC-003 authorization requirements are satisfied. Examples are synthetic, not copied private account responses.

## 1. Objectives and invariants

Define explicit, versioned, typed mappings from permitted provider responses into internal domain observations, persisted catalog models, Home Assistant entities and the sidebar WebSocket API. Separate identity, online presence, account availability, reported game activity, recently played games, played history, purchased/entitled library, trophy identity and artwork. Preserve absence, privacy restriction, stale data and provider errors without turning them into false physical-console facts.

**Non-negotiable:** `account_id` is not a console ID; `onlineId` is mutable display text; `npTitleId/titleId` is not `conceptId`, `productId`, `npCommunicationId` or `entitlementId`; `format` is not `launchPlatform`; entitlement does not imply installation, permanent ownership or play; provider lifetime playtime never becomes locally measured session time.

## 2. Provider endpoint and feature matrix

| Feature | Community-observed origin | Provider scope | Availability / release |
| --- | --- | --- | --- |
| Basic presence | `GET /api/userProfile/v1/internal/users/{accountId}/basicPresences?type=primary` | One requested account | Permission-gated, undocumented |
| Batch presence | PSNAWP `Client.get_presences(account_ids)` | Several requested accounts | Batch size, privacy and partial results unverified |
| Current title | `basicPresence.gameTitleInfoList` | Provider-reported account activity | Not direct hardware/gameplay proof |
| Played titles | `/gamelist/v2/users/{accountId}/titles` | Account history | Units and pagination need validation |
| Recent titles | Persisted GraphQL `getUserGameList` | Account recent library/history | Operation hash/schema may change |
| Purchased/entitled titles | Persisted GraphQL `getPurchasedGameList` | Account entitlement view | Purchase vs subscription/edition ambiguous |
| Trophy records | PSNAWP trophy models | Account/title trophy set | `npCommunicationId` separate from title ID |
| Catalog detail | PSNAWP catalog enrichment | Locale/product/concept | Optional and source/rights gated |
| Artwork | `conceptIconUrl`, `npTitleIconUrl` | Provider URL per title/concept | Host, copyright, size and caching gate |

No endpoint is approved merely because another endpoint works. Maintain endpoint-specific permission, scope, rate, region and version inventory.

## 3. Normalization conventions

- **Schema:** `schema_version` integer and typed record kind; additive optional fields only within compatible version. Reject unknown required enum/shape changes safely.
- **IDs:** Opaque strings, no lossy numeric conversion, no leading-zero stripping. Namespace keys as `psn:account:<id>`, `psn:title:<id>`, `psn:trophy:<id>`, `psn:concept:<id>`, `psn:product:<id>`, `psn:entitlement:<id>` for conceptual examples; exact canonical format subject to ADR-0004 approval.
- **Time:** UTC timezone-aware ISO 8601 internally; distinguish `received_at_utc`, `provider_event_at_utc`, `lastAvailableDate`, `firstPlayedDateTime`, `lastPlayedDateTime`, `fetched_at_utc`. Never infer exact session boundaries from poll timestamps.
- **Null semantics:** `null`/missing = unknown or absent data, not zero/false/off. `[]` = provider returned empty collection only when that is verified; 403/privacy is not empty.
- **Enum normalization:** Keep original raw value in a bounded internal diagnostic/typed mapping when safe; `UNKNOWN` for unfamiliar values. Do not guess game activity from `MOBILE_APP`.
- **Validation:** Bounded string lengths, list sizes, dates, numeric ranges, UTF-8 and URL types; reject malformed records without overwriting last accepted snapshots.
- **Provenance:** Every normalized record has source, provider endpoint/operation ID, observed timestamp, account scope, freshness and validity. No raw bearer headers or unbounded provider JSON persisted.
- **Version drift:** Pin tested adapter/library revision and source fixture provenance; record changes in an evidence manifest.

## 4. Account identity DTO

```text
PsnAccountIdentity
  schema_version
  provider = "psn"
  account_id: opaque required provider-stable string
  online_id: optional mutable display name
  avatar_ref: optional provider image reference
  account_visibility: visible | restricted | unknown
  linked_at_utc: optional
  verified_at_utc: UTC
  source
```

**Mapping:** Provider `accountId` or equivalent -> `account_id` after source-specific validation; `onlineId` -> display only. Reauth returning a different stable account ID must fail; account ID is never derived from display text or a console MAC. Missing account ID blocks durable account linking, not LAN monitoring.

## 5. Presence DTO and source authority

```text
PsnPresenceObservation
  schema_version
  account_id
  online_state: ONLINE | OFFLINE | UNKNOWN | RESTRICTED
  availability: AVAILABLE | AWAY | UNAVAILABLE | UNKNOWN
  reported_platforms: set of PS4 | PS5 | MOBILE_APP | PSPC | OTHER
  last_available_at_utc: optional provider timestamp
  reported_titles: list[ReportedGameActivity]
  provider_reported_at_utc: optional
  received_at_utc: UTC
  source_generation / run_id
  privacy_state: visible | restricted | unknown
  freshness: fresh | stale | none
  source_error: optional sanitized category
```

**Rules:** Provider offline is account scope only, not physical power. A 403/blocked relationship -> RESTRICTED, never OFFLINE. Timeout/429/5xx -> source degraded/stale, not an offline transition. Last available timestamp is not a session start/end. If multiple presence records/platforms exist, do not blindly choose the first as an authoritative physical device. PS5-MQTT's first `gameTitleInfoList` entry is a reference simplification, not a universal data contract.

## 6. Reported current game DTO

```text
ReportedGameActivity
  account_id
  title_key: optional GameTitleIdentity
  display_name: optional provider string
  format_platform: optional PS4 | PS5 | OTHER
  launch_platform: optional PS4 | PS5 | OTHER
  artwork_candidates: list[ArtworkReference]
  provider_position: optional integer
  received_at_utc: UTC
  assertion_scope: provider_account
  confidence: CONFIRMED_PROVIDER_REPORT
  physical_console_id: null unless separately established
```

Map `gameTitleInfoList[].npTitleId` to the namespaced title key, `titleName` or corresponding source display field to text, `format` and `launchPlatform` independently. A PS4-format game launched on PS5 must preserve both values. The title being reported by Sony is directly observed **as a provider report**; a local console running it is inferred/ambiguous without separate evidence. Do not persist a local player/game session merely because this DTO exists.

## 7. Game title and identifier crosswalk

```text
GameTitleIdentity
  provider: psn
  namespace: npTitleId | titleId | other_explicit
  opaque_id: string
  platform_scope: optional
  region_scope: optional

GameIdentityCrosswalk
  source_identity: namespaced ID
  target_identity: namespaced ID
  relationship: exact | edition | related_concept | uncertain
  evidence_source / evidence_at_utc
  verified: boolean
```

`npCommunicationId` identifies trophy communication context; `conceptId` may group related products; `productId` identifies commercial offer/edition; `entitlementId` identifies an account right. None may silently replace a title key. One-to-many and many-to-one mappings are possible and must be supported with evidence. Never deduplicate on normalized title name, artwork URL or marketing product name alone.

## 8. Played titles, recent titles and library DTOs

```text
PlayedTitleRecord
  account_id, title_identity, display_name?
  provider_play_duration: optional numeric value
  provider_duration_unit: explicitly verified unit | UNKNOWN
  play_count: optional nonnegative integer
  first_played_at_utc?, last_played_at_utc?
  fetched_at_utc, source, pagination_context

RecentTitleRecord
  account_id, title_identity?, rank/order?, provider_last_used_at_utc?
  source, fetched_at_utc

EntitlementRecord
  account_id, entitlement_id?, product_id?, concept_id?, title_identity?
  entitlement_kind: purchased | subscription | free | trial | unknown
  current_access: active | expired | unknown
  region?, edition?, source, fetched_at_utc
```

**Critical distinctions:** A purchased/entitlement endpoint name is not proof of permanent ownership; PS Plus access can expire. Physical disc games may be played without appearing in digital entitlements. A played-title aggregate does not prove local installation or a specific console. Provider duration units and `playCount` need independently verified schemas; absent duration is unknown, not 0. Never sum Sony lifetime time into ADR-0006 locally observed duration.

**Pagination:** Cursor/offset semantics belong to source adapter; record completeness and next cursor, detect repeated pages, dedupe exact namespaced title IDs, preserve page provenance. Empty first page and authorization failure are different.

## 9. Trophy and catalog metadata DTOs

```text
TrophySetReference
  account_id?, np_communication_id
  title_identity?: verified crosswalk
  trophy_platform?, trophy_progress?, fetched_at_utc

GameCatalogRecord
  title_identity or concept/product key
  locale: BCP-47 language tag
  localized_name?, description?, publisher?, release_date?
  source, fetched_at_utc, rights_status, stale_after_utc?
  mapping_confidence
```

Trophy progress belongs to a specific account and trophy set; catalog title metadata can be shared only when licensed and keyed by locale/source. The trophy set ID must not be used as the primary game identity without a verified crosswalk. Locale change should refresh presentation metadata, not create a new game or change historical duration.

## 10. Artwork reference and safety mapping

```text
ArtworkReference
  url_or_provider_ref: source-controlled reference
  role: concept_icon | title_icon | cover | unknown
  source, fetched_at_utc, license_status
  cache_allowed: boolean | unknown
  content_type?, width?, height?, cache_expiry?
```

Provider fields `conceptIconUrl` and `npTitleIconUrl` have different context and quality; source-specific priority must be explicit and testable. Before any backend fetch/proxy, validate allowed HTTPS hosts, DNS and resolved public IP, redirects at each hop, maximum response bytes, MIME type, image dimensions, decompression bounds and cache lifetime. Do not forward Sony bearer tokens to arbitrary image hosts. An available URL is not automatically permission to redistribute or cache the image.

## 11. Cross-source reconciliation matrix

| LAN state | PSN presence | PSN game | Safe normalized conclusion |
| --- | --- | --- | --- |
| AWAKE fresh | ONLINE | Title Y | Physical console awake; account reports Y; attribution not confirmed |
| STANDBY fresh | ONLINE | Title Y | Physical standby; account active elsewhere or sampled at different time |
| UNKNOWN | ONLINE | Title Y | Account report only; physical console unknown |
| AWAKE fresh | OFFLINE | None | Console awake; account provider-offline |
| AWAKE fresh | RESTRICTED | Hidden | Console awake; PSN privacy restricted |
| Two PS5 AWAKE | ONLINE one account | Title Y | No duplication of one game's time across both |
| LAN unreachable | PSN OFFLINE | None | Physical OFF not established |
| PSN unavailable | Last-known title | Stale | Keep last-known label, never present as live |

The ADR-0005 observation envelope is the authority for freshness, generations and idempotency. The ADR-0006 ledger is the authority for bounded local session accounting. Neither should be reimplemented in the PSN adapter.

## 12. Python module and Home Assistant projection boundaries

**Conceptual, not code created:**

```text
transport/psn/presence_adapter.py -> raw validated provider data
transport/psn/catalog_adapter.py -> source-specific metadata
domain/psn_dto.py -> immutable normalized account/presence/title types
domain/identity_crosswalk.py -> audited title/edition mappings
domain/state_reconciler.py -> source-aware fact projections
persistence/catalog_repository.py -> locale/source/TTL metadata
persistence/history_repository.py -> bounded session ledger
ha/psn_entities.py -> cached HA sensor/image projections
api/psn_serializers.py -> authorized bounded WebSocket DTOs
```

Transport code never imports frontend, and HA entity getters never issue Sony requests. Domain DTOs do not contain secrets. PSN credential ownership stays in ADR-0007, storage in ADR-0008, HA entity choice in ADR-0009 and API versioning/ACL in ADR-0010. No `media_player` may imply physical console power solely from PSN account/platform status.

## 13. Error and completeness contract

```text
ProviderResult<T>
  outcome: success | partial | unavailable | restricted | unauthorized |
           rate_limited | schema_incompatible | invalid_data
  data: optional T
  fetched_at_utc
  complete: boolean
  next_cursor: optional opaque string
  retry_after_utc: optional
  source_error_code: optional sanitized code
```

403/privacy -> restricted; 401/invalid grant -> reauth; 429 -> rate limit and Retry-After; 5xx/timeout -> degraded; unexpected JSON/GraphQL errors -> schema incompatible/partial as appropriate. A partially successful batch must preserve per-account outcomes rather than treating all accounts as present or offline. Never log raw provider response bodies or tokens. The frontend receives sanitized source status and last-known timestamps.

## 14. Synthetic fixture examples

**Presence (fictional):**

```json
{
  "accountId": "SYNTHETIC_ACCOUNT_001",
  "basicPresence": {
    "availability": "available",
    "lastAvailableDate": "2026-11-05T10:00:00Z",
    "gameTitleInfoList": [
      {
        "npTitleId": "SYNTHETIC_TITLE_PS4",
        "titleName": "Example Game",
        "format": "PS4",
        "launchPlatform": "PS5",
        "npTitleIconUrl": "https://example.invalid/title.png"
      }
    ]
  }
}
```

This is an illustrative shape, **not a verified complete provider schema**. The `example.invalid` URL must never be fetched. Adapter tests need source-pinned full fixtures only when provider usage is permitted.

**Entitlement (fictional):**

```json
{
  "accountId": "SYNTHETIC_ACCOUNT_001",
  "productId": "SYNTHETIC_PRODUCT_DELUXE",
  "conceptId": "SYNTHETIC_CONCEPT",
  "entitlementType": "subscription",
  "accessStatus": "expired"
}
```

An expired subscription is not permanent ownership or current access.

## 15. Deterministic mapping acceptance matrix

| ID | Scenario | Expected |
| --- | --- | --- |
| DTO-001 | Stable account ID + changed online ID | Same canonical account |
| DTO-002 | Missing account ID | No durable link |
| DTO-003 | Two PSN accounts | Isolated DTOs and tokens |
| DTO-004 | Presence online | Account-only ONLINE |
| DTO-005 | Presence offline | No physical console OFF |
| DTO-006 | Presence 403/private | RESTRICTED, not OFFLINE |
| DTO-007 | 429/timeout | Stale last-known and backoff |
| DTO-008 | Unrecognized availability enum | UNKNOWN with bounded source diagnostic |
| DTO-009 | Empty gameTitleInfoList | No provider-reported title, not no local gaming |
| DTO-010 | Multiple gameTitleInfoList entries | Preserve order and all valid entries |
| DTO-011 | PS4 format launched on PS5 | Distinct format and launchPlatform |
| DTO-012 | Null/malformed title ID | Unknown title identity; no fake key |
| DTO-013 | Same title name, different IDs | Distinct titles |
| DTO-014 | Title and trophy ID differ | No accidental merge |
| DTO-015 | Concept/product/title one-to-many | Crosswalk evidence preserved |
| DTO-016 | Provider duration unit unknown | Do not convert or sum |
| DTO-017 | Provider duration missing | Unknown, not zero |
| DTO-018 | Played title not in digital library | Preserve played history |
| DTO-019 | Entitlement expired | No permanent ownership claim |
| DTO-020 | Disc game absent from purchases | No false missing-play conclusion |
| DTO-021 | Recently played pagination repeated page | Detect duplicate and stop safely |
| DTO-022 | Partial batch response | Per-account completeness |
| DTO-023 | GraphQL hash/schema changed | Typed degraded adapter |
| DTO-024 | Locale changes | Metadata refresh, same identity/history |
| DTO-025 | Artwork URL points to private IP | SSRF rejected |
| DTO-026 | Artwork redirect to unauthorized host | Rejected |
| DTO-027 | Oversized/decompression-bomb artwork | Rejected |
| DTO-028 | Missing artwork | Placeholder, history intact |
| DTO-029 | Two PS5s and one PSN game | Attribution ambiguous |
| DTO-030 | LAN awake + PSN offline | Both facts preserved |
| DTO-031 | Old response arrives after newer generation | Rejected |
| DTO-032 | HA restart restores cached title | Historical/stale until refreshed |
| DTO-033 | Account unlink | Remove credentials and account projections; LAN remains |
| DTO-034 | No Sony permission | PSN adapters release-disabled |
| DTO-035 | Unauthorized frontend history request | Denied without data leak |
| DTO-036 | Title HTML injection text | Safely escaped in UI |

All tests are **defined, not executed**.

## 16. Release and approval gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| G1 | SPEC-003 Sony client/endpoint authorization | BLOCKED |
| G2 | Source-pinned presence DTO fixture and version | Not verified |
| G3 | Source-pinned played/recent/purchased schemas | Not verified |
| G4 | Stable account identity and reauth mapping | Not tested |
| G5 | Title/trophy/concept/product/entitlement crosswalk tests | Not tested |
| G6 | Presence freshness and privacy behavior | Not tested |
| G7 | Provider play duration units and scope | Not verified |
| G8 | Artwork source rights, cache and SSRF review | Open |
| G9 | Multi-console attribution correctness | Not tested |
| G10 | HA entity and WebSocket API integration | Not implemented |
| G11 | Rate limiting, pagination and partial failure | Not tested |
| G12 | Authorized live account tests where permitted | Not performed |

No gate is satisfied merely by a community repository or a synthetic example. A PSN-disabled LAN release must not falsely advertise these capabilities as operational.

## 17. Open research and decisions

1. Pin the exact provider DTO schemas at permitted and tested library revisions, including the `basicPresence` nested shape.
2. Determine canonical normalization and source-scoped ID equivalence, without guessing prefixes.
3. Confirm account presence enum/platform variants and batch partial-result behavior.
4. Verify provider `playDuration` unit, nullability, scope and freshness.
5. Verify recent/purchased GraphQL pagination and edition/region mappings.
6. Establish title-to-trophy and title-to-product crosswalks from reliable evidence.
7. Decide whether multi-title presence is displayed as a list or selected primary title, preserving raw order.
8. Approve permitted artwork hosts, image rights and cache policy.
9. Finalize locale fallback, source TTLs and account unlink retention.
10. Approve final HA entity naming, permission boundaries and versioned API fields.
11. Obtain Sony authorization basis for each feature or defer it.
12. Record fixtures/test outcomes and reviewer sign-off before enabling PSN features.

## 18. References

- [Protocol 08](../protocols/08-psn-authentication.md)
- [Protocol 09](../protocols/09-psn-presence.md)
- [Protocol 10](../protocols/10-game-metadata.md)
- [SPEC-003](SPEC-003-psn-authorization-and-availability.md)
- [ADR-0004](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- https://github.com/achievements-app/psn-api
- https://github.com/isFakeAccount/psnawp
- https://github.com/FunkeyFlo/ps5-mqtt
- https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network
- https://www.playstation.com/pt-pt/legal/terms-of-service/

**Outcome:** Typed PSN account/presence/game/library/trophy/artwork mappings, 36 deterministic test cases and 12 unpassed release gates documented. No Sony API calls, credentials, runtime modules or hardware tests were performed.

## LAN-versus-PSN application/title evidence (source-triangulated 2026-11-06)

**New candidate data route:** optional `running-app-titleid` and `running-app-name` headers parsed from LAN discovery by Chiaki-ng, PS5-Wake C and older pyremoteplay; consumed by Chiaki-KM for profile selection. See [second deep audit](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md). This is **not** yet a Sony-approved API, verified current foreground game, or universally present PS5 field.

Add future `SRC-PSN-01` / `SRC-PSN-02` evidence cases: multiple PS5 awake with one reported PSN title -> account-only presence/AMBIGUOUS physical attribution; LAN `CUSA` on PS5 versus provider `npTitleId`/concept/PPSA -> preserve source/platform/ID namespace, no name-based merge. A valid physical-console LAN app field can be shown as a **reported title as-of T**, independent of a linked PSN account; it cannot identify the player or create authoritative game-playing seconds. Distinguish ABSENT/EMPTY/VALUE/INVALID local metadata and PSN PRIVATE/RESTRICTED/NO_DATA. These are new test requirements, not executed tests.

## Provider title list vs Home Assistant first-title projection — 2026-11-06

[Home Assistant Core 2026.11.0 `helpers.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/helpers.py#L110-L138) takes the first element of `gameTitleInfoList` to populate an account/platform `SessionData`. Preserve all *permitted, bounded* normalized source title candidates in the proposed PSN DTO; a first-title display policy must never be misread as provider evidence that no other title exists. Add future source trace `SRC-PSN-06` multiple returned title records and `SRC-PSN-08/09` CUSA vs provider title IDs and GraphQL persisted hash changes. Keep LAN app metadata independent. See [deep source audit §11](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md#11-deeper-psn-runtime-source-audit--token-rotation-provider-title-selection-and-independent-failures). No new test executable or user credential.
