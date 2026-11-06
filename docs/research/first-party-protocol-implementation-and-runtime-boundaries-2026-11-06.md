# PlayStation Hub — First-party protocol implementation: standard-library and Home Assistant runtime audit

**Date:** 2026-11-06
**Status:** SOURCE-REVIEWED DESIGN / NO CODE / NO LIVE TESTS
**Authority:** Explicit maintainer requirement: implement the PlayStation Hub protocols and logic ourselves, with **no third-party PlayStation runtime libraries or extra installed pip/npm runtime packages**. This requirement replaces previous proposals to select a playactor/Chiaki/PSNAWP/pyremoteplay dependency.
**Policy:** [First-party / zero additional runtime packages](../architecture/first-party-dependency-sovereignty-policy.md)
**Project:** Home Assistant native custom integration, greenfield only, one panel and multi-console, optional later Remote Play and PSN, no mandatory MQTT.
**Note:** Standard Python and supported Home Assistant Core APIs are platform prerequisites, not "zero software dependencies in the universe". Home Assistant already has transitive Python dependencies. We must not add or require new independent runtime packages.

> Third-party repositories are **read-only protocol evidence**, never code to copy, vendor, import, wrap, spawn via CLI or bundle. The inspected code, byte layouts and constants are source-derived but not Sony-endorsed. Protocol applicability to the user's current firmware remains unverified.

## 1. Pinned source register

| Source | Relevant confirmed capability or limitation |
| --- | --- |
| [HA Core 2026.11.0 network integration](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/network/__init__.py) | Native async_get_adapters, async_get_ipv4_broadcast_addresses, and source-IP helpers; no need to import netifaces/ifaddr directly |
| [HA Core 2026.11.0 aiohttp helper](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/aiohttp_client.py) | async_get_clientsession(hass) and async_create_clientsession(hass), with HA lifecycle integration |
| [HA Core 2026.11.0 WebSocket API](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/__init__.py) | async_register_command registers handlers, requires collision/owner control |
| [HA integration manifest](https://contributors.home-assistant.io/core/integrations/manifest/) | requirements = pip packages; dependencies = other HA components; custom integrations need not list packages already required by HA |
| [HA blocking operations](https://contributors.home-assistant.io/core/internals/blocking-operations/) | Blocking network/disk operations cannot run in HA event loop; use async I/O or executor |
| [Python asyncio transports](https://docs.python.org/3.14/library/asyncio-protocol.html) | Built-in UDP DatagramProtocol/transports; TCP streams via asyncio |
| [Python ssl](https://docs.python.org/3.14/library/ssl.html) | TLS sockets, NOT a general raw AES-128-CFB API |
| [Python cryptographic services](https://docs.python.org/3.14/library/crypto.html) | hashlib/HMAC/secrets built in; NO general AES encrypt/decrypt API |
| [Python sqlite3](https://docs.python.org/3.14/library/sqlite3.html) | Built-in relational ledger and transaction primitives; async call-site/worker ownership must be explicit |
| [playactor source](https://github.com/dhleong/playactor/tree/a9e72d67a3930a8f06455927edb547a1754ef0ac) | TS reference for DDP and Remote Play format, not a runtime dependency |
| [Chiaki-ng source](https://github.com/chiaki-ng/chiaki-ng/tree/43728af2e639fecb8a7af1cd68c29820a40de973) | Independent C reference, AGPL-3.0; use concepts, not copied source/key tables |
| [PS5-MQTT source](https://github.com/FunkeyFlo/ps5-mqtt/tree/7ab3075d276f3eeecd81a3322c72231af8cd51bd) | Discovery topology and functional traps; no MQTT/Node requirement for PlayStation LAN itself |
| [psn-api](https://github.com/achievements-app/psn-api/tree/1e9d9a806fcd884a4ddee8086bfe92594611da9f) / [PSNAWP mirror](https://github.com/isFakeAccount/psnawp/tree/fcd7e8334495585b5a8d7502b3b527f34f9d7777) | Unofficial Sony account endpoint knowledge; not public Sony authorization |

## 2. Runtime inventory and permitted engineering tools

### Explicit allowed categories
- **Python standard library**: asyncio, socket, struct, dataclasses, enum, typing, ipaddress, datetime/zoneinfo, time, json, logging, pathlib, sqlite3, hmac, hashlib, secrets, ssl, base64, urllib.parse (for URI parsing only), collections, contextlib, concurrent.futures, unittest.
- **Supported Home Assistant interfaces**: config entries, Config Flow, runtime_data, network integration's adapter/broadcast APIs, native entity and device registries, event helpers, Repairs, diagnostics, shared aiohttp session via Home Assistant helper, WebSocket API, integration-managed static/frontend panel.
- **Frontend**: authored in our own JavaScript ES modules/Web Components, CSS and native browser primitives; may interact with Home Assistant's documented frontend hooks, no external frontend bundle/CDN/framework needed by design.
- **Development-only test/format/release tools**: distinguish from deployed runtime. Future CI may invoke HA's supported tooling (hassfest/HACS Action) and Python unit testing, without introducing PlayStation runtime dependencies.

### Forbidden runtime categories
- No imports/installations of playactor, psnawp, psn-api, Chiaki, pyremoteplay, ps5-remoteplay, playdirector, aiosqlite, netifaces, or PlayStation status/power clients from PyPI/npm.
- No mandatory MQTT broker, Home Assistant App/add-on, extra Docker container, Node.js process, PS5-MQTT services, shelling out to playactor, child process wrappers or JS runtime to do server-side protocols.
- No copying/vendoring external GPL/AGPL code, keys, or crypto tables into the integration to evade dependency rules. Upstream ideas/packet evidence require independent implementation and source traceability; license review if any verbatim material is ever proposed.
- No package download from a CDN, third-party hosted runtime API or additional user-installed package to make LAN monitoring work.
- Do not import private, unstable Home Assistant internals for convenience when a supported public helper exists.

### Important precision
- \`manifest.json: "requirements": []\` (or omitted, subject to hassfest) targets **zero extra pip installations**, not the absence of Home Assistant's preinstalled libraries.
- \`manifest.json: "dependencies": ["network"]\` is a possible **platform-component dependency**, not a pip package. Exact required/optional declaration and hassfest import-check policy must be verified in implementation.
- Direct use of aiohttp through the supported HA \`async_get_clientsession(hass)\` helper means using an HTTP capability **already supplied and owned by Home Assistant**, not installing our own aiohttp client. It still runs on a transitive external Python package. If the maintainer literally forbids *all* third-party code even when HA already embeds it, a Home Assistant integration is inherently dependent on Home Assistant's own stack and the requirement must be scoped; do not claim otherwise.

## 3. Source-first native DDP/UDP wire contract (no external library)

### Source-derived PS5 discovery candidate

[playactor \`src/protocol.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/protocol.ts) formats:
- Start line \`SRCH * HTTP/1.1\` terminated by LF.
- Header \`device-discovery-protocol-version:00030010\` terminated by LF.
- Send using UDP to PS5 DDP destination port **9302**, determined in its \`waker/udp.ts\` and \`discovery/standard.ts\`.
- The PS4-specific reference uses UDP **987** and version \`00020020\`; separate protocol profile, not silently sent to a PS5.
[Chiaki-ng \`lib/src/discovery.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L67-L90) independently formats search with the same conceptual start line and device discovery version header.

### Source-derived status response

[Chiaki-ng response parser](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L91-L139):
- \`200\` => \`READY\` (our provisional physical \`AWAKE\` projection),
- \`620\` => \`STANDBY\`,
- Any other well-formed status => \`UNKNOWN\`, NOT awake by default.
- Candidate headers: host-id, host-type, host-name, host-request-port, device-discovery-protocol-version, system-version, running-app-titleid, running-app-name.

The decoder must not blindly reproduce [playactor messages.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts) where \`non-620=>AWAKE\`, full-colon splitting and potential untrimmed CR appear. The tests must distinguish ABSENT/EMPTY/VALUE/INVALID running-app metadata; a console-reported app name is not confirmed gaming minutes or PSN account identity.

### Proposed transport architecture
1. One integration-scope UDP discovery service, **no external protocol library**.
2. Obtain target IPv4 broadcast addresses from Home Assistant's \`network.async_get_ipv4_broadcast_addresses(hass)\`, or use an explicitly validated target IP; ensure network integration availability and user-interface adapter selection are respected.
3. Use built-in \`asyncio\` datagram endpoint and one owned socket/service per compatible protocol/binding, with bounded send deadlines, response queue and cancellation.
4. Parse replies in a pure \`bytes -> immutable normalized sample/error\` component; never write to HA entities or SQLite in \`datagram_received\`.
5. Deduplicate responses by validated physical identity and source generation, not by IP alone, and pass accepted samples through owner-specific reducer.
6. Separate discovery inventory from per-console monitor cadence; discovery does not need to restart for every UI entity access. Do not use the source's interactive 500ms sampling as an unattended recommended polling interval.
7. Filter unsafe interfaces/targets and enforce limits for hosts, datagrams, timeouts, memory, bandwidth and event-loop tasks; the exact configured numerical values remain to be measured and approved.
8. On network reload, interface changes, HA entry unload or application shutdown, close owned transports and fence callbacks before creating replacements.

**Important native network nuance:** In pinned HA Core, \`async_get_ipv4_broadcast_addresses\` includes \`255.255.255.255\` and computes configured adapter broadcasts when non-default enabled interfaces are present. It does not guarantee router/firewall forwarding or discovery across distinct routed VLANs. Do not import or use HA's internal \`ifaddr\` dependency directly.

## 4. Native wake/standby and Remote Play distinctions

**Passive discovery / status** can run entirely with stdlib + HA. Wake uses DDP \`WAKEUP\` with a pairing-derived credential; packet formatting is simple, but **credential provisioning is not**. Sending UDP does not prove the device woke. Only a fresh valid target-owned READY/200 sample confirms success.

**Standby** is an authenticated Remote Play control-session command in upstream references. The connection requires registration, per-console secrets, version-specific framing, negotiation, encrypted payloads and control frames. A TCP stream closing is not definitive physical standby. Do not implement "standby" as an imaginary uncredentialed UDP power-off command; keep it unavailable until its protocol prerequisites pass.

**Pure transport pieces possible without extra packages**: TCP \`asyncio.open_connection\`, stream readexactly, HTTP header/request framing and bounded response parser, nonce generation through \`secrets\`, SHA/HMAC via \`hashlib/hmac\`, binary integer/counter coding through \`struct\`, explicit state machines, sanitized correlation IDs, privacy checks. These are authored ourselves, but the very first real handshake must be validated against firmware and session/key behavior.

### Critical cryptography blocker under a literal no-extra-package policy

[playactor \`remoteplay/crypto/base.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/base.ts) uses \`aes-128-cfb\` and HMAC-SHA256 IV derivation; [\`socket/crypto-codec.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/socket/crypto-codec.ts) also has \`aes-128-cbc\` defaults in another codec path. The code uses Node's maintained cryptographic backend, NOT a pure JS cipher implementation. Its [\`remoteplay/crypto/keys.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/keys.ts) embeds version/device-specific transformation tables and requires provenance/licensing review.

**Python's stdlib provides hashlib/hmac/secrets and SSL/TLS, but has no general AES-128-CFB/CBC API.** The \`ssl\` module cannot be repurposed as a raw AES cipher for Remote Play. A homegrown AES implementation, copying third-party crypto tables, or calling an undocumented system OpenSSL C ABI through ctypes are **not accepted ways to satisfy the dependency constraint**.

**Consequences:** Remote Play pairing/standby crypto remains \`BLOCKED_CRYPTO_BACKEND\` under strict stdlib-only policy. Viable next-stage choices require **explicit maintainer approval**:
- Keep passive LAN status/title monitoring and no-crypto features independent; defer the encrypted Remote Play function.
- Allow one narrowly reviewed secure cryptographic primitive already available through a supported HA/runtime interface **if an appropriate supported API actually exists**, without adding a pip requirement; do not claim one exists yet.
- Relax the extra-package prohibition only for an audited minimal cryptography backend if later necessary (requires user's explicit approval). No PlayStation-specific third-party library would be used.

No claim is made that the Sony proprietary key transformations can be implemented safely/legal from publicly described protocol facts alone. The exact version-specific crypto/registration needs independent detailed acceptance tests and a permissibly sourced specification.

## 5. PSN account integration without an external PSN library

- Use a future explicit, provider-authorized account client (when Sony permits it), written in our own source; no PSNAWP, psn-api or PlayStationNetwork dependency.
- The client uses HA's managed \`async_get_clientsession(hass)\` rather than bundling a new HTTP client or using blocking stdlib \`urllib.request\` on the event loop.
- Own per-account token rotation, single-flight refresh, transport timeouts, retry/backoff limits, response schema normalization, privacy/403/429 error classification, list bounds and source freshness.
- **Critical legal limit:** published community NPSSO/OAuth endpoints and someone else's OAuth client credentials do NOT authorize us to ship a Sony account client. Do not silently copy third-party static client IDs/secrets or collect Sony passwords in Home Assistant. If authorization is unavailable, PSN feature stays not implemented/deferred, never mandatory for LAN.
- Provider account titles, recently played, entitlements and cumulative playtime are separate scopes, not physical device identity or direct game-running confirmation.

## 6. Native storage, panel and Home Assistant bridge

- \`sqlite3\` built into Python is sufficient for the logical local ledger; implement our own isolated **serialized database worker**, not \`aiosqlite\`, and never call blocking DB operations on HA's event loop. Worker ownership, drain/terminal proof, transactions and future backups are unchanged correctness gates, not a reason to add third-party packages.
- Use HA Config Flow and per-entry \`runtime_data\`, native entities and independent entry-owned monitors. A \`DataUpdateCoordinator\` listener-count lifecycle by itself must not control historical monitoring.
- Use Home Assistant WebSocket API for a private typed backend interface with server-side ACL/permissions and cursor/snapshot coherence.
- Write the sidebar as **plain JavaScript ES Modules + custom elements/CSS** bundled inside our HACS integration, not React, Vue, Vite, third-party card toolkit or runtime CDN. Source transpilation/build tooling is optional, but not required by our target design.
- HA's \`async_get_clientsession\` and native WebSocket API rely on the HA runtime; they are platform services, not extra packages declared in our manifest.

## 7. Own-code modular boundaries (design, not committed files)

\`\`\`text
custom_components/playstation_hub/
  manifest.json                              # No external pip runtime requirements
  __init__.py / config_flow.py / const.py
  domain/
    identity.py
    evidence.py
    power_state.py
    session_reducer.py
    title_sources.py
    errors.py
  transport/
    lan/
      wire.py                                # Binary/text DDP parse/format (pure)
      discovery.py                           # One asyncio UDP service, adapter aware
      monitor.py                             # Entry-owned per-console polling
      wake.py                                # Authenticated credential-dependent WAKEUP
    remote_play/
      protocol.py                            # Framing/state (future)
      registration.py                        # BLOCKED on crypto/credential proof
      crypto_backend.py                      # No custom AES; must remain unimplemented until approved
      control.py                             # BLOCKED on registration/crypto
    psn/
      client.py                              # DEFERRED until provider-authorized
      models.py
      token_manager.py
  storage/
    worker.py                                # stdlib sqlite3 in tracked owner thread (future)
    ledger.py
  api/
    websocket.py
  frontend/
    playstation-hub.js                       # Vanilla JS, no npm dependency
    playstation-hub.css
\`\`\`

These paths are illustrative module boundaries, NOT created implementation files or approval to scaffold. Avoid too many empty modules; implement by bounded work package.

## 8. Source trace and future acceptance matrix (NOT_RUN)

| Test ID | Requirement | Stage |
| --- | --- | --- |
| FIRST-01 | No extra pip packages: manifest requirements empty/omitted and no PlayStation runtime imports | Every PR/release |
| FIRST-02 | No npm/runtime frontend dependencies or CDN calls, no Node/CLI subprocess | Every PR/release |
| FIRST-03 | Native HA network adapters/broadcast behavior on HA OS including disabled adapters, multi-NIC and route constraints | WP-01/02 |
| FIRST-04 | Native asyncio UDP socket lifecycle bounded and no task leak after reload/cancel | WP-01/03 |
| FIRST-05 | Valid 200/620, unknown 503, malformed, colon, CRLF, Unicode, absent/empty running-app fields | WP-01 |
| FIRST-06 | Physical host-ID spoof/collision and same-IP replacement cannot reassign credentials or history | WP-02/03 |
| FIRST-07 | Multiple consoles monitored independently; unchanged samples are still accepted as history evidence | WP-03 |
| FIRST-08 | Wake returns CONFIRMED only after fresh 200 target-owned observation, never UDP-only | WP-03/06 |
| FIRST-09 | Standby and registration are unavailable without a vetted crypto backend and credential proof | WP-06 |
| FIRST-10 | Python stdlib AES unavailability is exposed as capability gap, not silently "solved" with custom crypto | WP-06 |
| FIRST-11 | PSN unavailable/not authorized does not change local LAN power/title monitoring | WP-07 |
| FIRST-12 | PSN token refresh single-flight and typed errors without PSNAWP | WP-07 |
| FIRST-13 | Native HA WebSocket ACL and frontend vanilla ES module; no external asset requests | WP-05 |
| FIRST-14 | stdlib sqlite3 never called blocking in HA loop; worker always fenced on shutdown | WP-04 |
| FIRST-15 | HA's native network/component dependencies verified by hassfest (no extra pip) | WP-01/release |
| FIRST-16 | Source licensing: no vendor or copy of GPL/AGPL PlayStation code/key tables/fixtures | Every PR/release |

**All status: NOT_RUN**. These are test requirements and review IDs, not executable tests or additions to the legacy total of planned cases.

## 9. Current open decisions and audit outcome

1. Does the maintainer intend **zero third-party packages additionally installed** (proposed/most practical) or literally no HA-runtime third-party internals even when used via official HA APIs (unrealistic for HA itself)? Document the latter distinction honestly, without blocking LAN.
2. Confirm \`network\` as required or after-dependency from HA's own API and hassfest behavior; do not assume \`requirements\` must contain an install.
3. Real PS5 firmware/LAN identity status and running-app fields require device tests, not assumptions.
4. Remote Play authenticated registration and standby is **conditional** on a vetted AES cryptographic backend and Sony-version-specific licensing/compatibility proof. No custom raw AES.
5. Sony provider account endpoints require authorization independently of whether we write the HTTP code ourselves.
6. No implementation has been authored, deployed, tested or authorized; no new branch, package or user device operation.

**Outcome:** The user's independence requirement is implementable for passive LAN, backend state/history and plain frontend using native Home Assistant/Python facilities, with substantial protocol code owned by PlayStation Hub. It is **not yet proven** for encrypted Remote Play under strict stdlib-only policy and not a substitute for Sony PSN authorization.

## 10. Second-pass DDP source-byte and interface audit — transport compatibility gates

The first-party strategy enables us to reason about **the wire protocol itself**, rather than selecting a library whose edge cases become ours.

### 10.1 Distinct outbound message terminators (do not assume one standard)

- [playactor \`src/protocol.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/protocol.ts) assembles UTF-8 Buffer bytes for \`SRCH * HTTP/1.1\n\` followed by \`device-discovery-protocol-version:00030010\n\`. No terminating NUL byte is explicitly added by that formatter.
- [Chiaki-ng \`lib/src/discovery.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L67-L90) formats essentially the same LF-delimited text, **but its send function transmits \`len + 1\`**, including a terminal NUL in its allocated C buffer ([lines 237–260](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L237-L260)).
- These are distinct source observations. We should accept/validate replies robustly with bounded optional trailing NUL (without treating interior embedded NUL as a normal header), and **test send-with-NUL and send-without-NUL against consenting actual PS5 firmware before choosing which is canonical**. The optional NUL is not proof of a firmware requirement and must not be silently appended to arbitrary messages.
- Don't treat TCP-like \`HTTP/1.1\` in UDP datagrams as a real HTTP web server request; keep DDP parsing separate from the HA-managed aiohttp cloud client.

### 10.2 UDP local binding and receive identity (not simply port 9302 in both directions)

- [Chiaki-ng discovery.h](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/include/chiaki/discovery.h#L20-L30) declares PS5 destination port \`9302\`, but the C implementation [tries local source ports \`9303..9319\` before ephemeral port 0](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L155-L200).
- [playactor UDP factory](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L157-L180) defaults \`localBindPort\` to port \`0\` (ephemeral) and uses one shared socket manager across protocol factory calls, with a listener per new discovery session.
- **Conclusion:** 9302 is the candidate **remote PS5 DDP destination**, not necessarily the client socket's local port. Bind strategy, source-interface selection, SO_BROADCAST, address family, response delivery, socket collisions and firewall restrictions must be validated on HA OS. Do not reserve one arbitrary local port as a universal protocol constant without evidence.
- Proposed own service: single owned UDP transport per compatible protocol/scope, monitor activity separate from UI listeners, bounded multi-target send and receive queues, local socket version/run generation, and guaranteed close/unload/cancel. No external socket manager.

### 10.3 Native HA network helper has a policy-specific shortcut

[HA Core 2026.11 \`network.async_get_ipv4_broadcast_addresses(hass)\`](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/network/__init__.py#L139-L162) starts with \`255.255.255.255\` and **returns only this limited broadcast when only the default interface is enabled** according to its network configuration. When a non-default adapter is enabled, it computes directed broadcast addresses for all enabled adapters using their IPv4 addresses and prefixes.

Therefore **do not claim that calling this helper always returns every subnet's directed broadcast address**. For more explicit single-interface/multihomed control, consider using the native \`network.async_get_adapters(hass)\` result and Python stdlib \`ipaddress.ip_interface(f"{address}/{network_prefix}")\` to calculate a bounded set of eligible broadcasts, respecting the HA user's enabled adapter settings. This calculation is our own small address-selection policy, not an extra third-party library. It must be verified against HA's network interface configuration and user consent before multicasting/broadcasting into additional subnets.

**Test cases**: one enabled default interface, multiple enabled interfaces, disabled IoT adapter, link-local, /31 or /32, route mismatch, target IP override, duplicated broadcast destination, interface reload and HA OS Docker-bridge topology. Exclude loopback and unsupported/unsafe interfaces according to a documented policy; never assume a directed broadcast gets routed across VLANs.

### 10.4 Wire/reducer compatibility acceptance set

- One PS5 SRCH packet to UDP 9302 with exact protocol-version header; test optional terminal NUL behavior rather than assume it.
- Multiple UDP responses and duplicates per attempt: source IP+port is not immutable owner; \`host-id\` is unverified until canonical identity protocol is established.
- Recognized response 200/620, unknown 503, malformed/truncated/oversized, embedded NUL, LF+CRLF, header duplicate/conflict, UTF-8, \`running-app-name\` with colon, optional app fields, version mismatch.
- Send/receive on ephemeral local port and optional explicit local port must not deadlock or incorrectly assume console replies are sent to a hard-coded port.
- Cancel and reload while old datagrams are queued: old \`run_id\` and source generation cannot change the new console current state or historical ledger.
- Every stable same-state successful point remains available for durable bounded history accounting even when the HA entity visible value does not change; a failed poll is not OFF.
- Source-level **possible** is not hardware-verified. No wire fixture was captured, and no UDP packets were sent in this audit.

**New engineering conclusion:** A true first-party DDP driver has to define packet bytes, transport endpoints, status/metadata grammar, source provenance and complete lifetime itself. That is practical with stdlib + native HA, but requires real on-device compatibility tests before making interoperability claims.
