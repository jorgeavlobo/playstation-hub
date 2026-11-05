# SPEC-005 — End-to-end testing, CI/CD and release quality gates

**Status:** Proposed, not approved; no tests or workflows executed
**Date:** 2026-11-05
**Scope:** PlayStation Hub, one HACS integration, one sidebar panel, LAN-only core, optional Remote Play and permission-gated PSN.
**Inputs:** Protocols 01–10, ADR-0001–0010, SPEC-001–004, docs/release/quality-gates.md.
**Branches:** Research on `main`; implementation only on `next` after approval; `develop` frozen legacy reference.
**Evidence principle:** A written test is not a passing test; an upstream source observation is not device validation.

## 1. Release philosophy and traceability

A feature can be marked RELEASE_READY only if its requirements, architecture decision, implementation revision, tests, security review and where necessary real-hardware evidence are linked. Tests must record exact code commit, HA Core and Python versions, console model/firmware, fixture provenance, expected and actual behavior, timestamp and reviewer. Every gate starts NOT_RUN. Never claim an official Home Assistant quality tier from internal aspirations.

Release scopes are separate:
- **LAN baseline:** discovery, stable device identity, observed physical state, native entities, historical ledger and sidebar; no Sony login, MQTT, add-on or Remote Play pairing.
- **Remote Play extension:** user-initiated pairing, wake and standby only after byte/crypto and hardware validation.
- **PSN extension:** account authentication, presence, metadata, library and trophies only after SPEC-003 provider permission and endpoint scope gates; code may exist but release feature must remain disabled until authorized.
- **Optional artwork and advanced statistics:** independently gated by rights, privacy and accounting semantics.

A blocked optional extension must not block a verified LAN-only release, but the release notes and UI must not advertise it as operational.

## 2. Test pyramid and ownership

| Layer | Scope | Harness | Gate |
| --- | --- | --- | --- |
| Static | Python typing/lint/security, JSON/manifest/translations, frontend lint/types | CI pinned tools | Required for every PR |
| Pure unit | IDs, parsing, observation ordering, session arithmetic, DTOs | pytest synthetic fixtures | Required for affected modules |
| Protocol contract | UDP/TCP framing, crypto known-answer vectors, PSN mocked schema | Fake transports, source-pinned fixtures | Required for relevant extension |
| Repository integration | SQLite transactions/migrations, Store, credentials, crash recovery | Temporary isolated DB and fault injection | Required for persistence |
| HA Core integration | Config flows, discovery, entities, services, coordinator lifecycle | pytest-homeassistant-custom-component / compatible HA harness | Required for HA release |
| API/frontend | WS ACL, subscriptions, pagination, reconnect, XSS, localization | Fake HA backend, browser automation | Required for sidebar |
| HA OS system | Clean HACS install, backup/restore, mobile, upgrades | Isolated supported HA OS instance | Required for public release |
| Real device | PS5 LAN state, discovery, optional pairing/commands | Authorized console, recorded firmware | Required for hardware capability claims |
| Authorized Sony account | Auth/refresh, privacy, schemas, rate limits | Only if permitted by SPEC-003 | Required for PSN release |

Tests must be deterministic, parallel-safe and offline by default. Networked hardware/provider tests are isolated, opt-in, non-PR jobs; never require real credentials in public CI.

## 3. Requirements-to-tests matrix

| Requirement | Source | Test families | Release scope |
| --- | --- | --- | --- |
| One HACS integration, no MQTT | ADR-0001 | HA-I, REL | LAN |
| One sidebar panel | ADR-0002/0010 | UI, API, REL | LAN |
| Multiple independent consoles | ADR-0004, SPEC-001 | LAN, HA-I | LAN |
| Fresh power distinct from unknown | ADR-0005 | OBS, HA-I | LAN |
| Conservative sessions, gaps, DST | ADR-0006 | SES, DB | LAN |
| Credential isolation and rotation | ADR-0007 | SEC, AUTH, DB | RP/PSN |
| Durable ledger, backups | ADR-0008 | DB, BAK, REL | LAN |
| HA native entities/actions | ADR-0009 | HA-I, SEC | LAN/RP |
| Remote Play wire and safety | SPEC-002 | RP, CRYPTO, HW | RP |
| Sony permission and API mapping | SPEC-003/004 | PSN, SEC, HW-PSN | PSN |
| Accessibility, translations, mobile | ADR-0010 | UI, I18N, REL | LAN |

## 4. Test IDs and representative critical cases

### LAN / identity: LAN-T
- LAN-T001: valid PS5 response creates verified candidate, never automatically pairs.
- LAN-T002: missing/invalid host ID cannot become a permanent identity.
- LAN-T003: second console discovered after first entry exists; independent devices.
- LAN-T004: same console through DHCP and manual probe deduplicates.
- LAN-T005: IP reassignment to another host ID blocks credentialed commands and history reassignment.
- LAN-T006: no reply does not mean OFF; standby recognized only from validated source.
- LAN-T007: multi-interface/VLAN/manual directed setup and bounded UDP cancellation.
- LAN-T008: coexists with official `playstation_network` without altering its registry.

### Observation and history: OBS-T / SES-T
- OBS-T001: late request generation cannot overwrite newer accepted state.
- OBS-T002: old run ID after reload is rejected.
- OBS-T003: PSN offline cannot overwrite fresh LAN AWAKE.
- OBS-T004: restored last-known state is stale until new evidence.
- SES-T001: same-state bounded samples advance one segment, no duplicate count.
- SES-T002: changed-state transition between polls has unknown boundary.
- SES-T003: outage beyond approved gap closes at last durable checkpoint; no backfill.
- SES-T004: replayed observation/event IDs cannot add duration twice.
- SES-T005: two consoles simultaneous usage sums resource-seconds; wall-clock union is separate.
- SES-T006: one account on two consoles cannot duplicate game time.
- SES-T007: Lisbon DST spring/fall, leap day, local midnight, time-zone changes.
- SES-T008: provider lifetime duration never added to local observed time.

### Remote Play: RP-T
- RP-T001: exact source-derived SRC3/RES3 and registration preface byte tests.
- RP-T002: independent HMAC-IV/AES-CFB known-answer vectors, counter/endian checks.
- RP-T003: malformed nonce, key and framing rejected; no partial pairing.
- RP-T004: authenticated control socket retained, fragmented/coalesced frames parsed.
- RP-T005: wake credential source mapping proven; wrong-console target blocked.
- RP-T006: standby when already in standby never wakes device.
- RP-T007: command send without confirmed post-state returns UNCONFIRMED.
- RP-T008: unload/cancel closes sockets and does not resend uncertain commands.

### PSN / credentials: PSN-T
- PSN-T001: release gate refuses provider adapter when Sony permission missing.
- PSN-T002: OAuth callback state/PKCE/redirect/account mismatch rejected.
- PSN-T003: five concurrent refresh consumers perform one refresh per account.
- PSN-T004: remote rotation plus local write failure yields non-durable error and reauth path.
- PSN-T005: 403 privacy is RESTRICTED, not OFFLINE; 429 respects backoff.
- PSN-T006: format vs launchPlatform, title vs trophy/product/entitlement ID remain distinct.
- PSN-T007: malformed/paginated/partial GraphQL results preserve completeness.
- PSN-T008: no NPSSO/access/refresh tokens in logs, diagnostics or UI.
- PSN-T009: unlink account does not disable LAN and does not leak account history.

### Persistence: DB-T / BAK-T
- DB-T001: atomic event/checkpoint/segment commit with injected failure.
- DB-T002: concurrent console writers serialize correctly without HA loop blocking.
- DB-T003: duplicate ID, invalid foreign key, schema mismatch and disk-full failures.
- DB-T004: migration v1->v2->v3 and interrupted migration recovery.
- DB-T005: read-only/quarantine on corruption, never silent history deletion.
- BAK-T001: HA OS backup includes intended data and credential stores.
- BAK-T002: WAL-active backup is application-consistent and integrity-checked.
- BAK-T003: restore older backup marks missing interval unknown; expired tokens require reauth.
- BAK-T004: no real credentials in exports or release artifacts.

### Home Assistant and UI: HA-I / API / UI
- HA-I001: config flow discovery, ignored candidates, reauth, reconfigure and migration.
- HA-I002: setup/unload one entry leaves other consoles and panel functioning.
- HA-I003: entities preserve unique IDs after IP/hostname change.
- HA-I004: wake/standby services validate target and user permission.
- HA-I005: entity getters do not perform network/disk I/O.
- API-T001: authenticated admin vs non-admin authorization on each private endpoint.
- API-T002: snapshot/subscription race cannot lose event; revision gap resync.
- API-T003: bounded pagination, invalid cursor/period rejection, cancellation.
- API-T004: WebSocket reconnect never automatically repeats power command.
- UI-T001: English and PT-PT strings, fallbacks and error translations.
- UI-T002: mobile/iOS safe-area, dark/light theme, keyboard, screen reader, reduced motion.
- UI-T003: malicious title/online ID escaped; image SSRF protections.
- UI-T004: HACS bundle hash/API mismatch yields safe upgrade notice.

## 5. CI/CD workflow proposal

**Pull request checks (offline, synthetic):**
1. Validate formatting/lint/type checks for Python and frontend, lockfiles and license inventory.
2. Parse `manifest.json`, `strings.json`, translations, services and repository metadata.
3. Run unit and protocol-contract tests, including known-answer vectors and property-based replay.
4. Run Home Assistant integration tests with fake coordinators and fake HTTP/UDP transports.
5. Run SQLite fault-injection/migration tests and API authorization tests.
6. Build bundled frontend deterministically; run browser component tests and inspect generated asset inventory.
7. Run Hassfest and HACS validation as supported by pinned action revisions.
8. Enforce secret scanning and dependency vulnerability review; upload sanitized coverage and test artifacts.
9. Reject a PR if a required check fails or changes generated assets without matching source/build metadata.

**Scheduled/nightly (no real credentials):** broader supported HA Core version matrix, Python compatibility, large synthetic history, concurrency, fuzz/property tests, frontend browser matrix and backup simulation.

**Manual controlled validation:** Home Assistant OS clean install, actual HACS install/upgrade/rollback, backup/restore, live PS5 network transitions and optional authorized Sony account flows. Explicit approval and secure private logs required.

**Release pipeline:** version/tag consistency -> clean build -> tests -> HACS/Hassfest -> artifacts/hash/signature policy -> human approval -> tagged release -> staged upgrade test -> changelog and rollback instructions. Do not automatically publish on a documentation commit.

## 6. Supported version matrix

Before implementation, pin:
- Minimum and maximum tested HA Core releases, plus the latest stable at release time.
- HA OS/Supervisor installation mode(s) actually tested.
- Python version matching HA Core and dependency constraints.
- Frontend browser engines and HA companion mobile webviews.
- Supported PS5 firmware/model and network topology; PS4 remains separate.
- HACS release/version and validation action revisions.
- Source library versions and known API compatibility.

`core/dev` source is a research reference, not proof of compatibility with the target stable. A new HA release should trigger a compatibility run and explicit release note, not silent support claims.

## 7. Security and compliance quality gates

- **SEC-G1:** no secrets in code, fixtures, logs, events, diagnostics, frontend, GitHub Actions artifacts.
- **SEC-G2:** per-console and per-account credential isolation and authorization.
- **SEC-G3:** command target validation and safe LAN host identity mismatch behavior.
- **SEC-G4:** admin/private API access checked server-side; panel visibility alone insufficient.
- **SEC-G5:** image URL, redirect, DNS, MIME and size SSRF defenses.
- **SEC-G6:** OAuth client/endpoint permission for Sony PSN (blocked until documented).
- **SEC-G7:** correct user consent and child-account privacy/retention.
- **SEC-G8:** database export/deletion and backup confidentiality.
- **SEC-G9:** dependency license, cryptographic table provenance and security review.

Security defects that leak credentials, misdirect power commands, erase history or bypass permissions block release irrespective of test coverage percentage.

## 8. Performance, scale and fault injection

Synthetic workload tiers: zero data, 100k rows, 1M rows, and ~13M raw observations for a multi-console 3-year upper-bound scenario. Record database bytes, WAL growth, CPU, memory, startup/migration duration, history query p50/p95/p99, write latency and HA event-loop responsiveness. These are benchmark scenarios, **not** measured results.

Fault injection: UDP loss, duplicate packets, delayed replies, TCP fragmentation, HTTP 401/403/429/5xx, OAuth refresh rotation failure, disk full, DB corruption, power loss, backup during writes, stale browser tab, WebSocket disconnect, HA unload during pending command, clock jump and DST boundary. Tests must assert both correct output and cleanup (no leaked tasks/sockets, duplicate events or unbounded retries).

Set numeric thresholds only after profiling representative Home Assistant OS hardware; do not invent performance promises.

## 9. Test fixture and secrets policy

- Use synthetic fictional identifiers, fake tokens and fixed test keys only; public known-answer vectors may be used with reviewed licenses.
- Pin upstream source commit and fixture derivation in a provenance manifest.
- No personal console host ID, PSN account ID, NPSSO, actual token, password, pairing PIN, network capture or real usage history in GitHub.
- Keep fake provider fixtures complete enough to test error/partial pagination, but never imply they prove a Sony production schema.
- Record random seeds for property-based failures and save minimal redacted reproduction cases.
- Isolate temporary SQLite paths and avoid shared mutable fixtures across parallel tests.

## 10. Test evidence record and gate statuses

Each gate must have an auditable record:

```yaml
gate_id: "LAN-G3"
status: "NOT_RUN" # NOT_RUN | PASS | FAIL | BLOCKED | WAIVED
scope: "lan"
requirement_refs: ["SPEC-001"]
test_ids: ["HA-016"]
code_commit: null
test_environment:
  ha_core: null
  python: null
  console_model: null
  firmware: null
fixture_provenance: null
expected_result: "Custom integration appears in Discovered after verified probe"
actual_result: null
run_timestamp_utc: null
reviewer: null
evidence_artifact: null
waiver_reason: null
```

**Rules:** A WAIVED status needs explicit owner, rationale, risk and expiration, and cannot override security/legal release blockers. A BLOCKED gate is not a PASS. A gate with no executable evidence remains NOT_RUN. Never use documentation completion as test completion.

## 11. Release gates and severity

| Gate | Release blocker? | Evidence |
| --- | --- | --- |
| REL-01 — requirements and ADR scope approved | Yes | Decision register and traceability |
| REL-02 — static, unit and integration CI green | Yes | Pinned CI run |
| REL-03 — HACS and Hassfest pass | Yes | Validation reports |
| REL-04 — HA OS clean install, reload, upgrade | Yes | Test log and versions |
| REL-05 — stable LAN identity/discovery on PS5 | LAN yes | Hardware evidence |
| REL-06 — session ledger and restore consistency | History feature yes | Crash/backup tests |
| REL-07 — backend permissions and secret isolation | Yes | Security tests |
| REL-08 — sidebar mobile/accessibility/i18n | Yes | Browser/device evidence |
| REL-09 — Remote Play crypto/pairing/commands | RP only | SPEC-002 all applicable gates |
| REL-10 — Sony client/endpoint authorization | PSN only | SPEC-003 documented permission |
| REL-11 — PSN DTO/privacy/rate tests | PSN only | SPEC-004 tests |
| REL-12 — release notes, recovery and support | Yes | Changelog and rollback guide |

**Severity:** Critical = unauthorized control, secret disclosure, silent data corruption, or privacy bypass; blocks all affected releases. High = core discovery/history/action failure or broken backup; blocks affected scope. Medium = degraded optional UI/metadata; can be deferred with documented limitation. Low = cosmetic issue; triage explicitly. No arbitrary coverage percentage can override critical failures.

## 12. Release variants and feature flags

| Capability | LAN-only release | Remote Play release | PSN-enabled release |
| --- | --- | --- | --- |
| Verified LAN discovery and power observations | Required | Required | Required |
| Multi-console HA entities | Required | Required | Required |
| One bundled sidebar | Required | Required | Required |
| Durable conservative history | Required if advertised | Required if advertised | Required if advertised |
| Wake/standby | Disabled/unavailable | Enabled after RP gates | Independent optional |
| PSN login/presence/library | Disabled with honest UX | Disabled unless authorized | Enabled only after Sony gates |
| Sony provider time/artwork | Disabled | Disabled unless authorized | Separately rights-gated |

Do not ship empty placeholder actions or UI labels claiming unsupported features. Disabled features should explain why without exposing implementation secrets.

## 13. Release readiness checklist

- [ ] Scope and ADR decisions approved.
- [ ] Stable CI test environments and dependency pins.
- [ ] All applicable gate evidence recorded with code commit.
- [ ] No critical/high unresolved defects in shipping scope.
- [ ] HA OS backup and restore tested under live database writes.
- [ ] Native entities and actions tested with multi-console configuration.
- [ ] PSN disabled if Sony permission remains unresolved.
- [ ] Real PS5 hardware tests completed for claimed capabilities.
- [ ] English and PT-PT localization, responsive/accessibility checks.
- [ ] User-facing release notes describe limitations, unknown states and data retention.
- [ ] Upgrade/rollback and recovery documented.
- [ ] Human release sign-off with reproducible artifact hashes.

## 14. Open decisions

1. Pin first supported HA Core/OS, Python and frontend versions.
2. Approve CI workflow/action revisions and coverage targets.
3. Select implementation test libraries and safe fake transports.
4. Define benchmark latency/storage thresholds from representative HA OS measurements.
5. Approve release gating evidence schema and reviewer responsibilities.
6. Decide staged LAN-only v1 versus broader scope after Sony authorization.
7. Define optional-feature flags and release UI semantics.
8. Approve policy for waivers and security exception handling.
9. Define live-hardware fixture privacy, capture storage and cleanup.
10. Complete SPEC-006 threat model and SPEC-007 hardware compatibility matrix.

## 15. References

- [Quality gates](../release/quality-gates.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)
- [SPEC-001 LAN discovery](SPEC-001-lan-discovery-acceptance-matrix.md)
- [SPEC-002 Remote Play](SPEC-002-remote-play-byte-contract-and-safety.md)
- [SPEC-003 PSN authorization](SPEC-003-psn-authorization-and-availability.md)
- [SPEC-004 PSN DTO mapping](SPEC-004-psn-presence-game-metadata-dto-mapping.md)
- [ADR-0004 Identity](../decisions/ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 Observation](../decisions/ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 Sessions](../decisions/ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007 Credentials](../decisions/ADR-0007-credentials-and-token-persistence.md)
- [ADR-0008 Storage](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0009 HA entities/actions](../decisions/ADR-0009-home-assistant-integration-entities-actions.md)
- [ADR-0010 Sidebar API](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://developers.home-assistant.io/docs/development_testing/
- https://github.com/home-assistant/core
- https://github.com/home-assistant/actions
- https://www.hacs.xyz/docs/publish/integration/
- https://www.home-assistant.io/common-tasks/general/backups

**Outcome:** Test pyramid, release scope boundaries, 50+ representative test cases, evidence record, security gates, CI/CD workflow and twelve release gates documented. All gates are currently NOT_RUN or BLOCKED. No executable tests, GitHub Actions or hardware operations were performed.

## 16. Current Marketplace and Core Quality Scale audit — additional release gates (2026-11-05)

Source review: [Batch 02 official audit](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md); [all 54 Core rule applicability statuses](../standards/internal-quality-scale-applicability.md). **Core quality tiers are not official awards for custom integrations.** We voluntarily adopt applicable rules as internal quality goals and separately satisfy actual Marketplace checks.

### Additional design and release tests (all NOT_RUN)

| ID | Criterion | Test |
| --- | --- | --- |
| REL-13 | Explicit `PARALLEL_UPDATES` per entity platform | Review sensor/binary_sensor/button and concurrent button requests |
| REL-14 | Typed per-entry `runtime_data` | Unload one console while other entry/panel continues |
| REL-15 | Distinct validation vs execution errors | Invalid target raises `ServiceValidationError`; device failure raises `HomeAssistantError` |
| REL-16 | One outage and one restoration log | Simulated repeated network failures and recovery |
| REL-17 | Per-entry/device diagnostic redaction | Snapshot tests with synthetic tokens, account IDs, titles, private usage history |
| REL-18 | Safe stale device behavior | Months of no UDP response never auto-delete device or history |
| REL-19 | Dynamic independent console discovery | New PS5 gets separate entry without reload/identity confusion |
| REL-20 | System health loaded entry behavior | Disabled/ignored/unloaded entries cannot access absent `runtime_data` |
| REL-21 | Marketplace installation artifact bounds | Download/unpacked <=100 MiB and <=50,000 files |
| REL-22 | Marketplace post-write validation | Domain/manifest conflict or failure safely refuses/reverts install |
| REL-23 | Per-module Python coverage | Voluntary target >95% for **each** relevant module, not aggregate percent |
| REL-24 | Repo onboarding/removal documentation | README/docs cover fields, features, unknown states, compatibility, backups, removal |

The 12 original release gates remain binding project checkpoints; REL-13 through REL-24 are additional sub-gates, not proof the product is ready. The Marketplace limits are actual installation checks; Core's >95%-per-module rule is an internal optional quality target, not a custom Marketplace catalog certification.
