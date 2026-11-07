# PlayStation Hub — First-party implementation and dependency sovereignty

**Date:** 2026-11-06
**Authority:** EXPLICIT MAINTAINER REQUIREMENT — first-party PlayStation protocols and business logic; no runtime dependence on external PlayStation libraries or separately installed runtime packages.
**Status:** REQUIREMENT ACCEPTED / TECHNICAL CRYPTO EXCEPTION UNRESOLVED / NOT IMPLEMENTED
**Research:** [Standard library + Home Assistant Core source audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md)
**Branch:** Documentation on main. develop is never-deployed synthetic prototype and is source reference only, not migration or dependency.
**Product:** One native Home Assistant custom integration, one own JavaScript sidebar panel, multi-console; no MQTT, Home Assistant App, Docker, Node or cloud required for core LAN monitoring.

> IMPORTANT: "Build it ourselves" is a project requirement about **who implements the PlayStation-specific functionality and what extra packages users must install**. It is not a mandate to recreate the Python interpreter, Home Assistant Core, TLS or standardized secure cryptographic algorithms. These platform primitives are not PlayStation libraries. This document explicitly resolves past project suggestions that a PlayStation package should be selected for runtime.

## 1. Rules now accepted as product requirements

**FP-01: All PlayStation-specific runtime behavior is authored and maintained in this repository.** DDP discovery, LAN parsing, health and source reconciliation, per-console polling, title metadata interpretation, state transitions, history/reports, command orchestration, panel and optional future Sony adapters are our own code.

**FP-02: Do not add independent PlayStation protocol libraries.** No playactor, Chiaki, PS5-MQTT, PSNAWP, psn-api, pyremoteplay, playdirector or forks as imported, bundled, vendorized, dynamically loaded or shell-executed runtime dependencies. They remain external *reference sources*, pinned and reviewed for behavior/errors.

**FP-03: Target zero new Python runtime requirements.** Preferred integration manifest uses \`"requirements": []\` (or omit field if allowed by actual hassfest) so installing the integration does not trigger extra Python pip dependencies. HA-provided integration-level \`dependencies\` are a separate manifest concept and may legitimately include \`network\` where required.

**FP-04: Use Python standard library and supported Home Assistant APIs.** Own networking via asyncio/socket, parsing via bytes/struct, sqlite3 ledger, hashlib/hmac/secrets, standard logging and time. For adapter/broadcast discovery use \`homeassistant.components.network\` helpers (Core 2026.11 source proof), not own netifaces/ifaddr import. For HTTP use managed HA clientsession helper, not a bundled external client.

**FP-05: No frontend runtime package/framework dependency.** Bundle own JS ES modules, standards-based Custom Elements and CSS inside the same integration. No React/Next/Vue/npm runtime, no remote CDN assets, no separate frontend release or browser-side raw Sony token use.

**FP-06: No required auxiliary service.** No MQTT Broker, App/add-on, executable CLI, Node service, remote bridge, dedicated Docker container or background daemon required for baseline LAN features.

**FP-07: No copied/vendored third-party implementations or license circumvention.** Source review may map protocol constraints, packet shapes and independent test requirements. Verbatim GPL/AGPL/CPL code, proprietary crypto tables, and fixture assets cannot enter the repository without explicit rights/attribution review. New code/comments/docs in English, modular and extensively documented.

**FP-08: Never build our own general cryptographic primitives.** No hand-written AES/CBC/CFB, unaudited crypto or undocumented native OpenSSL FFI to pretend Remote Play is dependency-free. All sensitive features must use vetted primitives supplied by a supported platform interface or require a separately authorized narrow cryptography exception. No assumption that a suitable HA-exposed AES API already exists.

**FP-09: No unauthorized Sony account access.** Writing our own HTTP requests is not equivalent to Sony permitting undocumented PSN endpoints or reuse of another application's OAuth client identifiers/secrets. Optional PSN account features remain permission/availability-gated and may be deferred. No cloud authentication necessary for core local status.

**FP-10: Keep capabilities independent.** Missing PSN, blocked Remote Play crypto, title metadata absence or account authentication failures must not prevent native physical LAN status, archive access, configured Home Assistant entities or their own source time accounting.

**FP-11: Audit and measure, not just declare.** On every code PR/release check manifest requirements, static imports, spawned processes, embedded bundles/CDN URLs, license provenance and test coverage; no approval because a document states zero-dependency. Report transitive HA platform dependencies truthfully.

**FP-12: The policy does not authorize implementation.** Current main contains documentation and the old develop prototype remains untouched. Explicit user approval is required before writing an implementation branch.

## 2. What "no dependencies" includes and excludes

| Runtime layer | Allowed | Forbidden | Current status |
| --- | --- | --- | --- |
| Python language | Standard library | Extra protocol/helper pip package | Accepted direction |
| Home Assistant runtime | Public supported HA helpers/integrations, including core \`network\` | Importing unstable private internals as a shortcut | Conditional API compatibility tests |
| UDP LAN transport | Own asyncio datagram endpoint and parser | Node/playactor/Chiaki bridge | Research-ready |
| Console status | Own strict 200/620/unknown reconciler | Treat non-620 as AWAKE; import upstream status wrapper | Research-ready |
| Local app/title | Own optional DDP header normalization | Require PSN account or third-party field parser | Hardware semantics unverified |
| Wake | Own authenticated DDP packet and status verification | Unauthenticated fake wake or assume send=confirmed | Credential provisioning gate |
| Standby/Remote Play | Own session framing, command state; vetted crypto backend when approved | Custom homegrown AES or copied upstream crypto/key tables | BLOCKED_CRYPTO_BACKEND |
| PSN optional | Own authorized account client using HA HTTP helper | Import PSNAWP / reuse someone's OAuth client | BLOCKED_PROVIDER_AUTHORIZATION |
| History | stdlib sqlite3 + owned worker | aiosqlite/external storage service | Design-only |
| Frontend | Native ES modules/custom elements | React/Vue/CDN/npm runtime | Design-only |
| Tests | Standard unittest and HA's existing test/release infrastructure | Shipping third-party test fixtures as implementation dependencies | No tests written |

**Honest interpretation:** Even with \`"requirements": []\`, Home Assistant itself necessarily depends on third-party modules internally. A platform API that returns an aiohttp client does not make aiohttp "our external library"; it is still a transitive HA dependency. If we impose a ban even on invoking platform-managed HTTP/cryptographic interfaces, we would contradict the goal of a native Home Assistant integration. The accepted target is **zero independently installed runtime packages + 100% own PlayStation protocol logic**, not physically zero third-party code in the operating system.

## 3. Source/ownership review process

For every adapted wire behavior:
1. Identify the originating third-party code or official platform document and pin the exact commit or release.
2. Write protocol facts and known limitations in docs with evidence class SOURCE_OBSERVED, SOURCE_CORROBORATED, PROJECT_PROPOSED, VERIFIED_ON_DEVICE, or TESTED_IN_OUR_CODE.
3. Independently implement parsing/framing/state behavior in our own module; do not transliterate upstream GPL/AGPL logic line-by-line.
4. Create new tests with synthetic inputs authored from documented protocol behavior; do not copy copyrighted test-vector files or secret/static key tables by default.
5. Run actual Home Assistant and PS5 tests once implementation is explicitly authorized, and revise the closest existing spec rather than proliferating speculative ADRs.
6. Keep exact dependency exception decisions in this policy, with explicit user approval and release notes.

## 4. Safest phased capability plan

- **LAN foundation (no extra packages):** source-discovered UDP parsing, native network adapter discovery, multi-console identity, state and optional reported-app/title; no pairing, Sony account or AES required.
- **Native data (no extra packages):** entry-owned reducer, independent Home Assistant entity state, sqlite3 history, one panel and reports. Database worker/storage durability remains to be measured, not delegated to third-party ORM/aiosqlite.
- **Credential-dependent wake:** own DDP packet formatting only when credentials are independently established through an approved flow; do not fake a pairing.
- **Remote Play pairing/standby:** remain blocked pending a vetted AES backend/runtime and key/protocol provenance/firmware tests; no user-visible false "all features finished" claim.
- **Optional PSN cloud:** pending Sony-authorized access and own per-account OAuth lifecycle; never mandatory for LAN.

## 5. Implementation-stage enforcement checklist (all NOT_RUN)

- [ ] \`manifest.json\` verified by hassfest with no extra \`requirements\`, plus only approved HA integration dependencies/after_dependencies.
- [ ] Static import/dependency scan finds no forbidden PlayStation/library imports or vendored code.
- [ ] No \`subprocess\`, shell CLI, Node, MQTT service, hidden extra containers/daemon or CDN runtime asset.
- [ ] One native HA network/broadcast interface contract verified and no direct \`ifaddr\`/netifaces import.
- [ ] Pure UDP packet parser and response semantics tested independently of HA and network.
- [ ] Native HTTP helper is used only for authorized cloud features and no blocking stdlib urllib call in HA loop.
- [ ] Frontend contains own JS ES modules and native UI, no external runtime framework.
- [ ] Crypto blocker policy enforced: Remote Play encrypted features remain unavailable without explicit approved secure backend.
- [ ] No copied GPL/AGPL source/key tables; license provenance reviewed.
- [ ] Offline/PSN-failure mode does not alter LAN state, data history or panel.
- [ ] HA reload/unload/worker/callback tests verify no subprocess or orphaned transport.
- [ ] Real console and Home Assistant OS verification is clearly labelled TESTED or remains NOT_RUN.

## 6. Current disposition

**Accepted requirements:** Own PlayStation protocol and UI code; no external PlayStation packages; no additional Python/npm runtime dependencies; no extra service; HA/Python standard platform APIs allowed; modular/expandable/English documented implementation.

**Technical feasibility:** Local discovery and source processing can be researched as self-contained code. Secure Remote Play crypto remains a named blocker under a strict no-new-runtime-dependency policy; Sony PSN service access remains permission-blocked. These **optional** blockers must not stop LAN implementation research.

**No runtime implementation or test performed in this documentation pass.**

## 7. Platform-preinstalled cryptography clarification — candidate only (2026-11-06)

**New verified fact:** The pinned [HA Core 2026.11.0 \`pyproject.toml\`](https://github.com/home-assistant/core/blob/2026.11.0/pyproject.toml) directly requires \`cryptography==50.0.2\`. PyCA 50.0.2 offers standardized AES and, for legacy interoperability, [CFB within \`cryptography.hazmat.decrepit.ciphers.modes\`](https://cryptography.io/en/50.0.2/hazmat/decrepit/). The earlier finding that **Python's standard library has no raw AES API** remains correct.

**Permitted by the package-count target, not yet by the literal library prohibition:** Using PyCA **already installed by Home Assistant** would add *zero new pip packages* and allow all PlayStation-specific wire protocol, orchestration, state and key derivation logic to remain first-party. But PyCA is still an **external third-party library**, not the standard library or a Home Assistant-owned raw AES helper. It therefore is NOT automatically authorized under this policy.

**Explicit pending maintainer choice:** Either (A) approve a *strictly scoped* PyCA AES primitive exception, only where already pinned and available in supported Home Assistant versions, with full license/compatibility/CFB-version/security tests and no PlayStation SDK, or (B) reject all third-party crypto and leave encrypted Remote Play pairing/standby DEFERRED. The default today remains **NO CRYPTO IMPORT / BLOCKED_CRYPTO_BACKEND_APPROVAL**. This is not a request to install \`cryptography\` and not permission to implement Remote Play code.

**Not a shortcut:** Never replace PyCA with handwritten AES, copied Chiaki key tables, random OpenSSL ctypes FFI or unaudited cipher modes. The protocol-specific tables and Sony credentials still need independent legal/security and firmware evidence. The standalone LAN/SQLite/panel architecture is unaffected.

## 8. PS5 lookup tables: source equivalence does not grant redistribution rights (2026-11-07)

The [new source/rights/test-oracle investigation](../research/ps5-remote-play-lookup-table-provenance-rights-and-independent-oracles-2026-11-07.md) verified **all 8,192 bytes of four PS5 protocol lookup tables are identical** in Chiaki-ng, Playactor and the 2026 Python port. The source lineage is not independent: Chiaki has the complete arrays by December 2020; Playactor adds them March 2021 and its [PR #16](https://github.com/dhleong/playactor/pull/16) expressly acknowledges Chiaki; Python explicitly generated its tables from Playactor in September 2026.

**Licensing nuance to preserve:** Chiaki source is AGPL-3.0-only-OpenSSL; Playactor's `package.json` declares ISC; Python port is AGPL-3.0-only. An ISC package label is not proof that every earlier shared binary table was independently developed or that its author had every redistribution right. Equally, equal table bytes are not automatically copyright infringement or proof copyright subsists in functional constants. The [Portuguese DL 252/94](https://diariodarepublica.pt/dr/legislacao-consolidada/decreto-lei/1994-34555675), [EU Directive 2009/24/EC](https://eur-lex.europa.eu/legal-content/en/TXT/?uri=CELEX%3A32009L0024) and [CJEU C-406/10](https://eur-lex.europa.eu/legal-content/EN/SUM/?uri=celex%3A62010CJ0406) provide conditional interoperability/observation protections but do not automatically license literal code or data reproduction. If encrypted control is later publicly distributed, expert rights review may be necessary for these precise tables.

**Source policy remains:** No raw lookup tables, their generated derivatives, third-party program code or complete AGPL/GPL fixture data may be copied into PlayStation Hub **until a distinct documented rights/provenance decision**. Do not work around the rule with renaming/encoding/obfuscating bytes. Pure AES/HMAC independent standard math can later be tested from RFC 4231 / NIST 800-38A, but mathematical conformance ≠ Sony console interoperability. The already-installed PyCA AES primitive is an **independent**, still unapproved third-party import exception, not a way to acquire rights to Sony-protocol tables.

**Proof states:** Table-byte equivalence SOURCE_CONFIRMED; legal classification/permission OPEN; Sony PSN account access/firmware OPEN; original implementation/tests NOT_RUN; encrypted Remote Play remains BLOCKED_CRYPTO_BACKEND_APPROVAL. Passive LAN and UI remain independent. This research does not authorize coding or waive the no-added-package rule.

## 9. Third-party-free account input: manual Sony Account ID instead of SDK OAuth (2026-11-07)

[PSN Account ID source/consent analysis](../research/first-party-psn-account-id-provisioning-and-pairing-trust-audit-2026-11-07.md) and [first-party pairing identity contract](first-party-psn-account-identity-and-pairing-provisioning-contract.md) clarify the zero-dependency rule: a **manually supplied numeric Sony Account ID or canonical eight-byte little-endian Base64 form** can satisfy the account-identifier INPUT of community-observed PS5 *local registration* without importing PSNAWP, psn-api, Chiaki or Playactor, and without any Sony OAuth flow **inside that local registration method**. A Sony account itself, its Remote Play user settings, a legitimate Pair Device PIN, source-specific crypto key-table rights and approved AES backend remain prerequisites. No guarantee of offline console pairing.

A [Sony official personal-data request](https://www.playstation.com/pt-pt/support/account/data-request/) provides a user-facing personal-data export path; community reports suggest it includes Account ID, but the field is not guaranteed in Sony's public schema. **Do not import the full Excel export** or keep its contents. [Microsoft](https://support.microsoft.com/pt-pt/excel/keeping-leading-zeros-and-large-numbers) warns that 16+ digit numbers rounded in numeric Excel cells cannot be fixed by later cell formatting; use only the exact original decimal string and Python integer encoding, never browser JavaScript Number. User-supplied account identity is not a verified Sony ownership token.

**Explicitly prohibited:** Reusing Sony official Remote Play/Android OAuth client secrets extracted from Chiaki/Playactor/psn-api, NPSSO cookie harvesting, Sony password collection, unauthorized profile scraping, external account-ID lookup service as required runtime dependency, jailbreak/offline account payloads or a hidden console/cloud account bridge. If a genuinely Sony-authorized OAuth client is approved later, it is optional and independent of passive LAN. Neither Account ID nor its Base64 representation is a wake credential; a post-pairing secret derives from PS5-RegistKey. No implementation approval implied.
