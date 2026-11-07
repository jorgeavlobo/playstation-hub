# PlayStation Hub — First-party PSN Account ID and local Remote Play pairing provisioning contract

**Date:** 2026-11-07
**Status:** PROPOSED DESIGN / MAINTAINER NO-EXTERNAL-LIBRARY RULE ACCEPTED / NO CODE OR LIVE PAIRING
**Research:** [Source-triangulated account ID encoding, acquisition, privacy and authorization audit](../research/first-party-psn-account-id-provisioning-and-pairing-trust-audit-2026-11-07.md)
**Scope:** An optional explicitly triggered PS5 local Remote Play pairing wizard, separated from native LAN status/title/usage monitoring and separate from any future optional Sony provider account presence.
**Security gates:** \`BLOCKED_CRYPTO_BACKEND_APPROVAL\`, \`BLOCKED_PROTOCOL_KEY_TABLE_RIGHTS\`, \`BLOCKED_SONY_PROVIDER_AUTHORIZATION\` when requiring a provider identity. The first two block **encrypted pairing**; provider authorization only blocks **automatic Sony account lookup**, not manual Account ID input. None block passive LAN.

## 1. Required separation of terms

| Domain datum | Meaning | Source/retention |
| --- | --- | --- |
| \`SonyAccountNumericId\` | Sony's per-account numeric 64-bit \`user_id\`, encoded from Sony account info in reviewed client code | User-supplied or actually Sony-authorized; personal identifier |
| \`RemotePlayAccountId\` | Canonical Base64 of **eight little-endian bytes** of that number | Pure local transform, NOT OAuth bearer token |
| \`PsnOnlineId\` | Public-facing PSN username | Separate; never used as numerical ID |
| \`LoginEmail\` | Sony login identifier | Never requested or retained for pairing |
| \`PsnOAuthToken\` / \`NPSSO\` | Auth credentials | NOT needed for manual ID path; forbidden to ask just for conversion |
| \`PairDevicePin\` | Number displayed on PS5 Pair Device screen | Explicit short-lived input; do not persist/log |
| \`ConsoleUserPasscode\` | Optional later local user login passcode | Different from Pair Device PIN; do not persist/log by default |
| \`ConsoleRegistKey\` / \`RpKey\` | Secrets received from successful console registration | Scope to one console/account; private managed credential record |
| \`LanHostId\` / \`ConsoleOwnerKey\` | Physical device discovery and verified binding | Not a Sony account, separate source authority |

Sony's official [account privacy policy](https://www.playstation.com/pt-pt/legal/privacy-policy/) distinguishes a unique account number from the PSN online ID. The Sony official [Remote Play settings](https://www.playstation.com/pt-pt/support/games/remote-play-settings/) identify the manual Pair Device UX. The *8-byte Base64* wire presentation derives from source implementations (not a Sony public Remote Play API specification).

## 2. Proposed account input modes

### Mode A — Manual numeric Sony Account ID

Future user selects "I already know my numeric PlayStation Account ID", provides a decimal string to our local HA pairing flow. Python backend, not JavaScript \`Number\`, validates ASCII decimal unsigned 64-bit integer and **encodes exactly eight bytes little-endian then canonical Base64**. This requires neither a Sony OAuth token nor PSN SDK; the **source of the number is still user-asserted**.

### Mode B — Manual Remote Play/Chiaki-style Base64 ID

Future user selects "I already have the Base64 Account ID". Backend validates **exactly 12 characters and a single trailing \`=\`**, strict standard Base64 alphabet, exactly eight decoded bytes and identical re-encoded result; it may additionally decode the equivalent unsigned numeric value for private input confirmation. No remote lookup/verification is implied. Keep the value out of routine logs.

### Mode C — Sony-authorized provider lookup (conditional)

Only if a **genuinely granted Sony client identity and permissible scopes** are later obtained, build a separately owned authorization-code/redirect/refresh/reauth adapter through supported HA HTTP and official consent. Never paste borrowed application Client IDs, secrets, unauthorized callbacks or NPSSO tokens into the integration. An Authorized Apps entry is user consent/revocation, not a general-purpose OAuth-client registration mechanism.

**Not supported by default:** PSN online-name scraping, unapproved lookup services, importing Playactor/Chiaki/PSNAWP at runtime, console jailbreak/payload or any user-password capture. The source input must not be guessed from the PS5 friendly name, IP or DDP host ID.

## 3. Assurance levels — do not conflate format with ownership

\`\`\`text
AccountIdentityAssurance:
  NOT_SUPPLIED
  USER_ASSERTED_FORMAT_VALID
  CONSOLE_ACCEPTED_PAIRING
  PROVIDER_VERIFIED  // only if a separate authorized Sony assertion is proven

PhysicalConsoleAssurance (separate):
  DDP_CANDIDATE
  PAIRED_OWNER_BINDING
  CONFLICT_OR_REPLACEMENT

PairingCapability (separate):
  CRYPTO_UNAVAILABLE
  ACCOUNT_ID_INPUT_READY
  USER_PAIR_SCREEN_REQUIRED
  IN_PROGRESS
  PAIRED
  ERROR
\`\`\`

- A Base64-decoding success is **USER_ASSERTED_FORMAT_VALID**, not a validated Sony account, nor the user's ownership.
- A decrypted/validated pairing reply is **CONSOLE_ACCEPTED_PAIRING** within the intended physical console/credential scope, not a Sony public identity token.
- Only an independent, properly authorized Sony identity response may justify **PROVIDER_VERIFIED**. Never implicitly set it because the result contains 8 bytes.
- A physical-console owner conflict or user permission mismatch must suspend the credential binding rather than transfer keys automatically.

## 4. Future pairing state flow (not executable code)

\`\`\`text
LAN_CONSOLE_CONFIGURED
  |
  +-- Passive DDP status/title/history works without an account
  |
  +-- User explicitly selects "Pair PS5" (admin/permission)
         |
         +-- Check AES/backend/table-provenance/firmware safety gates
         |       ↳ BLOCKED: explain capability unavailable; LAN unchanged
         |
         +-- Choose Manual Decimal OR Manual Base64 Account ID
         |       ↳ Reject malformed; store no OAuth secrets
         |
         +-- Display source assurance USER_ASSERTED and target-console identity
         |
         +-- Ask user to open Sony PS5 Pair Device screen
         |
         +-- Ask for the current Pair Device number, not Sony password/passcode
         |
         +-- Own first-party UDP 9295 SRC3/RES3
         +-- Own encrypted TCP registration /sie/ps5/rp/sess/rgst
         +-- Validate PS5-RegistKey / RP-Key and response owner
         +-- Private console/account credential binding
         |
         +-- Optional later, separate explicit "Standby" operation
                 ↳ Remote Play login passcode only if console asks
                 ↳ Verify physical 620 via independent LAN DDP
\`\`\`

The manual Account ID path does **not** promise that a disconnected retail PS5 will pair offline or that a Sony account is unnecessary on the console. It only removes the requirement for a *Sony cloud call by this client's registration routine* when a legitimate ID is already available.

## 5. Own-code boundaries (interface sketch, not files)

\`\`\`text
AccountIdentityParser        // Pure stdlib decimal/Base64 validation/conversion
AccountIdentityRegistry      // Per-user local opaque reference and source provenance
PairingIntent                // User/admin + console + account ID + operation generation
PairingCoordinator           // Per-console cancellable operation lease
PairDevicePinInput           // One-time user-provided value; never logged
RegistrationCryptoAdapter    // unavailable until lawful table and secure AES approval
RegisteredConsoleCredential  // private RP-Key/RegistKey, independent of usage ledger
ProviderAccountAdapter       // optional, only legitimately authorized Sony client
\`\`\`

Do not create a separate integration per Sony account merely because several accounts can use one PS5; future multi-entry/owner design must preserve one shared LAN monitor and independently scoped account credentials. Store no OAuth token for purely manual Account ID provisioning, and never retain a stale PIN or a literal redirect URL in generic HA diagnostics.

## 6. Finite source and release gates

| Gate | Meaning | Current state |
| --- | --- | --- |
| ID-01 | 8-byte little-endian Base64 account encoding from three source implementations | SOURCE_CONFIRMED, not tested by PlayStation Hub |
| ID-02 | Local pairing function accepts supplied Account ID and PIN without own OAuth call | SOURCE_CONFIRMED in reviewed implementations; no hardware validation |
| ID-03 | Numeric/Base64 input validation and no JS 64-bit precision loss | DESIGN_READY / NOT_RUN |
| ID-04 | Legitimate user-provided ID origin, account privacy and multiple consoles/accounts | PROPOSED / NOT_RUN |
| ID-05 | Sony-approved OAuth/client access for automatic lookup | NOT VERIFIED / DISABLED |
| ID-06 | AES primitive exception plus lawful PS5 protocol lookup tables | BLOCKED_PENDING_EXPLICIT_DECISION |
| ID-07 | Real PS5 pairing, expiry, wrong account, session/passcode safety | HARDWARE_NOT_RUN |
| ID-08 | Secrets and user identity never leaked in HA logs/WS/history | DESIGN_READY / NOT_RUN |
| ID-09 | Native LAN must work with no PSN account, no RP pairing and Sony outage | PRODUCT_REQUIREMENT / NOT_RUN |

**No implementation code, new runtime package, OAuth credentials, real account ID, PS5 PIN or device interaction was produced.** Extend existing Protocol 04/08, SPEC-002/003 and Architecture Guide, without creating ADR-0023/SPEC-023.

## 7. Official Sony personal-data export and numeric-precision safety (2026-11-07)

**Research refinement:** [First-party Account ID source investigation §§12–13](../research/first-party-psn-account-id-provisioning-and-pairing-trust-audit-2026-11-07.md#12-later-official-first-party-acquisition-route--sony-data-access-request-2026-11-07) has confirmed a Sony official self-service **personal-account-data export** route: [PT-PT PlayStation data-access requests](https://www.playstation.com/pt-pt/support/account/data-request/). Community reports indicate its Excel file's **Account Detail** worksheet can contain the account number, although Sony's help article does not guarantee this exact field is always included. The **EU Data Act device-data request is different** and is not the correct default for account identity.

**Critical requirement:** [Microsoft](https://support.microsoft.com/pt-pt/excel/keeping-leading-zeros-and-large-numbers) officially confirms Excel numeric values retain at most **15 significant digits**. A 19-digit Sony account number must be captured as **unmodified text**, never parsed/rounded as Excel numerical value or JavaScript Number. We have not inspected Sony's actual workbook cell type, so the source must be checked rather than declaring the export inaccurate. A pre-rounded number cannot be repaired simply by switching a cell to Text, and a Base64 transform of that wrong integer will still look structurally valid.

The future pairing user guidance may link to the **official Sony personal-data request** as a source, but must not import/store the entire XLSX file, scrape Sony's account-management website, reuse browser cookies or ask for an uploaded spreadsheet. The user privately supplies only the exact account-number string, with source \`USER_SONY_EXPORT_ASSERTED\` but **not SONY_PROVIDER_VERIFIED**. A separately authorized Sony client remains the only proposed way to obtain a provider-authenticated assertion. The future parser must preserve all 64-bit bits in Python server-side \`int\`, checking bounds and canonical Base64 before any crypto/network work.

**Additional future tests:** \`IDP-21..24\` in the source research cover large integer precision, Excel text versus numeric provenance, frontend string transport and unrepairable pre-rounding. All NOT_RUN. No code, user export or account number was accessed in this revision.
