# PlayStation Hub — First-party PS5 Remote Play registration, control-session and standby source audit

**Date:** 2026-11-06
**Status:** DEEP PINNED SOURCE REVIEW / PROTOCOL DESIGN ONLY / NO CODE / NO CONSOLE TEST
**Purpose:** Explain the verified-by-source PS5 pairing/control wire flow deeply enough to implement a clean, original Python transport in a later authorized work package, without external PlayStation runtime libraries.
**Maintainer rule:** No playactor, Chiaki, ps5-remoteplay, pyremoteplay, PS5-MQTT, PSNAWP, Node process, console payload, vendored protocol code/key tables or new runtime packages. Python stdlib and supported Home Assistant APIs are allowed. A narrow direct PyCA AES primitive already shipped in HA Core is only a **candidate pending express maintainer approval**. No homemade AES.
**Scope:** Local PS5 Remote Play registration and short authenticated control to request standby; PSN remote hole punching, streaming audio/video, unrelated game data, SQLite backups and PS4 protocol variants are excluded.
**Documentation integration:** [Protocol 04](../protocols/04-remote-play-registration.md), [05](../protocols/05-remote-play-cryptography.md), [06](../protocols/06-remote-play-session.md), [07](../protocols/07-remote-play-commands.md), [SPEC-002](../specifications/SPEC-002-remote-play-byte-contract-and-safety.md), [new operation contract](../architecture/first-party-remote-play-registration-control-contract.md) and [Architecture Guide](../../ARCHITECTURE_GUIDE.md).

> **Evidence classification:** SONY_OFFICIAL means user-facing supported setup/settings, NOT an official Sony wire specification. PINNED_SOURCE means directly read at an exact third-party commit. PORTED_TEST means a synthetic test of code derived from another project, not independently measured firmware. PRODUCT_PROPOSED means an unapproved implementation rule. HARDWARE_NOT_RUN means we have not attempted pairing or issued network requests to the user's PlayStation.

## 1. Source register

| ID | Source | Exact role / evidence boundary |
| --- | --- | --- |
| RP-S01 | [Sony PT-PT PS Remote Play on PC/Mac](https://www.playstation.com/pt-pt/support/games/playstation-remote-play-on-pc-and-mac/) | Official PS5 setting, same-account requirement, manual Pair Device number and same LAN; no proprietary packet grammar |
| RP-S02 | [Sony Remote Play settings](https://www.playstation.com/en-us/support/games/remote-play-settings/) | Pair Device, Enable Remote Play, per-user settings, Connection History |
| RP-S03 | [Sony troubleshooting](https://www.playstation.com/pt-pt/support/games/ps4-remote-play-connection-troubleshooting/) | Network, same account, latest firmware, rest-mode setup; no authorization of our reverse-engineered API |
| RP-S04 | [playactor registration.ts at a9e72d67](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/registration.ts) | UDP preflight SRC3/RES3 on 9295, small post-search delay, POST registration endpoint, encrypted body and key parsing |
| RP-S05 | [playactor protocol.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/protocol.ts) | Minimal source HTTP patterns, response errors, big-endian control packet reader, heartbeat |
| RP-S06 | [playactor session.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/session.ts) | GET session nonce, GET control header negotiation on same TCP socket, encrypted fields, login |
| RP-S07 | [playactor packets.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/packets.ts) | 8-byte big-endian length/type/zero header; standby 0x50, login 0x05, heartbeat reply 0x1FE |
| RP-S08 | [playactor codec.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/codec.ts) | Independent encryption/decryption counters; header-only frames bypass cipher; payload encrypted |
| RP-S09 | [playactor crypto/base.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/base.ts) | AES-128-CFB, HMAC-SHA256-derived IV (nonce + big-endian counter), version-specific transform |
| RP-S10 | [Chiaki-ng regist.c at 43728af2](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c) | Independent C registration source, NUL-inclusive SRC3, port 9295, handshake and response validation; AGPL license |
| RP-S11 | [Chiaki-ng ctrl.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/ctrl.c) | Independent control message types 0x50, 0xFE/0x1FE, login/PIN; no secret PIN logging, concurrent control send |
| RP-S12 | [Chiaki-ng session.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/session.c) | Session nonce, RP-Version validation, credential failure distinctions, 9295 and session startup |
| RP-S13 | [ps5-remoteplay registration.py at 61e1f7dc](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/registration.py) | Python port of playactor; SRC3 without explicit NUL, retries, 0.1s delay, key validation |
| RP-S14 | [ps5-remoteplay HTTP helper](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/http.py) | Minimal asyncio HTTP/1.1 parser preserving TCP binary stream after headers; 0-length GET request body |
| RP-S15 | [ps5-remoteplay session.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/session.py) | GET init nonce, 0.2s connect delay, ordered encrypted request headers, frame read, login/passcode, standby with swallowed timeout |
| RP-S16 | [ps5-remoteplay test_session.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/tests/test_session.py) | Fake TCP console tests header+heartbeat coalescing, passcode, session errors and reset; synthetic tests, not hardware proof |
| RP-S17 | [HA Core 2026.11 pyproject.toml](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml) | cryptography==50.0.2 already Core-required, not stdlib and not an approved user exception |
| RP-S18 | [PyCA 50.0.2 decrepit CFB](https://cryptography.io/en/50.0.2/hazmat/decrepit/) | AES-CFB legacy mode exists under the decrepit compatibility interface; use only after approval and security review |

## 2. Correctly separate four identity/credential problems

1. **Physical PS5 DDP identity:** unauthenticated self-reported host-id / address from passive UDP. This is a device candidate, not a trusted account identity or registration credential.
2. **Sony/PSN account identifier:** the original [playactor registration.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/registration.ts) carries `Np-AccountId` into the encrypted registration payload. Obtaining an account ID via authorized user flow/manual validated input is **an independent prerequisite**. We must not copy another application's Sony OAuth client credentials or assume undocumented endpoints are authorized.
3. **Pair Device number on PS5:** the **manual registration PIN** displayed by Settings > System > Remote Play > Pair Device. Sony officially documents the action. This is used to establish registration/pair credentials while the console is on the pairing screen.
4. **Later user-login passcode:** a control session can request an *additional* login PIN/passcode frame (0x04 request, 0x8004 response) after registration, if that PlayStation user is protected. It is **not** the Pair Device number. Never silently reuse/store the registration PIN as a user passcode.

Successful registration produces separate console-scoped secret values such as `PS5-RegistKey` and `RP-Key` and possible `RP-KeyType`. Keep them in authorized private configuration scope, never in SQLite activity history, screenshots, DDP diagnostics, public panel data or routine logs. **Account A registration credentials are not automatically valid for Account B or Console C**.

## 3. Wire stages — derived from actual source, not Sony public protocol guarantee

### Stage A: manual user action and safe preflight

**SONY_OFFICIAL:** The user explicitly enables Remote Play for the relevant user and selects Pair Device on an awake PS5; Sony requires same network for manual pairing and the number shown on screen. The feature is intended for the same PlayStation account as the console.

**PINNED_SOURCE:** A UDP registration preflight precedes HTTP POST. Playactor sends `SRC3` to **UDP 9295**, waits for response beginning with `RES3`, then waits roughly **100 ms** before the next step. Chiaki-ng also uses SRC3/RES3, but its C `send` transmits the ASCII marker **with a terminal NUL** (`strlen + 1`), while the reviewed Python port sends `b"SRC3"` without an explicit terminal NUL. This source difference must be tested; it is not evidence that either version is universally mandatory.

**Important:** This is a distinct **registration preflight** on 9295, NOT the normal passive DDP `SRCH` on 9302. Do not conflate their sockets, discovery versions, listener lifecycle or acceptance windows. Prefer directed unicast to the manually selected validated PS5. A mere `RES3` prefix match is untrusted until source address/port and intended console context are verified; protocol lacks identified cryptographic proof in this step.

### Stage B: encrypted registration request

Both playactor and Chiaki-ng use PS5 registration route **POST `/sie/ps5/rp/sess/rgst`** on **TCP 9295**, with `RP-Version` and a PIN-derived encrypted registration payload. The inspected Python port identifies PS5 `RP-Version` as `1.0`.

- Inputs: validated PS5 target, explicit pairing PIN, PSN account identifier and cryptographically secure registration nonce. Never store/log PIN in durable activity data.
- Payload includes `Client-Type` and `Np-AccountId` in source versions and is wrapped by version-specific cryptographic data. Byte framing, padding, key transformation and private table provenance require an independent clean specification and specific rights/security review.
- Response is decrypted and parsed as key-value fields. Verify the required `PS5-RegistKey` and `RP-Key`; Chiaki additionally tracks key type, console MAC and nickname fields. A nickname or host-id alone is not a secret.
- Only when registration **completes and validates** should a protected credential record be admitted; if HTTP success is returned with invalid key formats, the operation is FAILED rather than registered. Do not write the secrets before validation.
- A previously expired Pair Device number should lead to explicit new user input; never automatically replay old PIN requests or brute-force numbers.

### Stage C: session initialization without streaming

The registered credential is presented by **GET `/sie/ps5/rp/sess/init`** at TCP 9295. Source implementations expect the PS5 to return `RP-Nonce`, a base64-encoded **16-byte server nonce**. A missing, wrong-length or invalidly encoded nonce is a protocol error, not a blank default.

**Critical HTTP compatibility nuance:** [playactor protocol.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/protocol.ts) and [ps5-remoteplay http.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/http.py) put `Content-Length: 0` even on GET. Their code comments say some consoles respond `403` without it. This is a **community source-reported interoperability trap**, not a standard HTTP requirement or verified current firmware behavior.

A session version mismatch, another active Remote Play session, wrong credentials or unauthorized user must become a typed failure with no unintended state mutation. Avoid blindly retrying a session initialization when the original may remain reserved.

### Stage D: control-channel handoff on one TCP socket

- The source code sends **GET `/sie/ps5/rp/sess/ctrl`** with encrypted `RP-Auth`, `RP-Did`, `RP-OSType`, `RP-StartBitrate`, `RP-StreamingType` and protocol/version metadata.
- **Order of encrypted header creation matters** because the source cipher tracks a per-direction counter. The Python port's comment explicitly states the request header order occupies counter positions `0..4`. Changing a dictionary order without understanding this may invalidate the control negotiation.
- The resulting HTTP response contains an encrypted `RP-Server-Type` header. The client validates/decrypts it before processing binary frames.
- **The same established TCP connection then becomes an encrypted binary frame channel.** A generic HTTP helper may release, pool or close its connection and is not an appropriate abstraction for this socket takeover. Own a narrowly scoped `asyncio.open_connection` + bounded HTTP/1.1 header reader for this protocol, no extra Python package and no copied upstream implementation. Avoid over-reading into the first heartbeat: the Python port's fake-console test sends the HTTP response and first binary heartbeat together to enforce that invariant.
- Do not infer the control-only handshake is harmless to a person already using Remote Play. Session negotiation can reserve resources, interfere with existing sessions or display connection events. This must be an explicit requested operation, **never automatic background polling**.

### Stage E: post-handshake binary control

[playactor packets.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/packets.ts) and Chiaki-ng `ctrl.c` agree on **8-byte frame header**:

```text
uint32_be payload_length  // length excludes header, no signed overflow
uint16_be message_type    // e.g. login, passcode, heartbeat, goto_bed
uint16_be reserved = 0
followed by payload_length bytes
```

Source-recognized message kinds:
- Login request `0x0005`.
- Server user-passcode request `0x0004`, client response `0x8004`.
- Server heartbeat `0x00FE`, client heartbeat reply `0x01FE`.
- GOTO_BED / standby command `0x0050`.

**Caveat:** These are implementation-source constants, not a signed Sony public protocol registry. Unknown message types should not crash, block heartbeat, trigger unintended commands or be reflected unsafely.

**Crypto sequencing:** The header is unencrypted in the reviewed codec. Only nonempty payloads advance **distinct send and receive encryption counters**. An eight-byte header-only control frame does **not** consume a cipher counter; decryption of a control HTTP header may already have consumed a separate receive-side counter before binary frames start. Test exact counter state on initiation, encrypted headers, heartbeat-only frames, login, passcode and other payloads. Never randomly reset an active counter after reconnect/partial send.

## 4. Command result ≠ physical power result

The original Playactor standby wrapper sends `0x0050` and waits for the control socket to terminate. In the Python port, the lower-level standby coroutine catches/only logs an expired receive-close deadline while the outer wrapper can return success; neither is an independent status probe. Thus:

1. `COMMAND_ACCEPTED`: authorization/valid console/account/credentials.
2. `CTRL_SESSION_ESTABLISHED`: authenticated short control session, possibly intrusive.
3. `FRAME_SENT`: standby frame written/drained; no physical state claim.
4. `VERIFYING`: bounded independent DDP source observations on the target console.
5. `CONFIRMED_STANDBY`: source-qualified fresh `620`/STANDBY reply from the intended physical owner.
6. `INDETERMINATE`: deadline expired/socket closed without an acceptable new 620; preserve true last-known sample and UNKNOWN coverage.
7. `FAILED`: explicit registration, login, rights, framing, cryptography or network error.

A response arriving during a DDP scan still has the **on-wire correlation uncertainty** documented in Protocol 01 and ADR-0021 (no response-echo nonce). Therefore `CONFIRMED_STANDBY` here means a fresh **source-reported** 620 observation with validated owner policy, not mathematically proven causation by our specific command or the precise transition instant.

## 5. Critical new independent source insights

### 5.1 The header/body transition and coalesced TCP reads

The [Python fake-console test](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/tests/test_session.py#L83-L100) sends HTTP response headers and a heartbeat in the **same network write**. The Python client uses `readuntil(b"\r\n\r\n")` and continues with its existing `StreamReader` to parse binary frames; it does not discard bytes after HTTP header boundary.

**OUR REQUIREMENT:** Byte parser MUST handle arbitrary TCP segmentation, including header split across reads, multiple frames in one chunk, HTTP and frame in same chunk, and zero-payload heartbeat. A request `Content-Length: 0` is verified separately from response. No generic web client is used for socket ownership transfer.

### 5.2 Distinguish test-source evidence from hardware

`iharosi/ps5-remoteplay` is explicitly a Python **port of playactor**; its synthetic registration/crypto vectors and fake console do not independently prove modern PS5 firmware compatibility. Chiaki-ng provides an independent C implementation of many concepts but follows its own codec/streaming stack. A third-party test passing in CI is **not** our execution, source license compliance or live hardware proof.

### 5.3 Login PIN safety and session ownership

Chiaki-ng `ctrl.c` explicitly avoids hex-dumping the user login PIN even in verbose tracing. Our own implementation must likewise treat Pair Device number, user passcode, PS5-RegistKey, RP-Key, PSN account ID and any OAuth tokens as secrets (with different retention/usage lifetimes), enforce per-console/per-account authorization and never expose them in HA entities, frontend WebSocket events, SQLite session ledger, backups without encryption review or Repairs diagnostics.

An already active Remote Play connection can reject another client. A failed/abandoned control handshake may leave the pairing/session reserved; the Python port's tests exercise forcibly aborting a stalled session. That is **an implementation-specific recovery technique**, not permission to immediately retry indefinitely. Own short timeouts, stop tokens, explicit negative acknowledgements and safe cleanup; never emit a fake successful standby on a lost TCP connection.

## 6. No PlayStation package, but encrypted control still has an explicit gate

- We can implement *our own* UDP preflight, byte framing, HTTP/1.1 bounded parser, TCP stream ownership, state machines, cryptographic nonce/HMAC counter orchestration and terminal socket cleanup with Python stdlib.
- Python standard library does **not** provide raw AES-CFB. HA Core 2026.11 itself requires `cryptography==50.0.2`; PyCA exposes legacy CFB under its *Decrepit* API. Using it directly could add **zero new pip installations** but would still be a third-party library import.
- The maintainer has **not yet approved** that narrow primitive exception. No implementation may silently import it. State remains `BLOCKED_CRYPTO_BACKEND_APPROVAL` for pairing and standby.
- If not approved, **defer encrypted controls**, while passive LAN statuses, game/app metadata, source-based history and the sidebar remain first-party and independent.
- Even with an approved AES primitive, the source-specific key derivation tables have ambiguous license/provenance concerns (some source repositories are AGPL/GPL) and must be handled through a separate clean-room specification and legal review. Do not copy or transform verbatim tables or test vectors into our code as a dependency shortcut.
- A user's Sony account identifier still requires authorized/legitimate provisioning. A Pair Device number alone does not meet the PSN identity requirement in the community registration implementation.

## 7. Proposed first-party module interfaces (no source code created)

```text
Domain:
  RemotePlayPairingIntent
  ConsoleIdentityBinding
  RegistrationCredentialRecord
  RemotePlayOperation
  RemotePlaySessionStatus
  ControlCommandReceipt

Wire/transport:
  PairingPreflightTransport       // UDP SRC3/RES3, 9295
  RegistrationHttpClient         // dedicated bounded POST over TCP 9295
  RegistrationPayloadCodec       // own framing + approved AES backend only
  SessionInitHttpClient          // GET nonce /sess/init
  ControlTcpStream              // HTTP header handoff to same binary TCP stream
  ControlFrameCodec             // 8-byte header; per-direction counters
  ControlProtocolActor          // login/passcode/heartbeat and send command
  PowerVerificationAdapter      // separate existing LAN DDP status observations
```

No actual Python files are authorized by this design. Interfaces must be modular and documented in English. Do not couple credential records to historical activity ledger, and do not couple Remote Play/control-session lifetime to Home Assistant entity getter/listener lifecycle.

## 8. Detailed future acceptance trace matrix — all NOT_RUN

| ID | Future evidence/test | Required result |
| --- | --- | --- |
| RP-F01 | Wrong/expired manual Pair Device number | Explicit registration failure; no credential persistence |
| RP-F02 | Normal DDP `SRCH` vs pairing `SRC3` | Distinct UDP 9302 vs 9295 transport/profile, no conflation |
| RP-F03 | SRC3 without vs with terminal NUL | Byte variants tested on real firmware, not guessed |
| RP-F04 | RES3 from unexpected UDP source or truncated | Reject/not confirm pairing intent |
| RP-F05 | Announcement reply never arrives | Bounded timeout and socket cleanup, no brute-force |
| RP-F06 | Registration POST missing/invalid RP-Version | Typed version/compatibility error, no retry storm |
| RP-F07 | Encrypted registration response absent RP-Key | Explicit invalid credential error; no partial save |
| RP-F08 | Correct RP-Key but malformed PS5-RegistKey | Reject, no wake/standby authorizations |
| RP-F09 | Wrong PSN account ID / console pairing mismatch | No device/session reassignment |
| RP-F10 | Pair Device number vs later 4-digit user passcode | Different lifecycle and UI/secret storage |
| RP-F11 | Session init GET without Content-Length: 0 | Record source-expected 403 compatibility; test current firmware |
| RP-F12 | RP-Nonce malformed base64/wrong length | Fail closed before control channel |
| RP-F13 | Control request encrypted header order reversed | Counter mismatch detected, no ghost login |
| RP-F14 | Control HTTP response + heartbeat same TCP chunk | No bytes dropped; HTTP parser retains stream |
| RP-F15 | Control HTTP headers divided across many TCP reads | Bounded parse, no premature frame decode |
| RP-F16 | HTTP content-length nonzero/unsupported transfer | Reject unless explicitly proven safe protocol variant |
| RP-F17 | 8-byte zero-payload heartbeat | No AES counter advance and proper reply |
| RP-F18 | Separate outbound/inbound nonempty payloads | Independent encryption counters and deterministic decryption |
| RP-F19 | Passcode required, missing or invalid | Typed error, no user secret logging, no false login |
| RP-F20 | Unknown frame type / truncated / oversized frame | Bounded protocol error, safe close without command |
| RP-F21 | Control session already in use | No automatic takeover, typed conflict, prompt cleanup |
| RP-F22 | Cancellation before/during HTTP→binary handoff | TCP/UDP closed, old operation fenced, no ghost task |
| RP-F23 | Successful send of 0x50 but no 620 | INDETERMINATE, not physically confirmed |
| RP-F24 | Remote socket closes after 0x50 | DDP confirmation required, not inferred from close |
| RP-F25 | Session standby wait expires but wrapper returns True | Reject optimistic library semantics; require DDP |
| RP-F26 | Two consoles / two accounts overlapping control jobs | Per-console and credential scope isolation |
| RP-F27 | HA unload/reload during login or standby | Old controller cannot emit success or persist credentials |
| RP-F28 | Firmware changes response/crypto version | Safe capability unavailable, not key/table guess |
| RP-F29 | No approved AES backend available | Pairing and standby disabled; passive LAN still works |
| RP-F30 | PSN account login not authorized | Pairing requiring account ID deferred; no copied OAuth client |
| RP-F31 | Socket-only command generates unwanted Remote Play connection | Explicit user intent + interference validation before release |
| RP-F32 | Correct long-running heartbeat and clean logout | Bounded control session and definite terminal cleanup |

**All 32 trace IDs are source-design cases to integrate into existing SPEC-002, NOT a new numbered SPEC or runnable tests.** Future CI must first implement an *original* fake PS5 responder for UDP and TCP without copying third-party fixture/code assets, then limited user-consented hardware verification with firmware version and redacted logs. Do not infer real console interoperability from a fake test.

## 9. Priority conclusion

**Recommended next technical documentation topic after this audit:** complete an isolated, legally reviewable **cryptographic compatibility/provenance matrix** for PS5 Remote Play (PIN seed, IV derivation, version/firmware changes and clean test-vector provenance) **only if needed for a planned authorized implementation**; no immediate commitment to write proprietary key tables or choose PyCA.

**The decisive blocker** is no longer "how do we send a UDP wake/standby command?" It is obtaining legitimate pairing/account identity, correct versioned encrypted registration and an approved vetted AES primitive. The LAN component already has an independent non-cryptographic path and must remain operational if any of these gates fail.

**Outcome:** Documentation-only source analysis. Zero package installation, zero code or SQL DDL, zero protocol test execution, zero console/PSN request and no automatically created ADR-0023/SPEC-023.
