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

## WP-00 prerequisite

[WP-00](../architecture/WP-00-implementation-readiness-and-decision-closure.md) defines the approval and evidence needed before WP-01 implementation on `next`. No test or release gate has passed by writing the readiness plan.

## Updated HA 2026.11 and Marketplace compatibility gates

[Official-source re-audit](../research/official-source-reaudit-home-assistant-2026-11.md) adds validation targets for a pinned 2026.11.0/Python >=3.14.2 **research baseline** (minimum product support unapproved): DeviceInfo dataclass/UNDEFINED serializing, single-entry device registry ownership, `async_setup_entry`/unload/migrate exception behavior, explicit flow `step_id`, in-place entity ID renames, per-entry repairs, 2026.11 entity naming, frontend panel background/theme/removed components, and integrated Marketplace install/update behavior. HACS Action and Hassfest, `media_entertainment.gaming`, full `translations/en.json`, `brand/icon.png`, catalog release/version alignment and `hacs.json.homeassistant` need tests. Store/backup hook source review is not a passing SQLite restore test.

## WP-00A baseline and pure LAN contract gate

[WP-00A](../architecture/WP-00A-home-assistant-baseline-and-lan-contracts.md) selects Home Assistant Core `2026.11.0` and compatible Python `>=3.14.2` as source-verified reference, with formal product-minimum acceptance pending. The first 20 LAN contract tests are documented but all remain NOT_RUN. Later HA OS, actual console, Marketplace/HACS, backup, Remote Play and Sony permission gates retain their independent requirements. Do not claim source inspection is runtime compatibility.

## Legacy source-to-new-code review matrix

[Source code review blueprint](../research/legacy-code-review-and-refactoring-blueprint-2026-11.md) lists 12 audited legacy limitations and strengths, 20 proposed tests, and complete-file/code-review requirements. All 20 tests are NOT_RUN. Future implementations must show that source-derived design improvements are exercised by tests; no legacy App/MQTT code was merged or updated.

## Verified legacy frontend test-source inventory (no execution)

[Legacy frontend source audit](../research/legacy-frontend-source-audit-2026-11.md) confirms 80 `test(...)` declarations across ten JavaScript test files on `develop`. Their count does **not** establish a current pass result and does not substitute for new native-panel/WebSocket/HA OS tests. During future implementation, classify each old test as preserve/adapt/retire/replace and add accessibility, theme, multi-console and authorization evidence. No test suite was executed during this source audit.

## Official Quality Scale and Marketplace evidence requirements — Batch 02

[Batch 02 review](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md), [all 54 Core rule mappings](../standards/internal-quality-scale-applicability.md) and [SPEC-005 additional gates REL-13–REL-24](../specifications/SPEC-005-end-to-end-testing-ci-release-quality-gates.md) add: typed runtime_data, explicit platform concurrency, invalid-input versus transport action exceptions, source outage/recovery logs, allowlisted diagnostics, safe non-deletion of unreachable PS5s, multi-console dynamic discovery, loaded-entry system health, per-module Python coverage aspiration, Marketplace install rollback and limits (100 MiB / 50,000 files). **All new and old release tests remain NOT_RUN**, and Sony permission remains a separate blocked gate.

## Multi-console monitoring lifecycle gates (source review only)

[Core 2026.11 runtime review](../research/ha-core-2026-11-multi-console-runtime-source-audit.md) and [SPEC-008](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md) introduce 46 unexecuted tests and 12 approval gates. Required release evidence includes: no-listener historical monitoring; no duplicate per-console UDP probes; explicit disabled polling and missing-data gaps; two-console independence; setup of a previously validated sleeping console; teardown/failed-setup task cancellation; one-console unload without closing shared history/panel; safe identity/IP changes; no false hardware OFF; and correct historical durability state. The exact scheduler architecture is still a proposal, not a tested release capability.
