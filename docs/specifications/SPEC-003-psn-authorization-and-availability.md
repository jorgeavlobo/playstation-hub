# SPEC-003 — PSN authorization, permitted API access and availability

**Status:** Proposed research and release-gate specification; no authorized third-party Sony client or live access demonstrated  
**Date:** 2026-11-05  
**Scope:** NPSSO, OAuth bootstrap and refresh, official versus community APIs, browser handoff, account identity, endpoint availability, rate limiting, privacy and safe degradation  
**Inputs:** Protocols 08–10; ADR-0004/0005/0007/0008/0009/0010; SPEC-002 (Remote Play separation)  
**Branch:** Documentation on `main` only; no executable code or real credentials  
**Decision:** PSN features remain **BLOCKED FOR RELEASE** until a defensible Sony permission/client/endpoint basis is established. LAN-only functionality is independently viable.

> **Evidence taxonomy:** SONY-OFFICIAL = published Sony support/legal material; HA-OFFICIAL = official Home Assistant integration/source, not Sony authorization; COMMUNITY-OBSERVED = source-visible third-party implementation, not contractual access; PROPOSED = our engineering policy; BLOCKED = prerequisite not established; UNTESTED = no permitted live test. An HTTP 200, working community library or Sony-owned mobile OAuth client identifier is not permission to redistribute an integration using that client.

## 1. Product objective and scope separation

Provide the smoothest *authorized* account linking possible: a user opens Sony's sign-in page, uses an existing Sony browser session when available, and links a stable PSN account to Home Assistant without giving their password or MFA secret to PlayStation Hub. Ideally a provider-approved OAuth redirect returns an authorization code automatically; in the absence of an authorized callback, investigate an explicit user-mediated NPSSO handoff. Preserve LAN discovery, console state, local pairing and locally collected history if PSN is unavailable, unauthorized or unlinked.

PSN account identity, presence, played-game history, purchased digital entitlements, trophies and artwork are distinct scopes. Authorization for one endpoint does not imply authorization for all.

## 2. Sources and authorization confidence matrix

| Mechanism | Observed reference | What is established | What is NOT established |
| --- | --- | --- | --- |
| Sony account login/passkeys/2SV | Sony support | Users can authenticate to Sony in Sony-controlled UX | Home Assistant may read Sony cookies |
| NPSSO `ssocookie` route | PSNAWP / psn-api / psn-mcp | Community documents browser retrieval with signed-in Sony session | Public Sony developer contract for this route |
| NPSSO -> authorization code -> OAuth tokens | psn-api / PSNAWP | Community code implements exchanges | Third-party right to use embedded client credentials, scopes or redirect |
| OAuth callback via HA | HA application credentials / config flow | HA supports provider OAuth flows when provider registration exists | Sony-approved PlayStation Hub client, redirect or scope |
| PSN presence basicPresences | psn-api / PSNAWP / official HA PSN | Source-visible account presence requests | Public Sony API guarantee, stable schema or permitted distribution |
| Recently played / purchased GraphQL | psn-api | Source-visible persisted GraphQL operations | Stable operation hashes or authorized entitlement scraping |
| Game artwork/CDN | Provider responses / HA | URLs appear in responses | Redistribution/caching rights |
| Official HA `playstation_network` | Home Assistant Core | HA uses PSNAWP 3.0.3 and manual NPSSO config flow | Sony's endorsement of our client or permission to copy credentials |
| Partner/developer programs | Sony business/developer pages | Some authorized programs may exist | Eligibility or access to the consumer PSN account endpoints needed here |

**Permission evidence required:** Exact Sony-issued or otherwise legally supportable basis for the specific OAuth client, redirect URI, scopes, endpoints, usage rate, data fields, storage and artwork. Record source, owner, applicable region, date, restrictions, renewal and review. Legal review is separate from technical interoperability.

## 3. Three account-linking options and security constraints

### A — Authorized OAuth redirect (preferred only if Sony permits)

1. User initiates Link PSN account from Home Assistant.
2. Backend creates short-lived, unpredictable `state` bound to the authenticated HA user, configuration flow and intended account-link operation.
3. Where provider supports/requires it, use PKCE and a registered redirect URI, with anti-CSRF and exact redirect/origin validation.
4. Open Sony-owned authorization page; Sony authenticates the user (possibly already signed in).
5. Sony redirects to the **registered** callback with a one-time code; HA exchanges code server-side through the authorized client.
6. Validate stable provider account identity and granted scopes; reject mismatched account or missing required permission.
7. Persist token generation durably before marking account linked; no token exposure to frontend.
8. Expired/denied/invalid callback yields a bounded, cancelable, user-friendly error.

**BLOCKED:** No Sony-authorized third-party client/redirect/scope combination has been established for PlayStation Hub. Do not substitute Sony's mobile-app client or another application's registered redirect URI. A generic OAuth callback URL is not proof Sony will register it.

### B — Assisted NPSSO transfer (community-observed, permission-gated)

1. Show a link to Sony's login/NPSSO browser route, never a fake Sony sign-in form.
2. The user signs in on Sony if necessary; if already authenticated, Sony may return the relevant token without another login.
3. The user explicitly copies the NPSSO and pastes it into a protected Home Assistant config/reauth field.
4. Backend validates through an approved/allowed exchange, resolves stable account identity, persists only necessary secrets, clears transient input.
5. Never store NPSSO in browser localStorage, URL, logs, entity attributes or diagnostics. Do not retain it after bootstrap unless justified and approved.
6. A copied NPSSO is a bearer secret; explain that disclosure may grant account access and use only the Sony-controlled page.

**BLOCKED FOR DISTRIBUTED RELEASE until permission review:** The community-observed exchange may depend on undocumented Sony OAuth clients/endpoints. A manually pasted token does not itself establish permission to use those APIs.

### C — Automatic cookie extraction from existing browser (not a supported HA solution)

A browser visiting the Home Assistant origin cannot read Sony-origin cookies or arbitrary cross-origin response bodies under same-origin policy. A remotely hosted HA OS Python process cannot access the user's already-running browser cookies. A local browser instance under Chrome DevTools control (as used by psn-mcp) is a different execution environment and would require a companion/extension or risky browser-control design inconsistent with our one-HACS-install product. Do not promise invisible cookie extraction, CORS bypass, hidden iframes or automatic NPSSO retrieval.

## 4. Account identity, scope and credential boundaries

- Canonical owner: provider-stable PSN `account_id`, not mutable online ID or console MAC/IP.
- One account can associate with multiple consoles and vice versa; account presence cannot prove which physical console is active.
- OAuth access/refresh token records are account-scoped; Remote Play `RP-Key`, pairing PIN and `PS5-RegistKey` are console-scoped and **never interchangeable**.
- Validate identity after initial exchange and every reauth. If a different account is returned, reject rather than silently relabel history.
- Store token response fields only as needed, with expiry, scope, client context, generation and UTC times; never store Sony password, MFA code or passkey.
- PSN game/library/private social data must be opt-in and respect Sony visibility settings and child-account restrictions.
- Access to trophies, friends, game lists and purchased entitlements must be independently permission-gated; no opportunistic probing of private accounts.

## 5. Proposed token manager and durable refresh state machine

```text
UNLINKED -> USER_LINK_REQUESTED -> BOOTSTRAPPING
 -> VALIDATING_IDENTITY -> PERSISTING -> AUTHORIZED
AUTHORIZED -> REFRESH_DUE -> REFRESHING -> PERSISTING -> AUTHORIZED
REFRESHING -> TEMPORARY_FAILURE -> BACKOFF -> REFRESHING
REFRESHING -> INVALID_GRANT -> REAUTH_REQUIRED
AUTHORIZED -> USER_UNLINK -> CANCEL_WORK -> DELETE_SCOPED_SECRETS -> UNLINKED
```

**Invariants:** Single-flight refresh per account, no cross-account token overwrite, compare-and-swap generation, bounded retries with jitter and Retry-After, never report durable success before storage acknowledgement, no config-entry reload on every refresh, no token in diagnostics. Expiry derives from actual response lifetime and a separately justified safety margin, not every UI render.

**Crash window:** Sony token rotation and local persistence cannot be a distributed atomic transaction. A crash after provider rotation but before durable replacement may invalidate the previous refresh token; recovery can require user reauthentication. An old backup may contain a rotated/revoked token. Neither case must erase local console history or impair LAN status.

**Error distinctions:** `invalid_grant` is not a timeout; a 429 is not revocation; a 403 may be privacy/permission; 5xx is provider outage; malformed schema is an adapter compatibility fault. Do not perform unauthorized alternate-account retries.

## 6. Endpoint inventory and permission gates

| Data feature | Community implementation | Scope / ambiguity | Gate |
| --- | --- | --- | --- |
| Account identity | PSNAWP / psn-api | Stable provider account ID | Client and identity validation |
| Basic presence | `basicPresences?type=primary` | Account/platform presence, not physical PS5 | Sony endpoint permission, privacy |
| Presence batch | PSNAWP batch method | Rate and authorization may differ | Provider permission, per-account budget |
| Recent titles | `getUserGameList` persisted GraphQL | Hash/schema may change | Endpoint permission and fixtures |
| Played titles/play duration | `/gamelist/v2/users/{accountId}/titles` | Lifetime/account-scoped; units to verify | Endpoint permission, privacy |
| Purchased digital library | `getPurchasedGameList` persisted GraphQL | Entitlement not proof of permanent ownership | Endpoint permission, region/PS Plus |
| Trophy metadata | PSNAWP trophy models | Different ID namespace | Endpoint permission, user privacy |
| Cover/artwork | `conceptIconUrl`, `npTitleIconUrl` | Rights, host and cache expiry unknown | License/SSRF and redistribution review |

Each endpoint needs an independent record of permitted purpose, scopes, region, retention, quotas, error semantics and release enablement. **Do not enable all PSN features because one token exchange succeeds.**

## 7. Availability, rate budget and degradation

The official Home Assistant PlayStation Network documentation reports a budget of **300 requests per 15 minutes** for its integration and uses approximately 30-second main refresh intervals, with different friend refresh behavior. These are **reference facts, not a universal Sony contractual quota** for PlayStation Hub, particularly not for all internal GraphQL operations.

**Proposed scheduling:** Centralized per-account request budget, endpoint-specific costs and cadence, shared in-flight deduplication, bounded concurrency, adaptive backoff and jitter, controlled manual refresh, and cached backend observations for all dashboard subscribers. Rate limits should never cause a per-card refresh storm.

| Provider state | PSN projection | LAN/Remote Play projection |
| --- | --- | --- |
| Healthy + authorized | Fresh permitted presence/catalog | Independent |
| Network outage | Stale/unknown with timestamp | Independent |
| HTTP 429 | Rate limited; retry after bounded delay | Independent |
| HTTP 403/privacy | Restricted; no bypass | Independent |
| Token expired/invalid grant | Reauth required | Independent |
| Endpoint schema changed | Adapter degraded, last-known visibly stale | Independent |
| Account unlinked | Stop polling, remove secrets | Preserve console state and independent history |
| PSN disabled by compliance gate | Feature unavailable with explanation | Fully functional LAN-only target |

No provider polling from HA entity getters or frontend renders. Account availability must not become a console physical power signal.

## 8. Browser security, callback and CSRF checklist

- Only Sony-controlled HTTPS origin handles password, passkey and MFA.
- Exact registered redirect URI and allowed origin; no open redirect.
- `state` bound to HA user/flow, unpredictable, single-use and time-limited.
- PKCE if required/supported, correct verifier/challenge lifetime and validation.
- Reject callback replays, missing state, cross-user completion and swapped accounts.
- Never send OAuth bearer tokens or NPSSO through URL query, fragment, WebSocket status events or frontend bundle.
- Enforce strict TLS and expected Sony hosts; no forwarding auth headers across untrusted redirects.
- Do not use implicit login to probe an account without user consent.
- Treat any Sony cookies as browser-owned and inaccessible to HA origin absent explicit provider-supported flow.
- Only enable callback after Sony client/redirect permission is established.

## 9. Privacy, consent and account removal

Require explicit user choice to link PSN and explain which fields may be read: presence, game names, trophies, library and any social information. Apply data minimization; avoid storing full raw responses. Respect visibility restrictions and children/parental settings. No scraping via alternate accounts to bypass private status.

Unlink cancels outstanding requests, deletes that account's local bearer secrets and disables associations according to approved retention. Account-specific historical data deletion/export must be separately confirmed. Do not claim Sony-side revocation unless a permitted verified API supports it. Home Assistant backups may retain historical copies of secrets and require appropriate user guidance.

## 10. Deterministic synthetic test matrix

| ID | Test | Expected |
| --- | --- | --- |
| PSN-A001 | Authorized flow state generated | Bound to one HA user/flow and expiry |
| PSN-A002 | Callback with wrong/replayed state | Rejected; no token commit |
| PSN-A003 | Redirect URI mismatch | Rejected |
| PSN-A004 | PKCE verifier mismatch | Rejected where applicable |
| PSN-A005 | User already signed into Sony | Supported flow may avoid login; no promise of cookie capture |
| PSN-A006 | Assisted NPSSO synthetic input | Transient, no frontend/log persistence |
| PSN-A007 | NPSSO invalid/expired | Safe reauth error |
| PSN-A008 | Account identity mismatch on reauth | Reject replacement |
| PSN-A009 | Five concurrent refresh requests | One provider refresh per account |
| PSN-A010 | Two accounts refreshing concurrently | Independent locks and credentials |
| PSN-A011 | Rotation response + successful commit | New generation durable before success |
| PSN-A012 | Rotation response + disk failure | No false durable success; reauth path |
| PSN-A013 | Old backup token invalid | Reauth, LAN unaffected |
| PSN-A014 | OAuth invalid_grant | Reauth, no infinite retry |
| PSN-A015 | 429 Retry-After | Bounded backoff |
| PSN-A016 | 5xx/timeout | Preserve prior credential, degrade source |
| PSN-A017 | 403/private presence | No bypass; no false offline |
| PSN-A018 | Schema/GraphQL hash change | Typed adapter degraded |
| PSN-A019 | Multiple dashboard subscribers | Shared cached request, no extra polling |
| PSN-A020 | PSN offline + console LAN awake | Hardware remains awake |
| PSN-A021 | One account + two consoles | No automatic physical attribution |
| PSN-A022 | Unlink during refresh | Cancel safely, no late secret commit |
| PSN-A023 | Diagnostic/export inspection | No bearer secrets or sensitive raw data |
| PSN-A024 | Missing Sony authorization evidence | PSN adapter release-disabled |
| PSN-A025 | Library entitlement revoked | No assertion of permanent ownership |
| PSN-A026 | Child/privacy restricted account | Respect restriction, no probing |
| PSN-A027 | HA restart with stale tokens | Validate expiry and safe refresh |
| PSN-A028 | Permission per endpoint | Disabled scope never queried |
| PSN-A029 | Token leaked in redirect to other host | Reject and never forward header |
| PSN-A030 | Disabled PSN provider | LAN discovery and monitoring unaffected |

All cases are **defined, not executed**.

## 11. Release approval gates

| Gate | Evidence required | Current status |
| --- | --- | --- |
| G1 | Sony-authorized client or documented permissible OAuth/NPSSO basis | **BLOCKED** |
| G2 | Permitted endpoint/scope/region matrix | **BLOCKED** |
| G3 | Authorized redirect/callback flow or approved assisted handoff | **BLOCKED** |
| G4 | Stable identity, reauth mismatch and account isolation tests | Unexecuted |
| G5 | Durable refresh-token generation, crash and backup recovery tests | Unexecuted |
| G6 | Rate limit, privacy, child account and 403/429/5xx tests | Unexecuted |
| G7 | Presence/library metadata schema and version fixtures | Unexecuted |
| G8 | Artwork license and safe caching/proxy rules | Open |
| G9 | HA config-flow and multi-account lifecycle integration tests | Unexecuted |
| G10 | Security review: callback, token leakage, permissions, SSRF | Unexecuted |
| G11 | Authorized real account tests where permitted | Not performed |
| G12 | Formal release sign-off and documented user-facing limitations | Not approved |

**No gate may be marked passed based solely on community source, a public OAuth URL or a successful unauthenticated HTTP request.** Preserve exact evidence and approval date when closing a gate.

## 12. Decision paths if Sony authorization is unavailable

1. **Preferred:** Continue investigating legitimate Sony client/endpoint access, without promising an approval process that has not been established.
2. **Safe release scope:** Ship independently validated LAN discovery/status and optionally permitted local Remote Play control, with PSN account linking disabled or clearly deferred.
3. **Do not:** silently borrow another application's client credentials, bypass privacy controls, collect Sony passwords in HA, deploy hidden cookie scraping or falsely claim official PSN API support.
4. **Future:** Revisit PSN adapters if Sony provides an appropriate supported integration path, keeping source-specific interfaces stable.

The requirement for automatic Sony sign-in remains a product goal, **not a currently proven deliverable**.

## 13. Open questions and next research

- Is any Sony consumer PSN developer/partner authorization available for the precise account endpoints needed?
- What terms govern the NPSSO `ssocookie` route, exchange, client identifiers, scopes and use from a distributed Home Assistant integration?
- Is an independently registered redirect URI and authorization-code callback permitted for this application category?
- Which API endpoints are contractually available and at what rate/retention/region?
- Can a user-approved PSN account be linked without storing NPSSO after bootstrap?
- What credential storage implementation satisfies the selected HA Core version and backup consistency policy?
- What per-account privacy and child account consent rules apply to game history and social data?
- Which library metadata and artwork rights permit local caching and frontend display?
- How should optional cloud capabilities be represented in HA config flow when Sony authorization remains unavailable?
- What synthetic and legally authorized live tests can be performed before release?

## 14. Sources and traceability

### Internal
- [Protocol 08 — PSN authentication](../protocols/08-psn-authentication.md)
- [Protocol 09 — PSN presence](../protocols/09-psn-presence.md)
- [Protocol 10 — Game metadata](../protocols/10-game-metadata.md)
- [ADR-0007 — Credential isolation](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0010 — Sidebar API](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)

### Sony
- https://www.playstation.com/pt-pt/legal/terms-of-service/
- https://www.playstation.com/en-us/support/account/2sv-psn-login/
- https://www.playstation.com/en-us/support/account/privacy-settings/

### Official Home Assistant
- https://www.home-assistant.io/integrations/playstation_network/
- https://github.com/home-assistant/core/tree/dev/homeassistant/components/playstation_network
- https://developers.home-assistant.io/docs/core/platform/application_credentials
- https://developers.home-assistant.io/docs/data_entry_flow_index/

### Community implementation (not authorization)
- https://github.com/achievements-app/psn-api
- https://github.com/isFakeAccount/psnawp
- https://github.com/tmrp/psn-mcp
- https://github.com/Emkraan/homeassistant-playstationnetwork
- https://github.com/FunkeyFlo/ps5-mqtt

**Outcome:** A 30-case synthetic matrix and 12 PSN release gates separate proven HA/community mechanisms from Sony-authorized access. All gates remain open; G1–G3 explicitly blocked. No executable code, credentials, login or live provider requests were performed.

## Deep upstream PSN concurrency tests — 2026-11-06 (source trace only, NOT_RUN)

[Source triangulation §11](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md#11-deeper-psn-runtime-source-audit--token-rotation-provider-title-selection-and-independent-failures) compares PSNAWP authenticator's expiry/refresh code with Emkraan's explicit per-client mutex and immediate token-pair persistence. Add future trace assertions `SRC-PSN-03` same-account simultaneous expiry -> one refresh, `SRC-PSN-04` flat OAuth error vs nested API error -> typed reauth, `SRC-PSN-05` crash between provider token rotation and local store -> recover without false durable success, `SRC-PSN-07` PSN permission/429 outage -> LAN unaffected, `SRC-PSN-10` unload while in-flight refresh -> old run fenced. No Sony authentication, token or real data was accessed in this review; these cases are not executed or added as a new SPEC.
