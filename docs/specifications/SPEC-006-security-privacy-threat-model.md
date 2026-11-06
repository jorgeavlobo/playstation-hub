# SPEC-006 — Security & Privacy Threat Model

**Status:** Proposed security specification — no implementation, penetration test or sign-off
**Date:** 2026-11-05
**Scope:** PlayStation Hub HACS integration, LAN discovery, Remote Play, PSN, SQLite/Store, HA entities, authenticated sidebar/WebSocket, backups, build/release
**Inputs:** Protocols 01–10; ADR-0004–0010; SPEC-001–005; security architecture
**Branch:** Documentation on `main` only; `develop` and `next` unchanged

> **Security evidence:** Requirements and mitigations below are proposals, not verified protections. No Sony credentials, local network scan, hardware pairing or security testing was performed. Sony PSN OAuth/endpoint permission remains blocked under SPEC-003.

## 1. Objectives, assumptions and boundaries

Protect household accounts and gameplay history; prevent unauthorized wake/standby, wrong-console targeting, theft of NPSSO/OAuth/Remote Play keys, unsafe network requests, corrupted history and excessive resource consumption. Preserve LAN-only operation when PSN is unavailable. The deployment assumes an HA Core process running on a host that may contain other integrations and add-ons; filesystem compromise of the HA host can expose unencrypted secrets. HA authentication and a sidebar menu do not themselves provide per-operation authorization.

**Trust boundaries:** (TB1) unauthenticated UDP discovery ↔ LAN parser; (TB2) validated console identity ↔ Remote Play privileged control; (TB3) Sony browser session ↔ HA auth backend; (TB4) third-party Sony endpoints ↔ provider adapters; (TB5) HA authenticated WebSocket ↔ private history and mutating commands; (TB6) Python runtime ↔ SQLite/Store/filesystem; (TB7) release build/dependencies ↔ HACS-installed code; (TB8) private history ↔ exports/backups/diagnostics; (TB9) external artwork ↔ HTTP fetch/cache/browser.

## 2. Assets, principals and adversaries

| Asset | Sensitivity | Owner | Principal risks |
| --- | --- | --- | --- |
| NPSSO, access/refresh tokens | Critical bearer secrets | PSN account | Account takeover, leaked logs/backups |
| Remote Play registration keys/wake secret | Critical device control | Validated console/principal | Unauthorized power control |
| OAuth state/PKCE verifier/authorization code | Transient high | Link flow | CSRF, replay, account substitution |
| Console host ID/IP/hostname | Personal/device identifiers | Physical console | Tracking, identity spoofing |
| Player/game timeline, child activity | Private personal data | User/account/console | Unwanted household disclosure |
| SQLite ledger and checkpoints | Integrity-critical | Integration | Corruption, fabricated minutes, loss |
| HA device/entity registry | Integrity-critical | Home Assistant | Device confusion and cross-target commands |
| Sidebar/WebSocket session | Authenticated boundary | HA user | Unauthorized reads, mutations, XSS |
| Build artifacts and dependency graph | Supply chain | Maintainers | Malicious package, compromised release |

Threat actors: unauthenticated LAN peer, compromised or malicious HA integration/add-on, lower-privileged HA user, hostile provider payload or image URL, attacker with stolen backup, malicious upstream dependency, accidental maintainer disclosure and an authorized user operating the wrong console. No claim that a `host-id` cryptographically authenticates a PS5.

## 3. Method and risk scoring

Use STRIDE categories (spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege) plus privacy misuse. Rate **impact** and **likelihood** 1–5, record residual risk after mitigation, evidence, owner and disposition. A score is triage guidance, not permission to waive critical flaws. Critical examples (token disclosure, unauthorized power control, history corruption, privacy bypass) block affected release even when score is low. Status vocabulary: PROPOSED, IMPLEMENTED_UNVERIFIED, TESTED, BLOCKED, ACCEPTED_RISK (with owner/expiry).

## 4. Threat register

| ID | Boundary | STRIDE / threat | Impact | Required control | Verification |
| --- | --- | --- | --- | --- | --- |
| TH-001 | TB1 | Forged DHCP Sony OUI/hostname | False discovery | Probe and validated protocol ID; no auto-pair | SEC-T001 |
| TH-002 | TB1/TB2 | Spoofed host-id or IP reuse | Keys sent to wrong console | Revalidate identity, block mismatch, pairing binding | SEC-T002 |
| TH-003 | TB1 | Oversized/malformed UDP packet | Parser DoS | Bounded datagram, strict parser, rate limit | SEC-T003 |
| TH-004 | TB2 | Replay/wrong crypto counter | Session compromise | Source-verified nonce/counter, audited crypto | SEC-T004 |
| TH-005 | TB2 | Standby triggers implicit wake | Unwanted power change | Fresh preflight; never wake to standby | SEC-T005 |
| TH-006 | TB2 | Unconfirmed command reported successful | Incorrect automations | Post-command evidence, UNCONFIRMED state | SEC-T006 |
| TH-007 | TB3 | Fake Sony login or browser cookie extraction | Credential theft | Sony-origin login only; no password collection | SEC-T007 |
| TH-008 | TB3 | OAuth CSRF/state replay/account swap | Wrong account linked | Single-use state, PKCE where applicable, identity check | SEC-T008 |
| TH-009 | TB3/TB6 | Token rotation race | Lost authorization | Per-account single-flight, durable generation commit | SEC-T009 |
| TH-010 | TB4 | Undocumented Sony client/scope use | Compliance/privacy risk | Provider permission gate; disable PSN until approved | SEC-T010 |
| TH-011 | TB4 | Provider 403/429 bypass/retry storm | Privacy breach/DoS | Respect restrictions, budget and Retry-After | SEC-T011 |
| TH-012 | TB5 | HA non-admin accesses private timeline | Privacy disclosure | Backend ACL on every endpoint and target | SEC-T012 |
| TH-013 | TB5 | User sends wake for another device | Unauthorized action | Target-scoped permission and stable identity | SEC-T013 |
| TH-014 | TB5 | XSS via title/online ID | Session misuse | Escape untrusted strings, no unsafe HTML | SEC-T014 |
| TH-015 | TB5 | Unbounded history query | Resource exhaustion | Server-side cursor, limits, cancellation | SEC-T015 |
| TH-016 | TB5 | Reconnect replays standby/wake | Duplicate command | Operation IDs, never auto-resend mutations | SEC-T016 |
| TH-017 | TB6 | SQLite partial write/crash | Incorrect duration | Atomic checkpoint/event transaction, idempotency | SEC-T017 |
| TH-018 | TB6 | Live WAL database copied naively | Corrupt backup | Consistent SQLite backup and restore validation | SEC-T018 |
| TH-019 | TB6/TB8 | Unencrypted secret in backup/export | Token disclosure | Separate secrets, backup access/encryption review | SEC-T019 |
| TH-020 | TB6 | HACS update overwrites DB | Data loss | Mutable data outside code directory | SEC-T020 |
| TH-021 | TB7 | Compromised dependency/build artifact | Arbitrary HA code | Pin/review dependencies, provenance, scan releases | SEC-T021 |
| TH-022 | TB7 | Credential in GitHub Actions log | Token disclosure | Synthetic fixtures, secret scan, redacted CI | SEC-T022 |
| TH-023 | TB8 | Diagnostics expose child activity | Privacy disclosure | Default redaction and authenticated export | SEC-T023 |
| TH-024 | TB8 | Unlink retains hidden account secrets | Privacy failure | Scoped durable deletion and documented backups | SEC-T024 |
| TH-025 | TB9 | Artwork URL SSRF/redirect to LAN | Network compromise | Allowlist, DNS/IP checks per redirect, size/MIME caps | SEC-T025 |
| TH-026 | TB9 | Artwork license violation | Legal/release issue | Rights inventory, disable caching until approved | SEC-T026 |
| TH-027 | TB1/TB5 | Discovery/API flood | HA availability loss | Per-source/connection rate and concurrency budgets | SEC-T027 |
| TH-028 | TB6 | Downgrade reads newer schema | History damage | Read-only reject, migration/rollback plan | SEC-T028 |
| TH-029 | TB5/TB8 | Browser shared-device history residue | Privacy disclosure | In-memory state, logout purge, no private localStorage | SEC-T029 |
| TH-030 | TB4/TB5 | PSN presence mistaken for hardware state | Wrong automation/activity claim | Source-scoped authority, uncertainty | SEC-T030 |

## 5. Credential lifecycle security

PSN tokens are owned by canonical PSN account identity; Remote Play pairing credentials by canonical console and pairing principal. A token must never cross owners or be stored in the session ledger, entity attributes, JS, logs, notifications, traces or diagnostics. No NPSSO in URL query/fragment. Use HA-supported secure storage patterns with filesystem permissions and explicit backup policy; HA Store/Config Entries are not encrypted vaults by default. Do not invent homemade encryption or claim key separation when ciphertext and key coexist. Sony refresh-token rotation and local storage are not distributed atomic; surface reauth when crash interrupts rotation.

Credential deletion must cancel in-flight tasks, fence old generations, remove only scoped secrets and document that older HA backups may retain prior copies. Do not claim Sony-side revocation without supported endpoint. For Remote Play, registration PIN and session nonce/counter are transient; revalidate physical console target before every privileged operation.

## 6. Network, protocol and cryptographic controls

Use strict bounded UDP parsing, address-family and source validation, conservative discovery concurrency and explicit user acceptance. A valid discovery response establishes a protocol-level claim, not cryptographic identity. No wake/pairing from background DHCP. Remote Play implementation must pass independent known-answer vectors and framing tests from SPEC-002, including nonce length, counter endian/direction, AES-CFB mode and exact registration bytes. Source-derived encryption is not automatically authenticated encryption. Avoid logging raw packets with credentials. A successful socket write does not prove standby.

## 7. HA authentication, authorization and WebSocket

Initial design preference: admin-only private panel and history/mutation APIs pending finer ACL; **backend checks remain mandatory**. Resolve each requested target against canonical registry, current authenticated HA user and operation permissions. Do not trust a frontend-supplied `device_id`, `config_entry_id`, account ID, page cursor or requested URL. Separate read from write scopes; require explicit user confirmation for destructive export/delete/unpair and power controls where product policy requires it. Bound response size, query time and subscriptions; unsubscribe on disconnect and reject stale runtime generations. Use consistent sanitized error codes.

## 8. Privacy model and retention

Gameplay history may reveal household schedules, children's activity, purchases and social information. Minimize raw provider responses and collect only opt-in PSN fields. Show provenance, completeness and attribution; avoid inferred personal activity being presented as fact. Define console history retention separately from PSN account unlink, and permit authorized export/purge. Avoid indiscriminate SQL cascades from account removal into independent console history. Backup copies and Recorder history have separate lifecycle and must be disclosed. No telemetry or external analytics by default without a separate opt-in decision.

## 9. Data storage, backup and recovery security

One integration-owned SQLite ledger is a proposed candidate, not an approved implementation. Enforce transactional ingestion and unique IDs; never silently replace a corrupted DB. Test disk-full, migration interruption, downgrade and stale backups. WAL mode requires consistent snapshot mechanism; copying `.db` alone under active writes is not accepted. Document data-path permissions, credential-store backup inclusion, archive encryption, snapshot high-water mark, restore integrity and reauthentication of stale Sony tokens. A history export must exclude bearer secrets and be authenticated and bounded.

## 10. Artwork, external content and supply chain

Artwork proxying is optional and disabled until source rights and fetch policy are approved. Validate HTTPS, host allowlist, DNS rebinding/private IPs, redirects at every hop, response byte limit, MIME signature, dimensions and decompression bounds. Do not forward Sony bearer tokens to arbitrary artwork URLs. Frontend treats provider strings as untrusted text. Dependency controls include reviewed lockfiles, pinned actions, license inventory for Chiaki/playactor-derived tables, reproducible release bundle, dependency scan and HACS/Hassfest validation. Do not expose source maps containing sensitive build paths or secrets.

## 11. Security test plan

| ID range | Harness | Mandatory evidence |
| --- | --- | --- |
| SEC-T001–003 | Fake DHCP/UDP | Spoof, mismatch, malformed payload and safe abort |
| SEC-T004–006 | Crypto/session fake | KATs, no implicit wake, command confirmation |
| SEC-T007–011 | Fake OAuth/provider | CSRF, token isolation, permission block, backoff |
| SEC-T012–016 | HA WebSocket/services | ACL, wrong target, XSS, pagination, replay |
| SEC-T017–020 | SQLite/Store/backup | Atomicity, snapshot restore, secret isolation, path safety |
| SEC-T021–024 | CI/diagnostics/unlink | Supply chain, secret scan, redaction, scoped deletion |
| SEC-T025–026 | Fake image fetcher | SSRF, redirect, MIME/size, rights gate |
| SEC-T027–030 | Fault/load/domain | Flood, schema downgrade, logout, source authority |

For each test record code SHA, environment, synthetic fixture provenance, expected/actual results, timestamp and reviewer. No test in this specification is marked passed.

## 12. Security release gates

| Gate | Required outcome | Status |
| --- | --- | --- |
| SEC-G01 | Threat register triaged and ownership assigned | NOT_RUN |
| SEC-G02 | Credential isolation and secret scanning passed | NOT_RUN |
| SEC-G03 | LAN identity and command-target safety passed | NOT_RUN |
| SEC-G04 | Remote Play crypto and pairing safety passed | NOT_RUN |
| SEC-G05 | HA WebSocket/API ACL and XSS passed | NOT_RUN |
| SEC-G06 | SQLite backup/restore, corruption and privacy passed | NOT_RUN |
| SEC-G07 | Artwork SSRF/license reviewed if enabled | BLOCKED/NOT_RUN |
| SEC-G08 | Sony client/endpoint permission for PSN | BLOCKED |
| SEC-G09 | Child/account privacy, retention, unlink/export tested | NOT_RUN |
| SEC-G10 | Dependency/license/release artifact audit passed | NOT_RUN |
| SEC-G11 | HA OS/mobile/browser validation passed | NOT_RUN |
| SEC-G12 | Human security review and sign-off | NOT_RUN |

A BLOCKED gate cannot be waived into PASS. Optional modules can be excluded from a narrower LAN-only release, but all relevant common security gates must pass. Security-critical vulnerabilities block the affected release regardless of code coverage.

## 13. Incident response and vulnerability handling

Document a private vulnerability-reporting channel before public release, severity triage, response owner, supported versions and security patch procedure. On suspected token leakage, instruct user to revoke/re-authenticate through supported Sony controls; never log the secret during diagnosis. On database corruption, preserve evidence, stop writes and guide backup restore; never silently reset history. On misdirected power commands, disable affected capability until identity mapping is corrected. Release advisories should explain impact and remediation without exposing private identifiers.

## 14. Open decisions and sign-off

- [ ] Approve threat model scope, ownership and risk thresholds.
- [ ] Pin HA Core baseline and exact permission APIs.
- [ ] Finalize credential store, encryption/key custody and backup retention.
- [ ] Validate canonical console ID and cryptographic pairing trust boundary.
- [ ] Decide admin-only v1 versus per-user historical ACL.
- [ ] Approve data retention/export/deletion for child and household history.
- [ ] Resolve Sony PSN API client/endpoint authorization or exclude PSN.
- [ ] Review image rights and SSRF-safe fetch strategy.
- [ ] Pin dependencies and source licenses; add CI secret scanning.
- [ ] Execute synthetic tests and HA OS/hardware checks.
- [ ] Record accepted residual risks with owner, date and expiry.
- [ ] Complete SPEC-007 hardware/firmware compatibility matrix.

## 15. References

- [Security architecture](../architecture/security-architecture.md)
- [SPEC-001 LAN discovery](SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-002 Remote Play](SPEC-002-remote-play-byte-contract-and-safety.md)
- [SPEC-003 Sony authorization](SPEC-003-psn-authorization-and-availability.md)
- [SPEC-004 DTO mapping](SPEC-004-psn-presence-game-metadata-dto-mapping.md)
- [SPEC-005 CI/release gates](SPEC-005-end-to-end-testing-ci-release-quality-gates.md)
- [ADR-0007 credential lifecycle](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008 storage](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009 HA integration](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [ADR-0010 sidebar/API](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- https://developers.home-assistant.io/docs/core/diagnostics/
- https://developers.home-assistant.io/docs/frontend/extending/websocket-api
- https://www.home-assistant.io/common-tasks/general/backups
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/www-community/attacks/Server_Side_Request_Forgery
- https://sqlite.org/backup.html

**Outcome:** Thirty identified threats, thirty corresponding security test cases and twelve unpassed security gates. Research only; no implementation or security validation.


## 16. Administrator recovery, untrusted archives and privilege boundaries — 2026-11-06

**Security architecture remains a proposal; no implementation/security tests.** [Official-source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) and [SPEC-014](SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) specify a protected history restore flow within the single Home Assistant panel.

New threat paths:
- **Privilege escalation:** A non-admin or a previously admin user with revoked permissions submits a recovery confirm, export or file choice. Require server-side HA require_admin and current authority at each phase; sidebar visibility alone is insufficient.
- **Stale approval / TOCTOU:** Candidate bytes, file size, ledger cursor, association mapping or canonical console ID changes between preview and confirm. Bind preview to digests, expected revision, admin, expiry and scoped candidate; revalidate under exclusive global restore gate immediately before mutation.
- **Path traversal / archive bombs / symlinks:** Hostile imported backup attempts arbitrary path reads/writes, huge decompression or disk exhaustion. Accept opaque server-side candidates; future import must impose strict archive member ownership, path containment, file count/decompressed bytes and time limits. Never expose arbitrary local filesystem paths, URL fetches or direct SQL queries.
- **Replay / double restore:** Two tabs/admins repeat same confirmation after network loss. Manager-owned idempotent job ID, one exclusive promotion, durable journal and no automatic retry of destructive operations.
- **Connection or Core shutdown:** Client WebSocket disconnect unsubscribes progress only; it does not prove a half-promoted SQLite operation was cancelled. Controller-owned recovery job must settle or restart safely. An uncooperative worker may remain after HA timeout; never reopen the same DB path before confirming closure.
- **Identity graft:** Restored old console entry at reused IP or old PSN account association causes misattribution / privileged hardware command. Disable affected writes and controls until identity independently validated; ledger UUID/commit cursor alone is not enough to prove same fork.
- **Diagnostics disclosure:** Repairs and public diagnostics exclude raw game/title/player history, canonical private identifiers, credentials, archived payloads, absolute paths, tokens and opaque authorization preview tokens.
- **False source trust:** Supervisor restore-progress event proves a job state, not the origin/authentication of an app-owned SQLite file. A SHA hash is integrity evidence only, not a signature when payload and manifest are both user-controlled.

User-created Hub/Archive Config Entry and private history retention remain accepted product directions per ADR-0011; the specific recovery API/UX still needs maintainer approval and all 72 SPEC-014 cases remain NOT_RUN. Existing security gates remain unpassed.


## 17. Crash-atomic file-promotion and malicious journal integrity threats — 2026-11-06

[Official SQLite/Python/POSIX source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md), and [SPEC-015](SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) add new future security cases. Threats include a tampered active pointer targeting a malicious symlink/path; a forged recovery journal claiming COMPLETED despite an old active pointer; an old executor still writing into a renamed SQLite DB while a new writer shares its WAL; a partial published generation after power loss; a low-privilege browser repeating a previously approved recovery decision; and retention GC deleting the only good original or a live backup source.

Proposed mitigations: fixed private storage roots with canonical path allowlist, generated UUID basenames, no symlink/hardlink aliases, bounded versioned journal/pointer content and digest validation; separate user/admin ACL from file metadata (hash is not authentication); exclusive HubController recovery lease; positive closure of all SQLite workers before pointer selection; separate per-generation SQLite paths and SQLite-managed WAL/journal names; same-filesystem atomic pointer update plus file and directory fsync on tested OS; original generation preservation; idempotent startup reconciliation; globally scoped Repairs on uncertainty, and strict secret/identity segregation.

A journal marked COMMITTED does not prove matching HA Config Entry registry/PSN identity because these are separate systems. Recovery must revalidate canonical physical identity before privileged controls resume, and never claim sessions recorded after an old backup if no current copy exists. All 80 SPEC-015 scenarios are NOT_RUN and no threat-control implementation is approved.
