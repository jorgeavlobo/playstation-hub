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
