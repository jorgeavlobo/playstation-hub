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
