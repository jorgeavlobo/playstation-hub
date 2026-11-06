# PlayStation Hub — LAN running-app identity, foreground evidence and game/provider boundaries

**Reviewed:** 2026-11-06
**Status:** DEEP SOURCE AUDIT / SOURCE-PINNED BEHAVIOR / NO CONSOLE VALIDATION / NOT IMPLEMENTED
**Authority:** Maintainer requires a completely first-party PlayStation Hub, zero extra installed Python/JavaScript runtime packages, no MQTT, external protocol services, PS5 console-side payloads, or Sony cloud mandatory for LAN.
**Proposed contract:** [LAN app evidence and title identity](../architecture/lan-running-app-evidence-and-title-identity-contract.md)
**Related:** Protocols 01, 02, 09, 10; ADR-0005, ADR-0006, ADR-0020, ADR-0021; SPEC-004 and SPEC-021. This is a targeted research addition, **not** a new numbered ADR/SPEC.
**Comparison baseline:** Home Assistant Core 2026.11.0 and pinned public upstream commits. No code/DDL/test/hardware access.

> Observing a header named "running-app-name" does not establish human gameplay, foreground controller focus, launched-by-player identity, installed library, purchased license, exact start/stop timestamp or game-platform equivalence. This document explicitly distinguishes those different claims.

## 1. Evidence layers — keep independent

| Level | Data | Evidence and confidence | Allowed product use |
| --- | --- | --- | --- |
| E0 | Validated LAN UDP response | Community protocol implementations + candidate sender/host ID; unauthenticated self-report | Reachability and candidate console point |
| E1 | Optional DDP \`running-app-titleid\` and/or \`running-app-name\` | Console-endpoint *reported application*, sampled at reception | Show "reported app" with last seen, title ID and confidence if fresh |
| E2 | Title-ID family/prefix (CUSA, PPSA, NPXS, etc.) | **Heuristic classification only**; naming scheme varies by platform/region | Format a namespaced identifier and candidate app classification |
| E3 | Title metadata/covers from an optional provider | Cloud or user-supplied metadata, separate provenance/canonical ID | Enrich display, not overwrite original sample identity |
| E4 | Local app appears stable across bounded identical DDP samples | Temporal interpolation under approved policy, NOT exact player interaction | *Potential* "bounded reported-app coverage" with explicit uncertainty |
| E5 | Foreground game/controller-focus evidence | Not established by ordinary DDP samples in reviewed source; would require a new independently validated source | Cannot be claimed or implemented merely from E1 |
| E6 | Exact user/player activity or human gameplay | No public verified LAN proof in inspected source | Must remain UNKNOWN, not report as measured personal playtime |
| E7 | PSN account presence and lifetime playtime | Provider-specific, account scope and privacy/authorization | Separate metrics; never automatically attribute to hardware |

**Strongest supported E1:** Optional LAN field recognition in multiple third-party parsers and *actual client use* in Chiaki-KM. Availability and semantics on an actual currently supported retail PS5 remain UNVERIFIED.

## 2. Actual source data path — follow the fields end to end

### 2.1 Chiaki-ng: DDP response → host cache → changed notification

- [Chiaki-ng \`lib/src/discovery.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L91-L139) recognizes \`running-app-titleid\` and \`running-app-name\` headers along with \`host-id\`, power response code and source metadata.
- [\`lib/include/chiaki/discovery.h\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/include/chiaki/discovery.h) declares the two fields in \`ChiakiDiscoveryHost\`, not a Sony-guaranteed app-state interface.
- [\`lib/src/discoveryservice.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discoveryservice.c#L305-L388) matches/updates cached hosts by claimed \`host-id\`, advances \`last_ping_index\` even if nothing visible changes, applies \`UPDATE_STRING\` to every optional string (including the running-app fields), and reports changed host list only if a field changes.
- **Critical semantics:** With \`UPDATE_STRING\`, an absent running-app field in a later packet is represented as a null pointer in the new response and can **clear a previously cached field**, triggering a changed notification. This is a *cache replacement behavior*, not proof that the application was closed. Do **not** copy "header absent => running app ended".
- Cache host removal after missed pings is an availability decision, not an OFF or game-closed observation. A good historical reducer must receive **all accepted samples**, not only the changed-list callback.

### 2.2 Chiaki-KM: actual UI and automatic profile consumer

Pinned [Chiaki-KM fork at \`9f84d0ba\`](https://github.com/leonanluppi/chiaki-km/tree/9f84d0baf82ac87072781f7ad0a909291c46e2b5) supplies a concrete chain:

1. [\`gui/src/discoverymanager.cpp\`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/discoverymanager.cpp#L394-L414) copies the native discovery host fields into a Qt \`DiscoveryHost\`, converting strings with \`QString::fromLocal8Bit\`; this might not match every firmware character encoding/host locale. Preserve received bytes and define explicit decoding in our own implementation rather than inheriting a locale-dependent conversion.
2. [\`gui/src/qmlbackend.cpp\` host list](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/qmlbackend.cpp#L750-L805) publishes \`app\` and \`titleId\` per discovered console.
3. [\`gui/src/qml/MainView.qml\`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/qml/MainView.qml#L298-L308) displays the app name/title ID if nonempty; this is a real user-facing local title feature.
4. [\`gui/src/qmlbackend.cpp\` updateDiscoveryHosts](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/qmlbackend.cpp#L2380-L2400) forwards app fields to an active session **only when** host IP equals session host, PS4/5 target matches, a registered host is found and the registration key matches, and source state is READY. Do not copy its network-address equality as our canonical identity, but note the extra effort to avoid sending arbitrary discovered title data to the wrong session.
5. [\`gui/src/streamsession.cpp\`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/streamsession.cpp#L1102-L1131) updates locally detected app fields and applies a **750 ms debounced input-profile change** with a generation counter to avoid previous profile timers taking effect. This is a UI/control-profile stability policy, **not** proof that gameplay lasted 750 ms or that a running-app title means foreground.
6. [\`gui/src/inputprofile.cpp\`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/inputprofile.cpp#L7-L49) maps (a) metadata unavailable -> default profile; (b) both title/name empty after discovery -> navigation profile; (c) matching name or candidate \`CUSA\` title ID -> game-specific profile. These are **software presentation heuristics**.

The active session is built from discovery metadata only when it is a *local* target and READY ([qmlbackend.cpp, session setup](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/qmlbackend.cpp#L1625-L1640)). Remote PSN session lacks equivalent local discovery metadata. **Our integration will not open Remote Play streaming merely to obtain these values**.

### 2.3 PS5-Wake: a misleading "home screen" assumption

[PS5-Wake C probe](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L461-L476):
- If status code = 200 and \`running_app_name != NULL\`, it prints the name and title ID.
- If code = 200 and \`running_app_name == NULL\`, it prints "Home Screen".
- This shows how a user-facing program **chooses to interpret missing metadata**; it is **not a separate PS5 \`home-screen-state=true\` field**.
- The code's example assumes title ID accompanies name; we should not assume the two headers are always present as a pair.
- Do **not** reproduce this inference in canonical historical data. Distinguish \`FIELD_ABSENT\` from explicit \`NO_APP\`, from \`HOME_FOREGROUND\`, and from \`LAST_KNOWN_TITLE\`.

### 2.4 Earlier independent parsers and their limitations

- [Archived \`pyremoteplay\` DDP parser, 2022](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py#L100-L145) special-cases \`running-app-name\` to avoid losing colons, but generic headers are still split on colon without maxsplit. This is old recognition of the field, not live PS5 certification.
- [Playactor DDP parser](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts#L23-L49) risks colon truncation and maps all non-620 statuses to AWAKE. Our code will use strict 200/620/UNKNOWN and split only the first header colon.
- Chiaki-KM is a fork using Chiaki's parser. Agreement across both is **shared lineage**, not two independent device captures.

## 3. Sony official evidence: a running game can be paused behind Home

[Sony PlayStation official control centre documentation](https://www.playstation.com/en-us/support/games/customize-ps5-control-center/) explicitly says some games/apps are **paused while the home screen is displayed** and can be resumed from the games home. This is important first-party product behavior that directly disproves the naïve claim that "application still running or loaded" necessarily means human active gameplay or foreground rendering.

The [official PS5 quick-start/manual](https://www.playstation.com/en-us/support/hardware/ps5-console-users-guide/) and related Sony product docs describe multiple home/media/game contexts. The DDP field \`running-app-*\` is **not defined by those Sony support pages**; do not attribute undocumented wire semantics to Sony official guidance.

Consequences:
- Showing Home during an ongoing game is not equivalent to closing/uninstalling the game.
- A title ID surviving Home is not necessarily a broken DDP response; it may describe a loaded/paused app.
- A title ID disappearing at Home could be DDP semantics or a missing optional header. Neither is proof without a controlled capture.
- Even if two identical app reports are 30s apart, at most infer **bounded reported-app continuity**, not player interaction for 30s.
- \`AWAKE\` physical console and \`ACTIVE_FOREGROUND\` human gameplay are independent dimensions.

## 4. How much more would exact foreground detection require?

A separate [PS Game State Lib](https://github.com/StonedModder/ps-game-state-lib/tree/963a0e256ab32090143d44dc7964551aca70ed77) explicitly tries to classify \`LOADED_UNKNOWN\`, \`ACTIVE_RUNNING\` and \`SUSPENDED_OR_HOME\`, using console-side process/controller focus/Shell lifecycle evidence:
- [README](https://github.com/StonedModder/ps-game-state-lib/blob/963a0e256ab32090143d44dc7964551aca70ed77/README.md) describes console-side ELF payload, loader and TCP listener;
- [\`src/fg_state.c\`](https://github.com/StonedModder/ps-game-state-lib/blob/963a0e256ab32090143d44dc7964551aca70ed77/src/fg_state.c#L366-L419) evaluates controller focus, game app-ID and Shell scene markers, and explicitly does not equate loaded process to foreground game.

**Product gate:** This requires running a **payload on the PlayStation itself** (including a compatible loader). It does NOT satisfy our independent, retail-console-friendly, no-extra-console-software Home Assistant integration requirement. Use it **only as contrasting evidence of which additional signals would be necessary**. Do NOT add it as a runtime provider, automatically deploy executables to the console, recommend modifying retail firmware, or claim the TCP payload port is an official consumer PS5 API. It may have firmware-specific instrumentation and was not tested here.

Thus, absent some separately verified passive source with equivalent foreground/interaction evidence, our first release can truthfully show reported application and bounded observations but **cannot claim precisely measured player playtime**.

## 5. Title identifiers: the actual key space is larger than CUSA/PPSA

Sources:
- [Chiaki-KM \`inputprofile.cpp\`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/inputprofile.cpp#L35-L49) uses CUSA IDs on a PS5 for PS4 backward-compatible games.
- [Community PS5 Title-ID wiki](https://www.psdevwiki.com/ps5/index.php?section=2&title=Title_ID) documents \`PPSA\`, \`NPXS\`, \`ECAS\`, \`ELAS\`, \`ELJM\` examples and regional variants. This is **community**, not a complete Sony official allocation registry.
- [Community Sony prefixes](https://consolemods.org/wiki/AV:Sony_model_prefixes) recognizes PS4 \`CUSA\` and PS5 \`PPSA\`/regional IDs, and \`NPXS\` system software. Prefix classes are heuristic and may have exceptions.
- [Source \`ps-pkg-title-renamer\`](https://github.com/bsgonzalezq/ps-pkg-title-renamer/tree/ba4676de3c0a0e21a4e74849c4eb18e692df137d) documents PS4 \`param.sfo\` and PS5 \`param.json\`, and that the same display name can correspond to separate PS4/PS5 title ID records. It is a **package metadata processing tool**, not evidence of what the DDP host transmits, a supported retail console query API or a suitable runtime PlayStation Hub dependency. Its source is GPL-3.0: do not copy.
- [psn-api played/recent/purchased game providers](https://github.com/achievements-app/psn-api/tree/1e9d9a806fcd884a4ddee8086bfe92594611da9f) expose account scope with title/content/concept/product identifiers; not guaranteed identical to the DDP running-app key.

### 5.1 Proposed title-key identity matrix

| Input identifier | Proposed identity scope | Safe inference | Prohibited inference |
| --- | --- | --- | --- |
| DDP \`CUSAxxxxx\` | Source=LAN_DDP, family=CUSA, opaque raw ID, declared platform=PS4-app | Likely PS4-format app, even on physical PS5 | That the hardware is a PS4, or same as a PS5 edition |
| DDP \`PPSAxxxxx\` | Source=LAN_DDP, family=PPSA | Likely PS5-native title | Exact SKU, entitlement, store concept ID |
| DDP \`NPXSxxxxx\` | Source=LAN_DDP, family=NPXS | Possible system/app identifier requiring classification | Automatically count as a user-playing game |
| DDP \`ELJM/ECAS/ELAS/other\` | Source=LAN_DDP, family recognized or UNKNOWN | Regional/format candidate | Reject as invalid solely for not being CUSA/PPSA |
| DDP unknown string | Source=LAN_DDP, \`OTHER\`, original raw key preserved (bounded) | It is an opaque claimed app ID | Declare app absent/invalid because prefix unfamiliar |
| DDP title name only | Source=LAN_DDP, \`ID_MISSING\`, display label only | Console reported a name at time T | Merge with title by matching text |
| PSN \`npTitleId\` / \`titleId\` | Source=PSN, explicit provider scope | Provider account/platform title identifier | Direct hardware identity or direct DDP equality |
| PSN \`conceptId\` | Source=PSN_CATALOG, concept scope | Product/catalog concept relation subject to provider evidence | Immutable local game/session primary key |
| Store \`contentId\`, \`productId\` | Store/package/catalog scope | SKU/entitlement/edition metadata | A console is currently running that content |

**Do not hardcode a closed allowlist of title families.** Separate physical console platform (PS5), app target family (could be PS4), original source ID namespace and user-friendly game concept. Prefix-based app/game/system classification is **a hint**, not a verified state. Preserve unknown future identifiers and explicit potential collisions.

**Canonical proposal:** \`(origin, id_namespace, raw_id)\` for per-source title identity, with separate optional \`platform_hint\`, \`friendly_name\`, \`localized_labels\`, \`game_concept_relation\` and a reversible, evidence-backed mapping registry. Preserve original ID casing/raw field for audit, and optionally a validated normalized ASCII uppercase search form. Do not use formatted display names, artwork URLs or product listings as primary keys.

### 5.2 Identifier transformations and false matches to avoid

- Hyphenated and unhyphenated notation (\`PPSA-01411\` vs \`PPSA01411\`) may appear across community catalogs. Only normalize with a **source-specific, tested, reversible rule**; preserve raw form and punctuation. Do not blindly remove separators from arbitrary strings.
- A PS4 region/edition can have a different CUSA ID even when the game name matches; a PS5 upgrade may have PPSA ID. Reusing a marketing name across versions does not prove equal binary title or unique player statistics.
- Avoid assumed \`CUSA\` ↔ \`PPSA\` ↔ \`npTitleId\` ↔ \`conceptId\` ↔ \`productId\` equivalence. Relationships may be many-to-many and require independent provider authorization/metadata, manually reviewed links or original source evidence.
- Game editions, DLC, patches, installed game, licensed game, reported running app and PSN play history are **different entities**. An app title ID should not automatically create a purchase/license record or report a PSN lifetime number.
- Local naming can use the DDP reported name without cloud. Artwork/catalog enrichment is optional and cannot silently change source identity.

## 6. Proposed first-party DDP application observation DTO

This is a **logical schema**, not Python executable source or SQLite DDL:

\`\`\`text
LanRunningAppSample:
  console_owner_key           // Only after validated local console identity
  raw_host_id                 // Untrusted self-reported DDP identifier
  source_protocol             // LAN_DDP
  source_generation           // Local lifecycle, NOT on-wire nonce
  response_status             // 200/READY, 620/STANDBY, other/UNKNOWN
  received_at_utc_us          // Receiver clock point, not actual launch time
  temporal_quality            // WINDOW_ASSOCIATED_UNVERIFIED, etc.
  id_header_presence          // ABSENT | EMPTY | VALUE | INVALID
  name_header_presence        // ABSENT | EMPTY | VALUE | INVALID
  raw_title_id                // Optional bounded string, exact source provenance
  title_id_namespace          // CUSA/PPSA/NPXS/etc or OTHER/UNKNOWN
  title_id_platform_hint      // Source heuristic, not physical console platform
  raw_app_name                // Optional bounded display string
  decoded_name_encoding      // Documented decoder policy, never silent corruption
  normalized_display_title    // Optional presentation field; not identity
  app_classification          // UNKNOWN | POSSIBLE_GAME | POSSIBLE_MEDIA | POSSIBLE_SYSTEM
  foreground_evidence         // NOT_AVAILABLE for ordinary DDP observations
  player_evidence             // NOT_AVAILABLE for ordinary DDP observations
  source_validity             // ACCEPTED | QUARANTINED | REJECTED
\`\`\`

**Logical parser thresholds** (datagram max, number/length of fields, timestamp policy, allowed Unicode) must be measured and approved later. Do not choose numbers from thin air or copy upstream C buffer sizes as a universal Sony limit.

## 7. Rule table: missing fields and title transitions

| Previous accepted local sample | New accepted sample | Safe fact | Historical/game implication |
| --- | --- | --- | --- |
| None | READY + title ID/name | Title reported at T | 0 earned duration, no player |
| A at T0 | A at T1 (both app values present) | Same app twice at points, with source policy/correlation uncertainty | Optional bounded **reported-app** continuity only under separately approved B, not gameplay |
| A at T0 | B at T1 | App metadata changed somewhere in bracket | Do not assign [T0,T1) entirely to A or B |
| A at T0 | READY + app headers **ABSENT** | A no longer reported in this packet | Do not assert A closed or home; current title may become UNKNOWN/STALE |
| A at T0 | READY + explicitly EMPTY app fields | Literal empty fields observed (if accepted for firmware) | Candidate NO_APP_REPORTED, not confirmed home or exact game exit |
| A at T0 | STANDBY (regardless of app headers) | Physical standby reported at T | No new game duration across transition bracket |
| A at T0 | Failed poll / no reply | Source unavailable | Retain last-known A timestamp; do not backfill |
| A at T0 | READY + same title after hours of missing data | Report again, with discontinuity | UNKNOWN gap, not uninterrupted play |
| A at T0 | READY + name changed but ID same | Display label/locale changed or source disagreement | Don't necessarily split title identity by name |
| A at T0 | READY + ID changed but name same | Could be another edition/platform/SKU | Do not merge sessions by marketing name |
| PSN account reports title X | LAN reports title Y | Two source-scoped observations | No automatic trust override or player/console attribution |

**UI labels proposed:** \`Last console-reported application\`, \`Reported as of <time>\`, \`Source: Local network\`, \`Application identity unverified\`, \`Game activity not measured\`. A display can show a likely game but must never silently label it "played continuously for X hours" without the explicit interval-quality scope.

## 8. Future validation matrix — all NOT_RUN

| Trace | Scenario | Evidence requirement / expected conservative result |
| --- | --- | --- |
| LAT-01 | PS5 awake on games home, no title opened | Determine whether DDP emits absent, empty or stale running-app headers |
| LAT-02 | PS5 game launched, active input in foreground | Observe both DDP fields, first report delay, casing, title namespace |
| LAT-03 | Home button while game remains loaded/paused | Determine whether ID persists/clears; **do not** assume foreground |
| LAT-04 | Switch game A to game B | Record sampling bracket, app-ID changes, header absence |
| LAT-05 | Open media streaming application | Determine whether DDP reports non-game app and non-CUSA/PPSA title |
| LAT-06 | Run backwards-compatible PS4 CUSA game on PS5 | Preserve CUSA family despite physical PS5 |
| LAT-07 | Native PS5 PPSA game | Confirm observed actual raw ID and normalization |
| LAT-08 | System app NPXS or regional ELJM/ECAS/ELAS | Preserve type and classification ambiguity, no false gaming |
| LAT-09 | App title with colon, Unicode and changing locale | Preserve parser bytes/value and safe display encoding |
| LAT-10 | Both title/name missing, only name present, only ID present | Separate field presence/identity states, no fake home |
| LAT-11 | A to B switch between sparse samples | UNKNOWN bracket / bounded claimed app, no exact transition claim |
| LAT-12 | Same ID, name changes after game update | Stable source identity; separate localized label revision |
| LAT-13 | Same display name, different CUSA/PPSA IDs | Distinct source identities; optional audited relation only |
| LAT-14 | PSN offline/unconfigured while LAN available | Local reported title feature remains independent |
| LAT-15 | PSN reports title X, physical DDP reports Y | Independent facts, no automatic merge/player attribution |
| LAT-16 | Multiple PS5 awake with distinct titles | Unique physical scopes, no first-awake heuristic |
| LAT-17 | Timeout, delayed UDP, source-generation swap | Last-known/staleness; no backdated exact state |
| LAT-18 | Game A remains loaded while home/UI foreground | Demonstrate why DDP-only != actual foreground gameplay |
| LAT-19 | Age threshold/continuity budget B exceeded | Current title becomes stale, covered seconds stop |
| LAT-20 | Malformed/self-spoofed title ID/name and host ID | Quarantine/escape; no owner or game identity overwrite |
| LAT-21 | Unknown title prefix/new firmware naming | Preserve opaque source ID without rejecting valid device |
| LAT-22 | Deliberate console title rename and artwork change | Original observation/time unaffected; metadata is versioned |
| LAT-23 | Provider game concept links many platform editions | Distinct app title IDs remain distinct; no loss of provenance |
| LAT-24 | Normal retail PS5 with no installed console-side payload | Only passive DDP capability exposed; foreground classification unknown |

Future tests must separately record firmware version, physical owner, local interface/topology, exact accepted byte payload (redacted), Python/HA version, source clock, result, and whether a console screen capture/manual observation actually verifies foreground. These trace IDs are **qualitative additions to existing SPEC-001/004/021**, not new runnable tests, not 24 passed checks and not a new SPEC number.

## 9. Research decision and next stage

**Recommended source contract (PROPOSED, not implemented):**
1. First-party native LAN parser always retains optional running-app ID/name as independent source fields, with source/identity/time/quality and absence classification.
2. Current UI may display "console-reported app" when fresh; a probable game badge can be heuristic if clearly qualified.
3. No official duration claiming actual foreground human gameplay from DDP alone. Optional bounded reported-app coverage requires separately approved policy, hardware validation and exact uncertainty labels.
4. Keep \`title namespace + source identity + raw ID\` separate from PSN/Store concept/SKU IDs and from the physical console type.
5. Do not require Sony authentication, third-party PlayStation Python packages or on-console payloads to expose basic LAN game metadata.
6. Additional runtime/payload methods to detect process/controller foreground are **out of scope**, not fallback dependencies.
7. Update existing Protocol 02/10, ADR-0005/0021, SPEC-004/021 and Bible. No new ADR/SPEC or generic backup study.

**Next genuine unknown:** actual consumer PS5 DDP response behavior across real firmware/home/app/game/background/rest scenarios. Source reading can specify test questions, but **cannot resolve physical semantics** without controlled hardware observations. If implementation remains disallowed, the research must remain epistemically honest rather than inventing answers.

## 10. References

1. [Chiaki-ng DDP parser](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c)
2. [Chiaki-ng DDP host cache](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discoveryservice.c)
3. [Chiaki-KM dynamic update and profile control](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/qmlbackend.cpp)
4. [Chiaki-KM profile stability debounce](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/streamsession.cpp)
5. [PS5-Wake C DDP probe](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c)
6. [Archived pyremoteplay](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py)
7. [Sony official PS5 control center](https://www.playstation.com/en-us/support/games/customize-ps5-control-center/)
8. [Community PS5 title IDs](https://www.psdevwiki.com/ps5/index.php?section=2&title=Title_ID)
9. [Community Sony model/identifier prefixes](https://consolemods.org/wiki/AV:Sony_model_prefixes)
10. [PS Game State Lib payload-only foreground instrumentation](https://github.com/StonedModder/ps-game-state-lib/tree/963a0e256ab32090143d44dc7964551aca70ed77)
11. [Package metadata title/edition identity contrast](https://github.com/bsgonzalezq/ps-pkg-title-renamer/tree/ba4676de3c0a0e21a4e74849c4eb18e692df137d)
12. [psn-api provider title scopes](https://github.com/achievements-app/psn-api/tree/1e9d9a806fcd884a4ddee8086bfe92594611da9f)

**Final verification state:** This was a read-only upstream source and official Sony feature review. No real console packet, PSN call, device pairing, Home Assistant deployment, code, database or test run was performed.
