# LAN discovery

**Document status:** Initial specification — source research, not live validated  
**Last reviewed:** 2026-11-05  
**Implementation:** Not started  
**Primary proposed Python module:** `custom_components/playstation_hub/transport/discovery.py`

## 1. Objective and scope

Find PS5 consoles on local IPv4 networks without an external service.

## 2. Source-confirmed upstream behavior

UDP SRCH to port 9302; PS5 discovery version 00030010. HTTP-like response headers include host-id, host-name, host-type, system-version and host-request-port. Global broadcast and per-interface directed broadcasts are used upstream; a manual address fallback is necessary across routed networks.

## 3. PlayStation Hub architecture decision

Discovery must deduplicate by stable host ID, enforce bounded timeouts, close sockets, distinguish no reply from standby and reject malformed/unrecognized status responses.

## 4. Proposed interface contract

The module must expose typed, async-compatible operations and return normalized domain objects or explicit typed errors. Transport I/O must not block the Home Assistant event loop. No Home Assistant entity or frontend component may perform protocol I/O directly. Each observation must record its source and UTC timestamp. Details of function signatures remain **to be specified**, not implemented.

## 5. Failure, privacy and lifecycle policy

All network operations need bounded timeouts and cancellation-safe cleanup. Invalid or stale data must never be reported as confirmed current state. Secrets must not enter logs, diagnostics or frontend assets. The integration must unload cleanly and handle multiple consoles without shared mutable protocol state.

## 6. Source references

- https://github.com/dhleong/playactor/blob/main/src/discovery/model.ts
- https://github.com/dhleong/playactor/blob/main/src/discovery/standard.ts
- https://github.com/dhleong/playactor/blob/main/src/discovery/messages.ts
- https://github.com/FunkeyFlo/ps5-mqtt/blob/main/ps5-mqtt/server/src/playactor/discovery.ts

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
