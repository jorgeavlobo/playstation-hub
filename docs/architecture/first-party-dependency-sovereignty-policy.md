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
