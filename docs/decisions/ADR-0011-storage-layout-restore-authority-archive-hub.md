# ADR-0011 — Private storage layout, backup/restore authority and Hub/Archive Config Entry

**Status:** PROPOSED — explicit maintainer approval required; no code or tests
**Date:** 2026-11-06
**Domain:** playstation_hub
**Scope:** Where long-term private SQLite history may live; which files can be restored; whether a permanent, zero-console Hub entry should anchor the sidebar.
**Evidence:** [Official-source storage research](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md), [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md)
**Depends on:** ADR-0002 (one panel accepted), ADR-0004 (console identity proposed), ADR-0006 (duration/gap accounting proposed), ADR-0007 (credentials proposed), ADR-0008 (SQLite candidate proposed), ADR-0010 (frontend/API proposed), SPEC-008/009/010.

> This is a **decision proposal**, not a decision record in Accepted status. Documenting a preferred option does not authorize coding, selecting a minimum HA version, or changing current users' data. The maintainer has not yet approved SQLite path, backup method or additional Hub Config Entry.

## 1. Problem statement

The product tracks years of console/game sessions across independently configured physical consoles and optional PSN accounts. A single SQLite ledger and a single sidebar panel should remain usable and safe during Marketplace updates, Home Assistant OS/Container backups, full/partial restore, removal of the last console, normal reboot, and hardware migration.

Prior ADR-0008 proposes a SQLite file outside the integration source; SPEC-009 proposes a shared manager; SPEC-010 documents why old staged snapshots must not automatically replace a valid live DB. These do **not** settle the physical path, archive restore authority or no-device UI lifecycle.

## 2. Requirements

- One HACS/Marketplace integration, one sidebar panel, one process-wide HubController, one DB writer. No MQTT broker, app/add-on, secondary server or external SQL service required.
- App-owned history outside executable custom_components path; file path resolved by a supported HA API.
- Native backup scope and restoration effects explicit for HA OS and Container.
- One unambiguous source for SQL restoration; never invent game/session seconds across an outage or restore.
- Strong protection against data loss due to stale snapshots, corrupt files, conflicting console IDs or partial restore.
- Private, bounded multi-year storage, with user-authorized export/purge and no Sony tokens in the general ledger.
- Archive remains useful even after individual physical consoles are removed, if the user retains appropriate integration configuration.
- No false promise that backup means consistent multi-file SQLite snapshot, or that restoring an old archive can recover post-backup changes.

## 3. Option 1 — Private SQLite subdirectory within HA config

**Preferred first-release location candidate:** a private app-specific subdirectory resolved by hass.config.path, e.g. <config>/.playstation_hub/ledger/history.sqlite3. This is not a Home Assistant standardized application-data directory.

**Pros:** survives ordinary integration source replacement; portable Core/Container path API; covered by configuration archive selection under reviewed Supervisor archive traversal; naturally co-locates with app-specific settings and recovery metadata.
**Cons:** full/selected-partial restoration of older HA configuration can overwrite live files; database inclusion is NOT proof of WAL-consistent copy; staging snapshots and live DB may both be archived; file permissions and disk space require verification.

**Other paths:** Home Assistant Store in .storage is suitable for small versioned JSON, not our detailed SQL ledger; .cache is excluded from backups; /config/www is exposed via frontend static files; /share and /media are separately selected for OS backups and may be accessible through apps/media/network mounts; HACS persistent_directory preserves folder over an update, not over restore. The host /mnt/data/supervisor/... path must never be hardcoded into a Core integration.

**Proposed outcome:** retain Option 1 as the default path candidate until HA OS/Container tests; do not choose PRAGMAs or create the folders yet.

## 4. Option 2 — Outside-config live database + snapshot within configuration

**Long-term candidate**, not default: an externally located, writable, private local DB that does not get copied with Core config; snapshots staged within the selected configuration backup.

**Pros:** live writer need not pause for the full config archive; a snapshot can be safely staged and included; a config-only restore to the same machine could leave newer external rows intact.
**Cons:** backup defaults may omit the external path; not automatically portable across installation types; /share may be accessible from other apps and subject to separate restore; custom external mounts may be network-backed and incompatible with SQLite WAL; restoring old Config Entry mappings can create a newer-ledger/older-config split-brain.

**Required safeguard:** stable ledger UUID plus independently verified Config Entry/physical-console identity epochs; refuse writes until mismatch reconciled. Snapshot back to a new machine still needs explicit import/provenance. No assumption the external path is universally available.

## 5. Backup authority alternatives

| Option | Principle | Availability trade-off | Source-of-truth risk |
| --- | --- | --- | --- |
| A: Quiesce all SQLite connections before and throughout archive | Copy a truly static main DB; no active WAL mutations | Monitoring may lose historic coverage during full backup | Must prove all readers stopped, post-hook failure and backup cancellation |
| B: Online snapshot + manifest, live writer continues | Immutable consistent snapshot generated by SQLite backup API | Better continuity while archiving | Live DB/WAL also copied by Supervisor; trusted restore selector unresolved |
| C: External live DB + snapshot within config | Archive only the staged immutable DB when config chosen | More portability and permissions requirements | Config/identity metadata split-brain on restore |
| D: Raw active DB/WAL copied by Supervisor | No extra implementation | Attractive but unproven | Reject as a consistent-backup guarantee |

**Current preference:** A as the simplest initial proof if its monitoring pauses are acceptable; B as the longer-term goal with explicit restore authority, not an automatically approved evolution. Without real HA OS tests neither A nor B is accepted.

**Hard boundary:** the application must not silently restore a stale staged snapshot when the live DB is valid on a normal restart. If the Supervisor already overwrote the live files with an old archive, those lost commits cannot be reconstructed without another independent backup.

## 6. Permanent Hub/Archive Config Entry alternatives

### A — No additional Hub entry

Console/account entries alone cause integration loading. Historical data remains on disk after last removal, but the panel need not load on next restart. Archived stats might require adding another console or a separate import tool. Low onboarding complexity, weak archive-only UX.

### B — One explicit Hub/Archive entry (preferred for long-term history product)

User adds one permanent logical Hub Config Entry via a normal UI confirmation flow, plus independent physical console/account entries. This logical entry is not a Sony device, not a poller, and is not the physical owner of the shared SQLite service; it is a persistent **integration loading and archive UI anchor**. The process-global controller still owns resources and single panel registration.

Implications:
- One reserved unique ID, dedupe even under simultaneous setup; dedicated discovery flow for additional PS5s rather than generic fallback.
- Hub-only startup should register exactly one panel and make stored history accessible via bounded read leases, without waking a console or issuing Sony credentials.
- Console/account removal cannot remove Hub entry or history; Hub removal while consoles exist cannot stop their runtimes; Hub removed as last entry leaves archive bytes until explicit purge but no guaranteed panel after restart.
- All archival access remains authenticated; initial admin-only scope candidate. No synthetic PlayStation DeviceEntry should be created for a logical Hub.
- Hub entry helps the backup platform be loaded when there are zero consoles, but does not guarantee that every backup route invokes hooks.
- New users must explicitly confirm the logical hub onboarding. Existing legacy Config Entries, if any, must not be mutated or duplicated without a separate migration plan.
- A hub unique ID is not a ledger UUID; restored/foreign data must be validated.

### C — Hub as a subentry of first console

Ties archival lifecycle to a removable physical console and conflicts with multi-console independent ownership. Not recommended without a substantive re-design of root ownership.

**Recommendation for review:** B, but **NOT ACCEPTED** pending explicit approval, flow/backup tests, documentation and migration UX assessment.

## 7. Decision matrix and product consequences

| Question | Current proposal | Evidence needed before Accepted |
| --- | --- | --- |
| Default live DB path | Private app folder under hass.config.path, outside integration source | Permissions, OS/Container backup behavior, HACS upgrade |
| Snapshot staging | Private, generation-scoped, immutable and validated | Crash/rename/fsync and archive membership tests |
| Backup v1 | Full quiescence as initial defensible candidate | Safe timeout, no lost-write promises, HA OS real archive |
| Later backup | Online Backup API with explicit authoritative restore selector | No stale snapshot promotion, live-file conflict handling |
| Restoration | Prefer valid live DB at normal startup; admin-selected replacement on ambiguity | HA restore/first-boot/migration tests |
| External paths | Advanced and off by default | Writable private local filesystem and backup scope |
| Archive-only UX | Explicit logical Hub Config Entry | Core Config Flow and no-console restart tests |
| History removal | Not on console/account/hub unload; explicit separate purge | Retention/privacy and recovery contract |
| First release | Fully functional installation, no blank placeholder | Complete SPEC-005/008/009/010/011 gates |

## 8. How to approve later

This ADR is ready for conceptual review, not automatic approval. An ACCEPTED status requires:
1. Maintainer explicitly chooses whether logical Hub entry is part of first release and which behaviour follows removal of all entries.
2. Maintainer selects a location/backup direction knowing full restore can overwrite newer application data.
3. A separate work package authorizes synthetic and HA OS verification of data path, backup hooks, snapshot and restore; no executable code is authorized by documentation alone.
4. Results and limitations are updated in this ADR and in the Bible before release decisions.

Technical proof does not convert a proposal into a maintainer-approved product choice by itself. Conversely, maintainer acceptance of architecture does not count as tests passed.

## 9. Alternatives rejected at design level

- Mandatory MQTT broker, PS5-MQTT add-on or independent server: conflicts with product scope.
- Integration source directory as the default historical ledger: unreliable update ownership.
- .cache as authoritative history: explicitly not backed up.
- Public /config/www or browser localStorage for sensitive historical data: exposure and lifecycle violations.
- A snapshot automatically restored on every startup merely because it has a valid checksum: can erase newer committed data.
- Treating a restored Config Entry ID, IP address or PSN nickname as proof of physical identity: can reattribute history to the wrong console.
- Promising that excluding the HA Recorder database also excludes the PlayStation Hub database: contradicted by pinned Supervisor filter.

## 10. Traceability

- [Source audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md)
- [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md)
- [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md)
- [ADR-0008](ADR-0008-storage-persistence-and-backup.md)
- [ADR-0010](ADR-0010-sidebar-panel-and-backend-api.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://contributors.home-assistant.io/core/integrations/backup/
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://www.home-assistant.io/common-tasks/general/backups/
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://www.sqlite.org/backup.html

**Status at publication:** PROPOSED. No source code or HA instance altered; no test executed; branch main documentation only and develop frozen.


## 11. Critical source correction — 2026-11-06

**Option A (freeze writes through the entire archive) is now BLOCKED, not preferred for first release, pending a verified safe-resume protocol.** In pinned Core, BackupManager.async_pre_backup_actions gathers all backup integration hooks and raises if *any* fails. In pinned Supervisor, HomeAssistant.backup awaits begin_backup **before** entering the try/finally that calls end_backup. PlayStation Hub could therefore successfully quiesce and never receive post-backup if another integration's pre hook fails. Blind timeout-based resumption could corrupt the archive if an archiver is still active.

**Revised research preference:** immutable Online Backup API snapshot avoids a long-held global write freeze, but safe backup/restoration still depends on handling Supervisor's independently archived live DB/WAL and authoritative snapshot selection. A verified external/private live-data root or explicit administrator-confirmed recovery may be necessary. No method is accepted. See [source audit §15](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md#15-new-p0-discovery--pre-backup-can-succeed-without-matching-post-backup) and [SPEC-011 §9](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md#9-p0-pre-backup-orphan-freeze-cases--2026-11-06). Earlier descriptions of A as an initial preference are superseded by this finding. Maintainer approval and HA OS tests remain required.
