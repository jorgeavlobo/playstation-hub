# PSN authentication

**Document status:** Initial specification — source research, not live validated  
**Last reviewed:** 2026-11-05  
**Implementation:** Not started  
**Primary proposed Python module:** `custom_components/playstation_hub/transport/psn/authentication.py`

## 1. Objective and scope

Obtain optional PSN account authorization for enriched activity data.

## 2. Source-confirmed upstream behavior

PS5-MQTT uses psn-api to exchange NPSSO for OAuth authorization, stores access/refresh token metadata and refreshes tokens. The upstream project uses an authenticated internal Sony service; public source does not establish Sony's official support for third-party integrations.

## 3. PlayStation Hub architecture decision

PSN must be optional and independently consented to. Do not expose NPSSO, access/refresh tokens or account IDs in logs, GitHub, frontend or diagnostics. Document expiry, reauth, unlink, data deletion, privacy and possible service incompatibility.

## 4. Proposed interface contract

The module must expose typed, async-compatible operations and return normalized domain objects or explicit typed errors. Transport I/O must not block the Home Assistant event loop. No Home Assistant entity or frontend component may perform protocol I/O directly. Each observation must record its source and UTC timestamp. Details of function signatures remain **to be specified**, not implemented.

## 5. Failure, privacy and lifecycle policy

All network operations need bounded timeouts and cancellation-safe cleanup. Invalid or stale data must never be reported as confirmed current state. Secrets must not enter logs, diagnostics or frontend assets. The integration must unload cleanly and handle multiple consoles without shared mutable protocol state.

## 6. Source references

- https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/psn-account.ts
- https://github.com/achievements-app/psn-api/blob/main/src/authenticate/exchangeRefreshTokenForAuthTokens.ts

## 7. Open questions and implementation-stage verification

- [ ] Finalize precise wire-format details and edge cases from the upstream source.
- [ ] Review licenses and any Sony service restrictions before reuse.
- [ ] Specify Python data models, error types and async lifecycle.
- [ ] Add synthetic positive/negative protocol fixtures and tests.
- [ ] Validate behavior on a test PS5 during implementation.
- [ ] Record firmware compatibility and recovery behavior.

## 8. Related documents

- [Protocol index](README.md)
- [Architecture guide](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md)

**Evidence boundary:** This document records source findings and intended design. It does not claim the protocol is officially documented by Sony or proven functional in PlayStation Hub.
