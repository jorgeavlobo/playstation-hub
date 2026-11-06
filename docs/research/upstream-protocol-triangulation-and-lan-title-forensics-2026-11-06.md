# PlayStation Hub — Upstream protocol triangulation and LAN title forensics (second deep audit)

**Date:** 2026-11-06
**Status:** SOURCE CODE CONFIRMED AT PINNED REVISIONS / DEVICE SUPPORT UNVERIFIED / NO IMPLEMENTATION
**Goal:** Go below high-level repo comparisons into exact parser behavior, field provenance, independent implementations, command confirmation and test oracles. This document **extends**, not duplicates, [the initial upstream audit](upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md).
**Project:** Native Home Assistant `playstation_hub` greenfield integration, optional PSN/Remote Play, no MQTT broker/add-on. Old `develop` was never deployed; no migration/import of synthetic SQLite history. No SQLite-backup research here.
**No scope expansion:** Amendment to existing Protocol 01/02/03/07/09/10 and SPEC-001/002/004/007/021 contracts; no ADR-0023/SPEC-023 and no implementation authorization.

> **Evidence taxonomy:** CODE_OBSERVED = a specific expression/function in a pinned upstream repository. TEST_VECTOR = an upstream test's expectation, not a physical console capture. THIRD_PARTY_OPERATIONAL = a project's claimed/implemented application behavior, not a measurement by PlayStation Hub. UNVERIFIED_HARDWARE = requires actual PS5 and firmware; SONY_OFFICIAL is reserved for Sony's own docs. An implementation ported from another implementation is not an independent confirmation.

## 1. Exact pins and lineage

| Repository | Revision / lineage | Important finding | Licensing |
| --- | --- | --- | --- |
| [playactor](https://github.com/dhleong/playactor/tree/a9e72d67a3930a8f06455927edb547a1754ef0ac) | `a9e72d67` (2026-11-05) | Original TS source; permissive non-620 status classification and simple header splitting | Inspect license separately before copying |
| [PS5-MQTT](https://github.com/FunkeyFlo/ps5-mqtt/tree/7ab3075d276f3eeecd81a3322c72231af8cd51bd) | `7ab3075d` (2026-11-04) | CLI/saga consumer of playactor, not independent protocol confirmation | MIT at reviewed commit |
| [Chiaki-ng](https://github.com/chiaki-ng/chiaki-ng/tree/43728af2e639fecb8a7af1cd68c29820a40de973) | `43728af2` (2026-11-03) | C source: 200/620/unknown, optional running-app header parsing | AGPL-3.0 |
| [pyremoteplay](https://github.com/ktnrg45/pyremoteplay/tree/a127422c2599034ec4428919bbaf8b4db278cd75) | `a127422c` (2022-08-23), now archived | Older Python DDP parser, explicit 200/620 constants, special treatment of running-app-name containing colon | GPL-3.0 |
| [ps5-remoteplay](https://github.com/iharosi/ps5-remoteplay/tree/61e1f7dc065a77f7e8b1de5057889a08b0208d9d) | `61e1f7dc` (2026-09-17); declared **port of playactor** | asyncio PS5 discovery/wake/standby and byte-exact fixtures **derived from playactor** | AGPL-3.0-only |
| [ps5-wake](https://github.com/iharosi/ps5-wake/tree/4806b2846e0a5c82ca5ad009731087ead6b9bccb) | `4806b284` (2026-07-04); archived | PS5-specific C probe explicitly captures/prints running-app title/name | GPL-3.0 |
| [chiaki-km](https://github.com/leonanluppi/chiaki-km/tree/9f84d0baf82ac87072781f7ad0a909291c46e2b5) | `9f84d0ba` (2026-07-20); Chiaki fork | Uses LAN application metadata to select a controller input profile, with absence handling | AGPL-3.0 |
| [HA Core PlayStation Network](https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network) | 2026.11.0 tagged source | Separate PSN account/device-platform abstraction, not raw local PS5 activity | HA project license, consult source |

**Important independence classification:** `ps5-remoteplay` explicitly states it was ported from playactor and that `tests/vectors.json` contains reference outputs from the TS implementation. Therefore agreement between their status parser, packet formats, wake behavior or fixtures is partly inherited and must NOT be counted as two independent firmware validations. Chiaki-ng and older pyremoteplay add different implementations; chiaki-km is itself based on Chiaki and is also not independent of its C header parser.

## 2. Source-level status mapping — exact risks

### 2.1 Comparison by real code

| Source & code | 200 | 620 | 503/unknown | Notes |
| --- | --- | --- | --- | --- |
| [playactor messages.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts#L23-L36) | AWAKE | STANDBY | **AWAKE** | `code === "620" ? STANDBY : AWAKE` |
| [ps5-remoteplay discovery.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/discovery.py#L56-L69) | AWAKE | STANDBY | **AWAKE** | Port inherits permissiveness; `DeviceStatus` lacks UNKNOWN |
| [Chiaki-ng discovery.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L102-L113) | READY | STANDBY | **UNKNOWN** | Explicit switch; safer model |
| [pyremoteplay ddp.py](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py#L24-L31) | STATUS_OK | STATUS_STANDBY | Not established by these constants alone | Confirm downstream use before claiming its unknown-state behavior |
| [ps5-wake C probe](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L461-L474) | Ready/app metadata | Standby | Unknown status printed | PS5-oriented tool, but no live test here |

**Project decision direction (still PROPOSED):** validate the HTTP-like response syntax and sender/host-ID identity first; accept exactly status `200` as **LAN_REPORTED_READY**, `620` as **LAN_REPORTED_STANDBY**, all other syntactically valid codes as UNKNOWN, and malformed packets as INVALID. Do not equate missing UDP reply with OFF. Separate `REACHABLE`, `POWER_REPORTED`, `FRESHNESS`, `CANONICAL_OWNER`, `COMMAND_STATE`.

The word READY is the name used by Chiaki, and our public AWAKE state is a normalization proposal. It does not prove that a screen is on, a player is present or that a specific game is being actively played.

### 2.2 Test lineage trap

- [ps5-remoteplay tests/test_protocol.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/tests/test_protocol.py#L20-L45) checks the parser against `tests/vectors.json`, with synthetic `HTTP/1.1 200 Ok` and `620 Server Standby` reply strings.
- These fixtures demonstrate roundtrip expectations in the port; they do **not** test an unfamiliar `503` or actual modern PS5 firmware. Their existence does not imply that the new PlayStation Hub's tests have run.
- To avoid false evidence inflation, distinguish agreement by upstream porting, independent parser behavior, upstream synthetic fixtures and actual PS5 capture as **four separate evidence levels**.

## 3. The overlooked LAN game/app metadata — precise provenance

### 3.1 Cross-repository field recognition

1. [Chiaki-ng lib/src/discovery.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L115-L135) copies optional `running-app-titleid` and `running-app-name` from discovery HTTP-like response headers into a physical `ChiakiDiscoveryHost`.
2. [Chiaki-ng lib/include/chiaki/discovery.h](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/include/chiaki/discovery.h) declares both as first-class members, with host ID, type, name, system version and source address.
3. [pyremoteplay pyremoteplay/ddp.py](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py#L100-L145) parses and explicitly special-cases `running-app-name` headers. This is a **2022** recognition of the field names, not a guarantee of PS5 support in 2026.
4. [ps5-wake ps5-wake.c](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L59-L64) defines both fields and [parses them](https://github.com/iharosi/ps5-wake/blob/4806b2846e0a5c82ca5ad009731087ead6b9bccb/ps5-wake.c#L100-L113); its `200` display branch prints name+title ID when present and otherwise labels home screen. This is PS5-specific code intent, still not an instrumented report from the user's device.
5. [playactor src/discovery/udp.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L115-L126) retains otherwise unknown discovery headers in `extras`, so a source adapter can choose to normalize these fields. It does not itself implement a source-validated running-game inference.

### 3.2 A real consumer of this metadata (not merely a parser)

The [chiaki-km fork](https://github.com/leonanluppi/chiaki-km/tree/9f84d0baf82ac87072781f7ad0a909291c46e2b5) uses `DiscoveryHost.running_app_titleid` and `running_app_name` to choose keyboard/mouse profiles. [`gui/src/inputprofile.cpp`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/inputprofile.cpp#L1-L49) distinguishes:
- **Metadata not available:** use Default; do **not** call this a known empty title.
- **Explicit empty title/name after local discovery:** navigation profile.
- **A recognized game title/name:** game-specific profile.
- **Other app/title:** Default.

In [`gui/src/discoverymanager.cpp`](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/gui/src/discoverymanager.cpp), a constant `PING_MS = 500` exists; the project's [ARCHITECTURE.md](https://github.com/leonanluppi/chiaki-km/blob/9f84d0baf82ac87072781f7ad0a909291c46e2b5/ARCHITECTURE.md) describes continued local discovery for Auto and a 750 ms stability window. These are a **specialized interactive app's choices**, not recommended unattended Home Assistant polling intervals. Validate actual code route/feature readiness on hardware, not the design document alone.

The fork also recognizes an example `CUSA` title ID for a PS4 game running by backward compatibility on PS5. **Implication:** `LAN_TITLE_KEY` must be namespaced by origin/platform; do not assume all PS5-executed titles have a `PPSA` PS5-native identifier. An exact mapping from CUSA/PPSA to PSN `npTitleId` or concept/product IDs needs independently verified crosswalk.

### 3.3 Critical semantic limitation

The **name of an app reported by a console**, the **foreground game rendered on screen**, the **installed title**, a **suspended app**, and **elapsed user gameplay** are five distinct claims. Sources above show a field and its use; none in this audit proves all five are equivalent in all PS5 firmwares.

The initial feature should therefore be: **“Local console reports an application/title”** with verified physical owner, report time, source, normalized ID/name and confidence. Live UI may show `reported_title` if fresh; statistical `played_time` remains separately gated. A missing optional header must be represented as HEADER_NOT_PROVIDED, not `NO_GAME`. A present but empty header must not be collapsed with missing; a first `200` without app fields is not a proven home screen.

### 3.4 No-cloud tests and user benefits

A LAN-only candidate can reduce PSN account requirements for a physical title label, potentially work during PSN outage and avoid falsely picking the first awake PS5 for account games. Test it without pairing/PSN and with non-game apps before presenting it as product functionality. Do not assume this improves privacy automatically: title and usage times may still constitute personal information.

## 4. Parser robustness: exact, demonstrable defects and safe contracts

### 4.1 Colon truncation in playactor

[playactor messages.ts lines 44–49](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts#L43-L49) uses `const [key, value] = line.split(/:[ ]*/);`. If a response header is `running-app-name:Example Game: Director's Cut`, the second colon creates a third array field and the destructured `value` loses the subtitle. This follows from JS splitting semantics, not a verified packet capture. A colon can also appear in a friendly name, URI or otherwise legitimate metadata. **Never port the split logic verbatim.**

The archived [pyremoteplay 2022 ddp.py](https://github.com/ktnrg45/pyremoteplay/blob/a127422c2599034ec4428919bbaf8b4db278cd75/pyremoteplay/ddp.py#L118-L145) appears to recognize this defect and specially preserve the whole `running-app-name` line, whereas its general `line.split(":")` still ignores other colon-containing values. [ps5-remoteplay discovery.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/discovery.py#L38-L54) is more robust in this respect: `line.split(":", 1)`.

**Proposed parsing rule:** split on the **first** colon only, preserve the original remainder (normalized whitespace policy), reject unsafe control characters/oversized datagrams, differentiate absent/empty/whitespace-only headers, limit lengths, and record decoded-field validity without storing raw sensitive LAN payload in routine diagnostics.

### 4.2 CRLF normalization and validation

playactor's `raw.toString().split("\n")` and `result[key.toLowerCase()] = value` do not visibly trim a trailing `\r` from CRLF header values. A datagram with `host-id:ABC\r\n` may yield the value `ABC\r`, which is unsuitable as a canonical identity. The [ps5-remoteplay Python parser](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/discovery.py#L38-L54) explicitly removes `\r`, and its [test protocol](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/tests/test_protocol.py#L42-L45) covers a colon-bearing name with CRLF.

Recommended parser guards: exact supported HTTP-like status line; bounded payload; CRLF and LF inputs; known protocol version; required validated `host-id` and suitable `host-type`; source IP sanity; normalized nonempty identifiers; reject duplicates/conflicting identity headers, excessive fields, control bytes and unknown types for durable owner updates. Retain unknown non-sensitive fields only in bounded diagnostic form.

**Threat boundary:** UDP broadcast data is not authenticated just because it looks like a PS5 response. A sender claiming a `host-id` does not demonstrate cryptographic ownership. No power action, Remote Play credential binding or historical data reassignment from a single untrusted packet. Physical identity needs the independent proof/registration plan from ADR-0004.

### 4.3 Data/state normalization proposal (not implementation code)

```text
LanDiscoveryObservation:
  packet_validation: VALID | PARTIAL | INVALID
  source_address: validated local endpoint (not canonical identity)
  reported_host_id: optional normalized candidate
  host_id_confidence: CANDIDATE | VERIFIED | CONFLICT
  host_type: PS4 | PS5 | UNKNOWN
  protocol_version: optional explicit ASCII version
  response_status_code: integer or invalid
  power_report: READY | STANDBY | UNKNOWN
  app_header_presence: ABSENT | EMPTY | VALUE | INVALID
  running_app_title_key: optional (origin=LAN_DDP, platform namespace, opaque value)
  running_app_name: optional sanitized display string
  requested_at_utc / received_at_utc / request_generation
  validity/freshness: independent dimension
```

This can be carried as a separate source-adapter DTO and translated into current ADR-0005 evidence envelopes. It is **not** a new mandatory SQLite table, nor proof of player identity or session duration.

## 5. Commands: precise outcome, waiting semantics and physical verification

### 5.1 Wake behavior differs in libraries

- [playactor/src/waker.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/waker.ts#L35-L85) sends WAKEUP then waits for same device ID discovered in AWAKE; its verification inherits its permissive parser.
- [ps5-remoteplay/src/ps5_remoteplay/wake.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/wake.py#L13-L23) sends WAKEUP **without waiting**; the CLI only awaits `wait_for_status` unless `--no-wait`. A library API success means packet emission, not state verification.
- The two implementations are not independent firmware confirmations: the Python implementation is a documented port of the TypeScript one.

**Expected PlayStation Hub state flow:** REQUESTED → SENT → VERIFYING → CONFIRMED only after a fresh, allowlisted 200 response for the correct verified physical owner. If deadline expires, result INDETERMINATE/TIMED_OUT, with last-known status preserved (not speculative AWAKE/OFF). If the first probe says already READY, make command idempotent only when owner/freshness preconditions hold.

### 5.2 Standby library outcomes are weaker than they appear

- [playactor/src/connection/remoteplay.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/connection/remoteplay.ts#L22-L32) sends standby packet and waits until receive loop ends; it does not perform an independent confirmed 620 status probe there.
- [ps5-remoteplay session.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/session.py#L180-L188) **swallows a timeout** while waiting for the session to close: it only logs the timeout. The module-level [`standby()` wrapper](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/session.py#L215-L236) then returns `True` after close, even though a fresh STANDBY probe is absent. This is a source-confirmed **logical success/reporting risk**, not evidence that the physical console stayed awake.
- [PS5-MQTT turn-off saga](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/turn-off-device.ts#L23-L35) updates status to STANDBY after the playactor wrapper returns. Thus it can be optimistic relative to what can be verified from a new LAN observation.

**Expected contract:** Sending a standby frame, successful TCP write, peer closing control session, Remote Play login success, or CLI exit=0 are **distinct** from 620 reported on a valid fresh LAN reply from the intended owner. No durable actual transition or session close solely from any of those interim signals. A long timeout may leave source in UNKNOWN/VERIFYING, and a later valid physical observation finalizes the transition at its sample time, without inventing the true transition instant.

### 5.3 Remote Play may disturb gameplay; make controls opt-in

Pairing, opening a control session or sending standby are active operations. Do not treat full Remote Play handshake as a passive background monitoring mechanism. Limit command concurrency per verified console, use explicit permissions and user intent, avoid credentials in logs, avoid overlapping control sessions and reconcile command outcomes after process restart without resending a possibly already-applied command.

Sony official setup docs for [Chiaki-ng](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/docs/setup/configuration.md) (third-party documentation, not Sony) describe enabling Remote Play and enabling rest-mode network wake; official PS5 user configuration requires validation at implementation.

## 6. Important PS5-MQTT implementation details for native HA architecture

The [PS5-MQTT check saga](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/check-devices-state.ts#L13-L60) loops sequentially and uses `break` when a device is transitioning, so a prior transitioning console may defer polling all later consoles in that pass. In addition, the saga publishes an update only when status changes or availability recovers. A native historical ledger **cannot rely on change-only MQTT publication as the source of periodic continuity evidence**; it needs its own accepted source observations/heartbeats with checkpoints (ADR-0021).

The [PS5-MQTT playactor CLI wrapper](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/playactor/client.ts#L60-L115) constructs shell command strings with interpolated target IP, credentials path and user passcode, then calls `sh.exec()`. This complicates shell-input safety, timeout handling and event-loop scheduling; **native Python transport should never form shell commands from device/credential metadata**. A direct async socket adapter is preferable; this is not an assertion that upstream was exploited.

The [PS5-MQTT update-account saga](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/update-account.ts#L11-L51) sorts preferred devices and picks the first awake matching platform for PSN account activity. This is a user-interface convenience heuristic and can be ambiguous for simultaneous PS5s. Do not use it as the basis for immutable game attribution or player time. The new optional LAN app metadata may eventually offer stronger device-scoped evidence, but does not give a player account or exact foreground gameplay proof.

The [multi-interface discovery implementation](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/playactor/discovery.ts) sends directed broadcasts via one shared scan, limiting event-listener proliferation. Native HA should similarly share/own compatible source listener resources and dedupe multi-interface replies after identity validation. `255.255.255.255` is not guaranteed to cross VLANs or firewall/router boundaries.

## 7. Why source differences matter to the v1 product

### 7.1 Functionality priority adjustment

**Highest immediate research-to-testing priority:** physical PS5 LAN status and optional running-app headers (passive, no PSN dependency). This may support local "reported application" visual cards, local title ID, latest reported app, last-seen and historical title-sample audit even when a PSN account isn't linked.

**Secondary:** verified wake and standby controls via separate command subsystem with per-console operation/lease and post-command observation.

**Later:** PSN user presence, catalogs and provider lifetime playtime; no license/authorization assumption and no automatic hardware mapping.

### 7.2 Do NOT equate sampled application with game duration

If local app metadata is present and stable between two qualified samples, it may eventually permit **bounded reported-app duration**, not exact time spent holding a controller or playing a game. A foreground/background/suspended state must be empirically classified. On rest mode, missing app header, home-screen app ambiguity, changes between polls, PSN unavailable and source timeout: prefer UNKNOWN rather than false zero seconds or continuous gameplay.

Time savings and accuracy must be balanced: 500 ms aggressive in an interactive remote-control fork is not automatically suitable for always-on home server. Use distinct cadence for discovery, current-state monitor, app metadata and command verification after real measurements and source limits.

## 8. Concrete protocol test-oracle matrix (documentation only)

| ID | Synthetic / later hardware scenario | Expected conservative outcome |
| --- | --- | --- |
| SRC-LAN-01 | `HTTP/1.1 200 Ok\n...` | READY with verified owner candidate; not player/game proof |
| SRC-LAN-02 | `HTTP/1.1 620 Server Standby\n...` | STANDBY only after header validation |
| SRC-LAN-03 | `HTTP/1.1 503 Unrecognized\n...` | UNKNOWN, never AWAKE |
| SRC-LAN-04 | `running-app-name:Example: Director's Cut` | Entire value retained, no truncation after colon |
| SRC-LAN-05 | `host-id:ABC\r\n` | Canonical ID `ABC`, not `ABC\r` |
| SRC-LAN-06 | Missing app header versus empty app header | Distinct ABSENT/EMPTY; no automatic "no game" assertion |
| SRC-LAN-07 | Unicode/UTF-8 title, malformed bytes, excessive length | Bounded/rejected/sanitized; source health independent of power |
| SRC-LAN-08 | Duplicate/conflicting `host-id`, host-type or response version | Identity conflict/invalid input; no automatic credential/historical reassignment |
| SRC-LAN-09 | Reply from unexpected IP; same IP different host ID | Reject unsafe ownership switch, preserve old history |
| SRC-LAN-10 | Duplicate replies from multiple broadcast interfaces | One observation per canonical accepted source/attempt, no duplicate device |
| SRC-LAN-11 | One console transitioning while second is active | Independent pollers; no global break/starvation |
| SRC-LAN-12 | Game -> home -> different title / media app / rest | Explicit new samples, uncertainty, no unsupported player attribution |
| SRC-CMD-01 | WAKEUP sent, no subsequent 200 | SENT/UNKNOWN, no confirmed power change |
| SRC-CMD-02 | Standby socket closes or command returns true, no 620 | NOT_CONFIRMED, no false historical standby |
| SRC-CMD-03 | Wait for close timed out but wrapper returns true | Detect ambiguous command result; verification required |
| SRC-CMD-04 | Permission/owner conflict or duplicated command | Deny or serialize, no speculative state |
| SRC-PSN-01 | PSN account reports title on two awake PS5 devices | Account-reported title; device attribution AMBIGUOUS |
| SRC-PSN-02 | Local DDP title ID differs from PSN title ID | Distinct namespaces, no name-only merge |
| SRC-HIST-01 | Repeated READY or title messages with same state | Preserve bounded durable checkpoint even without UI state change |
| SRC-HIST-02 | Timeout/reconnect with same title after hours | UNKNOWN gap, not uninterrupted game time |

These IDs are **analysis trace IDs**, not new executed tests or a new SPEC; future implementation should integrate the focused cases into existing SPEC-001/002/004/021/007 as needed.

## 9. Technical follow-through without new research spirals

1. Update existing Protocol 01/02/03/07/10 and ADR-0005/0021 to reference the new source findings.
2. Freeze a **provisional v1 LAN parser evidence contract** with status allowlist and optional `LAN_RUNNING_APP`, but mark actual firmware support UNVERIFIED.
3. During explicitly authorized WP-01, implement a pure bounded parser and synthetic table-driven tests, respecting original code ownership/licensing; no Sony tokens or real device needed.
4. In WP-02/03, collect consented actual PS5 LAN samples for home, running native PS5 game, backward compatible PS4 title, media app, switched game, standby and PSN offline. Validate host identity, field freshness and real payload grammar. Store only sanitized fixtures/metadata without personal names/IDs.
5. Control and PSN features stay separate; do not let their unverified API or crypto licensing block the pure parser.
6. **Stop condition:** No more numbered research packages or repeated backup reviews unless code/hardware tests reveal a documented contradiction. The next useful advance after this source review is executable empirical evidence when the maintainer chooses to implement.

## 10. References and claims-not-made

All source links are commit-pinned above. We did **not** capture any PlayStation user's LAN traffic, inspect their Home Assistant instance, pair their console, call PSN, validate real firmware, choose a runtime dependency, run tests, or create executable code. In particular:
- A parser recognizing `running-app-titleid` is NOT proof that every PlayStation 5 sends it.
- `200` is community READY classification, not a direct real-time observer of human gameplay.
- Synthetic vectors ported from playactor are not independent confirmation.
- No app may copy GPL/AGPL code/crypto tables or fixtures into a differently licensed distribution without proper review and license compliance.
- User-friendly game title labels and robust historical game time require separate source and semantic validation.

**Outcome:** Source-code-level comparison with actionable parser/command/metadata corrections, no v1 DDL, no new ADR/SPEC, no application implementation.
