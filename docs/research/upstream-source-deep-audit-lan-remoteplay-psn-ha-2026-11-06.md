# PlayStation Hub — Deep audit of upstream implementation repositories (LAN, Remote Play, PSN and Home Assistant)

**Date:** 2026-11-06
**Status:** SOURCE CODE REVIEWED / DESIGN CHANGES RECOMMENDED / NO IMPLEMENTATION OR DEVICE TEST
**Scope:** Reverse-engineered protocol sources, upstream bugs, feature gaps, source authority and license risks. **Explicitly excludes another SQLite-backup research cycle.**
**Precedence:** This is a source-audit amendment to Protocols 01–10, ADR-0004/0005/0006/0020/0021 and the WP-00B research stop policy. This is **not** an authorization to implement and **not** ADR-0023 or SPEC-023.
**Target:** LAN-first native Home Assistant custom integration with one sidebar, optional independent Remote Play and PSN account features, no mandatory MQTT.

> SOURCE-OBSERVED denotes actual behavior found in code at the pinned revisions. COMMUNITY-DOCUMENTED denotes the author's docs, not a PS5 hardware guarantee. PRODUCT-PROPOSAL is our independent target. UNVERIFIED requires a PS5/HA runtime fixture, permitted PSN testing or rights review. Reading a parser that accepts a field is not evidence that **every real PS5** emits it.

## 1. Audited repositories, exact source snapshots, and utility

| Repository | Reviewed revision / version | Role | Trust and direct-reuse boundary |
| --- | --- | --- | --- |
| [dhleong/playactor](https://github.com/dhleong/playactor/tree/a9e72d67a3930a8f06455927edb547a1754ef0ac) | `a9e72d67` / 2026-11-05 | Node/TypeScript discovery, UDP wake, Remote Play registration/control, mocks | SOURCE-OBSERVED; independently test parser and library behavior, do not blindly port code |
| [FunkeyFlo/ps5-mqtt](https://github.com/FunkeyFlo/ps5-mqtt/tree/7ab3075d276f3eeecd81a3322c72231af8cd51bd) | `7ab3075d` / 2026-11-04 (v1.8.1) | HA App/add-on orchestration, multi-subnet discovery, PSN-to-device heuristic, MQTT publication, e2e tests | MIT; reuse concepts/fixtures with license notices if ever copying permitted code, **do not copy MQTT/add-on architecture** |
| [chiaki-ng/chiaki-ng](https://github.com/chiaki-ng/chiaki-ng/tree/43728af2e639fecb8a7af1cd68c29820a40de973) | `43728af2` / 2026-11-03; current canonical repository, formerly streetpea/chiaki-ng | C discovery parser, optional LAN app headers, PS5 registration/crypto and source test vectors | AGPL-3.0; **study as independent technical evidence, do not copy/link code into an independently licensed integration without explicit licensing analysis** |
| [home-assistant/core PlayStation Network](https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network) | Core `2026.11.0` official tag | Official HA component lifecycle, account entity model, PSNAWP calls, rate limits | HA integration is account-centric; **not** verified local-console identity/control |
| [achievements-app/psn-api](https://github.com/achievements-app/psn-api/tree/1e9d9a806fcd884a4ddee8086bfe92594611da9f) | `1e9d9a80` / 2026-08-15 | TypeScript unauthorized/undocumented PSN presence, played-games, devices, titles, refresh | Endpoints are community reverse engineering; source availability is not Sony permission |
| [isFakeAccount/psnawp](https://github.com/isFakeAccount/psnawp/tree/fcd7e8334495585b5a8d7502b3b527f34f9d7777) | GitHub mirror `fcd7e833` / 2026-10-25; primary development on Codeberg; PyPI 3.0.3 | Python account APIs, exceptions, token refresh, provider rate limiting | Mirror head and published package need per-version comparison; unofficial Sony calls |
| [Emkraan/homeassistant-playstationnetwork](https://github.com/Emkraan/homeassistant-playstationnetwork/tree/aecbd580c39cc00692f06cec80df4b17c02e1e63) | `aecbd580` / 2026-10-29 | Custom HA PSN refresh durability/compatibility variation | Learn failure modes; not an authority for our physical PS5 state |
| [playdirector on PyPI](https://pypi.org/project/playdirector/0.4.2/) | **0.4.2, 2026-10-25** (metadata verified); source repository not retrievable via connected GitHub API during this audit | New Python Remote Play candidate, earlier 0.3.x API included LAN running-app metadata | **Important 0.4.x breaking change:** now ships embedded pyremoteplay engine, API changed, license **GPL-3.0-only**, no longer the older MIT 0.3.0 contract. Do not pick as dependency before source/license/runtime audit |
| [iharosi/ps5-remoteplay](https://github.com/iharosi/ps5-remoteplay) | Read public README via web only, no commit-pinned code yet | Async Python PS5-only port, reports byte-exact synthetic vectors | AGPL-3.0-only; supplementary research/test-vector candidate, not copied code |

**Repository identity update:** Following `streetpea/chiaki-ng` now resolves to `chiaki-ng/chiaki-ng`. Pin the canonical new repository and commit, not a moving redirect. PSNAWP's GitHub source is explicitly a read-only mirror; do not assume a GitHub branch is the upstream source of truth.

## 2. LAN discovery: more powerful than prior project assumptions

### 2.1 Critical cross-check of HTTP-like response status

- [playactor/src/discovery/messages.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts): `code === "620" ? STANDBY : AWAKE` (lines 28–35). This silently treats unsupported, malformed-but-tokenized or future codes other than 620 as AWAKE.
- [chiaki-ng/lib/src/discovery.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L91-L139): explicitly maps **200 -> READY**, **620 -> STANDBY**, other codes -> **UNKNOWN**.
- SOURCE-OBSERVED cross-implementation consensus: `200`/READY and `620`/STANDBY are established **community parser mappings**. PRODUCT-PROPOSAL: use an allowlist `200 -> AWAKE`, `620 -> STANDBY`, otherwise `UNKNOWN` with reachability/freshness separate. Actual firmware-specific wire fixtures still required.
- The legacy Protocol 02 open question "which other codes are awake" can now be narrowed: treat no unspecified code as AWAKE without new evidence. The official Sony LED state description does NOT prove the UDP code map.

### 2.2 Unexpected LAN *running-app* fields — major functionality opportunity

The same chiaki-ng discovery parser recognizes these headers:
- `running-app-titleid` -> `ChiakiDiscoveryHost.running_app_titleid` (line ~129).
- `running-app-name` -> `ChiakiDiscoveryHost.running_app_name` (line ~131).
- Also `host-id`, `host-type`, `host-name`, `system-version`, `host-request-port` and `device-discovery-protocol-version`.

[playactor/src/discovery/udp.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L115-L126) preserves unrecognized message fields in `extras`; its `IDiscoveredDevice` model does not promote running-app fields to typed properties. Thus a PlayStation Hub normalizer **can consider parsing those fields from LAN messages** without treating them as PSN observations.

An earlier documented [playdirector v0.3.0](https://pypi.org/project/playdirector/0.3.0/) `DiscoveredDevice` advertises `running_app_name` and `running_app_titleid`; the **latest v0.4.2 API is different** and does not itself prove retention of the old public object shape. Chiaki's parser support and old playdirector docs show community recognition of the header names, **not that every PS5 firmware emits them, that the values are a playable game rather than an app, or that absence = no game**.

**Proposed high-value, narrow tests to add to existing SPEC-001/004/021 (not a new SPEC):**
- Capture synthetic headers as parsed fields, include missing/empty/unknown ID.
- On a real PS5 with a user-consented local test: compare home screen, launched game, app switch, suspended game, standby and rest-mode transition; record which fields appear and whether values identify an actual *foreground* game, app still open in background, or stale metadata.
- Compare with and without PSN linked and with LAN device discoverable, without attempting Sony-cloud endpoints.
- Scope raw LAN data to verified physical console ID, parse bounded UTF-8 and restrict display name/IDs in diagnostics. A title ID is a **console-reported metadata field** until semantics validated, not automatically an accurate measured player activity session.
- If consistently available, a future `LAN_RUNNING_APP` source may support **local console/title attribution** more strongly than provider-account PSN presence. It does not identify the player without another source.

**Product priority consequence:** Make game detection during LAN-only WP-01/03 a candidate capability; do NOT declare PSN mandatory for showing titles or build the DB on the assumption that all games require account API access.

### 2.3 Multi-subnet / multi-interface discovery: upstream production lessons

[ps5-mqtt/server/src/playactor/discovery.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/playactor/discovery.ts#L11-L125) documents two concrete operational problems:
1. A limited global IPv4 broadcast `255.255.255.255` follows OS interface routing and may not reach consoles on another directly attached subnet. The add-on computes subnet-directed broadcast targets from each local non-loopback IPv4 address/netmask, plus global broadcast, with an optional explicit override.
2. Launching one playactor Discovery per target previously added excess listeners to its **shared UDP socket**; issue #692 led to one logical discovery session with a list of ping targets, avoiding `MaxListenersExceededWarning`. The code deduplicates returned devices by ID.

**Product-proposed Python/HA behavior:** Own one network lifecycle per integration/compatible protocol, enumerate safe local IPv4 interfaces, avoid uncontrolled directed broadcast and large multicast fanout, permit explicit target IP fallback, validate interface/port, dedupe by verified physical ID, handle duplicates from changed IP and collision safely. Do **not** copy the Node listener implementation or claim broadcast crosses routers/VLAN firewalls without an available route and ACL.

**Important:** PS5-MQTT's 5-second device poll and 60-second discovery recommendations are configuration defaults, not a Home Assistant or Sony contractual interval. Deduce Home Assistant scheduler and session time budgets only after actual tests.

## 3. playactor: wake and Remote Play control are different trust levels

- [src/waker/udp.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/waker/udp.ts): PS5 UDP port `9302`, PS4 `987`; wake sends a UDP packet with credentials to the selected device. Sending is not a physical-state confirmation.
- [src/waker.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/waker.ts#L35-L85): after `WAKEUP`, discovery rechecks matching `device.id` and `AWAKE` rather than relying on a UDP write alone. A useful command confirmation model; ensure underlying parser's "non-620 AWAKE" weakness is fixed first.
- [src/remoteplay/registration.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/registration.ts): registration first sends a search/preflight packet, then authenticated encrypted request (port `9295`); a missing preflight may cause registration rejection. Treat preregistration discovery as part of the pairing contract, not merely UI convenience.
- [src/remoteplay/session.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/session.ts): session initialization fetches and checks nonce/regist key before opening codec/socket; keep version-target-specific request/response evidence separate from ready console state.
- [src/connection/remoteplay.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/connection/remoteplay.ts#L13-L16): **apparent defect at checked revision**: `RemotePlayDeviceConnection.isConnected` returns `!this.socket.isConnected`. But [src/socket/tcp.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/socket/tcp.ts) implements `isConnected = !isClosed`; the wrapper looks inverted. Validate call sites; do not cargo-cult the getter.
- The same Remote Play wrapper's `standby()` sends packet then awaits socket receive termination; a closed connection is **not** by itself proof of an observed STANDBY on the console. Require separate verified status probe for durable power timeline.
- [chiaki-ng/lib/src/regist.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c) independently describes version-aware PS5 registration, pre-search, stop/timeout and key handling; [test/rpcrypt.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/test/rpcrypt.c) includes PS5 registration IV/key known-answer tests. These are useful independent **test-vector provenance** but AGPL code/fixtures require deliberate license analysis before direct inclusion.
- Do not launch a full video-streaming client to obtain status; the product has separate LAN status and optional authenticated command flow. Never presume session creation is harmless to an active user's game session.

## 4. PS5-MQTT: critical data-attribution and scheduling differences

### 4.1 The exact activity matching heuristic is not physical proof

[ps5-mqtt/server/src/redux/sagas/update-account.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/update-account.ts):
1. It may sort the device list to prioritize a configured `preferredDevices.ps5/ps4`.
2. It finds the **first** device where `status === "AWAKE"` and `device.type === account.activity.launchPlatform`.
3. It mutates that device's activity/activePlayers list and removes the account name from other devices previously assigned.

This is useful for a convenient best-effort Lovelace display. It does NOT prove which console has the game or which player is active. The code's mutable list logic also warrants testing for account replacement, duplicate players, stale update ordering, multiple titles and concurrent devices. **Our history must retain `PSN_ACCOUNT_REPORTED_TITLE` and explicit `INFERRED_ON_CONSOLE` separately**; default no confirmed title minutes solely from this heuristic.

### 4.2 Device poll, transition and failure behavior

- [check-devices-state.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/check-devices-state.ts#L13-L61): loops through devices **sequentially** and skips publishing if state unchanged. In `transitioning` state, code uses `break` (not `continue`), potentially stopping checks for **later consoles** in that pass. In catch, sets `status: UNKNOWN`, `available: false`, and clears activity.
- [turn-on-device.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/turn-on-device.ts): after playactor wake returns, publishes AWAKE. This inherits playactor wake's discovery confirmation and permissive parser risk; there is no separate strong local protocol cross-check of unexpected response codes.
- [turn-off-device.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/turn-off-device.ts): after playactor standby returns, publishes STANDBY; as noted above, a socket closing is not necessarily a validated fresh standby observation.
- [playactor/client.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/playactor/client.ts): shell-executes the playactor CLI for discovery/check/wake/standby, uses distinct timeouts for command complexity, explicitly catches subprocess nonzero exit including timeouts. A native Python integration should **not** run one shell process per device poll or infer success from an exit code.
- [poll-devices.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/poll-devices.ts) and discovery saga are independent cyclic tasks; the UI/state publication is MQTT-specific, not evidence that MQTT is required by the Sony protocols.
- [e2e/check-devices-state.e2e.test.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/e2e/check-devices-state.e2e.test.ts): mock-backed E2E checks spontaneous status transition and unavailable on check failure. [e2e/wake-failure.e2e.test.ts](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/e2e/wake-failure.e2e.test.ts) ensures a wake failure doesn't publish success. These are **automated source test designs**, not proof our HA integration or real hardware passed.

**Improvements for PlayStation Hub:** Per-console independent bounded poll tasks; no `break` starving other devices; same device serialized, independent others concurrent; transition jobs with operation IDs and verification deadlines; source failure changes availability and halts historical continuity but never rewrites confirmed hardware state to OFF. Publish cached HA state without MQTT.

## 5. Official HA PlayStation Network and competing custom integration

### 5.1 Core 2026.11.0's deliberate account-oriented architecture

- [HA `__init__.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/__init__.py): one account client, dedicated coordinators for user data, trophy titles, groups, friends list and friend subentries; its root device is a **SERVICE device keyed to PSN account unique ID**, not a verified physical PS5 serial.
- [HA `config_flow.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/config_flow.py): receives NPSSO token, resolves Sony account ID as Config Entry unique_id, supports friend subentries and reauth. User-based account unique IDs don't replace physical console identification.
- [HA `helpers.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/helpers.py): builds user data by invoking PSNAWP account devices, presence and profile. `active_sessions` are **provider-scoped/platform-derived projections**, not direct per-hardware session logs.
- [HA `media_player.py`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/media_player.py): creates platform-type media players (PS4/PS5 etc.) associated with the account, not physical hardware IDs. Distinguish their `media_title` and state from local-device runtime sensors.
- [HA manifest](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/manifest.json) pins `PSNAWP==3.0.3` and `pyrate-limiter==4.5.1`; don't infer that GitHub PSNAWP mirror `master` is identical to the installed wheel.
- [Official HA docs](https://www.home-assistant.io/integrations/playstation_network): 30s account updates, 180s friend refresh with scaling, reported 300 requests/15min, and explicit **last-used device** limitation. Provider's last-used platform may obscure another powered console.
- [HA config-flow tests](https://github.com/home-assistant/core/blob/2026.11.0/tests/components/playstation_network/test_config_flow.py) test account unique ID and friend subentry collision; use test design for source identity/duplicates, not model its PSN account as a physical device.

### 5.2 Custom Emkraan adapter: exact integration risks

- [coordinator.py](https://github.com/Emkraan/homeassistant-playstationnetwork/blob/aecbd580c39cc00692f06cec80df4b17c02e1e63/custom_components/playstation_network/coordinator.py) has a refresh-token persistence guard for rotated credentials and classifies PSNAWP errors for HA auth/retry.
- [compat.py](https://github.com/Emkraan/homeassistant-playstationnetwork/blob/aecbd580c39cc00692f06cec80df4b17c02e1e63/custom_components/playstation_network/compat.py) monkey-patches PSNAWP exception parsing to handle flat OAuth `invalid_grant` versus structured API errors and installs a token-refresh guard.
- Lessons: token refresh can race across worker calls; error serialization/body shapes differ; provider session loss should not break LAN monitoring. However, modifying a dependency's exception class globally is not a robust isolated integration strategy for multiple account entries. Favor an explicit adapter and dependency-version-aware error classifier, if Sony access is authorized.

## 6. PSN API source findings: data is not hardware truth

- [psn-api `getBasicPresence.ts`](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/user/getBasicPresence.ts): requests `basicPresences?type=primary` and treats error objects as failures even if response status was otherwise received; provider presence is not physical device-specific.
- [psn-api `getAccountDevices.ts`](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/user/getAccountDevices.ts): lists devices **associated with an account**, not necessarily a verified currently responding LAN host, or ownership/per-minute game activity.
- [getUserPlayedGames.ts](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/user/getUserPlayedGames.ts): account title list, separate from current running title and local duration.
- [getPurchasedGames.ts](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/graphql/getPurchasedGames.ts) and [getRecentlyPlayedGames.ts](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/graphql/getRecentlyPlayedGames.ts): GraphQL persisted query hashes and response-specific structures. Hashes are version-sensitive and features require authorization; purchase != local install, recent != current.
- [PSNAWP repository](https://github.com/isFakeAccount/psnawp): documentation explicitly calls it unofficial reverse engineering, warns of rate limits and account bans, and links canonical Codeberg development. Prefer PSN **optional and independent** until authorization/ToS reviewed.
- [PyPI PSNAWP 3.0.3](https://pypi.org/project/psnawp/3.0.3/): released 2026-03-07, after yanked 3.0.2. Validate actual Python package dependency version rather than taking unpinned mirror code.
- [playdirector 0.4.2](https://pypi.org/project/playdirector/0.4.2/): older v0.3.0 MIT/asyncio façade was **replaced** by GPL-3.0-only pyremoteplay-based API in 0.4.x. Do not adopt from outdated public API examples; licensing and source accessibility gate.

## 7. Architecture impact matrix (no extra ADR required)

| Area | New finding | Action on existing contracts |
| --- | --- | --- |
| Protocol 01 LAN discovery | Multi-interface directed broadcast, one listener/scan, explicit IP fallback | Add bounded per-interface candidate discovery and dedup/collision tests |
| Protocol 02 status | Chiaki 200 READY / 620 STANDBY / default UNKNOWN corrects playactor's overly broad mapping | Make 200/620 explicit **community mapping**, future codes UNKNOWN pending firmware evidence |
| Protocol 02 + 10 game identity | `running-app-titleid` / `running-app-name` optionally in LAN response | Add **LAN_RUNNING_APP** evidence family, no PSN required as assumption, no gameplay certainty yet |
| ADR-0004 canonical identity | LAN `host-id` appears in multiple sources, but not automatically cryptographically secure | Version/identity collision gates remain; source network endpoint not stable owner key |
| Protocol 03 wake | UDP send then validated matched discovery | Don't publish success before recognized fresh status; fix permissive parser |
| Protocols 04–07 | Pair pre-search, socket closure != standby confirmation; playactor inverted connection getter | Independent state/confirmation, bounded timeout/leases, versioned crypto fixtures |
| Protocols 08–10 | PSN account, titles and game lists are distinct; account attribution heuristic is not exact | Keep PSN optional, privacy-scoped, and separate from physical LAN title facts |
| ADR-0005/0006/0021 | LAN title candidate may support stronger local title association if validated | Add optional title field to physical observation and new confidence tag, no automatic historical duration yet |
| HA integration / panel | Official HA Core provider platform entity is not physical device | Own separate verified physical entities, one sidebar, source-scoped states |
| Dependency strategy | New Python alternatives have AGPL/GPL or changed API | Perform explicit license/version review before selecting dependency; prefer clean room concepts for local parser |
| Testing roadmap | Source bugs in playactor, PS5-MQTT and release drift | Add high-value regression fixtures to existing SPEC, no arbitrary 80-test document inflation |

### New evidence quality: what we **do know** versus what remains speculative

**High confidence from pinned source:**
- Source code recognizes exactly `200`, `620`, and `UNKNOWN` in chiaki, exposes running-app header names, and PS5-MQTT's heuristic and loop `break` behavior are directly inspectable.
- Official HA Core source uses an account-rooted PSN integration and its docs warn about last-used device projection.
- playdirector latest release is 0.4.2 and explicitly GPL-3.0-only; earlier 0.3.0 materials are not valid selection guidance.

**Requires a physical fixture or independent authorization:**
- Whether a particular firmware sends LAN running-app headers, when and how quickly those change, exact semantics (foreground game vs open app) and whether sending extra polls incurs consequences.
- Whether `host-id` is stable across firmware, reset, network reconnect and hardware replacement.
- Whether a specific Remote Play sequence works consistently on user's actual PS5 and current firmware.
- Whether Sony authorizes third-party PSN use and which provider data/limits remain available.
- Whether Python dependency + license + supported HA Core/Python runtime is suitable for redistribution.

## 8. Targeted next *empirical* work, not another literature loop

Do not open a new ADR-0023 or SPEC-023. In a **future authorized WP-01/WP-02**, test these first against controlled synthetic fixtures and then live user-consented console:
1. `HTTP/1.1 200`, `620`, unexpected `503`, malformed header, missing `host-id`, unicode running-app, duplicate broadcast and delayed same-IP different device.
2. LAN running-app on home screen, game started, switched, paused/rest, offline PSN; distinguish title metadata from active game seconds.
3. Two PS5s on distinct subnets and a host with many local network interfaces; explicit IP fallback; no duplicate listeners/tasks or global blocking.
4. Wake/standby errors, slow packet/session, timeout and post-command physical confirmation; never conflate socket closure with standby.
5. Official HA entry setup/unload, source monitoring independent of entity listeners, privacy-safe diagnostics, two-console identity.
6. Only after permission/feature stage: PSN account presence, privacy/403/429, title list, automatic attribution disabled by default.

**Stop/approval rules:** This source audit constitutes a material *new capability discovery*, so it is a justified amendment under WP-00B. It does **not** reopen the general research series or force selection of a GPL/AGPL source. No code, real console polling, credential use, Remote Play session, PSN call, SQLite transaction, or hardware test took place.

## 9. Source classification and re-audit triggers

- **Authoritative baseline:** versioned GitHub source/commit links above; source-specific upstream README/CI and changelogs; HA Core 2026.11.0 tag.
- **New audit trigger:** PS5 firmware update changes response codes/headers; source repository changes license/API or essential protocol; HA Core changes discovery entry lifecycle; real test contradicts existing interpretation.
- **Do not assume:** GitHub latest source == installed package source, old package README == current package API, community repository == Sony official API, source parser == feature available on all PlayStations, license compatibility without review.
