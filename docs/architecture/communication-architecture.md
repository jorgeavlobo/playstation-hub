# Communication architecture

**Status:** Planning — 2026-11-05.

## Data flow

PS5 LAN → discovery/status adapter → normalized console observation.

Optional Remote Play pairing/control → authenticated command adapter → fresh LAN confirmation.

Optional PSN presence → account observation → game metadata and player association with explicit confidence.

Normalized observations → state fusion → session tracker → SQLite / native HA entities → sidebar panel.

## Rules

- No third-party runtime bridge service.
- LAN monitoring must remain useful without PSN.
- Each transport has its own timeouts, credentials, lifecycle and failure status.
- No optimistic success on sending a command.
- Avoid mixing PS4 Second Screen and PS5 Remote Play wire formats.
- Keep the event loop non-blocking and allow multiple consoles.

See [protocol index](../protocols/README.md).

## Home Assistant Core PlayStation Network reference audit — 2026-11-05

**Status: source review; no implementation or device test.** Relevant upstream source: [Core PlayStation Network integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network), [official integration documentation](https://www.home-assistant.io/integrations/playstation_network/), [Home Assistant discovery guidance](https://contributors.home-assistant.io/core/integrations/discovery/).

- **SOURCE-CONFIRMED:** The official `playstation_network/manifest.json` declares DHCP matchers for multiple Sony MAC prefixes and `ps5-*`, `ps4-*`, `ps3` hostnames. HA's DHCP integration drives potential discovery opportunities and the official integration documentation confirms users can see it under **Discovered**. Its reviewed `config_flow.py` does not explicitly implement `async_step_dhcp`; verify exact Core discovery-to-flow dispatch and add a focused discovery test before copying this pattern.
- **SOURCE-CONFIRMED:** Official `config_flow.py` accepts user-supplied NPSSO, resolves stable account ID, blocks duplicate account entries, supports reauth/reconfigure, and has friend config subentries. This **does not** automate initial NPSSO browser capture.
- **SOURCE-CONFIRMED:** The official manifest pins `PSNAWP==3.0.3` and defines `cloud_polling`. Main PSN data polling is ~30 seconds; friend status is at least 180 seconds (adjusted for number of configured friends), group and friend list refresh ~3 hours, trophy title refresh ~24 hours. These are reference frequencies, not mandatory PlayStation Hub polling settings.
- **SOURCE-CONFIRMED:** Official Home Assistant provides media players, sensors, binary sensors, image entities and notify entities for account/game activity, trophy counts, PS Plus, profile images, friends and groups. See upstream `media_player.py`, `sensor.py`, `binary_sensor.py`, `image.py`, and `notify.py`.
- **CRITICAL LIMITATION:** Upstream media-player unique IDs combine PSN account ID with platform type. This is a PSN activity view, **not proof of unique physical-console identity**. Official HA documentation states PSN may only show activity for the last-used device. PlayStation Hub must identify consoles separately using validated local observations and only reconcile PSN presence with explicit uncertainty.
- **DESIGN DIRECTION:** PlayStation Hub should offer its own **Discovered** setup where supported, combining conservative HA-managed DHCP detection with the PlayStation-specific LAN discovery protocol (Protocol 01) for confirmation. Avoid false positives from MAC/OUI/hostname heuristics, deduplicate on validated stable console identity, handle DHCP address changes, and support manual setup if network discovery fails. Do not indiscriminately copy vendor prefixes or assume a DHCP match authenticates a console.
- **DESIGN DIRECTION:** Keep per-console physical devices and per-account PSN service identities independent in Home Assistant's device/entity registry. Multiple PS5 consoles may exist for one PSN account; a PSN platform value is insufficient to attribute gaming history to one physical device.
- **REVIEW GATES:** Inspect Home Assistant's DHCP flow dispatch, manifest discovery acceptance for custom integrations, device registry lifecycle and relevant automated tests; test simultaneous appearance of official PSN and PlayStation Hub discovery prompts, repeated discovery, unknown devices, renamed hosts and IP changes. Avoid reusing the official `playstation_network` integration domain; our planned domain is `playstation_hub`.

Full source references: [Core manifest](https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/manifest.json), [Core config flow](https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/config_flow.py), [Core media player](https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/media_player.py), [Core coordinator](https://github.com/home-assistant/core/blob/dev/homeassistant/components/playstation_network/coordinator.py), [Core config-flow tests](https://github.com/home-assistant/core/blob/dev/tests/components/playstation_network/test_config_flow.py), [Home Assistant DHCP](https://www.home-assistant.io/integrations/dhcp/).

## Detailed Home Assistant Core PlayStation Network source audit — 2026-11-05

The full 13-section, source-linked analysis is now maintained separately at [Home Assistant Core PlayStation Network — Deep Reference Audit](../research/home-assistant-core-playstation-network-audit.md). It covers manifest DHCP matchers, the Core config-flow fallback when `async_step_dhcp` is absent, multi-console implications, NPSSO and reauth, coordinators, PSNAWP, the account/platform device model, all five entity platforms, privacy, rate limits, test fixtures and architecture decisions.

**Confirmed discovery nuance:** HA's inherited `ConfigFlow.async_step_dhcp` can hand a discovered candidate to `async_step_user` when a source-specific DHCP step is absent. This default fallback is limited to an unconfigured integration / no other in-progress discovery flow. PlayStation Hub therefore needs a dedicated multi-console discovery design rather than simply copying the Core manifest. See [Home Assistant discovery guidance](https://contributors.home-assistant.io/core/integrations/discovery/) and the [Core config-flow source](https://github.com/home-assistant/core/blob/dev/homeassistant/config_entries.py).

## PSN presence research checkpoint — Protocol 09 (2026-11-05)

Detailed source evidence, endpoint parameters, normalized DTO concepts, polling, privacy and test cases are recorded in [Protocol 09](../protocols/09-psn-presence.md).

**Critical invariant:** Account online status and PSN game-title lists are cloud observations of a PSN account. They do **not** prove physical console power, unique physical console identity, game start/end timestamps, or which local PS5 is playing when multiple consoles exist. Independently confirmed LAN/Remote Play observations remain authoritative for their own narrow facts. PSN presence may enrich, but may not overwrite, local power evidence. Keep ambiguous/hidden/stale state explicit; do not invent durations or assign play to a person without sufficient source evidence.

**Research confirmed:** `psn-api` retrieves single-account `basicPresences?type=primary`; PSNAWP additionally uses platform filters, `withOwnGameTitleInfo` and an optional multi-account batch query. PS5-MQTT selects the first reported game. Official HA Core uses PSNAWP and refreshes user data approximately every 30 seconds; Sony privacy settings may restrict visibility and Home Assistant documents a rate budget of 300 requests per 15 minutes for its PSN integration. These are reference facts, not Sony-approved public API guarantees.

**Unresolved:** third-party PSN authorization, physical-console attribution for shared accounts, eventual account-vs-console device registry modeling, measured TTL/polling, and private/social-data retention.

## Game metadata, library and artwork research — Protocol 10 (2026-11-05)

The detailed source inventory, game identifier taxonomy, source-annotated metadata model, artwork safety, caching, library relationships and test matrix are recorded in [Protocol 10](../protocols/10-game-metadata.md).

**Critical data distinction:** Current game presence, provider recently played list, provider played-game history, digital entitlements, catalog details and locally measured Home Assistant sessions are six independent concepts. Purchased/PS Plus entitlements do not establish permanent ownership, installation or actual play; provider lifetime playtime cannot be silently added to local session totals.

**Identity boundaries:** Preserve `titleId`/`npTitleId`, trophy `npCommunicationId`, catalog `conceptId`, commercial `productId` and account `entitlementId` as distinct namespaces with audited crosswalks; never deduplicate using title text or a shared image URL alone. `format` and `launchPlatform` are software/platform facts, not unique physical hardware identifiers.

**Security/legal gates:** Optional PSN library/GraphQL access remains subject to Protocol 08's Sony-client authorization blocker. Remote artwork must pass host/size/type validation and licensing review; do not assume a remote cover URL permits copying or public redistribution. Preserve LAN-only operation regardless of Sony cloud or metadata failures.
