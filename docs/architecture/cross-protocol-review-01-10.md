# PlayStation Hub — Cross-protocol architecture review (Protocols 01–10)

**Review date:** 2026-11-05  
**Status:** Research audit; **no executable integration, PS5 live testing or implementation**  
**Scope:** Current `main` protocol documents 01–10; architecture, communication/security, decisions, HA Core reference audit and historical `develop` patterns.  
**Authoritative branch for research:** `main`; `next` remains future implementation work, `develop` remains frozen legacy reference.  
**Purpose:** Find contradictions, missing interfaces, lifecycle gaps, competing source semantics, prerequisites, unresolved decisions and acceptance criteria **before starting implementation**.

**Evidence taxonomy:**

- **VERIFIED IN PROJECT DOCUMENTATION:** Precisely stated in our current repository, not validated on hardware.
- **UPSTREAM-SOURCE OBSERVED:** Confirmed by reviewed reference source; not an official Sony guarantee.
- **HA-OFFICIAL:** Published Home Assistant development guidance.
- **PROPOSED:** Engineering recommendation, not yet approved.
- **BLOCKED:** A legal/provider/security dependency preventing an indicated feature from shipping.
- **LIVE-UNVERIFIED:** Needs authorized device/account test and target Home Assistant OS compatibility testing.

A detailed document is not a working implementation. A source-derived wire protocol is not a Sony-approved third-party API. These distinctions apply to **every** item in this review.

## 1. Executive verdict and scope control

**Finding:** The ten documents form a credible research base and clearly separate LAN, authenticated Remote Play, PSN authentication/presence and game catalog behavior. However, they are **not a complete implementation specification**. Ten areas remain cross-cutting architecture gates: (1) config-entry/identity ownership; (2) source-observation envelope; (3) session counting; (4) consent and secrets; (5) scheduling and network access; (6) persistence/backup; (7) HA entity/action lifecycle; (8) sidebar API/front-end/auth; (9) operational diagnostics/privacy; and (10) release and CI validation. All need explicit contracts and test fixtures.

**No change to established project scope:** One HACS custom integration, one multilingual sidebar panel, independently useful LAN monitoring, no mandatory MQTT, PS5-MQTT, Supervisor App/add-on, standalone server, or browser companion. PSN enrichment and Remote Play pairing are independent optional capabilities. The release must be genuinely functional and tested; no empty placeholder packaging.

**Priority definitions:** P0 = blocks a safe architecture or a proposed release scope; P1 = must be resolved before implementing the affected subsystem; P2 = improves maturity and user experience; P3 = later extension.

## 2. Protocol dependency map and primary ownership

| Protocol | Main responsibility | Depends on | Must not own | Main open gate |
| --- | --- | --- | --- | --- |
| P01 — LAN discovery | Probe, parse and identify local consoles | HA network access, LAN transport | Session accounting, PSN account | Stable identity and interface/broadcast strategy |
| P02 — console status | Normalize local status and freshness | P01 address/identity and status responses | PSN presence, UI media state | Response-code coverage, TTL and clock policy |
| P03 — wake | Explicitly wake a paired target | P01/P02 + P04 credentials | Automatic wake during discovery | `user-credential` derivation and confirmation |
| P04 — registration | Authorized Remote Play pairing | P01 device, user PIN + P05 | Cloud PSN token refresh | Exact credential mapping and safe storage |
| P05 — crypto | Typed crypto primitives, framing invariants | Reviewed upstream protocol references | User setup, sockets, mutable global state | Known-answer vectors, table provenance |
| P06 — session | Bounded authenticated Remote Play session | P04/P05, network I/O | Long-lived passive monitor, PSN account | Handshake/heartbeat/retry/cancellation |
| P07 — commands | Authorized wake/standby action and confirmation | P02/P03/P06 | Unconfirmed power states and optimistic success | Confirmation, concurrency and HA action semantics |
| P08 — PSN auth | Account authorization, token lifecycle | Provider-supported authorization, protected persistence | Physical console identity or LAN availability | Sony client entitlement; rotation durability |
| P09 — PSN presence | Account/platform/game observations | P08 tokens; polling budget | Physical device identity or exact durations | Privacy, TTL, cross-source attribution |
| P10 — game metadata | Catalog, IDs, digital entitlements, artwork | P08 for protected cloud routes, P09 for active title | Measured session ownership | Identifier crosswalk, rights, caching |

**Proposed dependency rule:** Protocol transports should depend on pure typed/domain contracts and account-scoped infrastructure, not on sibling protocol implementation classes directly. The domain reconciler consumes versioned, timestamped observations. Persistence and HA adapter layers sit beyond the domain core. The frontend consumes a secured, stable HA API, not provider endpoints.

### 2.1 Proposed topological implementation order (not a timeline)

```text
Core models / IDs / errors / observation envelope
  -> configuration & discovery identities + network access
      -> LAN discovery (01), state normalization (02)
      -> Remote Play registration (04) + crypto (05)
          -> wake (03) / session (06) / commands (07)
  -> independent PSN client authorization/security gate (08)
      -> presence (09)
      -> catalog and entitlement metadata (10)
  -> source reconciler -> event/session ledger -> HA entities/actions
  -> HA WebSocket/HTTP backend API -> versioned sidebar frontend
```

P03 can be specified before P04 but cannot be implemented correctly if its credential derivation depends on P04. P08–P10 are optional and may remain unavailable in a LAN-only release if authorization is blocked. Code must not make remote PSN availability a prerequisite for loading local console entries.

## 3. Cross-protocol findings register

| ID | Priority | Finding | Affected | Required close-out |
| --- | --- | --- | --- | --- |
| X-001 | **P0** | No approved physical-console/account/config-entry ownership and unique-ID policy | 01–04, 08–10, HA devices | ADR for per-console entries, account entries, multi-console dedupe and account associations |
| X-002 | **P0** | Conflicting interpretation risk: PSN account/game platform vs physical console state | 02, 07, 09, 10 | A single source-of-truth/authority matrix and reconciler contract |
| X-003 | **P0** | No unified session start/end/uncertainty accounting contract | 02, 07, 09, 10, historical code | Event/session ADR, gap policy, exact vs estimated time semantics |
| X-004 | **P0** | Remote Play credential derivation and crypto compatibility need independent proof | 03–07 | Synthetic known-answer fixtures, field-by-field crosswalk and test hardware gate |
| X-005 | **P0 BLOCKED for PSN** | No confirmed Sony-permitted client/redirect/scope/API use | 08–10 | Approved authorization/terms evidence, or omit PSN from release scope |
| X-006 | **P0** | Persistence architecture is still proposed despite target SQLite appearing elsewhere as assumed | 02, 08–10, ADR-0003 | Explicit storage ADR and backup/migration/recovery prototype plan |
| X-007 | **P0** | HA discovery's generic DHCP fallback may not support onboarding multiple separate consoles | 01, HA Core audit | Dedicated `async_step_dhcp` design plus stable-identity tests |
| X-008 | **P1** | Conflicting time/freshness conventions and absent common observation envelope | 01–03, 07, 09–10 | Typed envelope with source, receive time, generation, trust, device/account scope |
| X-009 | **P1** | No unified error taxonomy across LAN, Remote Play, PSN and storage | 01–10 | Domain failures with typed retryability, user remedy and privacy-safe diagnostics |
| X-010 | **P1** | Shared scheduling/rate/timeout/cancellation ownership not defined | 01–10 | Poll/command scheduler, account budgets, per-console locks and unload lifecycle |
| X-011 | **P1** | Multi-account PSN refresh plus API budget and privacy need a single security boundary | 08–10 | Per-account token manager/credential repository and permission model |
| X-012 | **P1** | HA entities/actions and native automation semantics insufficiently specified | 02, 03, 07, 09, 10 | Entity matrix, action authorization, availability semantics, stable unique IDs |
| X-013 | **P1** | Frontend panel has no finalized HA registration, WS API or translation/caching contract | All consumers | Frontend/backend API ADR, security and lifecycle tests |
| X-014 | **P1** | Device, credential, cache and history removal/restore lifecycle differs by scope | 01–10 | Explicit uninstall vs unlink vs unpair vs remove-device behavior |
| X-015 | **P1** | Metadata/remote-artwork security and rights requirements remain conditional | 09–10 | Allowed asset sources, SSRF defense, license and expiry/cache review |
| X-016 | **P1** | No exact supported HA Core baseline and release-compatibility matrix | Entire system | Version target, feature-gated HA APIs, HACS/Hassfest matrix and CI |
| X-017 | **P1** | Old project assumptions may leak into new architecture (MQTT topic/player/timezone/hardware) | `develop` -> `next` | Audit and re-implement pure logic only, fixtures without private data |
| X-018 | **P2** | No unified diagnostics, telemetry minimalism or support bundle format | All | Redaction and sanitized counters/error classification |
| X-019 | **P2** | Child accounts and social/playing privacy retention not fully scoped | 08–10 | Opt-in controls, data minimization, unlink/delete policy |
| X-020 | **P2** | Protocol sources pinned historically but live source branches move | 01–10 | Versioned evidence manifests and compatibility-change review |
| X-021 | **P2** | Relative UI localization and date/calendar policies need central ownership | Sidebar, sessions, metadata | i18n source/locale/fallback and UTC-to-local rendering policy |
| X-022 | **P2** | Feature promise 'does everything Core integration does and more' is unverified | All | Feature parity inventory and individual authorization/tests before release |

## 4. Identity ownership, multi-console and config-entry architecture (X-001, X-007)

**The project currently has three distinct identity axes:**

- **Physical console ID:** a trusted local/registration identifier, optionally supported by host ID and stable pairing identity; independent of mutable IP and DHCP hostname.
- **PSN account ID:** provider-stable Sony account identifier; display `online_id` is mutable and not authoritative.
- **Game title identity:** provider + title namespace + ID (+ relevant platform/edition scope); not the same as product, concept, trophy or entitlement ID.

**PROPOSED:** Maintain a central `ConsoleRegistry`, `PsnAccountRegistry` and `AccountConsoleAssociation`. Define foreign keys and association provenance. One Sony account may be used on multiple consoles; multiple accounts may use one console.

**Need to decide** whether a separate HA config entry belongs to every physical console and every Sony account, or an integration-wide hub entry owns child devices. Do not ship a hidden singleton state store that assumes one PS5. Per-console entries make HA lifecycle/removal and rediscovery more explicit, but shared history and account associations require a coordinator/owner with well-defined lifetime. This is a proposed option, not an approved ADR.

**Discovery contract:** DHCP gives a *candidate*, not an authenticated device. Explicit `async_step_dhcp` should probe with P01 and set a unique ID only when supported identity is trustworthy. Handle duplicates across manual address entry, LAN response and DHCP; allow ignore and rediscovery without duplicate entities. If stable identity cannot be confirmed, stop and present a safe manual/uncertain setup rather than using the IP as guaranteed permanent identity.

**Test targets:** two PS5 of same model, two accounts on same console, one account on two PS5, changed DHCP lease, console replacement, factory reset, broken hostname, PS5 standby, out-of-order discoveries, HA restart and simultaneous Core `playstation_network` installation.

## 5. Unified observation, clock and source-authority contracts (X-002, X-008)

### 5.1 Proposed immutable event envelope

```text
ObservationEnvelope<T>
  schema_version: integer
  source: LAN_DISCOVERY | LAN_STATUS | REMOTE_PLAY | PSN_PRESENCE | PSN_CATALOG
  source_instance_id: stable adapter ID
  physical_console_id: optional validated ID
  account_id: optional provider ID
  requested_at_utc: optional UTC timestamp
  observed_at_utc: UTC retrieval/receipt timestamp
  provider_event_at_utc: optional timestamp (distinct semantic)
  monotonic_received: process-local elapsed clock point (never persisted)
  generation: monotonic source-instance integer
  sequence: optional provider/protocol sequence
  freshness_policy_id: named validated policy
  content: normalized typed payload
  evidence: direct | inferred | ambiguous | unknown
  diagnostic_code: optional redacted code
```

The schema is conceptual, not a committed Python or storage format. Per-source `generation` is not a global ordering across different transports. Capture latest accepted source observation independently; do not compare timestamps across systems as though they were synchronized protocol clocks. On restart, re-establish per-source generations and mark restored state historical/stale until new evidence arrives.

### 5.2 Authority matrix

| Fact | Primary evidence | Secondary evidence | Forbidden inference |
| --- | --- | --- | --- |
| Physical console reachable now | Fresh P01/P02 LAN response | Authenticated Remote Play connection | PSN account online means this PS5 is reachable |
| Physical console in standby | Fresh protocol-specific standby response | Confirmed control/transition observation | 'PSN offline' means standby |
| Physical console off | Explicitly validated local signal if such a protocol exists | None by default | Silence/timeout means off |
| PSN account online | Fresh authenticated P09 response | Other permitted PSN account observation | Hardware is powered on |
| Game being reported | Fresh P09 title entry | Metadata P10 enriches identity only | Catalog entitlement means game is running |
| Player on a particular physical console | Direct validated binding if available | Explicitly labeled inference | Same platform, game or household proves player |
| Wake/standby command success | Fresh subsequent state or explicit reliable acknowledgment | Socket send result only means submitted | TCP write or UDP send means action succeeded |
| Local usage duration | Accepted P02/session observations with stated gap policy | PSN title observation may explain title | PSN lifetime playtime is local measured duration |
| Game permanently owned/installed | Source specifically confirming this property | Digital entitlement is limited evidence | 'Purchased' API entry proves permanent ownership |

### 5.3 Freshness state machine

`UNKNOWN -> FRESH -> STALE -> UNAVAILABLE` per source. Stale last-known information remains visible only if clearly labeled as such; stale observations cannot drive safety-sensitive command preconditions or continue session clocks without an explicit estimation rule.

**Gap policy pending:** Whether to close an active session at the last confirmed checkpoint, split it at an uncertainty interval, or represent open bounded estimates after missed updates must be decided in the session ADR. Avoid contradictory behavior across restart/disconnect, lost Wi-Fi and PSN outage.

## 6. Session, statistics and history specification gap (X-003)

The legacy `develop` project has valuable work on UTC event timestamps, persistent checkpoints, conservative accounting and Europe/Lisbon reporting, but none can be copied wholesale into the async HA integration. The new domain must define:

1. **Session types:** console-awake usage, account gameplay, game-specific activity, and unattributed/unknown intervals.
2. **Session identity:** unique session ID and supported console ID; optional player account and game title IDs with confidence/provenance.
3. **Boundary semantics:** exact direct transition versus first-observed timestamp; one-half-open interval `[start,end)` and no negative or duplicate duration.
4. **Data gaps:** explicitly recorded `unknown` intervals; no silent interpolation from last online PSN value.
5. **Attribution changes:** account change, game switch, console switch, privacy change, PSN unavailable; prevent time double-counting across user and console totals.
6. **Out-of-order observations:** reject/merge by source generation and timestamp with idempotent event keys.
7. **Restart recovery:** close/reopen at last durable checkpoint or document bounded interval uncertainty; never manufacture elapsed offline time.
8. **Time zones:** persist UTC; compute daily/monthly windows in configured local timezone, including DST and leap years. Legacy Europe/Lisbon is a test case, **not a hardcoded global default** for worldwide users.
9. **Statistics authority:** provider PSN aggregate time and PlayStation Hub observed local sessions are separate datasets, never summed.
10. **Reconciliation corrections:** permit evidence-backed amendments while retaining audit/source history; don't silently rewrite player attribution when a name or metadata mapping changes.
11. **Retention:** independent policies for account metadata, image cache, raw events, detailed sessions and optional exports.
12. **Backfill/import:** migration of old `develop` user data or Sony history is optional and subject to explicit authorization and source provenance, not implied by initial setup.

**Required ADR:** `Session Accounting & Uncertainty Policy`. It must contain finite-state transitions, a deterministic event ledger and tests for missing samples, clock skew, overlap, Wi-Fi loss, Home Assistant restart, DST, power changes, privacy changes, two consoles and two players.

## 7. Remote Play and local control handshake gaps (X-004)

The chain P04 registration -> P05 cryptography -> P06 session -> P07 command needs typed field and credential contracts. P03 wake credential may originate from P04 pairing. At present several documents refer to credential and crypto sources separately without one verified byte-level contract.

**Proposed credential ownership matrix:**

| Credential | Origin | Consumer | Storage boundary |
| --- | --- | --- | --- |
| Console host identity | P01 local response | 01/02/03/04/06 | Non-secret identity metadata |
| Remote Play registration PIN | User/console, transient | P04 | Volatile; never persist |
| Remote Play registration keys and RP metadata | P04 authorized pairing | P03/P05/P06/P07 as supported | Per-console protected secret store |
| Derived wake credential | P04/P03 mapping | P03 | Per-console protected credential only if necessary |
| PSN NPSSO | Sony browser + user authorization | P08 bootstrap | Separate PSN secret policy |
| PSN access/refresh | P08 OAuth exchange | P09/P10 | Per-account protected persistence |

**Key gates:** confirm cryptographic tables' provenance and licensing, independent known-answer vectors without real user secrets, byte order and encoding, nonce/counter lifetime, packet framing/fragmentation, timeout/cancellation, passcode and pairing errors, unexpected PS5 firmware variants and definitive command-acknowledgment semantics.

Do not expose 'power off', 'restart', controller/game launch, or other commands as shipping capabilities unless a supported upstream command and reliable confirmation are demonstrated. Distinguish wake (UDP/credential) from authenticated standby (Remote Play session). Never wake or pair merely because HA discovered a MAC match.

**Security:** Do not infer that AES-CFB alone provides modern authenticated encryption. Treat protocol-authenticated traffic according to proven wire semantics, no custom cryptographic algorithm invention. A Remote Play network session should be short-lived for commands unless future requirements justify a persistent connection and its resource/power cost.

## 8. PSN conditional functionality and authorization (X-005, X-011)

P08 documents NPSSO bootstrap, refresh, OAuth client constraints, per-account serialization, crash windows, login limitations and account unlinking. P09/P10 must depend on P08 through an abstract token accessor.

**Release blocker:** No independently authorized Sony third-party OAuth client/redirect/endpoint scope has been established for PlayStation Hub. An accessible internal endpoint or community mobile-app client constant does not authorize their use in a distributed product. Decide the lawful/contractual basis before live automated use or shipping PSN features. A LAN-only release may be viable with PSN UI disabled or clearly postponed.

**Behavior contracts:**

- Account ID stable on reauth; do not replace an account with another account's token.
- One single-flight refresh per account; same result to concurrent waiters, durability acknowledged before declaring successful persistence.
- Crash between Sony rotation and local commit is not fully atomic; recovery can require reauthentication.
- Stale backup credentials may be revoked; restore must not delete history.
- NPSSO manual transfer remains the only studied fallback reliably available without extra browser tooling; authorized OAuth callback and unattended cross-origin retrieval remain unproven.
- Respect account privacy including child accounts; do not scrape around forbidden status.
- Cache/account data policy must be independent of removable console history.
- Shared per-account PSN rate budget and cancellation; avoid per-card or per-entity polling.

## 9. Persistence and backup/storage ADR gap (X-006, X-014)

**Inconsistency found:** High-level plans sometimes speak of 'our SQLite database' as settled, whereas `ADR-0003-persistence-provisional.md` and the root guide explicitly say SQLite is *proposed, not approved*. This review treats it as **OPEN** until a signed-off ADR and HA OS backup/recovery tests.

Different state classes should not share a single unversioned file by default:

| Class | Proposed owner | Requirements |
| --- | --- | --- |
| Config identities/flows and small options | HA config entries | Versioned migration, unique IDs, entity lifecycle |
| Sensitive PSN and Remote Play credentials | Reviewed protected credential repository | Per-account/console isolation, redaction, rotation, backup/removal |
| Small durable checkpoint | HA Store or equivalent approved | Versioning, write consistency, restore |
| Long history/session ledger | Dedicated application SQLite **candidate** | Async-safe writes, schema migrations, transactional integrity, backup |
| Provider catalog metadata | Cache/repository | Source & locale, TTL, revisions, bounded retention |
| Image cache | Bounded cache | Rights/SSRF/size, eviction, no leakage |
| Home Assistant entity state | HA registry and Recorder as appropriate | Native automations, meaningful availability semantics |

**Explicit decisions pending:** config-relative path and supported HA API; backup scope; SQLite WAL handling, snapshots, open transactions and database consistency; schema versions and rollback; owner of shared storage with multiple config entries; what happens on removal of one console versus full uninstall; disk-full/corrupt-database recovery; encrypted backups versus runtime-at-rest encryption; key management; import/export privacy.

**Required proof:** Three-year synthetic multi-console history workload (including dense events), crash injections, restart/recovery, concurrent reads/writes, HA backup/restore while running, WAL restore and upgrade migration. Credentials and historical play data must never reside in HACS-managed code.

## 10. Home Assistant integration lifecycle and semantics (X-012, X-016)

**Official HA guidance:** Device/integration services use UI config flows rather than required YAML. Register general integration service actions from `async_setup`, not per-entry platform setup. Target required actions at the relevant entity/device/config-entry level and require explicit target (no accidental default console). <https://developers.home-assistant.io/docs/dev_101_services/>

**P0/P1 decisions needed:**

- Minimum supported HA Core version and Python/runtime compatibility.
- `manifest.json` domain, integration type, discovery matchers, dependencies and supported `config_flow`.
- `async_setup` versus `async_setup_entry`, `async_unload_entry`, removal and reload.
- Dedicated `async_step_dhcp`, `async_step_user`, reconfigure/reauth, options, duplicate abort and ignore behavior.
- Stable `DeviceInfo.identifiers` for physical consoles and separate PSN service account entries; `via_device` linking must not conflate identities.
- Sensor/binary_sensor/switch/media_player/button entities chosen for correct **semantics**. Wake/standby are commands; don't expose a stateful switch without reliably observed reversible states.
- Unavailable vs off vs standby vs unknown distinction and Recorder impact.
- Services/actions for targeted controls, permission checks and correct exception behavior; no unauthorized automation control during discovery.
- Translation strategy: backend config flows/entities/actions/error/repair messages plus frontend i18n, English source and PT-PT (other locales staged).
- Sanitize diagnostics and repairs; separate Sony rate limits from LAN connection status.
- No network calls or disk operations from entity property getters.
- Test dynamic entity addition/removal, collisions, upgrades and cleanup when a source or account is removed.

## 11. Sidebar panel, authenticated API, frontend distribution gap (X-013, X-021)

**Current decision:** Exactly one native sidebar panel, distributed with the Python HACS integration and versioned together, no parallel Lovelace card. There is **no approved exact mechanism** for serving/registering its JS, bundles, assets, permissions, API contracts, cache busting or translations.

**Proposed design:** Python owns backend API contracts; front end sends authenticated HA WebSocket requests for bounded history, game catalogs, console/account associations and commands. Use official HA WebSocket API extension as reference, with appropriate command schema and permission checks. Avoid exposing bearer tokens and unrestricted data in browser state. Only publish user-authorized information. <https://developers.home-assistant.io/docs/frontend/extending/websocket-api>

**Needed specifications:**

1. Panel registration/unregistration and frontend build packaging for supported HA Core versions.
2. HA auth access control and endpoint-level permission checks, not just visibility in sidebar.
3. WebSocket command namespace and versioned JSON contracts; pagination/filtering and bounded payloads.
4. Subscription snapshot + incremental update semantics; reconnect and old-generation invalidation.
5. UI loads from local integration bundle; cache version tied to manifest/release.
6. i18n loading with locale fallback and no business-logic hardcoded user strings.
7. Desktop/mobile responsive layout and resilient offline/error/stale presentation.
8. Security: CSRF if using HTTP, origin/caching, safe HTML rendering (XSS), URL validation, no secrets.
9. Multi-console select and multi-account status that does not imply physical game attribution.
10. Tests for HA upgrade, panel lifecycle, browser reload, reconnection, access permissions and source disappearance.

A frontend screenshot or mock-up does **not** validate this integration contract.

## 12. Common error handling, scheduler and observability (X-009, X-010, X-018)

### 12.1 Unified error model (proposal)

```text
DomainError
  category: authentication | permission | privacy | rate_limit |
            transport | unavailable | malformed | identity |
            persistence | concurrency | incompatible | cancelled
  source: lan | remote_play | psn | storage | frontend
  retryable: boolean
  retry_after_utc: optional UTC
  user_action: none | reconnect | reauth | repair | retry | manual_setup
  diagnostic_code: bounded sanitized identifier
  correlation_id: local opaque ID
```

Map individual wire errors without confusing a provider 403, radio silence or stale observation with a physical console state. No complete raw response bodies, credentials or private account identifiers in logs. Cancellation is not an ordinary outage; unload must terminate without retrying.

### 12.2 Scheduling owner

**Proposed:** Separate per-console LAN poll/wake/session serialization from per-account PSN authentication/rate limits, with an integration-level scheduler only for shared resource caps. Use monotonic deadlines in-process, configurable backoff with jitter, bounded network concurrency, no runaway tasks and safe cancellation.

A 30-second official HA PSN poll interval is a reference, **not** a universal Sony-supported budget. UI refreshes must reuse cached coordinator observations; don't call Sony for every render. Manual refresh should obey the same budgets.

### 12.3 Diagnostics and repair

Track sanitized last-success timestamps per source, timeout counts, identity mismatch, missing permissions, token lifecycle states (never tokens), pending queue depth, retry budgets, DB migration version and relevant firmware compatibility. Consider localized repair issues for reauth, pairing reset, invalid backup and unsupported console firmware. Diagnostics must be opt-in/minimal, never expose private artwork URLs with query tokens.

## 13. Cross-protocol contradictions and clarifications

**C-01 — SQLite approval:** `ARCHITECTURE_GUIDE` and ADR-0003 say *proposed*, while some later prose uses definite storage language. **Resolution:** Continue to mark SQLite candidate until approved.

**C-02 — P03's wake dependency:** P03 appears before P04/P05 in numbering but needs pairing-derived credential. **Resolution:** Protocol numbering is for research order, not implementation dependency order.

**C-03 — Remote Play vs PSN identity:** Both involve PlayStation accounts but credentials belong to different security domains. **Resolution:** Dedicated secret types/stores and no cross-use.

**C-04 — 'Confirmed game':** P09 can confirm the PSN **reported** a game, not that the particular physical PS5 is running it. **Resolution:** Always qualify which fact was confirmed.

**C-05 — 'Console off':** Lack of LAN status and PSN offline do not prove powered off. **Resolution:** Explicit OFF requires a validated independent state source; otherwise UNKNOWN/UNAVAILABLE.

**C-06 — Provider time vs locally measured time:** Sony aggregate play duration may include activity outside monitored consoles. **Resolution:** Never aggregate it into local session measurements.

**C-07 — Browser OAuth:** Sony login in browser does not grant HA access to Sony-origin cookies. **Resolution:** Authorized redirect/callback remains blocked; assisted NPSSO remains the studied fallback.

**C-08 — Account/platform media-player devices:** Core's PSN media player does not uniquely identify a physical PS5. **Resolution:** Separate service identity and hardware devices.

**C-09 — Digital library:** Purchased list can include subscriptions/free entitlement and exclude disc titles. **Resolution:** Distinct entitlement/play/history state.

**C-10 — UI vs backend:** Planned 'instant' dashboard updates cannot bypass backend API and provider rate limits. **Resolution:** Push cached snapshots/events, never repeated direct Sony requests.

**C-11 — Project status:** Detailed protocols 01–10 are **research docs**; some claim 'decision' where acceptance is not formally recorded. **Resolution:** Link approved ADRs and mark remaining choices as proposed.

**C-12 — Domain packaging:** Root `main` currently contains documentation and `next` remains an initial implementation branch. **Resolution:** Do not infer HACS readiness or a release from documentation quality.

## 14. Recommended ADR / specification backlog

| ADR/spec ID (proposed) | Priority | Deliverable | Depends on |
| --- | --- | --- | --- |
| ADR-0004 — Identity, config-entry ownership and multi-console | P0 | Stable unique-ID plan, associations, discovery dedupe and removal semantics | P01, HA Core audit |
| ADR-0005 — Observation envelope and source authority | P0 | Domain DTO + freshness, generations, confirmation/unknown policy | P01, P02, P09 |
| ADR-0006 — Session ledger and uncertainty | P0 | Finite-state accounting, gap policy, UTC/DST, recovery tests | ADR-0005, legacy domain study |
| ADR-0007 — Credentials and token persistence | P0 | PSN/Remote Play scopes, write durability, security, auth recovery | P04, P08, Security architecture |
| ADR-0008 — Data storage and backups | P0 | Approve/replace ADR-0003; storage topology, migrations, backup and restore | ADR-0006/0007 |
| ADR-0009 — HA entity and action contracts | P1 | Device hierarchy, entity semantics, commands, HA lifecycle | ADR-0004/0005 |
| ADR-0010 — Panel/API/frontend packaging | P1 | WS/HTTP API, auth, registration and i18n; bundle/release version | ADR-0009 |
| SPEC-001 — LAN discovery acceptance matrix | P1 | DHCP and LAN fixtures, stable identity, multiple consoles | P01, ADR-0004 |
| SPEC-002 — Remote Play byte contract and safety | P0 | P03–P07 credential/nonce/framing matrix and KATs | P03–P07 |
| SPEC-003 — PSN availability & permitted use | P0 (PSN) | Client registration/rights, scopes and acceptable integrations | P08–P10 |
| SPEC-004 — PSN presence/metadata DTO mapping | P1 (PSN) | Snapshot shapes, visibility, provider ID crosswalk | P09–P10 |
| SPEC-005 — End-to-end test & CI matrix | P1 | Fixtures, HA test version, HACS/Hassfest, errors, release gates | All |
| SPEC-006 — Security/privacy threat model | P1 | Secrets, network hosts, SSRF, UI permissions, retention | ADR-0007/0008/0010 |
| SPEC-007 — Supported console/firmware matrix | P1 | Model generations, observed compatibility and unsupported features | P01–P07 |

These are **proposed names**, not existing or approved ADR files; do not silently mark them accepted. Their purpose is to track design work before coding, not to expand the scope indefinitely.

## 15. Test and quality-gate matrix

### 15.1 Pure domain/unit tests

- Observation schema versioning, source freshness, UTC/monotonic semantics and invalid values.
- Reconciler contradictory LAN/PSN states, multiple accounts/consoles, stale responses, out-of-order events.
- Session accounting and gap/DST/restart behavior; exact/inferred labels and source provenance.
- Title identity crosswalk, entitlement vs playtime and metadata/cached artwork separation.
- Credential manager concurrent refresh, rotation, persistence failure and account mismatch.

### 15.2 Transport tests

- P01 UDP frame parsing, bound ports, invalid response and host-ID verification.
- P03 wake with synthetic user credential and confirmation timeout.
- P04 registration failure/success, PIN retry and multiple pairing credentials.
- P05 cryptographic vectors, nonce/counter and fragmented packet frames.
- P06 unexpected closure, authentication failure, heartbeat, cancellation.
- P07 command serialization, ack vs observed state, target permissions.
- P08–P10 account isolation, OAuth errors, 429 budget, privacy and schema changes.

### 15.3 Home Assistant tests

- Discovered flow, multiple device entries, DHCP fallback, ignored devices, manual IP, IP change.
- Proper entity/device registries, disabled entities, translation keys, stable IDs and unique names.
- Service/action target validation and authorization.
- Async setup/unload/reload/reauth and pending task cleanup.
- Panel WebSocket authorization and reconnect.
- Persistence backup/restore, schema upgrade, disk full and corruption.
- Compatibility with official PSN integration installed simultaneously.
- HACS custom repository install, HACS Action and Hassfest with target versions.

### 15.4 Live-hardware verification, deferred

- Actual PS5 standby/awake responses and hardware stable identity under controlled firmware versions.
- Wake and Remote Play registration commands with explicit user action.
- Real network loss, DHCP address change, Home Assistant OS restart, PSN outage and firmware changes.
- Authorized PSN account tests **only after** client/API permission gate, including privacy restrictions and two-console cases.
- No real bearer secrets, account IDs or private backups committed to public repositories.

**Release claim rule:** A supported feature must have traceable source requirements, passing synthetic/HA tests, and live validation when physical behavior is asserted. Shipping a feature disabled/unsupported is not equivalent to implemented parity.

## 16. Suggested architecture review sequence

1. **Normalize requirements** into `must`, `optional`, `future` across independent LAN, Remote Play, PSN, statistics and panel.
2. **Resolve ADR-0004/0005:** physical identity, account ownership, observations, authority and freshness.
3. **Resolve ADR-0006:** durable sessions, uncertainty, attribution and legacy migration eligibility.
4. **Resolve ADR-0007/0008:** secrets, storage, rotation, SQLite candidate and HA backup architecture.
5. **Close SPEC-002:** source-trace cryptography/pairing/wake/command semantics without live secrets.
6. **Resolve ADR-0009/0010:** HA entry lifecycle, entities/actions, panel/backend API and security.
7. **Close Sony gating** for optional PSN features or formally defer them in release scope.
8. **Prepare deterministic test fixtures and CI/HACS quality gates** against a declared HA Core baseline.
9. **Only then** implement on `next` and validate live hardware; never automatically merge legacy code into new integration.

This sequence is documentation-first and may be reordered if new evidence changes dependencies. It does **not** authorize starting implementation.

## 17. Next research questions requiring explicit decisions

- What is a stable console ID in practice across firmware/models, and how do we behave when it is missing?
- Do config entries represent consoles, PSN accounts, or a global installation, and who owns database lifetime?
- How precisely is an observed game session started/stopped when PSN polling and LAN statuses disagree?
- What counts as *confirmed* user gaming versus a probable association?
- How should history handle an hour of Home Assistant being offline or a PS5 being unreachable?
- Will per-account PSN library/game history be imported, and how is it visibly differentiated from locally observed time?
- How will NPSSO/refresh rotation and paired Remote Play secrets be stored, backed up and deleted?
- Which Sony client/API permissions can legally and reliably support PSN optional features?
- What Home Assistant Core minimum version supports every needed discovery/front-end/translation API?
- Which commands are actually implementable and confirmable on which firmware versions?
- How will the one sidebar panel authenticate its WebSocket calls, handle reconnection and avoid stale UI?
- What is the accepted behavior for partial failure: LAN available but cloud unavailable; database corrupted; account unlinked; source changes?

## 18. Source register and linked canonical specifications

### Internal project specifications

- [Architecture guide](../../ARCHITECTURE_GUIDE.md)
- [Protocol index](../protocols/README.md), [01](../protocols/01-lan-discovery.md), [02](../protocols/02-console-status.md), [03](../protocols/03-console-wakeup.md), [04](../protocols/04-remote-play-registration.md), [05](../protocols/05-remote-play-cryptography.md), [06](../protocols/06-remote-play-session.md), [07](../protocols/07-remote-play-commands.md), [08](../protocols/08-psn-authentication.md), [09](../protocols/09-psn-presence.md), [10](../protocols/10-game-metadata.md).
- [First-party connectivity ADR](../decisions/ADR-0001-first-party-connectivity.md)
- [Sidebar panel ADR](../decisions/ADR-0002-sidebar-panel.md)
- [Provisional persistence ADR](../decisions/ADR-0003-persistence-provisional.md)
- [Communication architecture](communication-architecture.md)
- [Security architecture](security-architecture.md)
- [Official HA PlayStation Network audit](../research/home-assistant-core-playstation-network-audit.md)
- [Release quality gates](../release/quality-gates.md)

### Official HA development references (reviewed or linked)

- Configuration entries: https://developers.home-assistant.io/docs/config_entries_index/
- Config flows: https://developers.home-assistant.io/docs/data_entry_flow_index/
- Integration service actions: https://developers.home-assistant.io/docs/dev_101_services/
- DataUpdateCoordinator: https://developers.home-assistant.io/docs/integration_fetching_data/
- Extending WebSocket API: https://developers.home-assistant.io/docs/frontend/extending/websocket-api
- OAuth application credentials: https://developers.home-assistant.io/docs/core/platform/application_credentials
- Entities and device registry: https://developers.home-assistant.io/docs/core/entity/
- Diagnostics: https://developers.home-assistant.io/docs/core/diagnostics/
- Quality scale: https://developers.home-assistant.io/docs/core/integration-quality-scale/
- Backups: https://www.home-assistant.io/common-tasks/general/backups
- HACS publishing: https://www.hacs.xyz/docs/publish/integration/

### Key upstream references

- Playactor: https://github.com/dhleong/playactor
- PS5-MQTT: https://github.com/FunkeyFlo/ps5-mqtt
- PSNAWP: https://github.com/isFakeAccount/psnawp
- psn-api: https://github.com/achievements-app/psn-api
- HA Core PlayStation Network: https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network
- Emkraan: https://github.com/Emkraan/homeassistant-playstationnetwork
- Sony account and legal: https://www.playstation.com/pt-pt/legal/terms-of-service/

**Final audit finding:** Research is comprehensive on the ten transport topics but cross-cutting implementation contracts and release gating remain incomplete. No use of Sony credentials, device interaction, code generation or live validation occurred during this review. The next documentation work should close the proposed ADR/spec gaps rather than declaring the application ready to implement.

## ADR-0004 documentation update — 2026-11-05

The proposed identity and multi-console design is documented in [ADR-0004 — Identity, multi-console ownership and Home Assistant configuration boundaries](../decisions/ADR-0004-identity-and-multi-console-ownership.md). Preferred **unapproved** option: one HA config entry per validated physical console and separate PSN account config entries under `playstation_hub`, with a provenance-rich many-to-many account/console association registry. The ADR details candidate/verified identity, DHCP-to-LAN discovery, stable unique IDs, address changes, secure pairing targets, account disassociation, independent runtime unloading, migration, ambiguity and synthetic tests. It does not settle the physical `host-id` stability or the exact supported Core multi-entry flow behavior.

## ADR-0005 documentation update — 2026-11-05

The proposed source-authority and reconciliation contract is now in [ADR-0005 — Observation Envelope and State Reconciliation](../decisions/ADR-0005-observation-and-state-reconciliation.md). It defines source-fact authority rather than a blanket LAN/PSN priority, independent freshness and health, immutable versioned envelopes, per-run and per-request ordering, safe state projection, command verification, confidence-scoped attribution and synthetic cases. **Proposed only**. ADR-0006 must close the separate session interval/duration gap; source-specific TTLs and Home Assistant entity semantics remain subject to testing and ADR-0009.

## ADR-0006 documentation update — 2026-11-05

[ADR-0006 — Session Accounting, Temporal Uncertainty and Usage Statistics](../decisions/ADR-0006-sessions-and-usage-statistics.md) now documents the **proposed** conservative ledger and statistics boundary. It is based on reviewed legacy transactional checkpointing and half-open UTC calendar aggregation but explicitly separates observed sample events from continuous physical proof. Long gaps produce unknown coverage; same-state samples may support bounded accounting only under a separately calibrated continuity policy; state changes across samples have uncertain transition boundaries. Player/game inference and Sony lifetime time remain separate. Proposed tests cover multi-console overlap, multiple accounts, deduplication, restart/crash/backup, Lisbon DST and configurable timezone. **The legacy 90-second maximum is a reference, not adopted. SQLite and actual source confidence remain unapproved.**

## ADR-0007 documentation update — 2026-11-05

[ADR-0007 — Credential Isolation, Lifecycle, Rotation and Persistence](../decisions/ADR-0007-credentials-and-token-persistence.md) defines the proposed boundaries between PSN account bearer secrets and per-console Remote Play pairing keys, single-flight token refresh, durable versioned replacement, non-atomic provider/local rotation recovery, user-driven Sony login, safe unlink/unpair, backups, HA secret handling and synthetic acceptance tests. The exact storage backend, encryption/key-management and backup consistency are deferred to ADR-0008. Sony third-party OAuth client/endpoint permissions remain blocked. **This is a proposed design, not an implemented security control.**

## ADR-0008 documentation update — 2026-11-05

[ADR-0008 — Storage Architecture, Durability, Backup and Restore](../decisions/ADR-0008-storage-persistence-and-backup.md) evaluates HA Config Entries, Store, Recorder, dedicated SQLite, export formats and mandatory external databases. Preferred **unapproved** hybrid: HA config entries/options for setup; versioned Store for bounded JSON settings; dedicated per-installation app-owned SQLite candidate for authoritative detailed sessions; HA Recorder for eligible native metrics; independently isolated credential persistence. Key gates are atomic per-observation sessions/checkpoints, single-writer ownership, multi-console associations, schema migrations, WAL backup consistency, Home Assistant OS restore tests, privacy and crash safety. No guarantee of a custom HA backup hook was established; it must be investigated and tested. ADR-0003 remains proposed and is not superseded as accepted.

## ADR-0009 documentation update — 2026-11-05

[ADR-0009 — Home Assistant Integration, Discovery, Entities and Actions](../decisions/ADR-0009-home-assistant-integration-entities-actions.md) defines a proposed native integration model: per-console and per-account config entries, validated DHCP and manual discovery, stable device/entity IDs, independent LAN and PSN coordinators, categorical power state rather than optimistic binary switch, explicit wake/standby buttons and targeted services, permission checks, repairs, diagnostics, localization, unload/reconfigure and official PSN coexistence. Exact HA Core baseline, API compatibility, physical firmware capabilities and PSN authorization remain unverified. The sidebar/API contract is deferred to ADR-0010.

## ADR-0010 documentation update — 2026-11-05

[ADR-0010 — Single Sidebar Panel, Authenticated Backend API and Frontend Delivery](../decisions/ADR-0010-sidebar-panel-and-backend-api.md) specifies the **proposed** unified sidebar/HACS frontend delivery using supported Home Assistant panel/static asset APIs, a namespaced authenticated WebSocket facade, ACL checks, bounded history/catalog pagination, snapshot/subscription revision guarantees, reconnect/error handling, locale/theme/accessibility, versioned frontend packaging and operation security. Home Assistant's KNX integration is a source-code precedent, not evidence of PlayStation Hub runtime compatibility. All API names/DTOs are project proposals. Runtime code and live HA OS tests remain pending.

## SPEC-001 research checkpoint — 2026-11-05

[SPEC-001 — LAN Discovery Acceptance Matrix](../specifications/SPEC-001-lan-discovery-acceptance-matrix.md) defines deterministic UDP parser fixtures, HA custom integration DHCP/discovery and multi-console setup tests, network-topology scenarios, canonical host identity migration constraints, security checks and nine sign-off gates. It does not approve ADR-0004 or claim a real Home Assistant OS discovery test has passed. The next protocol-specific validation specification is SPEC-002 Remote Play Byte Contract & Safety.

## SPEC-002 research checkpoint — 2026-11-05

[SPEC-002 — Remote Play Byte Contract & Safety](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md) consolidates Protocols 03–07 transport constants, credential ownership, AES-CFB/HMAC IV, registration, persistent control socket, framed commands and standby confirmation. It defines 28 deterministic tests and twelve currently unpassed release gates. Missing source-to-byte proofs for wake credentials, registration preface, Np-AccountId and control headers remain explicit. No runtime or hardware validation occurred.

## SPEC-007 compatibility checkpoint — 2026-11-05

[SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md) documents physical console-family, firmware, LAN/Remote Play and HA OS compatibility evidence. All twelve release gates remain unpassed; no PS5 hardware has been tested by this project. The next step is formal review of proposed ADR-0004–0010 and closure of P0 blockers, not unsupported release claims.

## Formal architecture review checkpoint — 2026-11-05

The [formal review of ADR-0004–0010](formal-architecture-review-adr-0004-0010.md) consolidates 18 consistency findings, separates LAN, Remote Play and PSN release gates, and proposes WP-00–WP-08. This does not change ADR status or close hardware, storage, PSN authorization or Remote Play byte-level blockers.

## 17. 2026-11-06 independent protocol-source triangulation (current addendum)

The [second commit-pinned upstream study](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) refines the earlier ten-protocol cross-check and **takes precedence for these narrow topics**: status code mapping, header parser grammar, LAN app/title metadata, physical wake/standby command verification and source-independent session checkpoints.

**Key corrections:** (i) `ps5-remoteplay` is a port of playactor with inherited permissive non-620 AWAKE parsing, so its synthetic vectors do not independently validate firmware; Chiaki-ng and PS5-Wake use 200 READY/620 STANDBY/other UNKNOWN; (ii) playactor's split-at-every-colon can truncate names, and may leave CR in identity header values; parse first colon and canonicalize LF/CRLF; (iii) Chiaki-ng, PS5-Wake, old pyremoteplay and the operational Chiaki-KM fork recognize/use optional DDP running-app fields, allowing a **potential** LAN-only reported-title source, independent of PSN, but not verified gameplay; (iv) standby receive-loop termination is not proof of state 620, and the Python port can swallow timeout yet return success; (v) PS5-MQTT only publishes HA updates on changed/unavailable state, so history requires independent same-state observation checkpoints. Preserve the existing design: source authority per fact, no mandatory cloud/MQTT, one controller, no speculative session time. No DDL or implementation authorized.
