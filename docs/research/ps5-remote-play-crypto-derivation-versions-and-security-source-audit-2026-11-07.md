# PlayStation Hub — PS5 Remote Play cryptography, derivation, protocol versions and source-safety audit

**Research date:** 2026-11-07  
**Status:** SOURCE-AUDITED / CRYPTO IMPLEMENTATION NOT AUTHORIZED / NO DEVICE OR CODE TEST  
**Scope:** The PS5 pairing and authenticated short-control flows defined in Protocols 04–07; specifically key derivation boundaries, AES-CFB selection, HMAC-IV calculation, per-direction counters, registration padding, protocol-version negotiation, test-vector independence, security and license provenance. This is **not** a return to SQLite-backup research.
**Maintainer requirement:** Every PlayStation-specific protocol is independently authored in PlayStation Hub; **no external PlayStation libraries, on-console payloads, new pip/npm runtime dependencies, copied key tables or homemade AES**. The Home Assistant-pinned PyCA primitive exception is **NOT APPROVED**. No implementation permission has been given.
**Core source baseline:** Home Assistant Core tag `2026.11.0` and Python >=3.14.2; upstream commits below. Follow [source independence policy](../architecture/first-party-dependency-sovereignty-policy.md), [Remote Play source audit](first-party-ps5-remote-play-registration-control-source-audit-2026-11-06.md) and [operation contract](../architecture/first-party-remote-play-registration-control-contract.md).

> This document **intentionally does not reproduce** upstream proprietary lookup tables, source code, complete key material, nonce/ciphertext hex vectors or private user credentials. It cites exact upstream files and describes what an independently reviewed implementation would need to prove. A repository containing an algorithm is not an authorized software or firmware contract.

## 1. Source evidence, scope and independence register

| Source | Commit/release | Directly observed | Limits |
| --- | --- | --- | --- |
| [Playactor crypto/base.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/base.ts) | `a9e72d67` | `aes-128-cfb`, nonce/counter HMAC-SHA256 IV, 480-byte registration preface, 16-byte sizes | Node implementation, not official Sony API |
| [Playactor crypto/modern.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/modern.ts) and [keys.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/keys.ts) | same | PS5-specific PIN/nonce/seed transformations and large tables | License and lawful source provenance unresolved; do not copy |
| [Playactor crypto/legacy.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/legacy.ts) and [model.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/model.ts) | same | PS4 pre-10 separate algorithm branch; PS5 target `PS5_1` / RP version `1.0` | PS5 RP 1.0 is **not** PS5 firmware 1.0 |
| [Playactor codec.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/codec.ts) | same | Separate outgoing/incoming counters; header-only 8-byte frames are unencrypted and skip payload counter | Does not prove behavior under every disconnect/partial transfer |
| [Chiaki-ng rpcrypt.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/rpcrypt.c) | `43728af2` | Independent C derivation and **CFB128** cipher implementation for OpenSSL and Mbed TLS builds | AGPL-3.0; embedded lookup tables not approved to copy |
| [Chiaki-ng regist.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c) | same | Registration preface and random 16-byte registration nonce, PIN/offset selection; local and PSN routes differ | PSN remote registration has different parameters; excluded from LAN v1 |
| [Chiaki-ng session.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/session.c) | same | RP version and nonce response parsing; supported version negotiation/retry path | Never simply accept a server-provided unknown/downgraded version |
| [Chiaki-ng test/rpcrypt.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/test/rpcrypt.c) | same | PS5 IV+registration seed expected results, PS4 encryption/decryption vectors | No comprehensive modern PS5 entire control channel test shown in inspected file |
| [Python ps5-remoteplay crypto.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/crypto.py) and [test_crypto.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/tests/test_crypto.py) | `61e1f7dc` | Python port using PyCA CFB, HMAC counter and fixtures | Port and its fixtures were sourced from Playactor; **not independent firmware confirmation** |
| [HA Core 2026.11 pyproject.toml](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml) | `2026.11.0` | `cryptography==50.0.2` included as Core runtime requirement | Third-party PyCA import **still requires explicit maintainer exception** |
| [PyCA 50.0.2 Decrepit](https://cryptography.io/en/50.0.2/hazmat/decrepit/) and [Cipher API](https://cryptography.io/en/50.0.2/hazmat/primitives/symmetric-encryption/) | official library docs | AES with legacy CFB available through Decrepit; API warns against unauthenticated/hazardous modes | CFB does not itself authenticate ciphertext; legacy capability may change |
| [Mbed TLS generic HMAC API](https://mbed-tls.readthedocs.io/projects/api/en/v3.5.2/api/file/md_8h/) | official library docs | `mbedtls_md_hmac_finish` writes the *full* configured digest to caller output | Relevant to a source-level C buffer-size concern below |

**Evidence independence:** Chiaki-ng and Playactor implement similar mathematics, but shared publicly circulated test vectors do not prove two separate firmware captures. The Python library explicitly identifies Playactor as upstream source. Chiaki's test and the Python port's test include a matching PS5 IV registration example; this is **cross-implementation mathematical consistency**, not proof of independent validation. The actual firmware version, source permissions, C compile modes and HA OS cipher backend were **not tested**.

## 2. Four different kinds of cryptographic bytes — do not mix them

| Type | Stage | Source-observed length | Ownership / lifetime |
| --- | --- | --- | --- |
| Registration random nonce (Chiaki calls ambassador in one context) | Pair Device registration | 16 bytes | Fresh generated `secrets.token_bytes` candidate, ephemeral; not user's PSN login secret |
| Registration PIN-derived AES seed | Encrypted registration payload | 16 bytes | Depends on short-lived manual Pair Device number, fixed lookup/source version; no storage before validation |
| Registration output `RP-Key` and `PS5-RegistKey` | Validated PS5 registration response | `RP-Key` 16-byte decoded; RegistKey separately typed/validated | Restricted per-console/per-account credential record, never usage ledger or diagnostics |
| Session `RP-Nonce` | GET `/sie/ps5/rp/sess/init` | 16 bytes after base64 decode | Fresh server session input, not interchangeable with registration nonce |
| Session derived AES key / transformed nonce | RP authenticated control session | 16 bytes | Derived from RP-Key + server nonce + version-specific tables; session-only |
| HMAC output used for IV | Registration and each encrypted control payload | Full SHA-256 output 32 bytes, **first 16 used as IV** | Per-counter ephemeral; never persist or log raw bytes |
| Cipher input payload / frame header | Registered control traffic | 8-byte frame header, bounded payload | Header unencrypted; nonempty payload encrypted, separate counters |

**Naming caution:** Chiaki's labels `bright`, `ambassador`, `morning` differ from Playactor's `seed`, `nonce`, `authKey`; never map by variable name alone. Require a stage-by-stage transformation diagram and known-answer *equivalence proof* before promoting a common internal DTO. A 16-byte common length alone does not mean two fields are semantically the same key.

## 3. Derivation graph and testable mathematical relationships

### 3.1 Registration branch

1. A genuinely new 16-byte nonce is required for each pairing attempt; using a reused nonce together with short-lived Pair Device PIN and static source tables can make ciphertext repeat under identical inputs.
2. Source registration preface is **480 bytes** (0x1E0), initialized with ASCII `A` in the Playactor and Chiaki local-registration paths. The PIN seed lookup and a *different* aeropause lookup use offsets selected from preface bytes, then embed two eight-byte halves into distinct preface locations. **Do not copy the tables or derived bytes**; only document this structural relationship and future compatibility test.
3. In these source revisions, because preface bytes are the fixed value 0x41, `preface[0x18D] & 0x1F` evaluates to **1**, and `preface[0] >> 3` evaluates to **8**. These are properties of the selected static **local pairing preface**, not universal Sony protocol requirements or evidence that alternative implementations may not randomize the preface.
4. The manual user-entered number is interpreted as an integer for the source-derived PIN seed. Its **display formatting, leading zero behavior, accepted range and expiry** must be validated against the real console and handled without leaking the secret. Never force retries or brute-force.
5. A PIN-derived 16-byte AES key encrypts source-specific registration headers/payload. Decrypted response contains key names; incomplete/malformed keys produce registration failure, not a partially paired record.

### 3.2 Session branch

The reviewed Playactor, Chiaki and Python port agree on the following **general** derivation relationship:

```text
Session nonce (from PS5, 16 bytes)
         |
         +--[PS5-version-specific transform + lookup]--> Transformed nonce (16)
         |
RP-Key (from pairing, 16 bytes)
         |
         +--[PS5-version-specific seed transform + lookup with session nonce]--> AES seed (16)
                                                                                      |
Counter n (unsigned 64-bit BE) --------------------------------------------------------+
         |                                                                            |
         +--> HMAC-SHA256(key=version-specific IV key, message=transformed nonce || n)
                  | 
                  +--> first 16 bytes --> AES-CFB128 IV for *one* encrypted payload
                                             |
AES seed + IV + payload -----------------------+--> ciphertext / plaintext
```

**Source details to test, not copy:** For PS5 modern transform, the nonce-derived lookup offset depends on high bits of nonce byte 0; seed lookup offset depends on high bits of nonce byte 7, both indexed into large embedded tables. Per-byte transformations use addition/subtraction/XOR modulo 256. The same function names can have different branch behavior between PS4 versions and PS5. An upstream table is not a secure primitive; it is reverse-engineered protocol-specific material with provenance and legal review requirements.

**IV is NOT itself the nonce:** Reviewed sources form HMAC input from **16-byte transformed nonce followed by an 8-byte big-endian counter**; they take the first 16 bytes of the SHA-256 HMAC output as the AES-CFB IV. The HMAC digest must be calculated into a **full-size output** and only then truncated to the desired IV. Never directly write the full digest into a 16-byte array.

### 3.3 CFB128, not CFB8 or CBC

- [Chiaki rpcrypt.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/rpcrypt.c#L2290-L2426) explicitly selects `mbedtls_aes_crypt_cfb128` or OpenSSL `EVP_aes_128_cfb128`.
- [Playactor base.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/base.ts) sets `aes-128-cfb`; [Python port](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/crypto.py) uses PyCA `CFB`, not `CFB8`.
- A generic socket codec in Playactor defaults to CBC **only when no overriding algorithm is passed**; the Remote Play strategy explicitly requests CFB. It would be an interoperability bug to substitute CBC or CFB8 based on generic helper defaults.
- CFB behaves like a stream cipher and **does not require block padding** for payloads; the 480-byte registration preface is protocol framing/key material, **not CBC PKCS#7 padding**. The cipher mode itself gives confidentiality but not authenticity; message validity/authorization and bounded parsing are independently necessary.

## 4. Counter lifecycle is stateful and must not silently resynchronize

| Stage | Source behavior | Required future invariant |
| --- | --- | --- |
| Registration payload | Source uses initial counter 0 and registration-specific IV/preface/key | A pairing attempt owns its own fresh state, no cross-attempt counter reuse |
| Outbound control HTTP auth headers | Encrypted fields generated in an order that uses outbound counters, typically 0–4 in reviewed Python path | Counter/order pinned to protocol version; don't rely on generic dictionary reordering |
| Inbound `RP-Server-Type` | An encrypted server header consumed before binary frames | Inbound counter starts separately and advances upon successful validated decrypt |
| Control 8-byte header without encrypted payload | Clear length/type/reserved, **no counter consumed** | No artificial increment on empty heartbeats, login or standby frames |
| Control frame with encrypted payload | One per-direction counter per encrypted payload, not per arbitrary TCP read | TCP segmentation/coalescing never changes counter advancement |
| Partial send or connection exception | Source may have already advanced outgoing counter while bytes were buffered | Stop/fence session; do not naively retry the same serialized plaintext on same state |
| Counter wrap/overflow or unexpected frame | Not explicitly proven recoverable | Fail safely, close; don't reset counter and hope |
| New authenticated session | Fresh server nonce/cipher context required | Never reuse previous session's IV/counter history |

Important nuance: writing encrypted headers with one `Cipher` context versus per-message CFB context has different state semantics. The original source constructs a **fresh cipher per counter/payload** for session auth; do not treat it as one continuous CFB stream. Testing must cover both unchanged frame byte lengths and fragmented TCP reads.

## 5. Protocol versions versus real PlayStation firmware

The reviewed [Playactor model.ts](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/model.ts) maps PS5 devices to target `PS5_1` and Remote Play `RP-Version: 1.0`; PS4's 8.0/9.0/10.0 versions are separately selected based on its reported software version. [Chiaki session.c](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/session.c#L58-L90) also accepts `1.0` for PS5 and older PS4 versions.

**Do not conflate `RP-Version:1.0` with PS5 system firmware version.** RP-Version is a **protocol target designation**. Sony may update firmware while retaining RP protocol version, but that is only a hypothesis until current firmware tests. A server-reported version mismatch is typed failure/negotiation evidence, not authorization to silently downgrade key algorithms or select a PS4 branch based on string similarity.

Chiaki [session.c around lines 489–506](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/session.c#L489-L507) retries session request when the server reports a different supported RP version. This is a real implementation behavior but not necessarily safe policy for our control-only module. Require explicit allowlist + firmware compatibility review; reject unknown, unexpected or contradictory PS5/PS4 target version. No silent negotiation to ancient versions or repeated session acquisition.

## 6. Independent tests: significant gaps hidden by source agreement

**Playactor:** Provides source routines for PIN seed, IV, nonce transform and codec; source test/fixtures are implementation-owned. **Python port:** `tests/test_crypto.py` literally calls one case `test_generate_iv_playactor_case` and consumes `tests/vectors.json`, which prior project audit documented as generated from Playactor; it is not an independent field confirmation.

**Chiaki-ng:** `test/rpcrypt.c` has a PS5 registration IV case and PS5 registration seed/bright case, but the inspected encryption/decryption vector cases are named **PS4 pre-10**, not complete PS5 modern control encryption and HTTP handshake. The PS5 IV fixture's nonce and expected IV coincide with the Python port's `test_generate_iv_playactor_case` example — useful mathematical consensus, but not evidence of two independent PS5 firmware captures.

**Additional important gate:** Need an independently established, legally usable test oracle for **every** modern PS5 stage: manual pairing request/response (without private user secrets), 480-byte preface behavior, PIN→seed transformation, HMAC IV at counter 0 and nonzero, session nonce transform, session seed transform, five ordered outgoing encrypted HTTP fields, initial server-type decrypt, and a binary payload at nonzero counter in both directions. A fixture with a fake console based on the same algorithm proves the implementation agrees with **itself**, not that the actual console accepts it.

**Testing strategy when authorized:** Start with standard-library pure tests for HMAC/endianness/length/format/frame logic using our own synthetic data; only after explicit AES backend choice and legal key-table/fixture rights review, test actual encryption against an **independently sourced** permissible oracle; then user-consented real PS5 interoperability. Never copy secret material or upstream AGPL/GPL vectors into our distributable repository merely to make CI green.

## 7. High-priority source safety finding: conditional Mbed TLS HMAC output buffer

**Status: HIGH-CONFIDENCE SOURCE-LEVEL CONCERN / NOT COMPILED, REPRODUCED OR EXPLOITED.**

In the pinned [Chiaki-ng `lib/src/rpcrypt.c` conditional `CHIAKI_LIB_ENABLE_MBEDTLS` branch](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/rpcrypt.c#L2259-L2328), the local output buffer for HMAC appears sized for the **16-byte truncated IV**, yet the code configures `MBEDTLS_MD_SHA256` and calls `mbedtls_md_hmac_finish` directly on that buffer. SHA-256 HMAC produces **32 bytes**, and [official Mbed TLS SHA-256 output documentation](https://mbed-tls.readthedocs.io/projects/api/en/v3.5.0/api/file/sha256_8h/) requires a writable 32-byte digest output. This appears to be a **potential out-of-bounds write in the optional Mbed TLS build path**, not an issue with the OpenSSL branch, which explicitly has a full-sized HMAC buffer.

[CMakeLists.txt](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/CMakeLists.txt) defaults `CHIAKI_LIB_ENABLE_MBEDTLS` to OFF but has platform-specific logic that can enable it. Because we did **not** build, execute or establish the exact affected configurations, this remains a **source audit finding** rather than a demonstrated exploit, a confirmed security advisory, or a claim about the user's system.

**Our requirement:** Never copy the affected upstream C code. Any future HMAC primitive invocation must produce a **32-byte full digest into a correctly sized destination** before selecting the first 16 bytes for IV. Consider reporting the potential upstream issue through the upstream maintainer's preferred coordinated-security contact rather than treating it as a reusable implementation reference. No reproduction, binary exploitation or packet attacks were attempted.

## 8. Cryptographic dependency and legal feasibility

**PyCA Core bundle:** [HA Core 2026.11.0 `pyproject.toml`](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml) requires `cryptography==50.0.2`. Its official [Decrepit modules](https://cryptography.io/en/50.0.2/hazmat/decrepit/) include legacy AES CFB support. This could technically furnish a maintained block-cipher primitive **without installing a new pip package**, but a direct `cryptography` import is still third-party library use and **not approved under the maintainer's prohibition**. Version support, removal timelines, installation availability, FIPS/runtime policy and source-lifetime must be checked later if a narrow explicit exception is requested.

**Mathematical primitives:** `hashlib`, `hmac`, `secrets`, `struct`, `asyncio` from the Python standard library are available for some parts, but **not raw AES-CFB**. No homemade AES/CFB, no Mbed TLS/OpenSSL direct `ctypes`, no copied third-party key tables, and no assumption Sony account identifiers/PSN APIs may be reused without consent or authorization.

**Core interoperability blocker is bigger than just PyCA:** Even granting AES primitive access would NOT automatically grant the protocol-specific table data, lawful/appropriate usage, legitimate pairing account identifiers or proof that the current PS5 firmware accepts a short control-only Remote Play session. The first-party solution cannot be declared ready until these separate gates have passed.

## 9. Proposed first-party modular trust boundaries (no source files)

```text
RemotePlayCryptoPolicy          // approved cipher mode and version capabilities
  |
  +-- RegistrationNonceManager // cryptographically generated; per attempt only
  +-- PinInputValidator         // user Pair Device number, not user login passcode
  +-- RegistrationDerivation     // OWN future implementation; table provenance gate
  +-- SessionDerivation          // OWN future implementation; versioned nonce/seed transforms
  +-- IvDerivation               // HMAC SHA256 full digest -> first 16, counter=uint64 BE
  +-- ApprovedCipherPrimitive   // explicitly approved vetted AES-CFB, or UNAVAILABLE
  +-- ControlCipherState        // independent counters; correct HTTP and frame ordering
  +-- CredentialScope           // PS5 owner + PSN account; never historical observations
  +-- SecureDiagnostics         // redact all nonces, seeds, keys, PIN/passcode and plaintext
```

No cipher implementation is being created here. Any future interface must expose explicit *unavailable* capability, rather than fail open by selecting CBC/CFB8 or accepting unknown RP versions.

## 10. Focused future test-oracle traces — all NOT_RUN

| Trace | Required proof | Expected boundary |
| --- | --- | --- |
| CRY-01 | RP-Version 1.0 vs PS5 firmware version | Distinct fields, never conflated |
| CRY-02 | Normal PS5 registration PIN and account scope | Short-lived PIN, no early credential persistence |
| CRY-03 | Fresh registration random nonce for each attempt | 16 bytes, no reuse |
| CRY-04 | 480-byte registration preface layout | Exact length and source offsets, independently verified |
| CRY-05 | PIN seed and aeropause table version/rights | No unapproved copied constants, reproducible lawful oracle |
| CRY-06 | HMAC-SHA256 IV, counter 0 and large nonzero | Full digest then first 16, 64-bit BE |
| CRY-07 | CFB128 vs CFB8 and CBC | Only approved protocol CFB128, no generic codec fallback |
| CRY-08 | Proper nonce/seed transformation and independent source vectors | PS5-specific known-answer; independent of port |
| CRY-09 | Five ordered encrypted control HTTP fields | Correct outbound counter 0..4 |
| CRY-10 | Inbound RP-Server-Type decrypt | Distinct inbound counter path |
| CRY-11 | Header-only heartbeat/login/standby | No cipher counter advance |
| CRY-12 | Encrypted nonempty payload both directions | Per-direction counter monotonic, exact frame/payload split |
| CRY-13 | TCP segmentation/coalescing and cancellation | Counter based on logical payload, not socket read chunks |
| CRY-14 | Invalid key length, response nonce or corrupted ciphertext | Fail closed, sanitize diagnostics; no partial registration |
| CRY-15 | Unknown/contradictory RP-Version response | No silent downgrade/reuse different target keys |
| CRY-16 | PyCA not approved/unavailable | Encrypted control disabled; LAN works |
| CRY-17 | Alternative Mbed TLS full SHA256 output sizing | Never write 32-byte digest to 16-byte buffer |
| CRY-18 | Pairing credentials cross-account or console | Reject, do not crossbind or expose logs |
| CRY-19 | Source-key tables copyright/provenance | Explicit maintainer/legal rights review before coding |
| CRY-20 | Real firmware and account user consent | Hardware-bound compatibility evidence beyond synthetic fixtures |

**All 20 trace items are qualitative future checks for existing SPEC-002**, not a new numbered SPEC and not executed tests. No current Python project, AES backend, expected key vectors, credential JSON, or runtime package was created.

## 11. Decision register and stopping conditions

| Gate | Question | Current disposition |
| --- | --- | --- |
| AES-01 | May we use **HA-preinstalled PyCA solely as a standard AES-CFB128 primitive** while writing all PlayStation protocol logic ourselves? | UNAPPROVED — explicit maintainer choice required |
| AES-02 | Can we independently source/derive required PS5 lookup-table constants **without copying AGPL/GPL material** and satisfy redistribution/licensing? | OPEN — legal/technical source provenance |
| AES-03 | Is obtaining a legitimate PSN account ID/consent possible without unofficial third-party OAuth client reuse? | OPEN — identity/authorization |
| AES-04 | Does a current consumer PS5 accept this source-derived registration/control-only path without disrupting another user? | HARDWARE_NOT_TESTED |
| AES-05 | Can HTTP→binary socket ownership, counter and error rules be proven under fault injection? | NOT_RUN, future code |
| AES-06 | Are CFB mode security constraints/privacy met for our intended permissions and device networks? | REVIEW_PENDING |
| AES-07 | Are there new RP versions on current firmware? | HARDWARE_NOT_TESTED; source currently advertises PS5 RP 1.0 |

**Recommended next research:** No further copying/re-reading giant encrypted lookup tables. The highest-value open work is a **rights/provenance and known-answer test plan**, coupled with a real firmware capture *after* explicit implementation authorization and AES decision. If a clean table provenance or secure primitive cannot be established, Remote Play controls remain deferred without blocking native LAN, the panel or source-based history.

**Result:** Thorough documented source mathematics, version distinctions and security bounds; no AES code, no reproduced cipher vectors, no actual pairing, no copyrighted keys exported, no third-party package selected or installed, no main application source changed.
