# Quality gates

**Status:** Proposed — 2026-11-05.

Before first public release: HACS validation and Hassfest; supported HA version matrix; automated setup/unload/reload and config-flow tests; localization coverage; protocol negative tests; secure credentials; no event-loop blocking; live PS5 compatibility tests; database backup/restore; frontend panel mobile/desktop; release upgrade/rollback.

Internal target is Platinum-style engineering, not an official quality-scale rating.

## Formal test and release specification

[SPEC-005 — End-to-End Testing, CI/CD & Release Quality Gates](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md) defines the test pyramid, requirement traceability, CI/HA OS/hardware validation, synthetic security/fault tests, auditable evidence records and twelve release gates. All gates remain NOT_RUN or BLOCKED; documentation is not implementation evidence. Optional PSN features remain blocked by SPEC-003 Sony authorization; LAN-only release scope must pass its own tests.

## Security release gate linkage

[SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md) defines SEC-G01–SEC-G12 and SEC-T001–SEC-T030. Critical credential disclosure, unauthorized console commands, history corruption and privacy bypass block affected releases. Written controls are not passing tests.

## Hardware and firmware evidence

[SPEC-007](../specifications/SPEC-007-console-firmware-compatibility-matrix.md) defines hardware-family, firmware, power, network and Remote Play compatibility matrices and twelve release gates. No PlayStation model is currently hardware-verified in the PlayStation Hub implementation.

## Architecture review prerequisite

The [formal ADR review](../architecture/formal-architecture-review-adr-0004-0010.md) recommends conditional acceptance of ADR-0004–0010 only after explicit maintainer approval and evidence. All existing release gates remain in force; no test is marked passed by this documentation review.
