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

[WP-00](../architecture/WP-00-implementation-readiness-and-decision-closure.md) defines the approval and evidence needed before WP-01 implementation on a later authorized `feature/<scope>` branch. No test or release gate has passed by writing the readiness plan.

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


## Crash recovery, SQLite version and restore-safety release gates — 2026-11-06

[Source research](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md) and [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md) extend the release evidence requirements with 56 NOT_RUN test scenarios and 14 OPEN sign-off gates. Prioritize actual HA OS linked SQLite C library version (2026 WAL-reset fix/backports), single writer/checkpointer, stable idempotent receipts after ambiguous COMMIT, crash gap correctness, automatic restore-versus-normal-restart discrimination, complete backup snapshot/manifest plus archive file selection, full/partial Supervisor file replacement tests, non-destructive corruption recovery and archive-only panel behavior. Existing SPEC-008/009 scenarios remain open; overlapping scenarios are not independently tested by documentation. No release is qualified.


## HA OS storage root, backup deadlock and archive-only lifecycle gates — 2026-11-06

[Storage/restore research](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md) and [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) add 64 NOT_RUN cases and 16 OPEN gates. First release must verify private config-root placement, Core/OS/Container file paths, real archive members and exclusion semantics, atomic snapshot/manifest generation, restart-vs-restore authority, recovery of mixed config/ledger identities, one panel and Hub/Archive-only mode, reinstallation/uninstallation, privacy and retention.

**P0 source-proven inter-hook race:** Home Assistant Core's pre-backup hook manager gathers all loaded integration pre hooks and errors when any fails; pinned Supervisor awaits begin_backup before its end_backup finally. Thus a successful write-freeze in PlayStation Hub could remain without post-backup after another integration's error. The long-held SQL quiescence approach cannot be released without rigorous failure compensation and active-archive safety evidence. A static immutable SQLite snapshot avoids depending on a multi-minute freeze but still needs a safe restore selector.

All 64 cases remain definitions only; no tests, CI, HACS validation or hardware exercises have run. This extends (not replaces) SPEC-005, SPEC-008/009/010 and the explicit maintainer ADR approval gates.


## Immutable SQLite snapshot and archive trust release blockers — 2026-11-06

[Immutable snapshot source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md), [ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md) and [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md) introduce **64 NOT_RUN cases and 16 OPEN gates**. A successfully published SQLite Online Backup API artifact is NOT proof of a whole Home Assistant backup archive that can restore it automatically: in the pinned Supervisor/Core implementation no per-file exclude is provided to a custom pre/post hook and mutable app-owned SQLite files can be included. Future release requires actual archive member inspection and verified authoritative restore selection or a deliberately limited documented administrator recovery workflow.

The accepted architecture in [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06) commits to one logical Hub/Archive entry and retained private history, but does not close SQL, Core/Supervisor, security or restore test gates. The incomplete post-hook issue prohibits a writer that must remain frozen across an entire archive unless a separately verified safe-resume protocol exists. Negative fault cases include source writes during incremental backup, missing hook, two concurrent snapshot requests, interrupted two-file publication, GC racing an active tar copy, different ledger UUID, no restored backup intent and stale snapshot on ordinary restart. Never assert durable multi-year disaster recovery until tests pass.


## Restore authority and portable storage release gates — 2026-11-06

The [pinned official-source audit](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md), [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md) and [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md) add 64 planned but NOT_RUN tests and 16 OPEN gates. A release that claims safe disaster recovery must verify not only SQLite Online Backup snapshot consistency but also the authority of the restored file when raw live DB/WAL was separately archived, and the mismatch that occurs if HA configuration and share/media are restored from different times. Existing Backup Agent is a destination mechanism, not a source configuration archive file-exclusion hook in the reviewed Core/Supervisor API. The product must not promise restoration of commits absent from all surviving copies.

Required before shipping recoverable historical data: explicit trust classes for valid live DB, immutable verified snapshot, raw tar copy and external ledger; source lineage/fork detection beyond same ledger UUID and cursor; preserved original files; admin-only recovery consent; scoped physical-console/account identity validation; UNKNOWN coverage gaps; HA OS/Container mount and automatic/partial backup selection tests. Default T1 portable config-root direction remains conditional. T2/T3 external live stores cannot be mandatory or assumed local, private, or included in default backup. If fully automatic lossless restore becomes required, this is an unresolved P0 external API/design blocker; honest guided recovery may instead be approved as product behavior after tests.


## Native recovery and restoration provenance release blockers — 2026-11-06

[Official-source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014 PROPOSED](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) and [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) add 72 NOT_RUN scenarios and 18 OPEN gates.

Release gating for recovery must include:
- Hub-only RECOVERY_HOLD is a loaded, non-destructive mode with one sidebar, independent of consoles, without fabricating a blank SQLite ledger.
- A global Repairs issue for shared-ledger errors remains active through removal of any one console, while per-console repair issues may be entry-scoped; diagnostics never expose personal history/secrets.
- Every proposed PlayStation Hub recovery WS command enforces current administrator rights server-side. Preview/confirm checks digest, candidate lineage, ledger cursor/revision and canonical console/account associations under a global lock immediately before mutation. Stale or replayed confirmations cannot act.
- Recovery jobs are manager-owned, idempotent and cancellation-/shutdown-safe; a mobile/browser disconnect removes subscriptions only. An incomplete SQLite worker or failed file promotion must never be reported cleanly closed.
- Source classes distinguish published snapshot, verified archive, raw copied live DB/WAL and external/forked ledgers; no automatic largest-cursor merge or implicit post-restore Sony token authorization.
- The pinned Supervisor RESTORE_JOB_ID_ENV/BackupManager RestoreBackupEvent source chain is verified in Core and Supervisor source, but custom integration event timing and complete post-restore provenance must be tested on HA OS; never infer auto restore correctness from a generic completed job event.
- Existing documented pre/post backup hooks do not provide reviewed per-app file excludes; possible upstream enhancements are unfiled proposals, not release dependencies automatically accepted.
- Explicit admin authorization for history replacement and exact data-loss limits, plus full/partial HA OS and Container real restore tests, are separate release conditions.

An architecture review and a test definition are not a passing release gate. No code, tests, backup or restoration were performed for this update.


## Crash-atomic SQLite promotion, fsync and recovery journal release gates — 2026-11-06

[Official source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) and [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) add 80 NOT_RUN cases and 20 OPEN technical gates. Release cannot claim crash-safe restore until it demonstrates that no open SQLite database or hot WAL/journal was renamed/deleted, every executor/connection is positively closed before source switch, source and destination have separate namespaces, file and parent directory fsync behavior is correct on the actual HA OS filesystem, one small pointer is durably selected, journal revisions are crash-consistent, and startup resolves pointer/journal discrepancies without blind rollback or repeated promotion.

Required synthetic fault injection: fail at every journal/SQLite copy/destination closure/metadata publish/pointer replacement/reconcile/old-generation GC edge; power-cut and SIGKILL are separate from normal async cancellation. Also test wrong-source symlinks, network mounts, disk-full and private diagnostics; continued backend admin approval/ACL and independent HA Config Entry/physical-console/PSN identity revalidation. A complete old HA config restore may replace all pointers and generations simultaneously and cannot recover newer missing commits. These conditions do not supersede existing immutable snapshot archive consistency/backup hook and release authorization gates. Product-level Hub/Archive was accepted; the generation-pointer strategy remains proposed, not implemented.


## Recovery-Hold bootstrap and positive SQLite worker closure release criteria — 2026-11-06

[Source audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md) and [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md) introduce 80 NOT_RUN tests and 20 OPEN gates. The release cannot advertise self-recovering historical data if recoverable DB corruption makes the accepted Hub/Archive entry permanently SETUP_ERROR/SETUP_RETRY with no panel/Repairs. A deliberately LOADED Hub with internal RECOVERY_HOLD and a global DENY_WRITE gate is a preferred untested design; genuine fatal control-plane/config-entry migration errors must remain visible as native HA errors.

Require multi-entry startup coverage with global controller constructed before any source can persist; runtime_data before awaited entity forwarding; one panel/API; accurate source observation vs durable historical gap state; no unnecessary PSN reauth or PS5 control under identity conflict. Future worker implementation MUST demonstrate positive terminal connection/worker closure with cancellation, a running ThreadPoolExecutor Future, aiosqlite queued work, SQLITE_BUSY, long queries, disk full, Core pre-stop shutdown and failed Config Entry unload. A cancelled task, sqlite3.interrupt result or timeout is never adequate evidence to switch an SQLite generation pointer. Old WAL and journal must remain intact. Both W1 stdlib and W2 aiosqlite are unselected; actual linked SQLite version and release packaging require verification. No runtime/code/tests/hardware support inferred from source.


## Degraded capability policy and SQLite 0.22.x worker close release gates — 2026-11-06

[Source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) and [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) introduce 80 NOT_RUN cases and 20 OPEN gates.

Before enabling real source/control or historical persistence, prove a common backend operation policy across one Hub and multiple console/account Config Entries. Entity.available and hiding frontend buttons are not sufficient guards: test direct Home Assistant services, automation/entity methods, stale WebSocket commands, unauthorized users, identity conflicts and stopped/hung worker states. No historical writes during RECOVERY_HOLD; source-only UNSAVED LAN state, power controls during Hold and PSN refresh under Hold are separately open product decisions, with conservative power/Remote Play DENY as the research candidate. A separately verified read-only archived snapshot must not share unverified live SQLite handles.

Before ADR-0015 generation promotion, confirm every SQLite connection/reader/backup/worker has closed with a supported positive terminal contract. Pinned aiosqlite v0.22.0/v0.22.1 changed from Connection(Thread) to private worker-thread ownership; v0.22.1 stop/close Future notification precedes actual worker loop exit and must not be mistaken for a public Thread.join guarantee. Running ThreadPoolExecutor jobs are not cancelled by Future.cancel; sqlite3.interrupt is not close/COMMIT receipt. Fault injection must cover queue cancellation, a blocked statement, a long-running COMMIT, repeat shutdowns, reader connections, lost receipt, disk full and HA OS shutdown/power loss. If worker terminality cannot be verified, remain FAILED_UNSAFE_TO_REOPEN and never create a second active writer. No library approved and no platform release is qualified.


## First-boot explicit ledger genesis and no-silent-reset release criteria — 2026-11-06

[SQLite/HA/Python source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018 PROPOSED](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md), and [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) introduce 80 NOT_RUN scenarios and 20 OPEN gates.

Release must prohibit SQLite create-capable opens on an expected existing history path, including during setup, migration, health checks, failed restoration or recovery. Only a current administrator CREATE_NEW_HISTORY intent after bounded reliable inventory and a durable process-global provisioning lease may create a unique staged generation. Confirm SQLite read/write effective mode rather than treating successful READWRITE open as proof of a writable file. Root/mount/permission/symlink/corrupt/missing journal/snapshot/legacy evidence cannot be interpreted as a fresh installation, and existing old WAL/journal must never be removed to force creation.

Hub Config Entry creation via native Config Flow with reserved unique ID and duplicate-flow abort is separate from history genesis; manifest-wide single_config_entry must not exclude additional physical-console/PSN entries. An interrupted CREATE_INTENT or valid partial stage is reconciled idempotently, preserving provision_op_uuid/ledger_uuid and never creating a second history after lost UI acknowledgment. Validate staged schema, foreign keys, close, pointer and ledger/entry associations before enabling DURABLE_WRITE. Tests must inject full/partial HA OS backup restore, old Hub entry and missing data, retained archive after Hub removal, disk-full, mode=rw missing path, rwc unsafe destination, external mount, alternate HA Container path, two-admin create/import races and legacy flat DB migration. A no-local-history status is not proof a user never owned old data. No test has been executed.
