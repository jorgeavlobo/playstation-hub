# SPEC-002 — Remote Play byte contract, credential mapping and command safety

**Status:** Proposed, source-derived validation specification; no executable implementation or live console verification  
**Date:** 2026-11-05  
**Primary references:** Protocols 03–07, ADR-0004/0005/0007/0009, pinned playactor source tree `93ee087445db368acaba9ad50099bce56ca9141d`  
**Branch:** `main` documentation only; `next` and `develop` unchanged  
**Hardware scope:** PS5 first; PS4 protocol differences remain separately gated.

> This specification distinguishes **source-observed** fields and constants from **proposed PlayStation Hub behavior** and **unverified** interoperability. Byte-level examples are synthetic/public reference vectors, never private registration secrets. No Sony protocol approval or firmware compatibility is implied.

## 1. Scope and success criteria

Specify exact source-derived Remote Play wake, registration, cryptographic, authenticated session and standby-command interfaces. Define acceptance criteria for byte encoding, key ownership, input validation, timeout/cancellation, protocol framing, replay resistance, Home Assistant integration and command confirmation. This document does not authorize implementation or live interaction.

**Core invariants:** Explicit user pairing, stable console target, no accidental wake, no cross-console credentials, no sensitive logs, no optimistic power state, no mandatory Remote Play for passive LAN monitoring.

## 2. Dependency and trust map

```text
P01/P02 validated console identity + fresh status
   |
   +--> P04 explicit registration PIN + PSN account identifier
   |       +--> P05 registration crypto and validated credentials
   |                 +--> P03 UDP credentialed WAKEUP
   |                 +--> P06 TCP/HTTP init + control socket
   |                           +--> P05 session crypto + framing
   |                           +--> P07 explicit standby command
   |
   +--> P02 post-command LAN confirmation
         -> ADR-0005 reconciled power observation
         -> ADR-0006 session ledger
```

P08 NPSSO/OAuth credentials are not Remote Play registration keys. Any acquisition of `Np-AccountId` must be separately permission/format reviewed; do not assume an online display name is the required binary identifier.

## 3. Source-derived transport/constant register

| Flow | Transport | Port/path | Exact observed source values | Verification |
| --- | --- | --- | --- | --- |
| Wake PS5 | IPv4 UDP | destination 9302 | `WAKEUP * HTTP/1.1`, protocol version `00030010` | P03 source and datagram fixture |
| Wake PS4 | IPv4 UDP | destination 987 | PS4 version `00020020` | Deferred PS4 |
| PS5 registration discovery | IPv4 UDP | local and remote 9295 | request `SRC3`, expected response prefix `RES3` | P04 fixture |
| PS4 registration discovery | IPv4 UDP | 9295 in reviewed implementation | `SRC2` / `RES2` | Deferred PS4 |
| PS5 registration | HTTP over TCP | `:9295/sie/ps5/rp/sess/rgst` | POST, `RP-Version: 1.0` in reviewed mapping | P04 fixture |
| PS5 session init | HTTP over TCP | `:9295/sie/ps5/rp/sess/init` | `RP-RegistKey`, `RP-Version`; receive `RP-Nonce` | P06 fixture |
| PS5 control | Persistent HTTP/TCP socket | `:9295/sie/ps5/rp/sess/ctrl` | `RP-Auth`, encrypted `RP-Did` and RP headers | P06 fixture |
| Session heartbeat | Framed control socket | command codes | incoming `0x00FE`, outgoing `0x01FE` | P06/P07 |
| Login | Framed control socket | command code | `0x0005` | P06/P07 |
| Passcode challenge/answer | Framed control socket | command codes | `0x0004` / `0x8004` | P06/P07 |
| Standby | Framed control socket | command code | `0x0050`, zero payload | P07 |

These values are observed in a community implementation; verify protocol versions, ports, case, line endings and behavior against pinned source and firmware. A port number is not evidence that an arbitrary host is a PlayStation.

## 4. Wake-up byte contract and credential gap

Source-observed outbound fields:

```text
WAKEUP * HTTP/1.1
app-type:r
auth-type:R
client-type:vr
user-credential:<REDACTED>
device-discovery-protocol-version:00030010
```

The actual `user-credential` is **NOT YET FULLY TRACED** from registration response to wake serialization. This is a hard implementation gate. Do not fabricate a value, assume it equals `RP-Key`, `PS5-RegistKey`, a PSN token or a PIN, or log the final datagram.

**Required trace:** Identify the exact source function mapping stored registration fields to wake credential, data type, encoding, length, normalization, leading zeros and per-console principal. Compare against independent source and a synthetic credential fixture; then validate on user-authorized hardware.

**Wake state:** requested -> preflight identity -> sent -> verifying -> confirmed awake / unconfirmed / failed / cancelled. UDP send success means only the datagram was submitted. Confirm with a fresh, identity-matched P02 AWAKE response within bounded deadline.

## 5. Registration byte contract

### 5.1 UDP preflight

- Request: ASCII bytes `53 52 43 33` (`SRC3`).
- Response: starts with ASCII `52 45 53 33` (`RES3`), but source-address, length and correlation checks are additionally required.
- Reviewed implementation binds UDP local port 9295; evaluate port collision with other Remote Play software/HA processes.
- Source default timeout 30 seconds and 100 ms delay before HTTP registration are **reference values**, not approved defaults.
- On unexpected response, duplicate response, timeout or cancellation: close socket, do not advance to credential storage.

### 5.2 HTTP registration

```text
POST http://<validated-console-ip>:9295/sie/ps5/rp/sess/rgst
RP-Version: 1.0
<source-defined additional headers>
<encrypted registration body>
```

Body includes source-observed `Client-Type` and `Np-AccountId`, encrypted with PIN-derived PS5 crypto. Upstream registration preface is 480 bytes. Exact field offsets, full preface, padding, nonce placement, length/endian and encrypted body must be traced from pinned source into a field-by-field table **before claiming a complete wire contract**. No speculative bytes may be added to production fixtures.

### 5.3 Response parsing

The decrypted registration response contains CRLF-separated records including `RP-Key` (16 bytes, commonly 32 hex characters), `RP-KeyType` and `PS5-RegistKey`. Validate required fields, duplicate keys, malformed hex, missing lines, excessive response size and mismatched target. Commit credentials atomically to the per-console repository before declaring pairing ready.

**Credential owner:** validated physical console ID plus authorized pairing principal. Never store PIN as durable state; avoid copying full decrypted response to logs or history.

## 6. Cryptography contract and known-answer vectors

Source-observed PS5 Remote Play primitives:

| Operation | Source-derived behavior | Acceptance |
| --- | --- | --- |
| Session/registration cipher | AES-128-CFB | Match source byte output, not merely round-trip |
| IV derivation | HMAC-SHA256, digest first 16 bytes | Exact KAT |
| IV input | `nonce || uint64_be(counter)` | Counter big-endian, unsigned |
| Nonce | 16 bytes | Reject any other size |
| AES key | 16 bytes | Reject any other size |
| Counters | Independent inbound/outbound, initially zero | Correct increment, no wrap/reuse |
| Registration seed | PIN + PS5-specific lookup/transforms | Independent KAT required |
| Modern PS5 tables | Source-specific key tables | Licensing/provenance review required |
| Legacy Second Screen | AES-128-CBC in other codec | **Do not use** as PS5 Remote Play cipher |

### 6.1 Public source-derived IV test

```text
nonce_hex   = 3e7e7a825973adab2f694346bd44dab5
counter     = 0
expected_iv = 9044408273f8044dca767b5a16394d64
```

This is the publicly documented vector from P05's reviewed `base-test.ts`; verify directly against the pinned test source when building executable fixtures. A single passing vector is insufficient: require counters 0, 1, 2, max-safe boundary, different nonces, both directions, and independent AES-CFB ciphertext KATs.

**Security limitation:** AES-CFB encrypts but does not by itself authenticate ciphertext. Do not assert TLS-like authenticity or invent an authentication tag. Model the actual protocol's trust and authentication semantics and verify the peer identity/registration context.

### 6.2 Crypto verification cases

- Key/nonce length failures, empty PIN, wrong PIN, wrong PSN account ID length/encoding.
- HMAC input order, counter endian, overflow, nonce reuse and direction separation.
- CFB segment size/mode compatibility across Python crypto libraries.
- Registration seed and 480-byte preface byte-for-byte comparison.
- Encryption/decryption against source ciphertext vectors, not just self-consistent round-trip.
- Sensitive buffer handling and no credential logging.
- License/attribution and compatibility of lookup tables before copying code/data.

## 7. Session init and control socket

1. Validate physical target and durable registration record.
2. Connect to `/sie/ps5/rp/sess/init` with the source-required `RP-RegistKey`, `RP-Version` and HTTP headers.
3. Reject unexpected HTTP/application error, missing or malformed `RP-Nonce`.
4. Base64 decode `RP-Nonce` and require exactly 16 bytes.
5. Construct fresh per-session crypto state; do not reuse old nonce/counters.
6. Open `/sie/ps5/rp/sess/ctrl` with encrypted/authenticated headers as source specifies.
7. **Retain ownership of the persistent control socket** after HTTP handshake; generic clients that automatically close/release the socket are insufficient.
8. Complete login/passcode challenge if requested; do not mistake a session-open response for login success.
9. Handle heartbeat and bounded command transmission.
10. Close/clean resources on completion, timeout, failure or unload.

**Critical source-specific questions:** Exact `RP-Did` plaintext/encoding, `RP-Auth` transformation, header ordering/values, HTTP response parsing while retaining the socket, error reason codes, and timing/firmware differences must be recorded as test vectors before implementation.

## 8. Control packet framing

Source-observed eight-byte header:

```text
offset  length  type         meaning
0       4       uint32 BE    payload byte length
4       2       uint16 BE    command type
6       2       uint16 BE    reserved field
8       N       bytes        payload (encrypted when required)
```

**Synthetic standby packet:**

```text
00 00 00 00 00 50 00 00
```

The source's header-only standby packet bypasses payload encryption because no payload exists; it must still be sent only on a successfully authenticated control session. Test partial TCP frames, multiple frames per read, zero-length frames, malformed length, oversized payload, reserved bits, EOF mid-frame, unknown command, fragmented encrypted payload and counter advancement semantics. Never treat TCP `recv` boundaries as message boundaries.

**Heartbeat:** Incoming `0x00FE`, outgoing `0x01FE`, subject to source-defined payload and counter rules. Verify no duplicate heartbeat tasks and bounded liveness timeout.

## 9. Command safety, authorization and idempotency

- Pairing requires explicit user interaction and the console's user-displayed PIN.
- Standby/wake require an explicitly targeted validated console, appropriate stored credentials and Home Assistant permission checks.
- If a standby request targets a console already **freshly confirmed STANDBY**, return an idempotent already-in-state result; **never wake it just to send standby**.
- The reviewed upstream `openRemotePlay` may wake before session creation. PlayStation Hub must override this behavior through an explicit preflight policy.
- If state is stale or unavailable, do not optimistically assume awake; either reject or perform a safe directed status probe under the approved policy.
- Serialize commands per console; different consoles remain independent.
- Sending a standby packet, closing the socket or receiving a generic ack does not necessarily confirm standby. Confirm through a fresh identity-matched P02 standby observation or independently proven response semantics.
- After timeout, report `UNCONFIRMED` rather than success or physical OFF.
- Reconnect must not automatically repeat an uncertain power command.
- No command during passive discovery; no account/console identity guessing.
- No unverified full shutdown, game launch, controller emulation or other speculative actions in v1.

## 10. Protocol state machines

```text
Registration:
  UNPAIRED -> USER_INITIATED -> PREFLIGHT -> UDP_DISCOVERY
  -> HTTP_REGISTRATION -> CRYPTO_VALIDATION -> DURABLE_COMMIT -> PAIRED
  failure/cancel -> CLEANUP -> UNPAIRED or PAIRING_REQUIRED

Control:
  IDLE -> PREFLIGHT -> SESSION_INIT -> CONTROL_CONNECT -> LOGIN
  -> READY -> COMMAND_SENT -> VERIFYING -> CONFIRMED
  timeout/transport failure -> UNCONFIRMED or FAILED -> CLEANUP

Wake:
  IDLE -> TARGET_VALIDATION -> WAKE_DATAGRAM_SENT -> VERIFYING
  -> AWAKE_CONFIRMED | UNCONFIRMED | FAILED | CANCELLED
```

Do not persist ephemeral session counters, nonces or login passcodes as pairing credentials. Use ADR-0005 `run_id` and attempt generations to reject callbacks from previous unload/reload cycles.

## 11. Error taxonomy

| Category | Source condition | Safe response |
| --- | --- | --- |
| `identity_mismatch` | Host ID changed at address | Block keys/commands, rediscover |
| `not_paired` | No per-console credentials | Explicit pairing flow |
| `pin_rejected` | Registration authentication fails | Bounded user retry, no partial commit |
| `registration_timeout` | Missing RES3 or HTTP reply | Cleanup, no credentials |
| `crypto_vector_mismatch` | Derived bytes disagree with source KAT | Block implementation/release |
| `invalid_nonce` | RP-Nonce malformed/wrong length | Abort session |
| `invalid_registration_key` | Missing/incorrect RP-Key or RegistKey | Reject and repair |
| `control_http_rejected` | Init/control endpoint error | Typed protocol failure |
| `login_passcode_required` | Console requests passcode | User-directed secure input |
| `login_passcode_invalid` | Challenge response rejected | No unbounded retries |
| `frame_malformed` | Invalid length/type/header | Abort safely |
| `heartbeat_timeout` | Liveness expired | Close socket, command uncertain |
| `command_unconfirmed` | No fresh final state | Never optimistic power change |
| `storage_commit_failed` | Pairing keys not durably stored | Pairing not ready |
| `cancelled` | HA unload or user cancellation | No retry or stale callback |

## 12. Deterministic byte-level acceptance matrix

| Test | Requirement | Expected |
| --- | --- | --- |
| RP-B001 | Encode `SRC3` | Exact 4 bytes `53 52 43 33` |
| RP-B002 | Parse `RES3` from expected source | Accepted only under bounded source/size rules |
| RP-B003 | Reject spoofed `RES3` | No registration |
| RP-B004 | Build registration HTTP request | Correct path, method, required headers |
| RP-B005 | Registration preface length | Exactly 480 bytes for pinned source variant |
| RP-B006 | Registration seed KAT | Exact independent reference bytes |
| RP-B007 | HMAC IV KAT | Exact public expected IV |
| RP-B008 | AES-CFB KAT | Exact ciphertext and plaintext |
| RP-B009 | Counter encoding | uint64 big-endian and correct advancement |
| RP-B010 | Decode RP-Nonce | Strict base64, exactly 16 bytes |
| RP-B011 | Build session init headers | Exact byte-safe required values |
| RP-B012 | Build control auth headers | RP-Did/RP-Auth exact verified transformations |
| RP-B013 | Build standby packet | `00 00 00 00 00 50 00 00` |
| RP-B014 | Fragmented TCP read | Reassemble complete framed message |
| RP-B015 | Multiple packets in one read | Decode each exactly once |
| RP-B016 | Malformed/oversized length | Reject before allocating large buffer |
| RP-B017 | Unknown packet type | Bounded safe handling |
| RP-B018 | Heartbeat exchange | Correct request/response and counter behavior |
| RP-B019 | Login/passcode challenge | Correct type, offset, error handling |
| RP-B020 | Wake credential mapping | Exact source-traced value; **OPEN** |
| RP-B021 | Wake datagram | Correct allowed fields/port/format |
| RP-B022 | Command ack versus final state | Send alone never confirms power |
| RP-B023 | Wrong physical console at reused IP | Keys never transmitted |
| RP-B024 | Concurrent same-console command | Serialized; no duplicate session |
| RP-B025 | Cancel during handshake | Socket and secrets cleaned, no late callback |
| RP-B026 | Unpair/re-pair | Old keys scoped/deleted, no history corruption |
| RP-B027 | PS4/PS5 cross-protocol confusion | Reject incompatible version/port/key |
| RP-B028 | No Sony/Remote Play credentials | LAN monitoring still works |

## 13. Home Assistant and live-hardware acceptance matrix

| Gate | Evidence required | Current status |
| --- | --- | --- |
| G1 | Byte-level parser/serializer KAT suite passes | Not implemented |
| G2 | Independent crypto vectors and license review | Not complete |
| G3 | Wake user-credential fully source-traced | **Open blocker** |
| G4 | Registration/PSN account identifier byte contract | Incomplete |
| G5 | PS5 registration succeeds with explicit user PIN | Not tested |
| G6 | Persistent authenticated control socket, login, heartbeat | Not tested |
| G7 | Wake and standby confirmed by fresh LAN state | Not tested |
| G8 | No surprise wake on standby command; idempotency | Not tested |
| G9 | Multiple consoles, separate credentials and concurrent operations | Not tested |
| G10 | Security/permission/redaction and network mismatch tests | Not implemented |
| G11 | HA OS restart/unload/re-pair and credential restore | Not tested |
| G12 | Supported firmware/version compatibility and release checks | Not established |

**Gate rule:** A source citation, synthetic byte sample or documented expected result is not a passing test. Record executable test name, version, fixture provenance, expected/actual bytes, reviewer, hardware firmware and date before changing status.

## 14. Test harness design

- **Pure Python:** deterministic packet builders/parsers and cryptographic primitives without Home Assistant imports.
- **Synthetic fixtures:** only fictional host IDs, account IDs, keys, PINs and packet payloads; public upstream test vectors may be used subject to license.
- **Fake UDP/TCP transports:** controllable clock, fragmented/coalesced frames, socket errors, latency, cancellation, spoofed source and reused IP.
- **Fake HTTP Remote Play server:** predetermined init/control response headers, nonce, challenge and partial-body behavior.
- **Credential repository fake:** atomic commit, generation conflict, corruption and disk-full injection.
- **HA tests:** targeted services/buttons, admin ACL, command state, reload/unload and multiple config entries.
- **Live hardware:** user-authorized PS5, controlled PIN, known firmware, awake/standby transitions and real network conditions. Do not commit packet captures or actual credentials.

## 15. Security and provenance requirements

- Review licenses of playactor, Chiaki-derived tables and all borrowed test vectors before copying any source material.
- Treat protocol constants as reference facts, not Sony-authorized third-party protocol guarantees.
- Validate target console identity before every privileged connection; host-id alone is not cryptographic proof against a hostile LAN endpoint.
- HTTP over TCP port 9295 is not HTTPS; application-layer encryption and authentication must be evaluated on their own terms.
- Avoid custom cryptographic algorithm invention; use vetted library primitives with verified byte-level compatibility.
- Restrict outbound sockets to validated console addresses and expected ports; no arbitrary host/port from user-controlled responses.
- Never persist transient PIN, passcode, session nonce, session key/counter or decrypted raw response.
- Never expose RP-Key, RegistKey, wake credential or Sony tokens through entity state, frontend, diagnostics or logs.
- Provide explicit user confirmation and permission checks for wake/standby/pairing; background discovery has no side effects.
- Keep LAN-only operation independent from Remote Play failures.

## 16. Open research requiring further source inspection

1. Trace wake `user-credential` exact mapping from registration response to serialized datagram.
2. Derive full PS5 registration 480-byte preface layout with offset/size/endianness table.
3. Verify `Np-AccountId` representation and permitted method of acquisition.
4. Record exact seed, nonce, RP-Did and RP-Auth transformations from pinned upstream.
5. Confirm counter advancement on zero-payload frames and encrypted payload boundaries.
6. Trace login response offset 8 and all passcode/result codes with source test fixtures.
7. Confirm how HTTP control connection is retained without accidentally consuming or closing its socket.
8. Validate command completion semantics beyond generic connection close.
9. Review key-table license/provenance and applicable Sony protocol/terms constraints.
10. Validate supported PS5 firmware variants and explicit PS4 deferral.
11. Determine safe default timeouts, retry limits and resource budgets.
12. Decide whether registration can coexist with other Remote Play clients on local port 9295.

## 17. Source register

### Project
- [Protocol 03 — Wake](../protocols/03-console-wakeup.md)
- [Protocol 04 — Registration](../protocols/04-remote-play-registration.md)
- [Protocol 05 — Cryptography](../protocols/05-remote-play-cryptography.md)
- [Protocol 06 — Session](../protocols/06-remote-play-session.md)
- [Protocol 07 — Commands](../protocols/07-remote-play-commands.md)
- [ADR-0004 — Identity](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 — Observations](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0007 — Credentials](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0009 — HA actions](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [SPEC-001 — LAN discovery](SPEC-001-lan-discovery-acceptance-matrix.md)

### Pinned upstream implementation and official HA references
- https://github.com/dhleong/playactor/tree/93ee087445db368acaba9ad50099bce56ca9141d
- https://github.com/dhleong/playactor/blob/main/src/waker.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/registration.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/crypto/base.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/crypto/modern.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/codec.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/session.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/packets.ts
- https://github.com/FunkeyFlo/ps5-mqtt
- https://developers.home-assistant.io/docs/dev_101_services/
- https://developers.home-assistant.io/docs/core/entity/button/

**Outcome:** Source-derived byte contract, missing byte-level proofs, 28 deterministic test cases and 12 release gates documented. All release gates remain unpassed. No executable code, real pairing or device command was performed.

## Command-result source regression additions — 2026-11-06 (NOT_RUN)

[Triangulated upstream sources](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md) show that `ps5-remoteplay.wake()` sends UDP WAKEUP without waiting (CLI optionally waits); `playactor.Waker.wake()` waits for its own potentially over-permissive AWAKE parser; both `playactor RemotePlayDeviceConnection.standby()` and the Python port rely on session end. **Specifically, the Python port catches timeout while waiting for close and its outer standby wrapper can return True without a new status 620.**

Add fixtures `SRC-CMD-01` (wake send succeeds but no 200 -> NOT_CONFIRMED), `SRC-CMD-02` (standby session closes without 620 -> NOT_CONFIRMED), `SRC-CMD-03` (standby receive loop times out but wrapper returns true -> NOT_CONFIRMED), `SRC-CMD-04` (stale/wrong identity, conflicting commands -> denied/serialized). Preserve `REQUESTED/SENT/VERIFYING/CONFIRMED/INDETERMINATE/FAILED` separate from physical console facts. No credential or firmware test done. Do not copy AGPL/GPL implementations or crypto material without legal review.

## First-party crypto feasibility and command safety restriction (2026-11-06)

**New maintainer requirement:** No external PlayStation libraries and no new pip/npm runtime dependencies. [Policy](../architecture/first-party-dependency-sovereignty-policy.md), [source audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md). Use own framing/byte parser/state flow and Python stdlib; no subprocess with playactor, no Chiaki/pyremoteplay code, no vendor crypto tables. Python stdlib provides HMAC/SHA/hash and TLS but not general raw AES-128-CFB/CBC used by reviewed Remote Play source. An audited AES backend must be independently vetted/approved; hand-written AES, ctypes/OpenSSL FFI or copying third-party encryption code is NOT an approved workaround.

**Future failure cases:** FIRST-08 (sent wake without fresh verified 200 -> not confirmed); FIRST-09/10 (encrypted pairing/standby disabled when crypto backend absent, no invented success); FIRST-16 (license/source provenance), plus already documented socket-close-only standby invalid and payload integrity. Actual Remote Play implementation remains `BLOCKED_CRYPTO_BACKEND` while passive LAN remains independently viable. No tests executed.

## Deep source-derived first-party pairing/control acceptance handoff — RP-F01–32 (NOT_RUN, 2026-11-06)

**Primary evidence:** [Remote Play registration/control pinned-source audit](../research/first-party-ps5-remote-play-registration-control-source-audit-2026-11-06.md) and [project operation contract](../architecture/first-party-remote-play-registration-control-contract.md). The 32 RP-F trace IDs in that audit supplement the existing SPEC-002 descriptions; **all NOT_RUN**, not new numbered test suite, no code/CI/hardware evidence.

New high-value fixture requirements: (a) distinguish `SRCH` UDP 9302 from `SRC3/RES3` UDP 9295 and check source-reported suffix NUL variation, (b) manual Pair Device number separate from later login passcode, (c) validate decrypted registration `PS5-RegistKey`/`RP-Key` and account-owner scope, (d) GET init RP-Nonce 16-byte decode and error/version handling including source-claimed `Content-Length: 0`, (e) **control HTTP response and first heartbeat in same TCP write** without header reader overconsumption, (f) cipher header order/outbound-inbound counters and zero-payload frames, (g) login/passcode/heartbeat/unknown-frame and active-session conflict, (h) standby command 0x50 never physically confirmed by socket close alone, (i) HA reload/unload/permission and no background Remote Play, (j) no additional runtime package, no unapproved PyCA and no copied protocol crypto tables.

**Required release gate:** pairing, authenticated control and standby remain **BLOCKED_CRYPTO_BACKEND_APPROVAL** until a separately approved secure primitive, independent lawful account/credential procurement, clean-room crypto specification, current PS5 firmware compatibility, permission and noninterference tests have all passed. All passive DDP and local title monitoring remain independent and unblocked by optional controls.

## PS5 cryptographic derivation/version source audit — CRY-01–20 (NOT_RUN, 2026-11-07)

**Primary source:** [PS5 Remote Play crypto derivation/versions/independent-vector/security audit](../research/ps5-remote-play-crypto-derivation-versions-and-security-source-audit-2026-11-07.md), proposed [first-party operation contract](../architecture/first-party-remote-play-registration-control-contract.md), and [Protocol 05 addendum](../protocols/05-remote-play-cryptography.md). Its 20 `CRY-01..20` are **qualitative future review/test traces**, not a new numbered SPEC or 20 executed tests. The existing SPEC-002 status remains ALL NOT_RUN.

Future full coverage MUST separate: nonce/seed/PIN/aeropause stages and **lawful provenance of PS5-specific lookup tables**, HMAC-SHA256 full 32-byte output plus **first 16-byte IV** using uint64-BE counter, AES-128-**CFB128** versus incompatible CFB8/CBC, outbound/inbound state and HTTP header ordering, no cipher counter on zero-payload frames, server-type decrypt before binary login, loss/cancellation/overflow, strict supported `RP-Version` with **firmware version separate**, independently established modern PS5 test oracles beyond Playactor-derived Python fixture, and current real firmware/consented pairing tests.

**Source-safety guard:** Optional Chiaki Mbed TLS conditional HMAC-SHA256 path appears to have a too-small digest destination; OpenSSL branch has full output. This is an **unverified source concern**, not a demonstrated exploitable vulnerability. Our future HMAC should always produce full-length output into a correctly sized buffer and truncate only afterwards; do not import external C code or cipher tables. The user has NOT approved direct PyCA import and no new pip package, handmade AES, source copied keys or Sony OAuth credentials is authorized. Keep pairing/standby `BLOCKED_CRYPTO_BACKEND_APPROVAL`, without impacting LAN.
