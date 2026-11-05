# Protocol 08 — PlayStation Network authentication

**Status:** Source-derived technical specification; Sony-supported third-party authorization remains unverified  
**Reviewed:** 2026-11-05  
**Implementation:** Not started; no live account or console validation  
**Proposed module:** `custom_components/playstation_hub/transport/psn/authentication.py`  
**Reference revisions:** `psn-api` tree `1e9d9a806fcd884a4ddee8086bfe92594611da9f` (historical pin from protocol index); PS5-MQTT tree `7ab3075d276f3eeecd81a3322c72231af8cd51bd` (historical pin). Also reviewed current GitHub files on 2026-11-05; their branch heads may differ from these pins.

> **Evidence boundary:** Official PlayStation help confirms account sign-in, passkeys, two-step verification and account security. The NPSSO-to-OAuth-token exchange below is reverse-engineered/community-documented behavior, **not** an officially published third-party Sony integration authorization contract. Do not imply Sony approval, guaranteed endpoint stability or permission to reuse another application's OAuth client credentials.

## 1. Purpose and boundaries

Allow a user to **optionally** link a PlayStation Network (PSN) account to PlayStation Hub for PSN presence and game enrichment (Protocols 09–10). LAN discovery, basic console availability and locally authorized control must remain operational without PSN. Account authorization is distinct from console Remote Play registration (Protocol 04); credentials and failure states must not be conflated.

This specification covers account bootstrap, token refresh, identity lookup, storage, error handling and unlinking. Presence response mapping is Protocol 09; game metadata is Protocol 10.

## 2. Evidence inventory

| ID | Evidence | Classification | What it establishes |
| --- | --- | --- | --- |
| AUTH-01 | Official PlayStation account help and security settings | OFFICIAL | Sony supports browser sign-in, passkeys and 2SV, with user-managed account security. |
| AUTH-02 | `psn-api/src/authenticate/exchangeNpssoForAccessCode.ts` | SOURCE-CONFIRMED | Community implementation sends NPSSO cookie to Sony account OAuth authorization endpoint and reads a returned authorization code from a redirect. |
| AUTH-03 | `psn-api/src/authenticate/exchangeAccessCodeForAuthTokens.ts` | SOURCE-CONFIRMED | Community implementation exchanges an authorization code for access/refresh tokens with a form POST. |
| AUTH-04 | `psn-api/src/authenticate/exchangeRefreshTokenForAuthTokens.ts` | SOURCE-CONFIRMED | Community implementation uses a refresh-token grant and maps token lifetime fields. |
| AUTH-05 | `ps5-mqtt/server/src/psn-account.ts` | SOURCE-CONFIRMED | Reference application prefers stored refresh-token continuity, falls back to NPSSO, resolves account profile, and isolates PSN activity errors. |
| AUTH-06 | PS5-MQTT configuration documentation | SOURCE-CONFIRMED | Multiple PSN accounts are supported; token persistence and user-facing reauthentication instructions are described. |
| AUTH-07 | Home Assistant application credentials developer documentation | OFFICIAL | Supported OAuth integration helpers have provider/client-credential prerequisites, which are **not established for this Sony flow**. |

`SOURCE-CONFIRMED` means observed in upstream source, **not** confirmed by Sony or by PlayStation Hub.

## 3. Reference community authentication flow

The implementation in `achievements-app/psn-api` uses this observed sequence:

1. User signs in to PlayStation in **their own browser**, with Sony-managed password, passkey or 2SV.
2. The community workflow retrieves an `npsso` token from `https://ca.account.sony.com/api/v1/ssocookie` in the signed-in browser. **NPSSO is password-equivalent secret material.**
3. The community code sends an authorization request to `https://ca.account.sony.com/api/authz/v3/oauth/authorize`, using `Cookie: npsso=...` and manual redirect handling. It obtains an authorization code from the redirect's `Location` query parameter.
4. It POSTs a form to `https://ca.account.sony.com/api/authz/v3/oauth/token` using `grant_type=authorization_code`, the authorization code and a redirect URI, receiving an access token, refresh token and expiration values.
5. Later it POSTs to the same token endpoint with `grant_type=refresh_token` to renew the credentials.
6. PS5-MQTT loads a user's profile after authentication to resolve an account ID; optional presence enrichment is handled separately.

The reference code uses a specific mobile-client identifier, Basic Authorization value, redirect URI and scopes. **Do not copy these into PlayStation Hub or treat them as public client credentials licensed for third-party distribution.** Their owner, permitted usage, consent semantics and long-term validity must be established before implementation. Exact literals can be inspected in the pinned upstream source during a controlled legal/security review; this document intentionally does not reproduce reusable credentials.

### Sequence diagram (source-derived, non-shippable design)

```mermaid
sequenceDiagram
    actor User
    participant Browser as User browser / Sony
    participant Hub as PlayStation Hub (planned)
    participant Auth as Sony account endpoints (community-observed)
    participant Store as Protected HA credential store (TBD)
    User->>Browser: Sign in directly to Sony
    Browser-->>User: NPSSO (community-documented)
    User->>Hub: Explicitly provide token (proposed fallback only)
    Hub->>Auth: Exchange NPSSO for code
    Auth-->>Hub: Redirect with code
    Hub->>Auth: Exchange code for access + refresh tokens
    Auth-->>Hub: Tokens + expiry metadata
    Hub->>Store: Store token state securely
    Note over Hub,Store: Authorized client usage and secure storage remain blocked decisions
    Hub->>Auth: Refresh when needed
    Auth-->>Hub: Rotated token state
```

**Security constraint:** The sequence above documents third-party behavior, not an approved user experience. The preferred eventual UX is provider-authorized account linking without manual secret extraction **if Sony offers a suitable supported route**. We must not build a fake Sony sign-in form or ask for the user's Sony password in Home Assistant.

## 4. Identity and credential model (proposed)

Keep per-account identity independent of console identity:

- `account_id`: provider-resolved stable account identifier, not a user-editable display name.
- `online_id`: display name, changeable and non-authoritative for identity.
- `credential_state`: `not_configured | connecting | authorized | refresh_required | reauth_required | unavailable | revoked`.
- `access_token`, `refresh_token`, optional `npsso`: secret-bearing fields; never returned to frontend or diagnostics.
- `access_expires_at` and `refresh_expires_at`: UTC timestamps derived from provider-relative expiry using a safety margin.
- `last_auth_success_at`, `last_error_category`, `last_refresh_attempt_at`: sanitized operational metadata.
- `auth_generation`: optional monotonic generation to prevent late refresh responses from overwriting newer state.

Multiple PSN accounts must be independently configurable, refreshable and removable. An account-to-console association is a separate best-effort domain relation; an account may be active on more than one device and presence must not automatically prove which console is playing.

## 5. Proposed lifecycle and state transitions

1. **Unlinked:** no PSN account configured; LAN features continue unaffected.
2. **Authorized:** after a permitted, verified authentication path succeeds, resolve provider account ID and persist credentials atomically.
3. **Operational:** reuse a valid access token; refresh shortly before expiry or after a properly classified expiry response.
4. **Refresh:** serialize refresh per account, apply bounded timeouts, validate all returned fields, and atomically store new tokens before using them. Handle refresh-token rotation; never overwrite newer credentials with an older concurrent response.
5. **Transient failure:** preserve existing credentials securely, apply jittered exponential backoff and show PSN enrichment unavailable rather than claiming the console is offline.
6. **Invalid credentials / explicit revocation:** stop using the credentials, require deliberate reauthentication; do not retry invalid tokens in a tight loop.
7. **Unlink:** stop scheduling requests, cancel pending work, delete the account's local credential material and associated mapping, and define history-retention policy separately. Remote Sony-side revocation is **unverified** and must not be claimed unless implemented and confirmed.

### Reauthentication rule

A stale or expired NPSSO must **not** trigger browser scraping, password handling, repeated automated Sony logins or silent token harvesting. If the supported renewal chain cannot proceed, expose a safe reauthentication state. Reference PS5-MQTT can fall back to a previously configured NPSSO; whether PlayStation Hub should retain NPSSO after bootstrap is an **OPEN SECURITY DECISION**. Prefer not retaining bootstrap-only secrets if a supported flow makes that possible.

## 6. Home Assistant integration boundary (proposed)

- Implement account setup and removal using a Home Assistant config flow/options/reauth flow as appropriate; all operations must be asynchronous or use approved executor mechanisms.
- Assess `application_credentials` and `config_entry_oauth2_flow` **only if** a provider-supported OAuth application registration and proper client credential ownership can be established. A borrowed mobile app client ID does not satisfy that requirement.
- Keep tokens backend-only and protected by Home Assistant's appropriate secret/config-entry storage model, following current HA API guidance after source review. Do not assume `Store` automatically encrypts secrets at rest.
- Do not expose NPSSO, tokens, `Authorization` or `Cookie` in logs, stack traces, diagnostics, event bus, entity attributes, frontend responses, backups shared publicly, or test fixtures.
- Ensure configuration removal stops account refresh tasks and resources, without degrading LAN monitoring for unrelated devices.
- Preserve precise error typing so optional PSN failure never prevents setup of LAN-only functionality.
- Never include real token material in the repository or tests.

### Proposed Python interface contract (not implemented)

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PsnCredentialState(StrEnum):
    NOT_CONFIGURED = "not_configured"
    AUTHORIZED = "authorized"
    REAUTH_REQUIRED = "reauth_required"
    UNAVAILABLE = "unavailable"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class PsnAccountIdentity:
    account_id: str
    online_id: str | None


@dataclass(frozen=True, slots=True)
class PsnAuthorizationSnapshot:
    identity: PsnAccountIdentity
    state: PsnCredentialState
    access_expires_at: datetime | None
    last_success_at: datetime | None
```

This is a design example, **not** an API implementation. Actual interfaces, dependencies and secret-store ownership remain subject to ADR approval.

## 7. Error taxonomy (proposed)

| Category | Example | Required behavior |
| --- | --- | --- |
| `invalid_npsso` | Missing or invalid authorization redirect/code | Reject bootstrap; sanitize server response; request user action. |
| `unauthorized_client` | Provider rejects application/client identity | **Block** integration flow; do not search for bypasses. |
| `invalid_grant` | Expired/revoked refresh token | Move to `reauth_required`; do not loop indefinitely. |
| `rate_limited` | HTTP 429 | Honor Retry-After where trustworthy; bounded backoff. |
| `provider_unavailable` | 5xx, DNS or timeout | Mark PSN data unavailable, keep LAN controls and stored history. |
| `malformed_response` | Unexpected JSON, missing token or expiry | Reject atomically; never persist incomplete credentials. |
| `identity_mismatch` | Linked token resolves another account ID | Stop and require explicit user review. |
| `storage_failure` | No durable protected storage | Do not report authorized success; no in-memory-only silent success. |
| `unlinked` | User removes account | Cancel refresh work, clear locally held secrets and associations. |

All HTTP responses and redirects must be validated and size bounded. Do not follow an arbitrary OAuth redirect host; redact response bodies and URLs that may contain sensitive parameters. Set retry limits and a configurable, conservative rate policy.

## 8. Test plan before any shipping implementation

- [ ] Legal/provider-client authorization review, and document a compliant Sony-supported method or explicitly block shipping PSN authorization.
- [ ] Synthetic NPSSO bootstrap cases: success, invalid token, absent redirect, malicious redirect, altered code, transport timeout.
- [ ] Authorization code exchange: successful response, malformed JSON, missing token fields, HTTP 401/403/429/5xx.
- [ ] Refresh: valid token, near expiry, rotation, expired refresh, concurrent refresh, cancellation, restart between refresh and persistence.
- [ ] Account identity: renamed display name, mismatched account ID, multiple linked accounts, duplicate linking.
- [ ] Privacy: token redaction in diagnostics, HTTP exceptions, error logs, frontend and backups; credential removal behavior.
- [ ] Resilience: no-PSN LAN setup, provider outage, internet loss, restore from old backup, corrupt credential metadata.
- [ ] Authentication UX: security language, account unlink, explicit permission, useful reauth errors.
- [ ] Live PSN testing **only with an authorized test account and after resolving the client/endpoint permission gate**. Never run automated login attempts with real user credentials during documentation.

## 9. Open decisions / blockers

- **BLOCKED:** Is there a Sony-supported third-party OAuth authorization method for the desired PSN capabilities? Which application/client credentials and redirect URI can we lawfully own and distribute?
- **BLOCKED:** Are the presence endpoints and requested scopes contractually permitted and stable enough for an integration?
- **OPEN:** User-consent UX, optional/manual NPSSO fallback, and whether retaining NPSSO is acceptable.
- **OPEN:** Home Assistant credential storage and reauth APIs, config-entry boundaries, migration and backup secrecy.
- **OPEN:** Official account unlink/revocation mechanism; what remains locally versus remotely after unlinking.
- **OPEN:** Endpoint compatibility, scopes, rate limits, token clock skew, client error schemas and firmware/account-region differences.
- **OPEN:** Whether PSN presence is a required release feature or a later optional feature gated on verified authorization.

**Release decision:** PlayStation Hub must not ship an undocumented borrowed-client PSN login flow as though it were Sony-approved. A LAN-only release may proceed while PSN authorization is blocked, if consistent with product scope and quality gates.

## 10. Source references

### Official

- Sony PlayStation account security (PT): https://www.playstation.com/pt-pt/support/account/
- Sony PlayStation passkey support: https://www.playstation.com/en-us/support/account/set-up-passkey/
- Home Assistant application credentials: https://developers.home-assistant.io/docs/core/platform/application_credentials

### Community implementations (not official Sony API guarantees)

- psn-api overview: https://github.com/achievements-app/psn-api
- NPSSO authorization code: https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeNpssoForAccessCode.ts
- Access/refresh exchange: https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeAccessCodeForAuthTokens.ts
- Refresh-token exchange: https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeRefreshTokenForAuthTokens.ts
- OAuth base URL: https://github.com/achievements-app/psn-api/blob/main/src/authenticate/AUTH_BASE_URL.ts
- PS5-MQTT account adapter: https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/psn-account.ts
- PS5-MQTT account configuration: https://github.com/FunkeyFlo/ps5-mqtt/blob/main/add-ons/ps5-mqtt/DOCS.md

## 11. Related documents

- [Protocol index](README.md)
- [Protocol 04 — Remote Play registration](04-remote-play-registration.md)
- [Protocol 09 — PSN presence](09-psn-presence.md)
- [Protocol 10 — Game metadata](10-game-metadata.md)
- [Security architecture](../architecture/security-architecture.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

**Research result:** The community token exchange, renewal, identity and persistence sequence is documented sufficiently to plan boundaries and synthetic tests. Sony authorization for third-party client use, permitted scopes/endpoints and a compliant account-linking UX remain unresolved. No network authentication was attempted.
