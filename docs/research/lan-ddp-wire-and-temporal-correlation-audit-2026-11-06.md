# PlayStation Hub — First-party DDP wire contract, UDP temporal correlation and source-monitor audit

**Date:** 2026-11-06
**Status:** SOURCE-VERIFIED DESIGN RESEARCH / NO EXECUTABLE CODE / NO DEVICE OR HA OS TEST
**Scope:** PlayStation LAN Device Discovery Protocol (DDP), source-attribution and packet grammar, socket ownership, multi-interface scans, per-console poll/heartbeat requirements and optional local title fields.
**Decision precedence:** [First-party sovereignty policy](../architecture/first-party-dependency-sovereignty-policy.md) — no external PlayStation runtime library, no new runtime pip/npm dependency, no MQTT/add-on, no source/vendor binary copy. This is focused research under WP-00B, **not** a new numbered ADR/SPEC or implementation authorization.
**Predecessors:** [First-party runtime audit](first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md), [upstream triangulation](upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md), Protocols 01/02/10, ADR-0005/0006/0021.
**Research baseline:** Pinned HA Core 2026.11.0, Python >=3.14.2; source revisions listed below.

> Evidence labels: **UPSTREAM_SOURCE** = directly inspected code at pinned commit, **PYTHON_OFFICIAL** = Python 3.14 documentation, **HA_CORE_SOURCE** = the versioned Home Assistant implementation, **PROPOSED** = our contract awaiting approval, **DEVICE_UNVERIFIED** = no real PS5 packets have been captured. Reverse-engineered PlayStation DDP is not a Sony-supported public protocol contract.

## 1. High-value new findings (not another general backup study)

1. **The inspected DDP SRCH request has no explicit request identifier, transaction nonce or timestamp.** Both Playactor and Chiaki build a search line plus a static discovery-version header. Their parsers do not prove a receiver echoed a unique request ID. **It is impossible to authoritatively link every late UDP response to one exact poll merely from this inspected wire grammar.** Our local \`request_generation\` remains a local association heuristic, not an on-wire correlation guarantee.
2. **A Python asyncio UDP \`sendto\` return is not network delivery evidence.** Official asyncio documentation says send is buffered; \`error_received\` may not fire for undelivered UDP. A timeout is not physical OFF, and successful send is not a successful search or power command.
3. **Chiaki's discovery service receives unchanged responses but only publishes its state callback when a field actually changes.** Its internal \`last_ping_index\` is advanced for each valid matching host receipt; its public change notification is not a heartbeat ledger. PlayStation Hub must process accepted points even when the HA UI projection is unchanged.
4. **Chiaki's source parser rejects an empty header value** (its \`chiaki_http_header_parse\` rejects \`value_ptr == buf\` on newline), whereas our future model needs to distinguish OPTIONAL app header ABSENT versus present-but-empty versus INVALID. That distinction is a **project policy**, not a claim that Chiaki provides it or that firmware emits empty values.
5. **The same candidate SRCH text is sent with different UDP payload terminators and local bind ports by different upstream libraries.** Playactor formats without an explicit NUL and defaults to ephemeral port; Chiaki transmits \`len + 1\` and binds 9303–9319 then ephemeral. These are compatibility parameters to test, not grounds to choose a single value by intuition.
6. **Native Home Assistant network broadcast selection is policy-dependent.** The \`network.async_get_ipv4_broadcast_addresses\` API may return only the limited broadcast \`255.255.255.255\` when only the default interface is enabled. Use the supported adapter API and stdlib \`ipaddress\` for more explicit multi-interface user-selected behavior without importing third-party \`netifaces\`.

## 2. Source registry — direct code and official behavior

| ID | Evidence | Source and exact relevance |
| --- | --- | --- |
| DDP-S01 | UPSTREAM_SOURCE | [playactor packet formatter](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/protocol.ts) — static \`SRCH * HTTP/1.1\`, version header; no request ID |
| DDP-S02 | UPSTREAM_SOURCE | [Chiaki packet formatter](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L67-L90) and [send routine](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L237-L259) — send \`len + 1\` bytes, including NUL |
| DDP-S03 | UPSTREAM_SOURCE | [Chiaki port/version declarations](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/include/chiaki/discovery.h#L24-L30) — PS5 destination UDP 9302, version 00030010; PS4 separate profile 987/00020020 |
| DDP-S04 | UPSTREAM_SOURCE | [Chiaki local UDP socket creation](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L155-L215) — 9303–9319 then port 0, SO_BROADCAST |
| DDP-S05 | UPSTREAM_SOURCE | [playactor UDP socket manager](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L30-L67) and [factory](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/udp.ts#L157-L181) — ephemeral bind, shared sockets/listeners |
| DDP-S06 | UPSTREAM_SOURCE | [Chiaki response decoder](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c#L91-L139) — 200/READY, 620/STANDBY, unknown; host and optional running-app headers |
| DDP-S07 | UPSTREAM_SOURCE | [Chiaki HTTP-like response parser](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/http.c#L27-L128) — parses first colon, newline, rejects empty header values |
| DDP-S08 | UPSTREAM_SOURCE | [Chiaki service receives and publishes changes](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discoveryservice.c#L305-L388) — \`last_ping_index\` updated for all accepted replies, callback only if state/fields changed |
| DDP-S09 | UPSTREAM_SOURCE | [Chiaki host expiry by ping index](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discoveryservice.c#L266-L303) — threshold of missing ping cycles, not intrinsic physical OFF |
| DDP-S10 | UPSTREAM_SOURCE | [PS5-MQTT multi-interface adapter](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/playactor/discovery.ts) — multi-target broadcast with one scanner to avoid listener leaks |
| DDP-S11 | UPSTREAM_SOURCE | [PS5-MQTT change-only HA state](https://github.com/FunkeyFlo/ps5-mqtt/blob/7ab3075d276f3eeecd81a3322c72231af8cd51bd/ps5-mqtt/server/src/redux/sagas/check-devices-state.ts#L13-L59) — unchanged healthy status not republished to HA |
| DDP-S12 | HA_CORE_SOURCE | [HA Core 2026.11 network API](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/network/__init__.py#L57-L162) — \`async_get_adapters\` and broadcast helpers; default-only shortcut |
| DDP-S13 | PYTHON_OFFICIAL | [Python 3.14 event loop Datagram endpoint](https://docs.python.org/3.14/library/asyncio-eventloop.html#asyncio.loop.create_datagram_endpoint) — UDP transport creation, bind, allow_broadcast |
| DDP-S14 | PYTHON_OFFICIAL | [Python 3.14 DatagramProtocol](https://docs.python.org/3.14/library/asyncio-protocol.html#datagram-protocols) — \`datagram_received\`, \`error_received\`, \`connection_lost\` |
| DDP-S15 | PYTHON_OFFICIAL | [Python 3.14 DatagramTransport](https://docs.python.org/3.14/library/asyncio-protocol.html#datagram-transports) — \`sendto\` buffering, no transport-level delivery receipt |
| DDP-S16 | UPSTREAM_SOURCE | [playactor parser](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts#L23-L49) — non-620 ⇒ AWAKE and colon split/CRLF hazards (do NOT copy) |

## 3. Exact outbound wire envelope, with explicit unknowns

For **one candidate PS5 search**, source implementations encode the following printable content:

\`\`\`text
SRCH * HTTP/1.1\n
device-discovery-protocol-version:00030010\n
\`\`\`

This represents a **single UDP datagram** with LF-separated lines, not a TCP connection nor a conventional HTTP browser request. The actual encoded byte sequence must be verified; docs show \`\n\` as line terminator, not a literal backslash character. Chiaki transmits an additional terminal \`00\` byte; Playactor's formatter does not visibly add it. Both target UDP **9302** for PS5; local client port need not equal destination port. PS4 uses a different version/port profile, not one indiscriminate PS5 parser.

**Missing on-wire correlation:** No nonce, per-request ID or \`requested_at\` echo is present in the inspected static SRCH format. Therefore:
- A reply received during scan generation 9 may be a reply to an earlier request, an unsolicited announcement, or unrelated/malicious UDP data. A local generation tag cannot prove which outbound packet caused it.
- Serializing source requests, keeping one active scanner generation and bounding response acceptance windows reduce ambiguity, but cannot supply absent on-wire proof.
- Local \`sent_at\` and \`received_at\` are observational metadata, not the console's actual transition time. Don't backdate a console session solely on request start, or claim a precise transition from the response.
- Closing/fencing old callback handlers guards **our code**, but after a new UDP socket opens it may still see a late datagram indistinguishable from a fresh one if the packet lacks a correlation token. This is a **new explicit unresolved temporal confidence boundary**, not a bug solved by in-memory run IDs.
- Identity headers are self-reported and DDP is not authenticated by the inspected source. No irreversible physical owner merge, credential binding, command authorization or historical reassignment from one untrusted reply.

**Future observation labels proposed:** \`CORRELATED_IN_PROCESS_WINDOW\` (received during bounded current scan), \`UNSOLICITED_OR_LATE_POSSIBLE\`, \`SOURCE_UNVERIFIED\`. Never display these as proof of cryptographic identity or exact temporal freshness.

## 4. Defensive inbound parser profile — pure first-party module

### 4.1 Structural envelope

| Stage | Expected behavior, proposed | Reject/quarantine case |
| --- | --- | --- |
| Datagram bounds | Choose documented max bytes; reject oversize rather than silently truncating; log sanitized length, not raw packet | Too long, empty, interior NUL, invalid bytes |
| Optional terminal NUL | Allow at most one trailing NUL only if empirical fixtures support it; strip for parsing without changing raw digest semantics | NUL inside status/header, repeated trailing zero bytes unless approved |
| First line | Require bounded ASCII \`HTTP/1.1 <3-digit code> ...\` grammar for a *response* | \`SRCH\`/WAKEUP request reflected to our listener, invalid status digits, missing newline |
| Status | \`200\` ⇒ candidate READY; \`620\` ⇒ STANDBY; other valid code ⇒ UNKNOWN | Never non-620⇒AWAKE; malformed ⇒ INVALID |
| Header grammar | Split only on first colon; lowercase ASCII key with hyphen; tolerate LF and CRLF; reject malformed line/duplicate sensitive keys | Control chars, duplicate/conflicting host-id, malformed name, newline injection |
| Identity | Require nonempty bounded \`host-id\`, expected supported \`host-type\`, parse supported version according to documented policy | Unknown owner, mismatch, renamed/replaced same-IP device |
| Port | Validate \`host-request-port\` is a decimal integer 1..65535 if present/required by chosen source profile | Non-decimal, 0, overflow, unexpected duplicates |
| Strings | Decode with agreed strict/sanitized UTF-8 policy; do not treat source text as HTML; never log raw untrusted strings | Non-displayable controls, overlong Unicode values, invalid sequence |
| Running app | Preserve \`running-app-titleid\` and \`running-app-name\` independently, including ABSENT/EMPTY/VALUE/INVALID field classification | No invented game/title from absence or error |
| Source metadata | Keep \`source_ip:port\`, local listener generation, reception monotonic time (runtime only), received UTC time and scan-window ID | Untrusted owner or stale/closed source lease cannot write history |
| Result | Immutable source fact or typed error; never direct HA entity/SQLite mutation from socket callback | Parsing exception blocks all other owners or escapes event loop |

**Important distinction from Chiaki:** Its HTTP header parser rejects empty values; our model distinguishes explicit empty versus missing because **we want a safe representation even if real devices differ**. Whether an empty header is accepted or treated INVALID is a protocol-policy/firmware test gate; do not claim universal Sony behavior.

### 4.2 Live-state identity and source quality

A validated field set is not the same as authenticated console identity. Consider:
- Candidate \`host-id\` is a **self-reported identifier**. It may be stable in ordinary use, but no inspected DDP packet provides cryptographic proof or challenge-response.
- IP is an address, not an immutable owner ID. A new device on same DHCP address cannot inherit old sessions/credentials.
- Repeated same host-id from different source addresses could be a changed IP, duplicate interface response, or spoof/collision; do not assume one possibility.
- Two different host IDs at one address indicate conflict/replacement and require independent review.
- A reply from correct IP but unexpected ID is not a successful wake/standby confirmation.
- Publication of a source-only current state can be allowed with quality labelling; committing canonical durable history requires a separately defined physical owner verification policy.

## 5. Transport and scheduler contract — non-blocking, no extraneous packages

### 5.1 asyncio semantics that affect correctness

Python \`DatagramTransport.sendto\` queues bytes **without waiting for a response or guaranteeing delivery**. \`DatagramProtocol.error_received\` is only called in some error conditions; many lost datagrams produce no event. Therefore:
- A successful \`sendto\` is \`SEND_ACCEPTED_BY_TRANSPORT\`, never \`DEVICE_DISCOVERED\` or \`CONSOLE_AWAKE\`.
- An unsuccessful scan is \`NO_FRESH_REPLY\`/UNKNOWN source health, not OFF.
- Use timeouts on explicit response collection, with bounded pending replies and fair processing across consoles.
- On stop, close the transport and wait for/record \`connection_lost\` as appropriate. A close receipt means socket lifecycle ended, not any remote PlayStation powered off.
- Short-lived callbacks must not block on CPU-heavy parsing, disk, Home Assistant network calls or user UI state; heavy work happens in the owner reducer/queue outside DatagramProtocol callback.

### 5.2 Proposed ownership boundaries

\`\`\`text
Home Assistant entry/controller (one logical owner)
    |
    |-- Native Network Adapter Selector (HA network component)
    |-- LanUdpService (one bounded listener/transport per protocol/interface policy)
    |      |
    |      +-- DatagramInputQueue (bounded, redacted)
    |      +-- Pure DdpDecoder (no HA/sqlite/network side effects)
    |             |
    |             +-- CandidateIdentityRegistry (unverified vs verified)
    |             +-- ConsoleSampleRouter (per-owner ordering and generation)
    |                    |
    |                    +-- State/cache projection -> HA native entities
    |                    +-- Evidence admission -> history writer (if READY)
    |
    |-- ConsoleMonitor[A] (owned by config entry; polling continues without UI listeners)
    |-- ConsoleMonitor[B] (independent; same physical source socket may be shared)
\`\`\`

The diagram describes **responsibilities**, not mandatory class names or implementation files.

**Identity and generation:** Each source callback carries local service generation to fence old handlers; the response itself may lack an on-wire correlation token. Track \`received_during_window\` and \`last_satisfied_probe\` but don't promote this to absolute temporal truth. Maintain one active request per console/protocol where useful; simultaneous monitors may share one discovery scan and should not create separate broadcast listeners for every UI subscriber.

### 5.3 HA native multi-interface selection

HA Core [network.py API source](https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/network/__init__.py#L139-L162) chooses only limited broadcast \`255.255.255.255\` for the default-only adapter configuration, but includes per-subnet addresses when non-default adapters are enabled. Use the HA network component as source of enabled adapters and address/prefix values; stdlib \`ipaddress.ip_interface\` computes directed subnet addresses when independently necessary. Scope the selection to authorized local interfaces and a bounded list; avoid sending traffic to every Docker bridge, disabled interface, arbitrary remote subnet, broadcast of public/non-LAN networks or routes that cannot reach the target. Manual validated unicast IP remains an important fallback.

Do not conflate network availability, an enabled network interface, HTTP/PSN access, and the DDP console's power state. If the HA network integration has not loaded/failed, surface a source capability error rather than silently selecting unrelated host interfaces.

### 5.4 Last-known, TTL, and change-only notifications

Chiaki's source service advances the host's \`last_ping_index\` even if there is no data change, but calls the visible \`discovery_service_report_state\` only if a state, request port or string changes. It separately drops host records after its configured number of missed ping cycles (not because the PlayStation explicitly sends OFF).

PS5-MQTT similarly publishes unchanged healthy state sparingly. **Neither UI/change callback stream is a lossless observation ledger**. Our monitor requires raw/normalized **successful unchanged sample** admission for bounded historical accounting; its Home Assistant state projection may still suppress redundant UI updates. Expiring a last-known source must change CURRENT/AVAILABILITY, not write a fabricated physical OFF event.

A ping-cycle count and a freshness TTL are separate; a measured time gap B for bounded session calculation is yet another policy, as defined in ADR-0021. Do not copy Chiaki's host_drop_pings, PS5-MQTT cadence or develop's 90s as a universal limit.

## 6. Optional console-reported application/title source

Chiaki-ng's DDP response parser recognizes \`running-app-titleid\` and \`running-app-name\`. Other source implementations parse these fields and Chiaki-KM consumes them for input-profile selection. This supports a **possible** LAN-only title display route with no PSN account dependency, not a guarantee every PS5 reports the fields.

Proposed normalization:
- \`reporter\`: canonical *verified* console owner or UNVERIFIED_CANDIDATE.
- \`source\`: \`LAN_DDP_RUNNING_APP\`, NOT PSN_ACCOUNT_TITLE.
- \`id_namespace\`: \`DDP_CUSA\` / \`DDP_PPSA\` / \`DDP_OTHER\` / \`DDP_UNKNOWN\`, determined from actual field rules, not guessed by friendly name.
- \`title_id_presence\`, \`name_presence\`: ABSENT / EMPTY / VALUE / INVALID, independently for each field.
- \`reported_at\`: source sample received timestamp + uncertainty/rtt metadata.
- \`foreground_confidence\`: UNKNOWN until home/game/media/standby/backwards compatibility fixtures on actual PS5.
- \`player\`: UNKNOWN unless independent permitted account association evidence exists.
- \`duration\`: zero for the point sample. Bounded title continuity is an OPTIONAL future separate policy, **never exact human gameplay**.

A missing app header after previously visible app is a **metadata freshness/coverage break** to consider, not necessarily an app-closed transition. Do not turn PSN errors into LAN game-ended events. Users' local title names and play times remain personal and must be protected in diagnostics.

## 7. Focused future test-oracle matrix — RESEARCH ONLY, NOT_RUN

| Trace | Input or failure | Expected invariant |
| --- | --- | --- |
| DDP-T01 | Exact PS5 SRCH LF bytes, with and without optional trailing NUL | Distinct source-derived variants; select only after firmware test |
| DDP-T02 | Client bound to ephemeral port vs local 9303–9319 | Replies handled on owning socket; remote 9302 not confused with local port |
| DDP-T03 | UDP sendto succeeds but no response, error_received absent | No available/awake assertion, no power transition |
| DDP-T04 | Unsolicited/old reply arrives during new scan | No false proven poll correlation; temporal quality limited |
| DDP-T05 | Scan generation changes while prior callback queued | Old callback fenced; new socket still treats late replies conservatively |
| DDP-T06 | 200, 620 and 503 well-formed replies | READY, STANDBY, UNKNOWN respectively |
| DDP-T07 | Malformed status, reflected SRCH, interior NUL, too-long packet | Typed rejection/quarantine, never AWAKE |
| DDP-T08 | CRLF, LF, first-colon game subtitle, mixed-case headers | Correct normalized source fields, no truncation or CR in ID |
| DDP-T09 | Missing, empty and malformed optional app fields | ABSENT/EMPTY/INVALID not conflated with no game |
| DDP-T10 | Duplicate/conflicting host-id, host-type, host-request-port | No unsafe owner assignment; conflict diagnostic |
| DDP-T11 | One host ID from two networks; two IDs at one IP | Distinct unverified candidate states; never merge historical owners automatically |
| DDP-T12 | Success unchanged 200 repeatedly | Each accepted source sample may update durable evidence while UI state remains unchanged |
| DDP-T13 | 1–N timeouts then same-state response | Availability declines; no fabricated OFF or unbounded session backfill |
| DDP-T14 | Several consoles, one slow/transitioning | Other console deadlines and ingestion unaffected |
| DDP-T15 | HA Network default-only vs enabled multi-interface | Bounded target set, manual unicast fallback; avoid unauthorized bridge traffic |
| DDP-T16 | Closing/reloading UDP service while packets queued | No leaked transport, stale callback resurrection or post-unload write |
| DDP-T17 | Home screen, native PS5 game, PS4 CUSA game, streaming app, suspend, standby | Establish actual running-app semantics; do not claim before device test |
| DDP-T18 | Account PSN outage while LAN data available | Local source/candidate title unaffected and clearly scoped |
| DDP-T19 | Unknown host spoofing a known ID | No credential leak, history reassignment or irreversible pairing |
| DDP-T20 | Malformed inputs across Unicode/line counts/duplicates | Bounded memory, no crashes, sanitized diagnostics |

**Status:** All 20 trace cases describe future acceptance coverage, not 20 executed tests or a new numbered SPEC. Add them to existing SPEC-001/002/021 implementation planning. A synthetic replay of bytes without live firmware validates the parser code, not the physical console.

## 8. Practical evidence sequence and stopping rule

1. Accept/modify this proposed wire contract without assuming firmware support.
2. In a *separately authorized* WP-01, write a pure no-extra-package Python decoder with own deterministic byte fixtures and strict resource limits.
3. Write one native \`asyncio.DatagramProtocol\` transport and use HA Network API, with a mock transport and HA network adapter fixtures; no external PlayStation packages.
4. Run real PS5 user-consented **passive** DDP capture in WP-02/03: status 200/620, with/without terminal NUL request, local source ports, app metadata variations and multi-interface/host changes.
5. Distinguish a plausible successful response from cryptographically authenticated identity, exact time, exact app foreground or user activity; do not overstate evidence.
6. Update Protocols 01/02/10, ADR-0005/0021 and future SPEC assertions where live data contradicts the model; no unnecessary ADR/SPEC series.
7. Keep source consent, privacy and no-external-library requirement throughout. Do not begin encrypted Remote Play/PSN, database backup work or unrelated capability reviews as part of this DDP research.

**Outcome:** An implementable **proposed first-party DDP transport/decoder contract** with explicit uncertainty, no off-the-shelf PlayStation client, and no Home Assistant runtime tests, code, packet capture or new SQLite schema.
