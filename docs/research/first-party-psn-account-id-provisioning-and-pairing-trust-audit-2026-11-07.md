# PlayStation Hub — First-party PSN Account ID provisioning, local pairing independence and authorization audit

**Date:** 2026-11-07  
**Status:** SOURCE-VERIFIED ID FORMAT / PROPOSED ARCHITECTURE / NO CODE / NO SONY LOGIN / NO PS5 TEST  
**Scope:** How to identify the specific PlayStation account used by an *explicitly requested* PS5 LAN Remote Play pairing, without depending on PSNAWP/psn-api/Playactor/Chiaki as runtime libraries, or automatically reusing another Sony application's OAuth credentials.
**Project rule:** Own PlayStation-specific implementation, no additional pip/npm runtime packages, no MQTT/add-on, no console payload, no routine PSN cloud requirement for passive LAN, no Sony credentials or URL fragments in diagnostics. Encrypted Remote Play remains **BLOCKED_CRYPTO_BACKEND_APPROVAL**; source-specific key-table rights are **OPEN**.
**Reference baseline:** Sony official Portuguese Remote Play and account/privacy documentation; pinned Playactor, Chiaki-ng, Python port and psn-api sources. This is a **new focused source audit**, not a new ADR/SPEC, not a restart of SQLite research.

> **Strong distinction:** The source's 64-bit account number is a pseudonymous **account identifier**, not a PlayStation Network login email, online/display username, OAuth access code, NPSSO cookie, access token, refresh token, pairing PIN, user login passcode, console host-id or Remote Play registration key. Treat all as separate typed concepts and retention/security categories.

## 1. Official Sony product and identity evidence

- [Sony Remote Play Settings (Portugal)](https://www.playstation.com/pt-pt/support/games/remote-play-settings/) describes PS5 \`Definições → Sistema → Reprodução remota → Ativar Reprodução remota\` and manual \`Emparelhar dispositivo\`, selecting the same LAN and entering a **number displayed on the PS5**. It does not specify the proprietary LAN registration POST, Sony's public OAuth client registration process or how to request the numeric account ID.
- [Sony PS Remote Play support (Portugal)](https://www.playstation.com/pt-pt/support/games/) says use the **same account** in the Remote Play app and console, and documents rest-mode/relevant user settings. This is a user-account/product requirement, not a guarantee an independently authored LAN client is Sony-certified.
- [Sony account privacy policy (Portugal)](https://www.playstation.com/pt-pt/legal/privacy-policy/) explicitly distinguishes an **online ID (username)** and an **account ID (unique number associated with the account)**. This is strong first-party confirmation that these are different fields. It identifies usage/activity/account/device identifiers as personal information.
- [Sony authorized apps (Portugal)](https://www.playstation.com/pt-pt/support/account/manage-authorized-apps/) says third-party access occurs after user authorization and describes revoking previously authorized apps. It does **not** grant any arbitrary app permission to impersonate an existing official Remote Play or Android OAuth client.
- [PlayStation Partners](https://partners.playstation.net/) is an official developer partner entry point. In this audit no public self-service general PSN OAuth app-registration or publicly documented API contract was verified for this independent Home Assistant integration; **not verified** is not the same as proving none exists.
- [Sony account sign-in guidance](https://www.playstation.com/pt-pt/support/account/sign-in/) describes official account sign-in and passkeys. PlayStation Hub must never ask for a Sony password, 2FA recovery code, passkey credential or cookie just to obtain a numeric Account ID.

## 2. Cross-source proof of the exact identifier format

### 2.1 Numeric \`user_id\` to Chiaki/Remote Play Base64

**Playactor:** [\`src/credentials/oauth/requester.ts\` at \`a9e72d67\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/credentials/oauth/requester.ts#L24-L45) receives a Sony account-info field \`user_id\` as a **decimal string**, parses it with \`BigInt\`, writes an **unsigned 64-bit little-endian** integer to an 8-byte buffer, then Base64-encodes the bytes. \`online_id\` is explicitly a *different* account-name string.

**Chiaki-ng:** [\`gui/src/psnaccountid.cpp\` at \`43728af2\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/gui/src/psnaccountid.cpp#L41-L46) obtains \`user_id\` through a Sony account-info response, converts it to **8-byte little-endian**, then Base64-encodes it. [\`scripts/psn-account-id.py\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/scripts/psn-account-id.py#L109-L121) independently expresses the same conversion. The script **does not make its authentication route an officially approved third-party client**.

**Chiaki-ng registration C:** [\`lib/include/chiaki/regist.h\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/include/chiaki/regist.h#L15-L47) declares an **8-byte** account ID for modern registration; [\`lib/src/regist.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c#L205-L229) Base64-encodes those bytes into \`Np-AccountId\` inside the encrypted registration body.

**Important:** PS4 firmware older than certain Remote Play versions can use a textual \`Np-Online-Id\` branch, but **do not transport that fallback to the PS5 RP target**. \`online_id\` is never valid simply because it happens to be a familiar PlayStation username.

**Source-derived encoding rule (not implementation code):**

\`\`\`text
Numeric Sony user_id (base-10, 64-bit unsigned integer)
       ↓ encode EXACTLY 8 bytes, little-endian
       ↓ conventional Base64 of those 8 bytes
       ↓ canonical ASCII: 12 characters, ends in one "="
Np-AccountId for this reviewed registration protocol
\`\`\`

The conversion is **reversible and local**; it needs only Python's built-in \`int\` and \`base64\`, NOT a Sony login, PSN API, an external converter service or a cryptographic library. If a user already knows their legitimate numeric account ID, the future Config Flow can calculate Base64 **fully offline**. If the user already has the exact Base64 account ID, it can validate/decode locally and verify canonical re-encoding.

### 2.2 Identity format validation is not ownership verification

A 12-character syntactically valid Base64 string proves only that it encodes 8 bytes; it does not prove:
- that Sony assigned the underlying number to an account;
- that the account is controlled by the user;
- that this is the PS5 user currently signed in;
- that the account is permitted for Remote Play;
- that the manual Pair Device number is still valid;
- that the current firmware accepts the registration request.

Use **two separate statuses**: \`STRUCTURALLY_VALID\` and \`ORIGIN/OWNER_VERIFIED\` (the latter is **NOT** established by parsing). A successful console pairing establishes that the target *accepted that registration under the specified conditions*, not that Sony has cryptographically attested account ownership to PlayStation Hub.

**Canonical input parsing contract (PROPOSED):** Exact ASCII decimal digits without sign or whitespace except explicit trim, converted to an **unsigned 64-bit range**; alternatively canonical standard Base64 decoding into exactly 8 bytes followed by exact re-encoding. Detect multiple \`=\` signs, Unicode lookalikes, padding mistakes, URL-safe variants unless separately defined and noncanonical spellings. A value of all zeros may be *structurally* valid but should not automatically be declared an assigned Sony account. The only actual user ID validity test is a separately authorized pairing/account verification. Never store a name-based guessed account ID.

## 3. Key new architectural finding — local pairing need not invoke OAuth

**Evidence from function boundaries, not a user-tested firmware claim:**
- [\`ps5-remoteplay registration.py\`](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/registration.py#L61-L85) exposes a registration routine accepting **\`host, account_id, pin\`** directly, then performing local \`SRC3/RES3\` and encrypted TCP registration. **This particular function does not contact a Sony OAuth endpoint.** Its surrounding CLI may separately initiate account login to *obtain* the account ID.
- [\`playactor registration.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/registration.ts#L41-L89) accepts supplied account ID and PIN in the encrypted registration request; OAuth is separately called by [\`OauthCredentialRequester.requestForDevice\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/credentials/oauth/requester.ts#L68-L123) to obtain the value.
- [Chiaki \`regist.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c#L205-L229) accepts an already-available 8-byte PSN account ID and inserts its Base64 into the encrypted local registration payload. Its separate GUI/scripts fetch the numeric ID through Sony account endpoints.

**Conclusion:** The *client-side local registration function* can be **cloud-free at pairing time** if the user supplies a correctly obtained account identifier, a valid Sony console Pair Device number and the crypto prerequisites. This does **NOT** mean the retail PS5 can always pair while disconnected from PSN/internet, nor that online Sony account setup is unnecessary to enable the feature. Firmware/per-user settings and account relationship must be tested separately.

**Major engineering win:** The first-party app could support **manual Account ID provisioning** without an ongoing PSN SDK, third-party OAuth app, imported PSN cookies or self-hosted PSN proxy. This preserves LAN-only status/title monitoring even when pairing is not possible.

## 4. Compare account-ID acquisition routes and select allowable gates

| Source / proposed route | Technical possibility | Legal/privacy/trust assessment | Proposed product decision |
| --- | --- | --- | --- |
| **A. User supplies known numeric PSN Account ID** | Convert unsigned 64-bit value locally to Base64 | User asserted; source provenance must be clear; no token handling | **PREFERRED FUTURE INPUT MODE**, when separately authorized |
| **B. User supplies previously obtained Base64 Account ID** | Strict 8-byte decoder + canonical re-encode | Same ownership issue, but no Sony API call; may come from existing user-held information | **PREFERRED FUTURE INPUT MODE**, not automatically trusted owner |
| **C. OAuth via our legitimately registered Sony client** | Own HTTP client via HA-managed session and standard crypto only if Sony grants app credentials/scopes | No authorized client registration/grant confirmed for this project | **POSSIBLE ONLY WITH VERIFIABLE SONY AUTHORIZATION**, not assumed |
| **D. Copy Chiaki/Playactor official Remote Play client ID/secret** | Community code uses a Sony-owned client identity and redirect URI | Published strings are NOT our OAuth authorization and may violate account/service terms | **PROHIBITED** without valid authorization |
| **E. PSN-API / PSNAWP NPSSO cookie flow** | Unofficial client can exchange cookie for authorization code and bearer tokens | NPSSO is an authentication secret; borrowed mobile OAuth identity and endpoints do not constitute approved SDK | **NOT A RECOMMENDED/APPROVED ACCOUNT-ID GATE**; no NPSSO requests in PlayStation Hub |
| **F. Online-ID-to-Account-ID lookup service** | [psn-api \`getProfileFromUserName\`](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/user/getProfileFromUserName.ts) can request \`accountId\` given PSN authentication, subject to privacy | Online ID alone is not proof account owner; online ID may change; private/child accounts; services may collect profile data | **NO REQUIRED THIRD-PARTY LOOKUP**; never auto-query strangers |
| **G. Console-side ELF/jailbroken firmware account extraction** | Community projects can read identifiers from modified console environments | Violates normal retail PS5, no console payload/no third-party components rule; potential safety/security issues | **OUT OF SCOPE** |
| **H. Import pairing secrets from Playactor/Chiaki credentials.json** | Some compatibility is source-documented | Highly sensitive secret import, format and identity mismatch, violates own onboarding policy if mandatory | **NOT a prerequisite**; defer optional import to later separate review, never auto-scan user files |

Important trust ladder: \`USER_SUPPLIED_FORMAT_VALID\` → \`CONSOLE_PAIR_REQUEST_ACCEPTED\` → (only if a separate authorized Sony identity assertion exists) \`PROVIDER_ACCOUNT_VERIFIED\`. Do **not** infer the third level from the second. Console physical owner binding and account identity require separate evidence/provenance.

## 5. Why copied OAuth credentials are unacceptable even when Sony login page is real

[Playactor \`src/credentials/oauth/requester.ts\`](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/credentials/oauth/requester.ts) and [Chiaki \`scripts/psn-account-id.py\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/scripts/psn-account-id.py) embed a **Sony Remote Play-associated client identity/secret/redirect** and use a browser redirect/authorization-code path to retrieve the \`user_id\` field. The separate [psn-api authentication code](https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/authenticate/exchangeNpssoForAccessCode.ts) uses an **unofficial NPSSO-cookie route and a different app/client context**. These are *descriptions of third-party behavior*, not evidence of permission for this project to impersonate either client.

**Own OAuth authorization** would require a genuinely registered/authorized Sony client identity, appropriate scopes, consent, secure redirect and credential lifecycle, explicit handling of access/refresh tokens and Sony policy. The public Sony [Authorized Apps](https://www.playstation.com/pt-pt/support/account/manage-authorized-apps/) screen allows users to revoke linked apps; it is not itself an API-registration mechanism granting arbitrary access. Official PlayStation Partners listings are aimed at creators/partners and do not demonstrate an accessible general-purpose user-account API for a personal HA integration.

**Non-negotiable security:** Do NOT ask for, accept, store or log Sony password, OAuth authorization URL/code, access/refresh token, NPSSO cookie or third-party Client Secret just to look up the account number. Never embed source-copied OAuth client credentials as a workaround. Never direct users to paste live tokens into a support conversation or logs. The user can provide an Account ID to a future local-only Config Flow, but no such flow is implemented/approved yet.

## 6. Separate pairing output credentials and later wake

The local encrypted registration produces **\`PS5-RegistKey\`** and **\`RP-Key\`** among its source-derived response fields ([Chiaki \`regist.c\`](https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/regist.c#L830-L919)). They have different purposes:
- \`PS5-RegistKey\` is used to identify the registered client during later Remote Play session initialization; source [Playactor](https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/credentials/oauth/requester.ts#L46-L59) and [Python wake.py](https://github.com/iharosi/ps5-remoteplay/blob/61e1f7dc065a77f7e8b1de5057889a08b0208d9d/src/ps5_remoteplay/wake.py#L8-L11) derive a **wake credential** from a particular representation of that registration key.
- \`RP-Key\` is a separate authenticated session cipher input, not the Account ID, not the wake credential, and not the user passcode.
- User Pair Device PIN is used during initial registration; an optional user-console login passcode can appear during the later control session. Neither belongs in historical activity tables.
- A proper first-party credential vault record would scope the private RP keys to **verified physical console + intended account + registration generation**. Account-ID formatting success alone does not authorize pairing or key binding.

**No automatic sharing across consoles/accounts:** A single PSN Account ID may be associated with multiple physical consoles; one physical PS5 can have multiple local profiles. A single nickname/IP/host-id is insufficient to reassign registration credentials after DHCP reassignment, replacement device or HA restore.

## 7. First-party logical Account ID DTO and conversion contract (NOT executable code)

\`\`\`text
ProvisionedAccountIdentity:
  logical_account_entry_id          // integration-owned opaque local identifier
  source_kind                       // USER_DECIMAL | USER_BASE64 | SONY_AUTHORIZED
  original_input_kind               // never store raw user-typed string redundantly
  account_id_u64                    // validated 64-bit integer representation
  account_id_le8                    // computed 8-byte value (sensitive personal identifier)
  remote_play_account_id_base64     // canonical 12-character representation; one '='
  origin_assurance                  // USER_ASSERTED | SONY_AUTHORIZED (if actually proven)
  binding_assurance                 // UNPAIRED | CONSOLE_ACCEPTED_REGISTRATION
  physical_console_owner_key?       // separate independent identity
  user_privacy_scope                // consented per intended user/profile
  created_at / updated_at           // metadata, no unnecessary account activity tracking
  log_redaction_policy              // no full ID in logs/telemetry/diagnostics by default
\`\`\`

**Proposed minimal local converter rules:**
1. Input mode is explicit: \`NUMERIC_DECIMAL\` or \`CHIaki_BASE64\` (label final UI can be case-neutral). Do not guess based on strings that resemble PSN names.
2. Decimal input accepts ordinary ASCII 0–9 and a number in \`0..2^64-1\`; reject sign, exponent, fractional value, more than 64-bit, Unicode lookalikes and unbounded length. Do not convert via floating-point (JavaScript's \`Number\` loses precision above 2^53); conversion belongs **server-side Python arbitrary-precision \`int\`**, not JS \`Number\`.
3. Convert numeric \`n\` to **exactly eight bytes in little-endian order**, then conventional Base64. For 8 bytes the canonical Base64 is 12 characters long with **one** trailing \`=\`.
4. Base64 input: strict alphabet/padding, decode to exactly eight bytes, re-encode and demand byte-for-byte canonical equality; decode unsigned little-endian \`n\` for cross-mode display or test. Reject 11-byte decoded content, \`==\` as padding, mixed URL-safe symbols and other noncanonical representations unless explicitly supported by a future source profile.
5. Structural parse is *not* a Sony-issued proof of account existence/ownership, even if canonical. An all-zero ID may pass byte-format checks but is not thereby proven assigned. A proper local Pair Device flow still requires user consent and source-owner checks.
6. Store the canonical identity under privacy constraints; do not emit it in log lines, public dashboard data, diagnostics, persistent notifications or unredacted backups. Do not retain original user input in parallel unless necessary for conversion verification and disclosure.
7. A user can correct/remove their account binding without erasing independently sourced historical physical-console observations, subject to data minimization/retention controls.

## 8. Proposed configuration/onboarding decision tree

\`\`\`text
Native HA PlayStation Hub integration:
  A. Discover physical PS5 via LAN DDP — fully independent of Sony account
  B. Show status + optional LAN-reported app — NO PSN API, NO pairing PIN
  C. If user explicitly requests pairing:
       1. Check capability gate (lawful RP table provenance + approved AES)
       2. Check physical console binding/permission/owner
       3. Ask user to choose an existing local Account Identity or create one:
            i. Manually supply numeric Sony user_id
           ii. Manually supply canonical 8-byte Base64 form
          iii. Authorized Sony account identity provider (ONLY if an approved client exists)
       4. Locally validate/convert ID, but label ownership UNVERIFIED
       5. Ask user to open PS5 Remote Play > Pair Device
       6. Accept its short-lived PIN securely (not Sony account password)
       7. Perform own first-party SRC3/RES3 and encrypted registration
       8. Validate keys, bind only to intended console/account upon success
       9. Keep user login passcode and later standby as separate opt-in actions
  D. Account not known / approval missing:
       → Pairing UNAVAILABLE, but LAN monitoring/archive keep running
\`\`\`

This is *future design only*, not an implemented Config Flow or promise of working Sony pairing. Manual Account ID provisioning means no authentication token *during the client registration path*; it does not establish console offline functionality or cancel the need to observe Sony account/Remote Play user setting restrictions.

## 9. Failure taxonomy and privacy cases

| Failure | Source/situation | Future behavior |
| --- | --- | --- |
| \`ACCOUNT_ID_FORMAT_INVALID\` | Bad Base64, noncanonical padding or malformed decimal | Local input validation, no network or credential retention |
| \`ACCOUNT_ID_UNKNOWN_PROVENANCE\` | User supplied ID but ownership not proven | Accept only as user-asserted candidate; do not declare Sony verified |
| \`ACCOUNT_ID_WRONG_CONSOLE_USER\` | Pairing rejected for another user's ID | Typed failure, no key reuse/brute force |
| \`PAIR_DEVICE_PIN_EXPIRED\` | Pair Device number no longer accepted | Ask for a new user-generated number, no repeated guesses |
| \`SONY_OAUTH_NOT_AUTHORIZED\` | No own Sony-approved client credentials/scopes | OAuth option unavailable; manual identity option remains |
| \`SONY_PRIVACY_OR_RESTRICTED_USER\` | Child/private account constraints | Respect user/account permission, no third-party username lookup |
| \`CRYPTO_BACKEND_UNAPPROVED\` | No approved vetted AES / key-data rights | Pairing disabled; LAN unaffected |
| \`REGISTRATION_KEYS_INVALID\` | Malformed/partial encrypted response | No stored credentials, report pairing failure |
| \`OWNER_CONFLICT\` | Changed device/host-id/IP or account binding mismatch | Stop action; manual review before rebinding |
| \`CLOUD_OUTAGE\` | Sony access unavailable during optional provider path | LAN status unchanged; manual ID pairing still unproven in offline-firmware conditions |
| \`SECRET_IN_LOG_OR_DIAGNOSTIC\` | Any OAuth/PIN/RP key/account ID leakage | Fail privacy review, sanitize at source, no debug token dumps |

## 10. Planned source-focused tests — all NOT_RUN

| ID | Contract | Future assertion |
| --- | --- | --- |
| IDP-01 | 64-bit decimal ID | Roundtrip unsigned \`n → le8 → Base64 → n\` with our original synthetic numbers |
| IDP-02 | JS precision hazard | Conversion never uses a floating-point \`Number\` for full 64-bit IDs |
| IDP-03 | Canonical 8-byte Base64 | 12 ASCII chars with one \`=\`, exact decode/re-encode |
| IDP-04 | Invalid Base64 padding | Reject \`==\` extra or noncanonical encodings without calling Sony |
| IDP-05 | Decimal bounds | Reject negatives, floats, signs, overflow, Unicode lookalikes |
| IDP-06 | Source Sony online ID/email name | Does NOT silently become numeric Account ID |
| IDP-07 | User-provided identity | Label USER_ASSERTED and never SONY_VERIFIED from format validation |
| IDP-08 | Local registration function no OAuth call | Stub Sony network unavailable; mock first-party register accepts known account ID/PIN |
| IDP-09 | Unauthorized borrowed Sony client credentials | No constants/redirect embedded in source, no token/code handling |
| IDP-10 | Sony Authorized App revocation | Provider identity no longer assumed current; LAN unaffected |
| IDP-11 | Public search by PSN online name | Requires permitted authorization; do not query unknown/private accounts |
| IDP-12 | Multiple accounts on one console | Distinct pairing credentials and principal scopes, no cross-account reuse |
| IDP-13 | One account across multiple PS5s | Distinct per-console credential bindings, no IP/name shortcut |
| IDP-14 | Wrong account ID on Pair Device screen | Typed pairing failure, no PIN brute force or history mutation |
| IDP-15 | Expired PIN | No endless retries; new manual action required |
| IDP-16 | Account/credentials privacy | No log, diagnostic, WS, repair message, usage DB or screenshot leakage |
| IDP-17 | Missing Sony authorized app | Manual identity option supported in design; encrypted controls remain gated |
| IDP-18 | HA entry unload/restart | No stale pairing operation or cross-account credential resurrection |
| IDP-19 | Attempt pairing during PSN outage | Device-specific offline compatibility must be observed, **not asserted** |
| IDP-20 | No PSN account at all | Native LAN still available; encrypted pairing capability truthfully unavailable |

No executable tests, protocol client, Sony account lookup, fake-console implementation or user credentials have been created. These **20 qualitative trace IDs** belong as supplements to existing SPEC-002/003, not a new numbered SPEC, not additional executed test counts.

## 11. Research closure and genuinely unresolved evidence

**SOURCE_CONFIRMED:** (1) Sony distinguishes account ID numeric from online ID; (2) Playactor, Chiaki-ng and the Python port use **8-byte little-endian Base64** for modern PS5 registration Account ID; (3) their local registration routines accept a supplied account ID and Pair Device PIN **without calling OAuth in that routine**; (4) third-party community OAuth/NPSSO clients use distinct embedded client identities that are not authorization for PlayStation Hub.

**PROPOSED:** Native manual input (decimal or Base64) plus local conversion; account identity source provenance, privacy and scope gates; optional future **genuinely Sony-authorized** identity provider if approved.

**OPEN / PARTLY RESOLVED:** An **official Sony personal-data request workflow exists** and community users report the resulting Account Detail spreadsheet contains the numeric account ID, but Sony's support article does **not guarantee that this exact field appears in every account export**. Current personal-data export content is NOT inspected in this research; whether Sony will authorize an independent HA OAuth client; Sony-specific account/provider permission and present firmware constraints; lawful crypto table/AES primitive availability; actual pairing.

**Stop condition:** Do not repeatedly search arbitrary unofficial sites for a convenient numeric account ID lookup. Without an officially granted provider client or user-supplied ID from a trusted source, account lookup remains unresolved. Neither undocumented token extraction nor a compromised console is an acceptable workaround. The next useful non-duplicative step would be a **privacy/account scoping review for multi-user PS5 + HA Config Entries**, or actual implementation/hardware evidence after explicit maintainer authorization.

**Final status:** A documented first-party account-ID provisioning architecture with a legitimate **no-OAuth-at-pairing-time option**, not a verified or deployed Sony account login workflow. No external package, no code, no script invocation, no GitHub branch, no Sony login or console interaction.


## 12. Later official first-party acquisition route — Sony Data Access Request (2026-11-07)

**New material source discovery after the initial report:**

1. [Sony's official PT-PT "Como efetuar um pedido de acesso aos dados"](https://www.playstation.com/pt-pt/support/account/data-request/) explicitly provides a **self-service personal account data export** through official Account Management, *Definições de privacidade → Pedidos de acesso aos dados → Solicitar dados*. Sony states personal account information is delivered in an Excel file. A **different request type** covers **device data under the EU Data Act**; use the **personal account-data request**, not the device diagnostics request, when the goal is the account's numeric identifier.
2. Sony's [official PlayStation privacy policy](https://www.playstation.com/pt-pt/legal/privacy-policy/) already confirms the unique **Account ID number** is part of account/device identifiers it processes. However, **neither official page explicitly guarantees the exact field name or inclusion of Account ID in every export file**.
3. A [2022 community guide on r/remoteplay](https://www.reddit.com/r/remoteplay/comments/xwj5li/guide_on_getting_your_psn_account_id_easy_way_no/) reports finding the numeric account ID in an **Account Detail** worksheet of the personal-data export. [A 2026 Reddit report](https://www.reddit.com/r/remoteplay/comments/1svzzhp/help_getting_psn_account_id/) and a [2024 report](https://www.reddit.com/r/SteamDeck/comments/1cidmg3) also describe using the Sony account-data export for Chiaki pairing. **These are user reports, not an official field-layout contract or an export file we inspected.**
4. The same community guide describes a second, technically possible browser-only route: inspect a \`basicProfile/users/me\` response *already loaded within a user's authenticated Sony account-management session*. This is an **undocumented internal web response** whose path/content can change and whose browser developer tools may expose cookies/tokens. It is not an approved API contract for automatic Home Assistant requests, and we **do not recommend implementing or automating it**. Prefer the Sony personal-data request if an official route is needed.

**Proposed onboarding consequence:** Add a help text/link to **Sony's official data-access request** as an optional source for a user who does not already know their numeric Account ID. The user should **inspect their own export privately and provide only the Account ID value** to the future pairing wizard if present. Do **not upload/import the full Excel workbook** into PlayStation Hub, ChatGPT, a public GitHub issue or a third-party lookup service: exports can contain passwords-adjacent security details, personal/family profiles, purchase history and other personal information. Do not parse the full export just to find one scalar ID, and do not retain original attachments.

**Identity assurance:** A user typing an ID seen in their own Sony export is a stronger **documented provenance claim** than an arbitrary public username lookup, but without verifying the underlying document/authorized Sony signature we still label the value **USER_SUPPLIED_ACCOUNT_ID**; it is **not** automatically \`SONY_PROVIDER_VERIFIED\`. Even a verified numeric account ID does not bypass the PS5 Pair Device PIN or the unapproved encryption/lookup-table gates.

**Official Terms:** [PlayStation terms of service (Portugal, updated April 2026)](https://www.playstation.com/pt-pt/legal/terms-of-service/) prohibit unauthorized access and bypassing authentication/security, subject to applicable law and consumer rights. Do not construe requesting one's own personal account data as permission to use copied client secrets or undocumented Sony APIs in the integration.

**Revised conclusion:** We have a **Sony-published self-service route for requesting personal account information**, with credible but unofficial reports that its export includes the numeric Account ID. The product can offer optional user-provided Account ID and an official instructions link without any Sony OAuth code, external SDK or shared Sony token. **No actual data request, export inspection, user information or Sony account login was performed here.**
