# PlayStation Hub — PS5 Remote Play lookup-table provenance, interoperability rights and independent test oracles

**Date:** 2026-11-07  
**Status:** SOURCE AND PUBLIC-LAW RESEARCH / ACTUAL BYTES COMPARED IN MEMORY / NO TABLES COMMITTED / NO IMPLEMENTATION  
**User requirement:** Complete first-party PlayStation-specific code, no third-party PlayStation library, no newly installed runtime pip/npm package, no copying/vendorizing external code or lookup tables without separate rights review. No PSN account-provider dependency for passive LAN.
**Predecessor:** [PS5 crypto derivation/version audit](ps5-remote-play-crypto-derivation-versions-and-security-source-audit-2026-11-07.md), [first-party sovereignty](../architecture/first-party-dependency-sovereignty-policy.md), [Remote Play operation contract](../architecture/first-party-remote-play-registration-control-contract.md).
**Purpose:** Answer whether repeated public PS5 lookup tables constitute independent evidence, trace their actual chronological lineage, identify legal/redistribution questions without claiming a legal ruling, and design truly independent oracles for a later authorized implementation.
**All documentation and design in English.** No new ADR/SPEC; no code, no secret user data, no crypto package import, no live PlayStation testing.

> **Source methods:** Read commit-pinned public source through connected GitHub, extract hexadecimal byte sequences **in transient memory only**, compare each complete array positionally, and report only byte counts and exact-equality booleans. No tables, byte arrays, keys, hashes of secrets, or copyrighted vector files were committed or included in this document. These public protocol arrays are not PSN user credentials, but copying them into the product still requires rights/provenance and security decisions.

## 1. Definitive result of full-array comparisons

At the following pinned revisions, ALL PS5 source-table values matched **exactly byte for byte**:

| Logical PS5 table / source labels | Byte count | Chiaki-ng C | Playactor TypeScript | Python ps5-remoteplay |
| --- | ---: | --- | --- | --- |
| `INIT_KEYS` / PS5 `ps5_keys_0` | 512 | Match | Match | Match |
| `AERO_KEYS` / PS5 `ps5_keys_1` | 512 | Match | Match | Match |
| `AUTH_NONCE_KEYS` / PS5 `keys_a_ps5` | 3,584 | Match | Match | Match |
| `AUTH_SEED_KEYS` / PS5 `keys_b_ps5` | 3,584 | Match | Match | Match |
| **Total four logical PS5 tables** | **8,192** | **Identical** | **Identical** | **Identical** |

**Precise details:** Chiaki's current C file defines `ps5_keys_0` and `ps5_keys_1` at multiple local-versus-remote-registration source locations; every inspected occurrence of each had the same contents as the matching Playactor PS5 array. The 3,584-byte auth tables occur once each. The Python port's `bytes.fromhex` concatenation was parsed into bytes and individually compared with Playactor; all matched. The comparison checks **numeric bytes**, not raw source text formatting. This is a genuine whole-array equality result, not a visual/prefix comparison or an assumption inferred from project names.

**Caution:** Three projects holding the same 8,192 bytes is **one shared pool of constants**, not three independent discoveries or three live PS5 protocol confirmations. The byte equality does NOT establish who first reverse-engineered these values, who owns every right in them, whether any copyright attaches to the constants themselves, or that PS5 firmware in 2026 accepts the protocol. The names and placement differ across languages.

## 2. Historical origin and explicit maintainer attribution

| Date and public evidence | What we confirmed |
| --- | --- |
| **11 Dec 2020**, [Chiaki `20a7e9d`](https://github.com/chiaki-ng/chiaki-ng/commit/20a7e9d12335faf82209f8010ebb4a073ea844fe) | Original PS5 registration-era snapshot already contains the **512-byte init** and **512-byte aeropause** PS5 tables, each equal to the current values. The two large auth arrays were not yet present in that file snapshot. |
| **16 Dec 2020**, [Chiaki `aa9939e`](https://github.com/chiaki-ng/chiaki-ng/commit/aa9939e93c77f815e41fe6c6652f9b0541ca8c4f) | All FOUR PS5 arrays (512+512+3584+3584 bytes) are present and numerically equal to the current versions and modern Playactor arrays. The C source explicitly carries the `LicenseRef-AGPL-3.0-only-OpenSSL` SPDX-style marker. |
| **23 Mar 2021**, [Playactor commit `f71f27e`](https://github.com/dhleong/playactor/commit/f71f27e5b1d85baaa7988c0ec12eebdd2094ce91) | Playactor first adds `INIT_KEYS` and `AERO_KEYS` PS5 arrays equal to Chiaki's earlier two; no matching auth arrays in that commit snapshot. |
| **23 Mar 2021**, [Playactor PR #16](https://github.com/dhleong/playactor/pull/16) | The maintainer **explicitly states** that PS5 implementation builds on work from the Chiaki project. This is direct authorial attribution for the implementation's origin, not proof of original authorship or copying of every individual byte. |
| **31 Mar 2021**, [Playactor commit `435482d`](https://github.com/dhleong/playactor/commit/435482d36c96bc73996caa580e99d804a48de25f) | Adds the two full **3,584-byte** PS5 auth tables, matching Chiaki's Dec 2020 copies, and extends Remote Play control. At this commit, Playactor's `package.json` explicitly declares **ISC** license. |
| **15 Sep 2026**, [Python port initial commit `b74f3b3`](https://github.com/iharosi/ps5-remoteplay/commit/b74f3b3ae5e60a5753da13ff7452bc18b1689470) | The Python port's `keys.py` explicitly says its tables were **generated from Playactor `src/remoteplay/crypto/keys.ts`**, and they match numerically. The Python repository advertises **AGPL-3.0-only**. |
| **Nov 2026 snapshots** | [Chiaki-ng `43728af2`](https://github.com/chiaki-ng/chiaki-ng/tree/43728af2e639fecb8a7af1cd68c29820a40de973), [Playactor `a9e72d67`](https://github.com/dhleong/playactor/tree/a9e72d67a3930a8f06455927edb547a1754ef0ac), [Python port `61e1f7dc`](https://github.com/iharosi/ps5-remoteplay/tree/61e1f7dc065a77f7e8b1de5057889a08b0208d9) retain identical PS5 table bytes. |

**Strong evidence:** Chronological precedence (Chiaki 2020 → Playactor 2021 → Python port 2026), the Playactor author's express Chiaki acknowledgment and the Python source's express Playactor generation statement. **What remains unknown:** original Sony-table provenance, the rightsholder of the literal binary tables (if protectable), permissible redistribution of those exact bytes in a separately licensed work, and current Sony console-version compatibility. Do not equate a Git repository license with proven clean provenance of all third-party material inside it.

## 3. Licenses are different — factual matrix, not a legal decision

| Project | Evidence of license | Interpretation for PlayStation Hub |
| --- | --- | --- |
| [Chiaki-ng `rpcrypt.c`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/rpcrypt.c) | Source header: `LicenseRef-AGPL-3.0-only-OpenSSL`; repository reports AGPL-3.0 | Direct code/table copying into a differently licensed integration needs a **specific copyright/license/provenance analysis**. No automatic permission to omit attribution or conditions. |
| [Playactor `package.json`](https://github.com/dhleong/playactor/blob/435482d36c96bc73996caa580e99d804a48de25f/package.json) | Declares **ISC**, including at Mar 2021 introduction | ISC may allow redistribution of *material actually offered under its license* subject to its terms, but **does not itself prove the author's rights to grant another project's earlier data**. No top-level standalone LICENSE file was present in the inspected current repository tree; package metadata is still relevant evidence. |
| [Python `ps5-remoteplay`](https://github.com/iharosi/ps5-remoteplay) | AGPL-3.0-only; `keys.py` says Playactor-derived | Not independent; no need to import Python library or copy the table bytes. |
| [PyCA cryptography 50.0.2](https://pypi.org/project/cryptography/50.0.2/) | Verified PyPI: **Apache-2.0 OR BSD-3-Clause**, currently pinned by [HA Core 2026.11](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml) | A high-level vetted **standard AES primitive only**, if approved, is a separate concept from using PlayStation-specific key arrays. Still a third-party library import and NOT approved under maintainer's rule. |

**Do not claim:** (a) that all binary constants are automatically protected copyrighted works; (b) that numerical protocol data are automatically unprotected/public domain; (c) that applying ISC to identical arrays proves an AGPL violation; (d) that either project grants Sony protocol/API authorization. All of these would exceed the evidence and require legal advice.

## 4. Relevant EU and Portuguese law, with clear boundaries

**Authoritative legal texts (informational, not legal advice):**
- [Directive 2009/24/EC](https://eur-lex.europa.eu/legal-content/en/TXT/?uri=CELEX%3A32009L0024), Articles 1(2), 5(3), 6: protects program expression rather than underlying ideas/principles; allows specified study/observation by lawful users and restricted interoperability-related decompilation under conditions. These conditions do NOT grant unrestricted reproduction/disclosure of third-party code or all embedded arrays.
- [Portugal Decreto-Lei n.º 252/94, consolidated](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1994-34555675), **Art. 2**, **Art. 6(1)(b)** (legitimate user's observation/study) and [Art. 7](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1994-34555675-46564575) (narrow decompilation for necessary interoperability, with conditions and usage/disclosure limits).
- [CJEU Case C-406/10, SAS Institute v World Programming](https://eur-lex.europa.eu/legal-content/EN/SUM/?uri=celex%3A62010CJ0406) distinguishes functionality, programming language and format from protected program expression; copying source/expressive content remains a different legal question.

**Practical distinction:** Learning the behavior of an interface and authoring *our own protocol parser and state machine* has a different legal profile from pasting someone else's code, a generated data extraction or protected test corpus into a repository. **Whether a specific numerical Sony table is an uncopyrightable protocol fact, protectable compilation, trade secret, or third-party licensed expression is not settled here.** Sony account/device service terms, anti-circumvention constraints and software license attribution need a separate expert review if encrypted Remote Play is to be publicly distributed.

**No blanket prohibition claim:** The current PlayStation Hub policy "**do not copy until provenance/rights are resolved**" is a **deliberate conservative engineering rule**, not a legal conclusion that every use of constants is necessarily unlawful.

## 5. Truly independent testing must have different evidence tiers

| Tier | Oracle / source | What can be validated without copying PlayStation tables | What it cannot validate |
| --- | --- | --- | --- |
| **A — Public cryptographic standards** | [RFC 4231](https://www.rfc-editor.org/info/rfc4231/) HMAC-SHA256, [NIST SP 800-38A](https://csrc.nist.gov/pubs/sp/800/38/a/final) CFB128, [FIPS 197](https://www.nist.gov/publications/advanced-encryption-standard-aes) | Correct SHA256 digest output (32 bytes), IV truncation logic, byte ordering, AES/CFB128 primitive behavior once a vetted primitive is approved | Sony nonce-key transformations, fixed 8,192 bytes, PS5 RP pairing |
| **B — Original synthetic protocol tests** | Our own generated byte/HTTP frames, fake console, nonce/PIN/account placeholders | Packet length, TCP HTTP→binary socket handoff, zero-payload counter skipping, timeout/error/secret redaction, deterministic serialization | Sony accepts the chosen lookup/key transformation |
| **C — Permissible independently observed PS5 evidence** | User-consented retail-console interoperability, with legally obtained credentials and separately authorized primitive | Device responses, actual RP-Version, which encrypted registration/control frames it accepts, reference confirmation distinct from Playactor's self-tests | Automated reproduction of secret tables without a lawful technical method |
| **D — Cross-source existing vectors** | Chiaki PS5 IV/registration case and Playactor/Python fixtures | Historical cross-implementation consistency **for documented stage** | Independent provenance or complete live PS5 firmware compatibility |

**Recommended order:** Establish tier A mathematical correctness and tier B transport correctness in a future *authorized* implementation. Tier C is the only credible live firmware gate. Tier D is useful as **read-only investigation**, but using an existing test expected output from an AGPL/GPL source verbatim inside the project would need a separate rights decision. Do not award "independent" credit to a Python port's Playactor-derived fixtures.

**Key insight:** NIST/RFC vectors cover the **standard algorithm**, but there are no official Sony PS5 lookup constants in NIST or RFC 4231. A mathematically correct AES-CFB128 implementation without the Sony-specific table bytes would still be unable to interoperate. Conversely, knowing the arrays does not automatically establish rights, Sony authorization or successful credential pairing.

## 6. Realistic lawful routes for the remaining PlayStation constants

**Route 1 — Provenance and permission assessment (document-only, preferred now).** Trace each table to the oldest recorded release and underlying source rights, inspect how the original Chiaki authors documented derivation/attribution, and obtain a specific rights/redistribution opinion or permission if necessary. Git timestamps and byte equality **are provenance indicators, not a license transfer**. Do not embed bytes now.

**Route 2 — Independently derived protocol facts.** If a legitimate, user-authorized technical study of a retail console yields the *necessary protocol information* without copying a third-party implementation or bypassing prohibited controls, record exactly the method, scope, consent and legal basis. Do not promise this is easy: ordinary DDP power/title samples cannot reveal the hidden Remote Play lookup arrays. A passive capture of encrypted messages normally does not reconstruct secret constants.

**Route 3 — Explicitly accepted narrower reusable components.** If a later expert review establishes that a set of constants is legally reusable with particular notices/terms, request a **separate user decision** to include that precise data. This would still be a distinct decision from allowing PyCA for standardized AES. A protocol-data inclusion must not silently become a dependency on the Chiaki package.

**Route 4 — Defer authenticated control.** If provenance, user authorization, approved AES primitive or current-device interoperability cannot be established, **disable encrypted pairing/standby** and preserve the independent fully first-party LAN status, optional reported app, HA entities, session ledger and panel.

**Never:** conceal copied code/tables by renaming variables; auto-download/install external client code; extract Sony account/passwords from a third-party OAuth client; use unaudited homemade AES; attach a console ELF/payload as a dependency; or present successful encrypted control as already implemented.

## 7. Actionable, finite source/rights decision gates

| Gate | Evidence needed | Status |
| --- | --- | --- |
| ORIGIN-01 | Exact complete table comparison across Chiaki/Playactor/Python | **SOURCE_CONFIRMED** — all 8,192 bytes equal |
| ORIGIN-02 | Temporal/author provenance of the three publication paths | **SOURCE_CONFIRMED** — 2020→2021→2026 and explicit project attributions |
| ORIGIN-03 | Determine legal status and proper notices of **these numerical tables** in an independently written distributed program | **OPEN — expert/legal review**, not answered by repo license alone |
| ORIGIN-04 | Determine Sony account/firmware/authentication constraints for console-control functionality | OPEN |
| ORIGIN-05 | Explicit approve/reject HA-preinstalled PyCA AES primitive exception | **NOT APPROVED** |
| ORIGIN-06 | Original tests against public RFC/NIST crypto vector standards | DESIGN_READY / NOT_RUN |
| ORIGIN-07 | Our own independent fake-console transport tests without copied GPL/AGPL vectors | DESIGN_READY / NOT_RUN |
| ORIGIN-08 | Authorized PS5 actual pairing/control with independent evidence and safe nonintrusive procedure | BLOCKED / NOT_RUN |
| ORIGIN-09 | Confirm no third-party runtime packages/code, no tables/fixtures bundled without rights decision | REQUIREMENT ACCEPTED / RELEASE CHECK NOT_RUN |
| ORIGIN-10 | Stop research repetition when no new source evidence can settle rights or firmware questions | IN FORCE — WP-00B policy |

This source investigation resolves **which table bytes the projects share, when they appeared and who acknowledged prior work**. It does **NOT** resolve whether the precise numerical data can be redistributed, the Sony protocol's current official status, or safe interoperability with the maintainer's PS5. We must not keep recycling the same known tables merely to enlarge documentation.

## 8. Implementation-facing requirements — future only

- Keep `CryptoPrimitive`, `ProtocolKeyDerivationProfile` and `ConsoleRegistrationCredential` as **separate interfaces**. A library's license and an AES primitive do not authorize or supply protocol key data.
- Preserve source/revision provenance in a **documentation-only trace registry**; no raw key arrays or complete fixture hex committed while ORIGIN-03 is unresolved.
- Put official RFC/NIST vectors in a separate, non-Sony **standards conformance** category; do not label them as Remote Play interoperability tests.
- A firmware fixture must include explicit hardware version, RP protocol version, transport consent, redacted packet metadata and negative tests for bad credentials/occupied sessions; never expose real user secrets.
- If either rights, primitive, account authorization or firmware gate fails, the encrypted control capability remains unavailable. No optimistic standby or affected LAN source data.
- Do not open ADR-0023/SPEC-023 for this discovery. Amend Protocol 05, SPEC-002, first-party policy and Bible; require no branch until authorized implementation.

**Research result:** 8,192-byte exact equality and clear historical project lineage, official independent crypto standards and Portuguese/EU interoperability rights boundaries, with a finite release decision matrix. **No code/crypto data copied, tests run, Sony credentials accessed or user device contacted.**
