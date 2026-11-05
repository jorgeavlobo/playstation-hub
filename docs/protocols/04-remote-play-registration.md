# Remote Play registration

**Document status:** Initial specification — source research, not live validated  
**Last reviewed:** 2026-11-05  
**Implementation:** Not started  
**Primary proposed Python module:** `custom_components/playstation_hub/transport/remote_play/registration.py`

## 1. Objective and scope

Pair a console using a user-authorized Remote Play flow.

## 2. Source-confirmed upstream behavior

Upstream PS5 flow sends SRC3 over UDP 9295 and expects RES3, derives a PIN-based encrypted registration payload, POSTs to the PS5 Remote Play registration endpoint on port 9295 and decrypts a response containing RP-Key and registration material.

## 3. PlayStation Hub architecture decision

Registration must be an explicit UI step; PIN, account ID, registration keys and responses are sensitive. Handle wrong PIN, timeout, firmware mismatch, revocation and re-pairing. Do not assume pairing is necessary for LAN-only status.

## 4. Proposed interface contract

The module must expose typed, async-compatible operations and return normalized domain objects or explicit typed errors. Transport I/O must not block the Home Assistant event loop. No Home Assistant entity or frontend component may perform protocol I/O directly. Each observation must record its source and UTC timestamp. Details of function signatures remain **to be specified**, not implemented.

## 5. Failure, privacy and lifecycle policy

All network operations need bounded timeouts and cancellation-safe cleanup. Invalid or stale data must never be reported as confirmed current state. Secrets must not enter logs, diagnostics or frontend assets. The integration must unload cleanly and handle multiple consoles without shared mutable protocol state.

## 6. Source references

- https://github.com/dhleong/playactor/blob/main/src/remoteplay/registration.ts
- https://github.com/dhleong/playactor/blob/main/test/remoteplay/registration-test.ts

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
