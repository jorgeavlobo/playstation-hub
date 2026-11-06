# Official sources and external references

**Status:** Living index — 2026-11-05.

The canonical historical source register (DOC-001 through DOC-080) remains in [ARCHITECTURE_GUIDE.md](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md). Protocol-specific external source URLs appear in [docs/protocols](../protocols/README.md).

## Official documentation roots

- https://www.hacs.xyz/
- https://www.hacs.xyz/docs/use/
- https://www.hacs.xyz/docs/publish/
- https://www.hacs.xyz/docs/contribute/
- https://developers.home-assistant.io/
- https://contributors.home-assistant.io/
- https://www.home-assistant.io/

## Maintenance policy

Record title, canonical URL, publisher, reviewed date, source revision, evidence status, decisions, and change triggers. Never present third-party reverse-engineered code as official Sony documentation. Preserve moved URLs and mark superseded advice.

## Current quality, runtime and Marketplace source set — 2026-11-05

The [second official-source review](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md) inventories 29 official source entries (with one network-discovery cross-reference) and 22 prioritized findings. The [54-rule internal applicability matrix](internal-quality-scale-applicability.md) maps all 20 Bronze, 10 Silver, 21 Gold and 3 Platinum Core Quality Scale rules without claiming a formal tier for this custom Marketplace integration.

**Canonical current source categories:**
- https://contributors.home-assistant.io/core/quality-scale/rules/ — current rules
- https://contributors.home-assistant.io/core/integrations/discovery/ — DHCP/config flow ownership
- https://contributors.home-assistant.io/core/integrations/network-discovery/ — shared network services
- https://contributors.home-assistant.io/core/integrations/fetching-data/ — coordinator, cache and parallelism
- https://contributors.home-assistant.io/core/quality-scale/runtime-data/ — typed per-entry runtime
- https://contributors.home-assistant.io/core/quality-scale/action-exceptions/ — typed user/device errors
- https://contributors.home-assistant.io/core/integrations/diagnostics/ — redaction and test snapshots
- https://contributors.home-assistant.io/core/integrations/system-health/ — loaded entries only
- https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/ — separate flows
- https://contributors.home-assistant.io/marketplace/reference/validation/ — install-time limits and checks

**Version boundary:** The current online docs may evolve; verify exact API behavior against pinned Core 2026.11.0 source and retest after supported release upgrades. An audited official rule is not automatically applicable to a Marketplace custom project or proof of test completion.

## Home Assistant 2026.11 pinned multi-console runtime sources — 2026-11-05

The [pinned multi-console source audit](../research/ha-core-2026-11-multi-console-runtime-source-audit.md) and [SPEC-008](../specifications/SPEC-008-multi-console-runtime-and-coordinator-lifecycle.md) inventory the exact code paths and lifecycle contracts for native discovery and always-on console observations. New pinned Core references:
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/update_coordinator.py — first/last listener scheduler, pref_disable_polling, first refresh, push, error handling
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — DHCP generic fallback, async_on_unload, entry-owned task lifecycle, forward/unload setup locks
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/discovery_flow.py — centralized HA discovery flow helper
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/dhcp/__init__.py — built-in DHCP candidate/watchers
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/config_flow.py — cloud account config flow without dedicated DHCP step
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/shelly/config_flow.py — official multi-device discovery and host updating reference
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/shelly/__init__.py — native per-entry runtime/cleanup reference
- https://contributors.home-assistant.io/core/quality-scale/test-before-setup/ — intentionally offline device handling
- https://contributors.home-assistant.io/core/integrations/fetching-data/ — coordinator and entity listener-driven polling
- https://contributors.home-assistant.io/core/quality-scale/config-entry-unloading/ — failed setup / unload cleanup

These source facts guide architecture design; no PlayStation Hub test has been executed.


## Official SQLite, Python and pinned Supervisor recovery sources — 2026-11-06

**New source-backed reference:** [Crash recovery and restore provenance research](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md), with [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md). Reviewed official upstream SQLite transaction/WAL/backup/corruption and Python sqlite3 documentation, and exact Core 2026.11.0 / Supervisor SHA 69848689 backup and restore code. Upstream source confirms the rare WAL-reset corruption bug fix in 3.51.3 (2026-03-13) and selected backports; do not infer installed HA OS runtime library from Python version alone.

- https://www.sqlite.org/wal.html — WAL safety, checkpoints, 2026 WAL-reset bug
- https://www.sqlite.org/changes.html — patched SQLite release history
- https://www.sqlite.org/backup.html — Online Backup API snapshots
- https://www.sqlite.org/lang_transaction.html — atomic transaction and reader/writer semantics
- https://www.sqlite.org/howtocorrupt.html — crash recovery and corruption risks
- https://www.sqlite.org/pragma.html — FULL/NORMAL, integrity_check, foreign_key_check
- https://www.sqlite.org/rescode.html — SQLite failure classification
- https://docs.python.org/3.14/library/sqlite3.html — Python wrapper, linked SQLite, Connection.backup
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py — Core's separate restore entry point
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py — Supervisor-only backup hooks
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — full/partial config copy and Recorder-only exclusion

**Not validated:** installed SQLite C library version, exact HA OS restore session, operational snapshot consistency, dynamic archive-only UI, any executable test. Source findings do not constitute an approved decision or product capability.


## Official storage, configuration, Marketplace and backup source review — 2026-11-06

[Source-backed storage and archive entry audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md) with [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) and [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md). The following distinguish confirmed official framework behavior from untested PlayStation Hub proposals:

- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py — hass.config.path, cache_path and cache exclusion purpose
- https://contributors.home-assistant.io/architecture/core/registries/ — HA Store and .storage as native internal data
- https://contributors.home-assistant.io/marketplace/guides/integrations/ — custom integration update, persistent_directory
- https://contributors.home-assistant.io/marketplace/reference/hacs-json/ — persistent_directory versioned key
- https://www.home-assistant.io/common-tasks/general/backups/ — configuration, Recorder history, share/media/apps selection, encrypted backups
- https://www.home-assistant.io/common-tasks/os/ — host-side Supervisor storage; never hardcode host-only path in a Core component
- https://contributors.home-assistant.io/core/integrations/config-entries/ — one persisted Config Entry per instance, loaded at startup
- https://contributors.home-assistant.io/frontend/architecture/routing-and-panels/ — Core registration owns sidebar panels
- https://contributors.home-assistant.io/core/integrations/backup/ — backup.py pre/post hooks (not proof that post always runs)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/integration_platform.py — integration platforms loaded when the integration is active
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py — concurrent pre-hook gather and collective failure
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py — Supervisor backup/start/end handoff
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — begin_backup before post-hook finally; config backup/restore and Recorder-specific exclusion
- https://www.sqlite.org/backup.html — internally consistent SQLite Online Backup API snapshot

**Evidence boundary:** Pinned source proves a potential unmatched successful pre-hook on collective failure, NOT that PlayStation Hub exists or that a production freeze is occurring. File inclusion in a standard backup is not proof of consistent custom DB restore. Archive-only Hub entry and custom data path are maintainer-unapproved proposals.


## Official immutable SQLite snapshot protocol and backup filter audit — 2026-11-06

The [new source-pinned audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md), [ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md) and [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md) establish the current evidence baseline:

- https://www.sqlite.org/backup.html — SQLite Online Backup API, copy consistency, concurrency caveats
- https://www.sqlite.org/c3ref/backup_finish.html — backup_init/step/finish, source/destination connection ownership, restart under writes, busy/fatal results
- https://www.sqlite.org/uri.html — immutable=1 only truly immutable files; skipped lock/change detection
- https://www.sqlite.org/pragma.html — WAL checkpoints, FULL/NORMAL, integrity_check and foreign_key_check
- https://www.sqlite.org/lang_vacuum.html — VACUUM INTO as an alternative consistent copy; incomplete output/crash concerns
- https://docs.python.org/3.14/library/sqlite3.html — Connection.backup, pages/progress/sleep API, linked runtime version
- https://contributors.home-assistant.io/core/integrations/backup/ — pre/post preparation hooks; no custom archive-exclude return contract documented
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py — pre-hook gather/exception behavior and generic archive filters
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/const.py — fixed generic exclusion list
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py — authenticated Supervisor backup/start/end bridge
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/knx/backup.py — existing SQLite pre/post backup precedent; not proof against inter-hook failure
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/backup.py — Recorder's own pre/post lock semantics
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — pinned config backup filters, copying and restore

**Evidence boundary:** The absence of a custom per-file archive exclude option has been established only for the documented pre/post hook and the inspected pinned implementation, not as an eternal impossibility across all HA versions or external backup tools. Snapshot publication tests, actual HA OS archive contents and automatic restoration remain unverified. Maintainer product approval is recorded separately in [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06).


## Pinned Home Assistant OS/Core storage-mount and restore scope sources — 2026-11-06

[Official-source restore-authority audit](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md), [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md), [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md) preserve exact upstream evidence for why app-owned SQLite in config and separately mounted data roots behave differently:

- https://www.home-assistant.io/common-tasks/general/backups/ — default HA OS automatic backup includes configuration; normally excludes share/media, whose selection is independent.
- https://www.home-assistant.io/common-tasks/os/ — OS data directory, external storage/mount usages and backup vs share/media purposes.
- https://contributors.home-assistant.io/core/integrations/backup/ — backup destinations via Backup Agent and preparation/resumption via pre/post; no custom source file-exclusion return contract shown.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py — config root path/cache path.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py — Core archive exclusions and callback coordination.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/const.py — source-specific standard exclusions.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py — Core .HA_RESTORE route, not assumed universal Supervisor signal.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py — Core config/share/media bind-mount list.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — config backup/restore file selection and replacement.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py — folder backup/restore and network mount handling.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py — independent full/partial restore selections.
- https://www.sqlite.org/wal.html — WAL and filesystem restrictions.
- https://www.sqlite.org/backup.html — coherent SQLite online snapshots.

**Evidence limits:** no code, HA OS trial, backup archive inspection or hardware test. Fixed commit/tag source does not prove the user's installed versions. No documented source filter in this pinned pre/post mechanism is not a universal claim about future Home Assistant or all backup programs.


## Official administrator recovery, Repairs and Supervisor restore-progress sources — 2026-11-06

[New source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) and [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) catalog the following pinned source and official contributor documentation:

- https://contributors.home-assistant.io/frontend/extending/websocket-api/ — custom WebSocket commands, admin decorator, subscriptions and frontend callWS.
- https://contributors.home-assistant.io/core/internals/websocket-api/ — authenticated WS protocol, commands, context, errors.
- https://contributors.home-assistant.io/core/internals/permissions/ — backend user permission checks.
- https://contributors.home-assistant.io/core/integrations/repairs/ — global/per-entry Repair issue lifecycle; 2026.11 supports config_entry_id; new subentry argument belongs to later version.
- https://contributors.home-assistant.io/core/integrations/diagnostics/ — sensitive data omission and test snapshots.
- https://contributors.home-assistant.io/security/guides/integrations/ — secure integration entry points.
- https://contributors.home-assistant.io/core/integrations/backup/ — backup destinations vs pre/post preparation and resumption.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py — admin guard and independent scheduled async handler.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/connection.py — subscription cleanup on disconnect.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/__init__.py — global name-to-handler registration.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/issue_registry.py — config_entry_id optional and global Repair API at source pin.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py — RESTORE_JOB_ID_ENV and restore progress resumption.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py — RestoreBackupEvent, async_subscribe_events, state.
- https://github.com/home-assistant/core/blob/2026.11.0/tests/components/hassio/test_backup.py — official restore-progress-after-restart tests.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py — Supervisor passes job ID to Core on a restore.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/core.py — restore-job environment passed to Core launch.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py — distinct Core .HA_RESTORE route.

**Correction to older "no restore signal" statements:** The source shows a real first-party Supervisor/Core restore-progress path, but does not prove a universal supported custom-integrations restore intent providing SQLite snapshot digest and pre-data-open ordering. Reviewed custom pre/post backup hooks still have no application-specific archive file-exclusion return contract. No external HA issue/PR was created.


## Official SQLite, Python and Linux atomic recovery sources — 2026-11-06

[Crash atomicity source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) and [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) add the following upstream references:

- https://www.sqlite.org/howtocorrupt.html — official warnings against unlinking/renaming an open database; hot WAL and rollback journal must remain paired with original filename; multi-connection file locks.
- https://www.sqlite.org/atomiccommit.html — SQL atomic commit and filesystem synchronization assumptions; SQLite does not provide an application transaction spanning filesystem pointer and HA Config Entries.
- https://www.sqlite.org/wal.html — WAL lifecycle, checkpointing, last-connection cleanup and persistent WAL after unclean termination.
- https://www.sqlite.org/backup.html — complete Online Backup API as a consistent source for a separately verified working generation.
- https://docs.python.org/3/library/os.html#os.replace — os.replace is an atomic POSIX rename of ONE file/directory path on success, but cross-filesystem moves may fail; not an atomic multi-file DB+WAL transaction.
- https://man7.org/linux/man-pages/man2/fsync.2.html — file fsync does not necessarily guarantee the containing directory entry is durable; directory fsync required under Linux model.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — independent HA Config Entry/registry lifecycle and per-entry locks.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py — ordered global shutdown job and bounded stages.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — whole-config restoration can replace app pointer, recovery journal and generation files with older bytes.

**Evidence status:** Source mechanisms are documented; pointer+generation model is proposed, not an official HA feature. No supported HA OS file-system atomicity test, SIGKILL, power-failure simulation, SQLite worker validation or actual backup/restore was performed.


## Recovery Hold and SQLite worker cancellation reference set — 2026-11-06

The [Core/Python/third-party worker deep audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](../decisions/ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md), and [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md) record:

- https://contributors.home-assistant.io/core/integrations/config-entries/ — native entry states, domain and entry setup, runtime_data, unloading and long-running task ownership.
- https://contributors.home-assistant.io/core/integrations/setup-failures/ — ConfigEntryNotReady vs ConfigEntryError/AuthFailed; platform-level exceptions do not retry parent integration.
- https://contributors.home-assistant.io/core/integrations/repairs/ — global and Config Entry-scoped issue lifetime; Config Entry deletion hides/deletes scoped issue.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — pinned per-entry locks, setup/unload, awaited platform forwards, ten-second unload task wait, entry-owned background tasks.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py — forwarded per-entry platform setup.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/frontend/__init__.py — panel registration duplicate route policy.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py — one global pre-stop shutdown job before background task cancellation.
- https://docs.python.org/3.14/library/concurrent.futures.html — running Future.cancel and cancel_futures cannot stop running thread; shutdown(wait=False) not joined.
- https://docs.python.org/3.14/library/sqlite3.html — check_same_thread, Connection.interrupt, context manager commit/rollback vs connection close.
- https://docs.python.org/3.14/library/asyncio-eventloop.html — run_in_executor and executor shutdown semantics.
- https://aiosqlite.omnilib.dev/en/v0.21.0/api.html — candidate aiosqlite async connection/close/backup API, not approved dependency.
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py — pinned third-party single-thread queue: SQL enqueued before await, close queued behind tasks, stop sentinel.
- https://www.sqlite.org/wal.html — WAL connection lifecycle.
- https://www.sqlite.org/howtocorrupt.html — open DB rename and hot journal mismatch hazards.

**Evidence boundary:** Python and third-party implementation guarantees were read from documentation/source, not benchmarked or validated as safe HA OS behavior. Neither W1 stdlib executor nor W2 aiosqlite is selected/installed. No code or tests.


## Home Assistant operation guards and aiosqlite versioned worker lifecycle — 2026-11-06

[Degraded capability/SQLite worker source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](../decisions/ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md), [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) extend source references:

- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — native entry state is separate from application health/permission.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity.py — Entity.available is current presentation availability.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/service.py — entity-service backend registration, admin_only support, independent action dispatch.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/entity_platform.py — entity service registration delegation.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py — require_admin and async handler work.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py — early shutdown jobs and background task cancellation timing.
- https://docs.python.org/3.14/library/concurrent.futures.html — cannot cancel already-running ThreadPoolExecutor work; wait=True terminal shutdown semantics.
- https://docs.python.org/3.14/library/sqlite3.html — interrupt, check_same_thread, sqlite_version, connection closure.
- https://github.com/omnilib/aiosqlite/blob/v0.21.0/aiosqlite/core.py — Connection subclasses Thread, queued calls.
- https://github.com/omnilib/aiosqlite/blob/v0.22.0/aiosqlite/core.py — private thread ownership and queued stop.
- https://github.com/omnilib/aiosqlite/blob/v0.22.1/aiosqlite/core.py — stop(), close, worker sentinel, ResourceWarning.
- https://aiosqlite.omnilib.dev/en/stable/changelog.html — 0.22.x API/worker changes; not selected for PlayStation Hub.
- https://www.sqlite.org/wal.html — multiple reader/writer and WAL connection lifecycle.
- https://www.sqlite.org/howtocorrupt.html — hazards of renaming open SQLite database or deleting hot sidecars.

**Evidence boundary:** Version-tagged third-party source is not proof that aiosqlite 0.22.1 is installed in Core or on user's HA OS. The worker terminal contract, accepted degraded controls and safe automatic restoration are NOT established by source inspection. No code/tests executed.


## First-run Config Flow uniqueness and SQLite non-creating database opening — 2026-11-06

The [first-boot official-source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md), and [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) add:

- https://www.sqlite.org/uri.html — URI filename modes ro, rw, rwc and immutable caveats; no-create versus create.
- https://www.sqlite.org/c3ref/open.html — sqlite3_open_v2 READONLY, READWRITE, READWRITE|CREATE, and historical READWRITE read-only fallback on permissions.
- https://www.sqlite.org/c3ref/db_readonly.html — actual connection read-only mode validation.
- https://docs.python.org/3.14/library/sqlite3.html — sqlite3.connect with URI parameter, existing-only open and linked runtime version.
- https://docs.python.org/3.14/library/os.html — EAFP file operations, mkdir exclusive/exists error, os.open O_EXCL/O_NOFOLLOW where supported, permission and file errors.
- https://contributors.home-assistant.io/core/integrations/config-flow/ — user-confirmed Config Flows, stable unique IDs, async_set_unique_id and duplicate abort.
- https://contributors.home-assistant.io/core/quality-scale/unique-config-entry/ — forbid IP/name as unique hardware identity; duplicate entry quality rule.
- https://contributors.home-assistant.io/core/integrations/config-entries/ — persisted Config Entry data vs ephemeral runtime_data, setup/migrations, enabled/disabled.
- https://contributors.home-assistant.io/architecture/core/registries/ — native HA Store and .storage files distinct from private SQLite.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py — pinned Config Flow duplicate and entry save behavior; no cross-system transaction.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/storage.py — Store versioned data and delayed save, not an atomic SQLite+entry commit.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py — config-root and evictable cache path.
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py — config restore can replace previous local evidence.

**Source boundary:** SQLite opening and HA Config Flow uniqueness are official facts, but the proposed CREATE_NEW_HISTORY consent, journal and unique staging protocol remain unimplemented and untested. No server-side file evidence from the user's actual HA OS has been collected.


## Legacy develop branch, Supervisor App storage and targeted MQTT Discovery retirement — 2026-11-06

The [direct legacy develop audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md), [ADR-0019](../decisions/ADR-0019-legacy-history-provenance-and-cutover.md) and [SPEC-019](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md) list exact source files supporting future migration from old App and Lovelace:

- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/config.yaml — source App v0.5.0, slug, aarch64, /data default, MQTT service.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/config.py — options.json parse and single source/player config; never import credentials.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py — legacy SQLite schema v1–3, WAL, auto-creating/migrating constructor, sessions/events/checkpoints/singleton.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/models.py — ConsolePower, ActivityType, EventType, UsageSession.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/session_tracker.py — checkpoint recovery and continuity policy defaults.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/main.py — actual runtime max_gap_seconds=30.0, one selected player.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/usage_statistics.py — UTC half-open sessions and Europe/Lisbon/DST reporting.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/ps5_history_index.py — 36-month index is presentation/coverage view.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/mqtt_publisher.py — ten retained synthetic MQTT monitoring sensors.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js — old Lovelace card version 1.1.2 with hardcoded old entity IDs.
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/services/ps5-history-client.js — MQTT request/response via HA WebSocket; new native transport differs.
- https://www.home-assistant.io/integrations/mqtt/ — retained Discovery, republished ghost entities, exact-topic empty retained cleanup.
- https://developers.home-assistant.io/docs/apps — Home Assistant App/add-on architecture and Supervisor-managed configuration.
- https://www.sqlite.org/backup.html — coherent SQLite Online Backup copy, not raw live main file copy.
- https://www.sqlite.org/wal.html — hot WAL sidecar and restore integrity.

**Boundaries:** Reviewed only sanitized repo source and public official docs, NOT the installed private App data, actual entity registry or broker. The old synthetic device identifier ps5_monitoring_service is not a verified physical PlayStation ID. No migration, MQTT deletion, or tests performed.


## Official SQLite relational schema, partial indexes and reporting source review — 2026-11-06

[Greenfield SQLite v1 official-source audit](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md), [ADR-0020](../decisions/ADR-0020-greenfield-sqlite-v1-data-model.md), [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md) extend the source register:

- https://www.sqlite.org/foreignkeys.html — per-connection foreign_keys enabling; named PK/UNIQUE foreign-key parents.
- https://www.sqlite.org/lang_createtable.html — column definitions, NOT NULL, CHECK, PRIMARY KEY, named rowid behavior and null semantics.
- https://www.sqlite.org/lang_createindex.html — UNIQUE indexes and multiple NULLs; composite index behavior.
- https://www.sqlite.org/stricttables.html — STRICT table typing and minimum SQLite 3.37.0 compatibility.
- https://www.sqlite.org/partialindex.html — subset indexes and partial UNIQUE for active/open rows, not temporal overlap validation.
- https://www.sqlite.org/lang_upsert.html — uniqueness-based upsert; FK and CHECK failures remain errors.
- https://www.sqlite.org/lang_transaction.html — SQL transaction boundary and one-writer semantics.
- https://www.sqlite.org/wal.html — WAL concurrent readers, single writer, local filesystem and 2026 reset fix issue.
- https://www.sqlite.org/backup.html — internally consistent completed SQLite backup API destination.
- https://www.sqlite.org/pragma.html — foreign_key_check, integrity_check, user_version/application_id, busy settings.
- https://www.sqlite.org/lang_analyze.html — version-aware PRAGMA optimize and query planner statistics.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/db_schema.py — HA's Recorder owns its own ORM schema, not our custom SQLite tables.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/statistics.py — HA statistics have distinct source/retention and should not be used as hidden app ledger.

**Evidence limits:** SQLite features are documented by upstream, but linked SQLite C library version, Home Assistant OS filesystem, database performance, title and Sony API authorization and exact PlayStation Hub physical schema are not validated. ADR-0020 and SPEC-020 are designs, not executable SQL or HA runtime behavior. Legacy develop SQLite records are fictional and were never deployed; no data migration or backwards old-schema support is required.

## Temporal reducer and session-coverage official-source register — 2026-11-06

**Research:** [Observation-to-session reducer audit](../research/observations-to-sessions-temporal-reducer-source-audit-2026-11.md). **Decision:** [ADR-0021 PROPOSED](../decisions/ADR-0021-observation-to-session-reducer-and-temporal-coverage.md). **Tests:** [SPEC-021, 96 NOT_RUN / 24 OPEN/BLOCKED](../specifications/SPEC-021-observation-to-session-state-machine-and-replay.md).

| Publisher / official resource | Link | Verified research boundary |
| --- | --- | --- |
| Sony PlayStation | https://www.playstation.com/en-gb/support/hardware/ps5-ps4-power-indicator-lights/ | LED/physical modes are **not** LAN UDP status code proof |
| Sony PlayStation | https://www.playstation.com/pt-pt/support/hardware/ps5/ | Rest mode background behaviors are not verified active gameplay |
| Home Assistant | https://www.home-assistant.io/integrations/playstation_network/ | Account/provider presence is not canonical local console identity |
| Home Assistant | https://www.home-assistant.io/docs/configuration/state_object/ | HA current entity values/unknown/unavailable are not full durable session history |
| Home Assistant Contributors | https://contributors.home-assistant.io/core/integrations/fetching-data/ | DataUpdateCoordinator/push lifecycle requires explicit monitor ownership |
| SQLite | https://www.sqlite.org/lang_transaction.html | One writer; explicit transaction to commit evidence/checkpoints together |
| SQLite | https://www.sqlite.org/isolation.html | Readers see committed snapshot; report query must pin a consistent cursor |
| SQLite | https://www.sqlite.org/lang_upsert.html | UPSERT unique conflict cannot replace application id+digest receipt contract |
| SQLite | https://www.sqlite.org/foreignkeys.html | Enable/check each connection; row overlap requires application-level invariant |
| SQLite | https://www.sqlite.org/wal.html | WAL, concurrency/checkpoints, and 2026 WAL reset bug caveats |
| SQLite | https://www.sqlite.org/rescode.html | COMMIT/SQL failures require correct error and uncertainty handling |
| SQLite | https://www.sqlite.org/lang_savepoint.html | Inner release != outer commit; maintain one final durable boundary |
| Python 3.14 | https://docs.python.org/3.14/library/time.html | Monotonic runtime freshness, not durable cross-restart absolute clock |
| Python 3.14 | https://docs.python.org/3.14/library/zoneinfo.html | IANA calendar reporting and DST-aware UTC bounds |

**Evidence limits:** This review did not verify a real firmware response, an authorized Sony PSN API, an actual Home Assistant OS SQLite runtime, any Python worker, a SQL transaction on user data, or Home Assistant backups. The strict two-point bounded coverage policy and maximum B remain unapproved project choices. The old synthetic develop database remains outside scope.

## Final current research-track evidence set — deterministic replay and correction (2026-11-06)

**Research:** [Replay/correction source audit](../research/deterministic-replay-corrections-and-recovery-closure-audit-2026-11.md). **Technical ADR:** [ADR-0022 PROPOSED](../decisions/ADR-0022-deterministic-replay-and-versioned-corrections.md). **Research stop and empirical owner mapping:** [WP-00B](../architecture/WP-00B-research-freeze-and-implementation-readiness.md).

- https://www.sqlite.org/lang_transaction.html — atomic outer SQL COMMIT/ROLLBACK and one-writer transaction semantics.
- https://www.sqlite.org/lang_savepoint.html — inner RELEASE is not a durable outer COMMIT.
- https://www.sqlite.org/isolation.html — committed snapshot isolation; compare report data at one cursor.
- https://www.sqlite.org/wal.html — live WAL and checkpointing must not be divorced from database backup/recovery.
- https://www.sqlite.org/backup.html — official backup API, candidate coherent stage source requiring actual compatibility proof.
- https://www.sqlite.org/pragma.html — foreign key, integrity and journal/synchronous settings, not semantic game-time proof.
- https://www.sqlite.org/lang_upsert.html — uniqueness conflict behavior, not automatic payload-digest idempotency.
- https://docs.python.org/3.14/library/time.html — process-local monotonic time, not persisted absolute timestamp.
- https://docs.python.org/3.14/library/zoneinfo.html — IANA timezone/DST semantics for replayable reports.
- https://developers.home-assistant.io/docs/development_testing/ — Home Assistant implementation test guidance (may need current-path re-verification when tests start).

**Explicit evidence classification:** Official SQLite/Python documentation supports its named primitives only. The replay protocol, versioned correction model, incident response, automatic restore prohibition and research stopping criteria are PlayStation Hub project designs, **not official Sony/HA/SQLite features** and none has run on user's hardware. Further research only if specific implementation test fails or authoritative source/API changes.

## Pinned implementation-repository source audit — 2026-11-06

**Primary:** [Upstream source comparison](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md); version-pinned GitHub repositories and official HA Core tag below. **Not Sony official protocol documentation:** third-party reverse-engineering projects and package releases must be distinguished from official platform interfaces and runtime/hardware validation.

- https://github.com/dhleong/playactor/tree/a9e72d67a3930a8f06455927edb547a1754ef0ac — TS LAN discovery/wake/Remote Play, parser's non-620-is-awake risk, remoteplay isConnected inversion and standby socket closure.
- https://github.com/FunkeyFlo/ps5-mqtt/tree/7ab3075d276f3eeecd81a3322c72231af8cd51bd — v1.8.1 HA add-on; multi-interface broadcast, shared listener issue, state checking, PSN device-matching heuristic, e2e mock tests.
- https://github.com/chiaki-ng/chiaki-ng/tree/43728af2e639fecb8a7af1cd68c29820a40de973 — current canonical AGPL-3.0 Chiaki-ng source; discovery parses `200/620/UNKNOWN` and optional `running-app-titleid/name`; registration and crypto known-answer source.
- https://github.com/home-assistant/core/tree/2026.11.0/homeassistant/components/playstation_network — official HA PSN account-scoped coordinators, Config Entry, media players and app limitations.
- https://www.home-assistant.io/integrations/playstation_network — official documented 30-second data updates, 300 requests/15min, last-used console status limitation.
- https://github.com/achievements-app/psn-api/tree/1e9d9a806fcd884a4ddee8086bfe92594611da9f — unofficial account presence, device list, played/recent/purchased queries, refresh.
- https://github.com/isFakeAccount/psnawp/tree/fcd7e8334495585b5a8d7502b3b527f34f9d7777 — GitHub **mirror** (Codeberg primary), unofficial Python PSN wrapper.
- https://pypi.org/project/psnawp/3.0.3/ — published version pinned by HA Core, not necessarily current mirror HEAD.
- https://github.com/Emkraan/homeassistant-playstationnetwork/tree/aecbd580c39cc00692f06cec80df4b17c02e1e63 — custom HA token rotation/compat wrapper for comparison, not official physical-console integration.
- https://pypi.org/project/playdirector/0.4.2/ — Python package current as-of audit, now GPL-3.0-only and changed public API; old 0.3.0 MIT documentation is stale for dependency adoption.
- https://github.com/iharosi/ps5-remoteplay — separate AGPL-3.0 Python PS5 port with documented byte-exact synthetic vectors (README-only evidence; not audited or selected as runtime dependency).

**Source boundary:** Existence of optional `running-app-titleid`/name in parsers is evidence of a *possible* console LAN metadata source, not verified appearance on a specific PS5 firmware or exact active gaming time. Never copy GPL/AGPL protocol code or key tables into a different licensed integration without explicit licensing analysis. No production code or hardware test executed.

## Secondary source-level protocol triangulation and PSN runtime study — 2026-11-06

**Research index:** [Pinned source-audit, LAN title and PSN runtime comparison](../research/upstream-protocol-triangulation-and-lan-title-forensics-2026-11-06.md), with source/line-referenced differences and planned test trace IDs.

- https://github.com/iharosi/ps5-remoteplay/tree/61e1f7dc065a77f7e8b1de5057889a08b0208d9d — AGPL-3.0 Python port of playactor, not an independent firmware oracle; ported byte-vector tests and permissive status decoding; standby closes/times out without independent 620 confirmation.
- https://github.com/ktnrg45/pyremoteplay/tree/a127422c2599034ec4428919bbaf8b4db278cd75 — GPL-3.0 archived 2022 Python Remote Play/DDP, recognizes running-app name and unusual colon parsing.
- https://github.com/iharosi/ps5-wake/tree/4806b2846e0a5c82ca5ad009731087ead6b9bccb — GPL-3.0 PS5-oriented C DDP probe parses `running-app-name` and `running-app-titleid`; 200/620/unknown display handling.
- https://github.com/leonanluppi/chiaki-km/tree/9f84d0baf82ac87072781f7ad0a909291c46e2b5 — AGPL-3.0 Chiaki fork that uses local discovery app metadata to select controller profiles; CUSA backward-compatible title examples, no proof of all-firmware compatibility.
- https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/discovery/messages.ts — split-on-all-colons / CRLF hazards and permissive status classification.
- https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c — more conservative 200 READY / 620 STANDBY / unknown status and optional LAN app fields.
- https://github.com/isFakeAccount/psnawp/blob/fcd7e8334495585b5a8d7502b3b527f34f9d7777/src/psnawp_api/core/authenticator.py — inspected synchronous access-token refresh method and expiring-token state.
- https://github.com/Emkraan/homeassistant-playstationnetwork/blob/aecbd580c39cc00692f06cec80df4b17c02e1e63/custom_components/playstation_network/compat.py — per-account guard, refresh margin and OAuth error compatibility workaround; not a template to monkey-patch globally.
- https://github.com/Emkraan/homeassistant-playstationnetwork/blob/aecbd580c39cc00692f06cec80df4b17c02e1e63/custom_components/playstation_network/coordinator.py — refreshed token persistence without lifecycle reload.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/playstation_network/helpers.py — selects first provider title within primary platform account session; no unique physical LAN device identity.
- https://github.com/achievements-app/psn-api/blob/1e9d9a806fcd884a4ddee8086bfe92594611da9f/src/graphql/operationHashes.ts — reversed persisted GraphQL hashes, not a supported stable licensed API contract.

**Evidence boundary:** Third-party parser field recognition and code tests are not Sony official firmware support or user hardware captures. GPL/AGPL reference code/test assets are not approved for verbatim reuse; no Sony API permission is implied. No actual PlayStation Hub executable work was performed.

## Native Python / Home Assistant first-party runtime feasibility — 2026-11-06

**Maintainer decision:** [First-party dependency sovereignty](../architecture/first-party-dependency-sovereignty-policy.md), with [source-pinned implementation audit](../research/first-party-protocol-implementation-and-runtime-boundaries-2026-11-06.md), now takes precedence over historical proposed runtime library choices.

- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/network/__init__.py — native async_get_adapters, async_get_ipv4_broadcast_addresses, async_get_enabled_source_ips. When only default interface enabled, broadcast helper returns limited global broadcast only; source-specific directed addresses need native adapter info/prefix and stdlib ipaddress.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/aiohttp_client.py — HA-managed async HTTP clientsession, no own installed HTTP package needed.
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/__init__.py — native command registration, collision/owner checks needed.
- https://contributors.home-assistant.io/core/integrations/manifest/ — pip \`requirements\` versus native HA \`dependencies\`, not equivalent.
- https://contributors.home-assistant.io/core/internals/blocking-operations/ — event-loop blocking I/O policy and native HA client session.
- https://docs.python.org/3.14/library/asyncio-protocol.html — native UDP transports, DatagramProtocol.
- https://docs.python.org/3.14/library/ssl.html — TLS wrapper, not generic raw AES cipher.
- https://docs.python.org/3.14/library/crypto.html — hashlib/hmac/secrets, not a raw AES-CFB/CBC interface.
- https://docs.python.org/3.14/library/sqlite3.html — built-in sqlite3, no aiosqlite requirement.
- https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/protocol.ts — source-observed DDP search formatter without explicit NUL.
- https://github.com/chiaki-ng/chiaki-ng/blob/43728af2e639fecb8a7af1cd68c29820a40de973/lib/src/discovery.c — search source and NUL-inclusive \`sendto\`, local source port strategy, parsing and wake.
- https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/remoteplay/crypto/base.ts — HMAC-SHA256 and AES-128-CFB source, **not** an approved dependency or portable code/license grant.
- https://github.com/dhleong/playactor/blob/a9e72d67a3930a8f06455927edb547a1754ef0ac/src/socket/crypto-codec.ts — distinct AES-128-CBC default codec context.

**Evidence limit:** API/source existence and own-protocol feasibility are source evidence, not successful runtime, Sony permission, actual packet capture or AES backend authorization. No user data or console accessed.
