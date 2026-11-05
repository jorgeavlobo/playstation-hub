# ADR-0007 — Credential isolation, lifecycle, rotation and persistence

**Status:** Proposed for architectural review; not accepted, implemented, or tested with actual credentials  
**Date:** 2026-11-05  
**Scope:** PSN NPSSO/OAuth access and refresh tokens; Remote Play PIN/registration/session/wake credentials; Home Assistant secret persistence, backup/recovery, permission boundaries and account/device unlink  
**Preceding:** [ADR-0004](ADR-0004-identity-and-multi-console-ownership.md), [ADR-0005](ADR-0005-observation-and-state-reconciliation.md), [Protocol 04](../protocols/04-remote-play-registration.md), [Protocol 08](../protocols/08-psn-authentication.md)  
**Following:** ADR-0008 storage/backups, ADR-0009 HA entities/actions, ADR-0010 sidebar/backend API

> **Scope and evidence:** This ADR documents the desired trust boundaries, state machines, durable-store requirements and failure handling. Observed third-party Sony endpoints and OAuth clients are not Sony-approved third-party integration contracts. The PSN shipping authorization gate described in Protocol 08 remains **BLOCKED**. No real credential material, production account, live OAuth request or console pairing was used.

## 1. Problem statement and goals

PlayStation Hub needs two distinct kinds of authenticated capability: local, user-authorized Remote Play control of a particular physical console, and optional Sony PlayStation Network account enrichment (presence, titles and library). These are different trust domains. We cannot safely put all secrets into one global options map, expose secrets through the sidebar, or let one console/account's refresh process overwrite another one's keys.

Goals:
1. One HACS integration, without mandatory MQTT, standalone App, browser extension, background proxy or external credential service.
2. Keep local LAN discovery and status functional with **no PSN account**, and with **no Remote Play pairing** when only passive monitoring is wanted.
3. Make Sony login occur exclusively in Sony-controlled interfaces; no request for Sony password/2FA in Home Assistant.
4. Support account-specific authentication, token refresh, durable restart recovery and reauthentication while recognizing provider authorization limits.
5. Ensure pairings are scoped to a validated physical console, not merely current IP.
6. Avoid leaking bearer tokens or cryptographic keys via Python logs, entities, events, WebSocket, panel JavaScript, browser storage, diagnostics and support archives.
7. Support independent multiple consoles/accounts, bounded concurrency, cancellation and safe uninstall/unlink/unpair.
8. Do not declare a refresh/pairing operation successful until the required credential storage has acknowledged durability.
9. Build a versioned storage abstraction without prematurely selecting SQLite/Store/config entries or introducing fragile home-grown encryption.
10. Produce deterministic synthetic tests and a documented threat model before implementing.

## 2. Credential inventory and exact ownership

| Secret / artifact | Origin | Owner key | Consumer | Lifetime / protection |
| --- | --- | --- | --- | --- |
| Sony account password / passkey / MFA | User and Sony | Sony only | Sony login | **Never processed or stored by PlayStation Hub** |
| `npsso` | User's authenticated Sony browser (community documented) | Stable `psn_account_id`, once verified | PSN bootstrap if authorized | High-sensitivity bearer secret; retention is **OPEN** |
| OAuth authorization code | Valid provider authorization exchange | Account flow attempt | One token exchange | Transient only, not persisted |
| OAuth `access_token` | Sony auth endpoint | PSN account | PSN API adapter | Rotating/expiring bearer secret |
| OAuth `refresh_token` | Sony auth endpoint | PSN account | Token manager | Rotating bearer secret; durable replace |
| OAuth `id_token` if returned | Sony auth endpoint | PSN account | Account identity validation when applicable | Sensitive; store only if proven necessary |
| Remote Play registration PIN | Console and user | Selected validated console and flow | Pairing only | Transient; never durable |
| `RP-Key`, `PS5-RegistKey`, relevant pairing secrets | Authenticated Remote Play registration | Physical console + authorized pairing principal | Local wake/session/command adapter | Protected persistent per-console key material |
| Derived wake credential | Pairing material, as wire spec confirms | Same physical console/principal | Wake adapter | Derived on demand if feasible; persistence policy OPEN |
| Remote Play session nonces/counters/temporary keys | Protocol handshakes | One control session | Crypto/session adapter | Ephemeral only; zero/clear references on teardown where feasible |
| Console `host-id` / PSN `account_id` | LAN / PSN identity | Registry | Identity resolution | Not cryptographic secrets, but personal/device identifiers requiring redaction in diagnostics |

**Hard boundary:** A Sony PSN OAuth bearer token never substitutes for a Remote Play pairing key. A Remote Play registration credential is not an OAuth credential. Neither may be used against a newly resolved IP before identity checks. Account credentials must not be keyed by user-facing online ID or console nickname.

## 3. Alternatives considered

| Choice | Benefit | Risk / limitation | Recommendation |
| --- | --- | --- | --- |
| Secrets directly in `ConfigEntry.data` | Native lifecycle; precedent in Home Assistant and Emkraan | Plain serialized HA configuration is **not automatically an encrypted vault**; token rotation writes may be frequent | Accept only after scoped security review, not blindly |
| HA versioned `Store` in config area | Versioned structured persistence | Not automatic encryption; serialization/write durability and backup details require review | Strong candidate for secret repository **after validation** |
| Dedicated encrypted file | Confidentiality beyond filesystem permissions | Key-management, backup/restore and reliability complexity; a key stored alongside ciphertext adds little protection | Defer pending threat-model decision |
| OS keyring / external secrets vault | May improve key isolation | Not universally available on HA OS; violates no-extra-service aim if required | No mandatory dependency |
| Put tokens in game-session SQLite | Easy one database | Mixed retention/privacy and accidental export; more exposure | Reject |
| Keep all tokens in memory only | Limits disk exposure | Reauth on restart, unusable unattended refresh chain | Reject for target UX |
| Use another running HA PSN integration's tokens | Potential reuse | Runtime coupling, unsupported credential sharing and privacy conflict | Reject |
| Reuse public mobile-app OAuth client as though ours | Easy community example | Permissions and Sony approval not established | **BLOCKED** |

**Preferred decision direction, not final selection:** A `PsnCredentialRepository` and a `RemotePlayCredentialRepository` backed by an audited, versioned Home Assistant-compatible storage mechanism, isolated from session history. ADR-0008 selects the exact implementation, file location and backup policy. Restrict OS file permissions and Home Assistant user/API access; encryption at rest needs independent key custody to improve its threat model.

## 4. PSN account linking: allowed UX and known browser boundaries

**Product requirement:** Start from the PlayStation Hub configuration/panel, open Sony's own login as needed, reuse an already authenticated browser session when possible, and minimize manual steps. This is a UX requirement, **not evidence of an available Sony callback**.

The community `https://ca.account.sony.com/api/v1/ssocookie` route may expose NPSSO to a signed-in browser. JavaScript executing on the HA origin cannot read Sony-origin cookies or cross-origin response bodies absent explicit browser/provider permission; `window.open` and iframes do not bypass same-origin rules. A remote HA OS process cannot inspect the user's existing browser session. `psn-mcp` uses Chrome DevTools only because it owns a local temporary browser process; it is not a browserless HACS recipe.

**Assisted fallback:** Explicitly show the Sony sign-in/NPSSO link, receive a user-pasted NPSSO in a secure HA config/reauth form, validate it server-side, discard transient UI fields, and never put it in a URL, history entry, localStorage, or logs.

**Future automatic approach:** Only when an appropriately authorized Sony OAuth client and redirect URI are available, use supported HA application credentials / config-flow callback machinery, CSRF `state`, and PKCE where required/available. Do not substitute another application's registered redirect URI or silently scrape an account's browser cookies. Client ownership, endpoint scopes and third-party permission remain blocked release prerequisites.

**Account identity:** Resolve and verify provider-stable `account_id` before associating or storing long-lived credentials; reauth must compare it with the existing configured account ID. Reject alternate account credentials rather than silently rekeying history.

## 5. Account-scoped PSN token state machine

```text
UNLINKED -> BOOTSTRAPPING -> VALIDATING_IDENTITY -> AUTHORIZED
AUTHORIZED -> REFRESH_DUE -> REFRESHING -> PERSISTING -> AUTHORIZED
REFRESHING -> TEMPORARY_FAILURE -> RETRY_BACKOFF -> REFRESHING
REFRESHING -> REAUTH_REQUIRED
AUTHORIZED -> PROVIDER_REVOKED -> REAUTH_REQUIRED
ANY_LINKED -> UNLINKING -> UNLINKED
```

**Key invariants:**
- Token expiry is derived from response lifetimes at receipt and stored as a UTC absolute instant; reading or restarting does **not** extend the token validity.
- A 60-second access-token refresh safety margin is a proposed initial reference from Emkraan, not a universal Sony constant.
- A single refresh may be underway for each account. Concurrent callers await the same result (**single-flight**); different accounts operate independently.
- If refresh rotates the refresh token, persist the new response/generation **before reporting a durable successful renewal**. No reload of all Home Assistant entries merely because the token changed.
- In-flight stale refresh outcomes must never overwrite a newer token generation.
- Confirmed `invalid_grant` indicates reauth when no other permitted recovery path remains. A transport timeout, 429 or 5xx is temporary/unavailable, not automatic invalidation.
- Do not repeat invalid credentials at high frequency or use automated Sony logins to evade provider controls.
- If a refresh token is no longer usable, an optional retained NPSSO might support bootstrap **only if authorized**, its retention risk has been accepted and it remains valid. Otherwise request user reauth.

### 5.1 Token rotation failure window

Provider refresh-token rotation and local durable storage are **not a distributed atomic transaction**. A process crash or disk failure between remote rotation and local persistence can strand the old stored refresh token. Even fsync/local transactional semantics cannot eliminate that remote/local window.

Policy: minimize it through prompt persistence, block concurrent operations until the new generation is durable, surface errors safely, and allow user-authorized reauth without deleting LAN devices or history. Do not promise zero-loss token refresh.

### 5.2 Library compatibility

Official HA `playstation_network` uses PSNAWP 3.0.3 and accepts manual NPSSO. Emkraan restores a saved token response and guards concurrent refresh with a per-client lock, but monkey-patches internal exception handling. PSNAWP development-source constructor APIs should **not** be assumed present in the 3.0.3 PyPI release. Pick a tested/pinned package or an adapter exposing a stable supported interface; avoid global process-wide patches.

## 6. Remote Play credential lifecycle

```text
NOT_PAIRED -> USER_REQUESTED -> IDENTITY_PRECHECK -> AWAITING_PIN
 -> REGISTRATION_DISCOVERY -> EXCHANGE -> RESPONSE_VALIDATION
 -> DURABLE_COMMIT -> PAIRED
PAIRED -> CONTROL_SESSION -> PAIRED
PAIRED -> REPAIRING -> PAIRED | PAIRING_REQUIRED
PAIRED -> USER_UNPAIR -> UNPAIRED
```

- Registration is initiated only after explicit user action, against validated selected console identity. A DHCP candidate is never sufficient.
- Treat PINs as one-time transient secrets. Limit attempts and ensure cleanup on failure/cancel.
- Validate required registration response fields such as `RP-Key` and `PS5-RegistKey`, using Protocols 04–06 for exact format, and reject partial/corrupt records.
- Scope a credential to the physical console ID and pairing principal where applicable; multiple consoles must not share keys or a global mutable pairing session.
- Revalidate the device identity/address before credentialed wake/standby. A previous address reassigned to another console must not receive a prior console's keys.
- Session cryptographic nonces/counters must not be persisted as new durable pairing credentials by default; no nonce reuse after reconnection.
- A successful protocol registration response without a durable write is **not** a ready/paired integration state. Report storage failure and allow safe retry.
- An explicitly requested unpair deletes only the targeted console's pairing secrets; LAN monitoring and unrelated accounts/console histories remain available.
- Exact wake-credential derivation and registration key-table provenance remain under Protocols 03–05 verification. This ADR does not claim source compatibility.

## 7. Repository and serialization boundaries (proposed)

Separate repositories logically even if an eventual HA storage implementation shares a backend:

```text
PsnCredentialRepository
  load(account_key) -> credential generation or missing
  replace_if_version(account_key, expected_generation, new_secret)
  delete(account_key) -> durable deletion acknowledgment

RemotePlayCredentialRepository
  load(console_key, pairing_principal) -> pairing record or missing
  replace_if_version(console_key, principal, expected_generation, new_secret)
  delete(console_key, principal) -> durable deletion acknowledgment

CredentialStorageHealth
  last_successful_commit_at_utc
  durability_status: durable | degraded | failed
  schema_version / migration_status
```

These interfaces and records are **conceptual**, not code that exists. Exact HA write APIs, disk fsync assurances, encryption-at-rest behavior, backup inclusion and cross-entry ownership must be decided in ADR-0008.

**Record envelope:** schema version; owner kind/id; credential kind; account/console binding; generation; created/rotated-at UTC; absolute expiry where applicable; opaque secret fields; last-sanitized-error category. Never serialize entire raw HTTP responses when only defined fields are needed. Copy-on-write rather than in-place mutation of HA config entry objects. No non-atomic mixed writes of authorization generation and token pair.

**Concurrency:** Per-owner async lock/single-flight in coordinator, optimistic generation compare-and-swap (or transactional equivalent) at repository boundary, and bounded requests. If using executor-backed synchronous PSNAWP, provide one serialized authentication owner and safe thread-to-loop handoff; never directly modify config entries from a worker thread.

## 8. Home Assistant storage, backups and restore

- `ConfigEntry.data` and Home Assistant's `Store` helper persist JSON data in HA-managed configuration areas, but **do not constitute encryption by default**. Their concrete source and support guarantee must be inspected at the pinned HA Core baseline.
- Place mutable secret records under supported HA configuration storage, not inside `custom_components/playstation_hub/` or the public repo. Never include real user configuration in fixtures.
- Home Assistant backup encryption protects eligible backup archives at rest/transfer when enabled; it does **not** imply runtime encryption or that secrets can safely be emailed/shared.
- Verify actual backup inclusion and consistency with synthetic credentials and a restore test, considering source files, WAL, atomic writes and HA storage lifecycle.
- Restored refresh tokens may have been rotated after the backup; reauth could be required. Restored Remote Play keys may be invalid if the console has been reset/repaired.
- A restart restores metadata and credential records, checks expiry and identity, and schedules bounded validation. It must not treat historical `authorized` or `paired` flags alone as proof of current validity.
- A partially corrupt credential record must be quarantined with sanitized diagnostics, not silently overwritten or leak raw token text.
- Storage full/unwritable prevents declaring durable success. No cleartext sensitive backup copies generated by convenience code.

### 8.1 Encryption at rest decision gate

Threat-model alternatives:
1. Rely on HA host, authentication and protected filesystem plus encrypted backups, documenting residual host compromise risk.
2. Add application-managed encryption only with a key stored/separated appropriately; if ciphertext and key coexist in the same readable location, benefit is limited.
3. User-supplied external secret/key store as optional extension only; never a required plugin/service for ordinary HACS install.

Do not create custom cryptographic primitives. The exact policy needs a security review, supported host APIs and a backup/recovery story. **No claim of a fully encrypted secret vault is made.**

## 9. Backup, crash and recoverability matrix

| Event | PSN behavior | Remote Play behavior | LAN/history |
| --- | --- | --- | --- |
| Normal HA restart | Restore latest durable tokens, refresh only if due | Restore pairing, verify target when used | LAN independently starts; history preserved |
| Network down | Backoff without deleting tokens | Unreachable command fails safely; keys retained | Local monitoring recovers independently |
| Provider 429/5xx | Delay, preserve credentials | Unaffected | Unaffected |
| Provider invalid_grant | Reauth, no infinite retry | Unaffected | Unaffected |
| Crash before token persisted | Previously saved token may be invalid; reauth possible | Do not claim uncommitted pairing | Keep prior committed history |
| Crash during pairing | No partially paired ready state | Retry only after user action | LAN-only remains |
| Restore older backup | Token may be revoked/rotated; bounded validation | Pairing may need regeneration | No fabricated missing time |
| Console IP changed | PSN unaffected | Verify physical ID before privileged command | Rediscover address, preserve ID/history |
| Console hardware replaced | PSN unaffected | No silent key transfer | New console identity, old history separate |
| User unlinks PSN | Delete targeted account tokens, stop tasks | Unaffected unless separately requested | Preserve independent LAN data |
| User unpairs console | PSN unaffected | Delete targeted pairing secrets | Preserve console discovery/history |
| HACS source upgrade | No embedded secret migration copy | Same | Test storage schema migrations |

## 10. Permission and trust boundaries

**Threat model actors:** unauthorized HA user, malicious frontend JavaScript/third-party custom card, hostile LAN endpoint, compromised addon/container with filesystem access, corrupted cloud response, accidental diagnostic upload, backup disclosure and Sony account token compromise.

Controls:
- Apply Home Assistant auth/authorization checks to protected WebSocket and service actions; panel visibility alone is not authorization.
- No generic `get_credentials` WebSocket operation; API only exposes sanitized `linked/reauth_required` and token-expiry *status*, not secrets.
- No credentials in logs, frontend bundles, entity extra attributes, HA event bus, trace data, notifications, exception messages or analytics.
- Isolate per-account and per-console locks, rate limits and credential namespaces. Reject cross-owner writes.
- Validate HTTP redirect origin/size and TLS for Sony requests. Do not send bearer tokens to arbitrary URLs or images/CDNs.
- Remote Play goes only to the validated network target and expected fixed service ports; do not let user-influenced discovery response become an unrestricted SSRF/socket target.
- Sensitive memory cannot be guaranteed erased in managed Python; remove references promptly and avoid unnecessary copies/string formatting.
- Avoid storing temporary NPSSO in browser URL fragment, query or persistent form state; handle it only through authenticated HA backend config flow.
- Periodic credential validity checks must not trigger surprise Sony sign-ins or device power actions.

## 11. State and error taxonomy

| Error | Meaning | Correct response |
| --- | --- | --- |
| `npsso_invalid` | Invalid or expired bootstrap secret | Request deliberate user reauth |
| `psn_client_unauthorized` | Client/scope not permitted | Block PSN feature, do not bypass |
| `oauth_invalid_grant` | Refresh grant rejected | Reauth if no approved recovery |
| `oauth_rate_limited` | Provider throttling | Bounded Retry-After/backoff |
| `oauth_network_failure` | DNS/timeout/5xx | Degraded but not revoked |
| `oauth_malformed_response` | Unexpected JSON/expiry/token fields | Reject without replacing valid stored generation |
| `credential_generation_conflict` | Stale concurrent renewal attempted commit | Never overwrite newer generation |
| `credential_storage_unavailable` | Disk full or write failed | Report not durable, do not declare ready |
| `remote_play_pin_rejected` | Registration rejects user PIN | Stop bounded attempts, user correction |
| `remote_play_key_invalid` | Invalid pairing credential format | Reject or prompt re-pair |
| `remote_play_identity_mismatch` | Network target changed physical identity | Block privileged operation |
| `remote_play_session_rejected` | Pairing/session protocol rejected | Clear only session data, re-pair if required |
| `credential_record_corrupt` | Unreadable store/schema | Quarantine, explain recovery path, preserve unrelated records |
| `unlink_cancelled` | User/lifecycle cancels deletion | Preserve consistent previous state |

**Error contract:** Each failure has source domain, retryability, user remedy, redacted message and no raw server body. Cancellation and reload are lifecycle events, not lost passwords or network faults.

## 12. Removal, unlink, unpair and privacy

Three user actions are different:
- **Unlink PSN account:** stop scheduled PSN work, await/cancel refresh, delete that account's secret records and account mappings according to privacy policy. Do **not** claim remote Sony token revocation unless supported and verified.
- **Unpair physical console:** delete that console/principal's pairing credentials; keep LAN-only status and independent account identities.
- **Remove console/integration:** clean up config entries/entities/sockets/panel and secret material that the integration owns. Data-history retention or deletion must be separately user-controlled and governed by ADR-0008. HACS code uninstall may not automatically erase auxiliary storage.

No user information from another account may be copied into a replacement account or hardware record just because it has a matching display name or local IP. If duplicate secret records exist after restore, resolve by validated stable owner and generation; don't guess.

## 13. Interface boundaries and module candidates

```text
custom_components/playstation_hub/
  domain/credential_models.py             # Pure typed metadata and secret-state boundaries
  transport/psn/authentication.py         # Source-derived Sony adapter (permission gated)
  transport/psn/token_manager.py          # Per-account single-flight refresh
  transport/remote_play/registration.py   # Console-bound one-time pairing
  transport/remote_play/crypto.py         # Audited crypto algorithms, not homegrown
  persistence/credential_repository.py    # Interface; implementation ADR-0008
  coordinator.py                          # HA scheduling and lifecycle ownership
  config_flow.py                          # User linking, reauth, pairing/repair
  diagnostics.py                          # Sanitized status only
```

These are target module *ideas*, not required empty files or code to create today. Dependency arrows point from domain orchestration to abstract adapters/repositories; no frontend module imports provider secrets.

## 14. Synthetic tests and acceptance criteria

### PSN token lifecycle
- [ ] User-provided synthetic NPSSO results in one validated account identity and one credential record.
- [ ] A reauth token for a **different** PSN account cannot overwrite a linked entry.
- [ ] Five concurrent expired-token consumers produce exactly one provider refresh.
- [ ] Rotation persists new access and refresh tokens and expiry as one versioned record; stale completion cannot overwrite it.
- [ ] A refresh succeeds remotely but disk commit fails: durable status remains failure; potential reauth documented.
- [ ] 429/5xx/timeout do not erase usable tokens or declare revoked.
- [ ] Valid error body `{"error":"invalid_grant"}` maps to auth failure, not exception parser crash.
- [ ] A refresh token restored from an old backup can fail and trigger reauth without touching LAN.
- [ ] Token-only changes do not reload all entities or start overlapping coordinators.
- [ ] Access token and session validity are not artificially extended by restart or reading metadata.
- [ ] Sony callback can only be enabled with a provider-authorized client and properly bound state/redirect.

### Remote Play pairing and control
- [ ] Pairing rejected/cancelled cannot commit partial keys.
- [ ] Synthetic RP fields are validated for correct lengths/format and owner identity.
- [ ] Pairing in Console A cannot mutate Console B credentials.
- [ ] Same IP now points to Console B: A's key cannot be sent there.
- [ ] Transient registration PIN, nonce and session keys are never persisted.
- [ ] Unpair removes only matching scope; other accounts and console history stay intact.
- [ ] Missing/unreadable store never appears as “paired and ready”.
- [ ] Clean and crash restart preserve only committed pairing records; unsupported records prompt repair.

### Storage, privacy and multi-entry
- [ ] Immutable schema/version migration with synthetic test secrets; unknown schema rejected without destructive reset.
- [ ] Config/Store file permissions, path and backup scope verified on target HA OS/Core.
- [ ] Diagnostics and frontend data contain no NPSSO, OAuth tokens, RP-Key or console passcode.
- [ ] A malicious/untrusted redirect or image host never receives Sony auth headers.
- [ ] Two users/accounts cannot access each other's credentials through HA API.
- [ ] Async unload cancels inflight refresh/pairing safely and prevents old-generation commits.
- [ ] Restore after backup produces clearly degraded credentials if remote service revoked them, not false success.
- [ ] Full uninstall and privacy deletion follow explicit data ownership.
- [ ] No private snapshots/real credentials in tests, GitHub Actions logs or published releases.

## 15. Open decisions and approval requirements

- [ ] Confirm a Sony-sanctioned OAuth client/endpoint use basis for optional PSN capability; **blocked until then**.
- [ ] Decide initial NPSSO retention after bootstrap (preferred minimization when viable) and user-initiated reauth UX.
- [ ] Choose exact PSNAWP/version or separately permitted protocol adapter without global monkey patches.
- [ ] Approve per-account single-flight refresh, durable generation replacement and no reload on token changes.
- [ ] Confirm Remote Play pairing key provenance, exact wake derivation, and license compatibility.
- [ ] Select storage backend and API (ConfigEntry vs Store vs encrypted file) with target HA Core code audit.
- [ ] Define whether at-rest encryption is worthwhile given key custody and backups.
- [ ] Define secret record versioning, migrations, atomicity, crash semantics and per-entry deletion.
- [ ] Test HA OS backup inclusion and controlled restore with synthetic data.
- [ ] Approve retained-history/user unlink semantics and child-account privacy.
- [ ] Define full HA permission/ACL model and secure authenticated sidebar endpoints (ADR-0009/0010).
- [ ] Agree whether a LAN-only first release can ship if PSN permission remains blocked.
- [ ] Complete an independently reviewed threat model and security test matrix.

**Provisional recommendation:** Independent, owner-scoped credential repositories; centralized token lifecycle; no secrets in session SQLite, panel or diagnostics; assisted NPSSO fallback, automated linking only with approved Sony OAuth; safe per-console pairing; durable writes and bounded recovery. All technical choices remain subject to approval and verification.

## 16. Research sources and references

### Internal
- [Protocol 03 wake](../protocols/03-console-wakeup.md)
- [Protocol 04 registration](../protocols/04-remote-play-registration.md)
- [Protocol 05 cryptography](../protocols/05-remote-play-cryptography.md)
- [Protocol 06 session](../protocols/06-remote-play-session.md)
- [Protocol 07 commands](../protocols/07-remote-play-commands.md)
- [Protocol 08 PSN auth](../protocols/08-psn-authentication.md)
- [ADR-0004 identity](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 state](ADR-0005-observation-and-state-reconciliation.md)
- [Security architecture](../architecture/security-architecture.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

### Home Assistant official development documentation
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/data_entry_flow_index/
- https://developers.home-assistant.io/docs/core/platform/application_credentials
- https://developers.home-assistant.io/docs/core/diagnostics/
- https://developers.home-assistant.io/docs/integration_setup_failures/
- https://www.home-assistant.io/common-tasks/general/backups
- https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py

### Community implementation evidence, not Sony authorization
- https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeNpssoForAccessCode.ts
- https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeAccessCodeForAuthTokens.ts
- https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeRefreshTokenForAuthTokens.ts
- https://github.com/isFakeAccount/psnawp
- https://github.com/Emkraan/homeassistant-playstationnetwork/blob/main/custom_components/playstation_network/compat.py
- https://github.com/Emkraan/homeassistant-playstationnetwork/blob/main/custom_components/playstation_network/coordinator.py
- https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/psn-account.ts
- https://github.com/dhleong/playactor/blob/main/src/remoteplay/registration.ts
- https://github.com/dhleong/playactor/blob/main/src/credentials/model.ts
- https://github.com/tmrp/psn-mcp/blob/main/src/psn/browser-login.ts

**Outcome:** Security-oriented credential ownership, token renewal, independent pairing, persistence contracts and test plans documented. Final persistence API, storage encryption, Sony API entitlement, real PSNAWP version behavior and hardware pairing remain unresolved. This ADR is **Proposed**, not approved.
