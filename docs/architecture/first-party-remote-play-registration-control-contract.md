# PlayStation Hub — First-party PS5 Remote Play pairing, control and standby contract

**Date:** 2026-11-06
**Status:** TECHNICAL CONTRACT PROPOSED / USER REQUIREMENT FOR FIRST-PARTY CODE ACCEPTED / NO CODE OR HW TEST
**Source audit:** [PS5 Remote Play registration/control deep source review](../research/first-party-ps5-remote-play-registration-control-source-audit-2026-11-06.md)
**Existing specs:** Protocols 03–07, [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md) and [WP-00B](WP-00B-research-freeze-and-implementation-readiness.md).
**Critical prerequisite:** encrypted pairing/control remains `BLOCKED_CRYPTO_BACKEND_APPROVAL`. There is no approval to import HA-pinned PyCA or another third-party library, implement custom AES, or use unauthorized Sony account APIs.

## 1. Product intent / exclusion

Build a first-party PlayStation Hub with passive LAN discovery/status and local application evidence fully independent of Remote Play, plus **future optional explicitly authorized** Wake and Standby controls. A new default service must **never silently open a Remote Play session** just to poll current power or game metadata; a control session can contend with real game streaming and user state.

No playactor, Chiaki-ng, PS5-MQTT, ps5-remoteplay, PSNAWP, Node CLI or external protocol library is included. Python stdlib and supported Home Assistant APIs provide sockets and framing; secure cryptographic primitives require a separate explicit decision. Code, comments, tests, UI metadata and protocol documents must remain English.

## 2. Four independent credentials and scopes

| Credential or datum | Origin | Lifetime & restrictions |
| --- | --- | --- |
| DDP `host-id` | Unauthenticated LAN UDP response | Candidate physical device identity only; cannot authorize pairing |
| PSN account identifier | Verified/properly authorized user-account flow | Pairing input; account-scope, never presumed from console name |
| Pair Device number | PS5 Settings → System → Remote Play → Pair Device | Short-lived explicit user input for registration; never stored in history |
| User login passcode | Console user may request during authenticated control login | Different from pairing PIN; short-lived secret; do not silently reuse |
| `PS5-RegistKey`, `RP-Key`, key type and console bind | Validated decrypted pairing result | Restricted console/account credential record, not a game/usage observation |

The Sony manual-pairing screen and same-account requirement are official product behavior. The registered keys' byte format and transport details derive from community implementation source, not a Sony public API contract. Do not put any secret in durable activity reports, dashboard WebSocket replies or diagnostic logs.

## 3. Optional operation states and source quality

### Pairing state machine (proposed)

```text
UNPAIRED
  → WAITING_FOR_USER_PAIR_SCREEN_AND_NUMBER
  → PREPARING_SRC3_UDP
  → PREFLIGHT_VERIFIED_SOURCE_ONLY
  → ENCRYPTING_REQUEST   // blocked without approved AES/key provenance
  → POSTING_REGISTRATION
  → VALIDATING_KEYS
  → PAIRED
```

Every transition may end in `FAILED`, `CANCELLED`, `EXPIRED`, `UNAVAILABLE` or `USER_ACTION_REQUIRED`. No request retries guessing PINs; validated response data cannot automatically associate a different PSN account/physical console. Operation ID, console owner, account scope and local run generation isolate concurrent work.

### Short-lived control and standby state machine (proposed)

```text
IDLE
  → USER_AUTHORIZED
  → SESSION_INIT_REQUEST
  → NONCE_VALIDATED
  → CTRL_HTTP_HANDSHAKE
  → BINARY_CTRL_ATTACHED
  → LOGIN_REQUEST
  → USER_PASSCODE_REQUIRED? → LOGIN_CONFIRMED
  → STANDBY_FRAME_SENT
  → DDP_VERIFICATION
  → STANDBY_REPORTED_620
  → CLEANUP_TERMINAL
```

`SESSION_CONFLICT`, `AUTH_FAILED`, `FRAME_INVALID`, `NETWORK_ERROR`, `TIMEOUT_UNCERTAIN`, `STOPPED` and `WORKER_FENCED` are distinct terminal/error paths. A successful write/drain, missing TCP heartbeat or socket close is **not** the same as `STANDBY_REPORTED_620`. Fresh 620 remains a DDP source report, not proof of exact transition time or exact causal command acknowledgement (DDP request lacks an echoed nonce).

## 4. Verified-source message-stage register and ownership

| Phase | Endpoint and source-observed grammar | Own-code component | Critical invariant |
| --- | --- | --- | --- |
| Passive DDP (already separately researched) | UDP PS5 port 9302, `SRCH` | `LanDiscoveryTransport` | No credentials, no Remote Play session |
| Registration preflight | UDP PS5 port 9295, `SRC3`→`RES3`; source terminator variants | `PairingPreflightTransport` | Selected console, bounded reply wait; no PSN/outside network |
| Registration | TCP 9295, POST `/sie/ps5/rp/sess/rgst`, encrypted PIN/account payload | `RegistrationClient` + approved backend | Key validation before persistence |
| Session initialization | TCP 9295, GET `/sie/ps5/rp/sess/init`, `RP-Nonce` 16-byte result | `SessionInitializer` | No implicit retries if session reserved; validate nonce |
| Control negotiation | TCP 9295, GET `/sie/ps5/rp/sess/ctrl` with ordered encrypted fields | `ControlHandshake` | **Same TCP socket** becomes binary stream; HTTP parser must not discard frames |
| Binary control | Eight-byte BE `length, type, reserved`; payload-only encryption | `ControlFrameCodec` | Encrypt/decrypt counter ownership; frame bounds/unknown types |
| User login | Type `0x0005` and optional passcode `0x0004` / `0x8004` | `ControlLoginActor` | Pair number != user passcode; never leak |
| Heartbeat | `0x00FE` / `0x01FE` | `ControlHeartbeatActor` | Keep session protocol alive while user operation is active |
| Standby | Send `0x0050` then independently check PS5 DDP `620` | `PowerOperation` + existing DDP reader | Never affirm standby on send/TCP-close alone |

These are **design-level component names**, not files created. Distinguish remote PlayStation protocol traffic from cloud PSN authentication. Do not reuse generic HA aiohttp connections for a raw TCP socket takeover; native HA HTTP helper is reserved for supported optional cloud APIs.

## 5. Protocol/crypto invariants

- **HTTP header reading:** Protect against partial response lines, multiple TCP chunks, oversized/malformed headers, unexpected body/transfer framing, error reason headers, and an HTTP response concatenated with the first encrypted heartbeat in one TCP write. Preserve over-read bytes in the same owned stream.
- **GET compatibility:** Include `Content-Length: 0` in planned Remote Play GETs where pinned sources require it. It is an upstream PS5-specific compatibility observation, not a general HTTP rule.
- **Counter/state:** Each nonempty encrypted header-field or binary payload consumes a counter in the correct direction/order; 8-byte header-only frames do not consume payload counters. Accept only bounded unsigned counters; reject replay/overflow/gap without guessing how to resynchronize.
- **Cipher provenance:** Reviewed sources use AES-128-CFB with HMAC-SHA256-derived IV/counters; other codec contexts have AES-CBC. No cipher-mode swapping, in-house AES, undocumented OpenSSL ctypes, copied AGPL tables or test fixtures. HA Core ships PyCA as a platform dependency but its use is **not yet approved** under no-external-library rule.
- **Hardware authority:** Source code, fake console tests and backward-compatible PS4 formats do not prove current retail PS5 interoperability. Actual firmware matrix is required.
- **Authentication identity:** No Sony credential reuse from another application's OAuth client, no fake first-party Sony login form, no auto reuse of another user's paired RP keys.
- **Control interference:** Only an explicitly requested human/admin control operation may open a session; do not use a long-lived Remote Play socket for passive monitoring, and never take over an occupied session without a separate user-supported policy.
- **Storage:** Pair credentials stored separately from history with privacy/security controls. Purging an integration credential must not erase archived usage of the independent physical console.
- **Lifecycle:** Per-console control lease and terminal close proof, single operation per owner (with cancellable queue), no late-generation success after unload/reload, command result separate from physical sample.
- **Availability:** Missing/blocked encrypted control leaves LAN status/title monitoring and archive panel operational.

## 6. Admission/release gate register (not yet passed)

| Gate | Owner | Evidence required |
| --- | --- | --- |
| RP-G01 | Maintainer | Explicit approve/refuse HA-bundled PyCA AES primitive exception |
| RP-G02 | Protocol/licensing | Clean-room mapping of Sony key derivation tables/rights; no copying GPL/AGPL |
| RP-G03 | User/auth | Legitimate PSN account ID acquisition/provisioning without unauthorized OAuth |
| RP-G04 | Native UDP | SRC3 preflight packet/terminator/source validation on actual firmware |
| RP-G05 | Native TCP/HTTP | Regist/init/ctrl HTTP boundaries and socket takeover against fake + real console |
| RP-G06 | Crypto | Independent AES/IV/counter/replay known-answer tests using permissible fixtures |
| RP-G07 | Session | Login/user passcode/heartbeat/error types and safe session conflict handling |
| RP-G08 | Power | DDP standby verification after 0x50; no optimistic state or history |
| RP-G09 | HA security | Config Flow/secret storage/ACL/reload/unload, no passive session interference |
| RP-G10 | Release | Supported firmware+Core/Python matrix, no additional pip dependency and CI proof |

**All gates currently OPEN/BLOCKED/NOT_RUN.** These are dependencies for WP-06, not blockers for WP-01/02/03 LAN or the first-party ledger/panel. The user's direction to research does not authorize implementation.

## 7. Test handoff and non-goals

[Full source audit](../research/first-party-ps5-remote-play-registration-control-source-audit-2026-11-06.md#8-detailed-future-acceptance-trace-matrix--all-not_run) contains 32 focused RP-F01–32 *future* scenarios. Extend [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md) rather than adding a new SPEC number or counting source descriptions as passing tests.

No provider PSN API, open-source codebase or Home Assistant component automatically supplies a cryptographically accepted hardware identity. The *first-party integration* should degrade visibly when control cannot be offered, without pretending it supports standby or copying a third-party implementation.

**Outcome:** A scoped, testable, independently implementable architecture contract for **when controls are authorized and cryptographic prerequisites resolved**. Not a working Remote Play client, not a release promise, not an automatic dependency grant and not a hardware test.
