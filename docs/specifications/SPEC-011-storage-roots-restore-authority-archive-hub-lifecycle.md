# SPEC-011 — Storage roots, restore authority, and persistent Hub/Archive lifecycle

**Date:** 2026-11-06
**Status:** PRODUCT_ARCHITECTURE_ACCEPTED_IN_PRINCIPLE; TEST_SPEC_PROPOSED; NOT_IMPLEMENTED; ALL_TESTS_NOT_RUN
**Source audit:** [HA OS data paths and archive entry](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md)
**References:** [SPEC-010](SPEC-010-crash-recovery-restore-provenance-and-archive-access.md), [SPEC-009](SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md).
**Baseline:** Core 2026.11.0, Supervisor SHA 69848689a1e982ebe92d80e344fc086d8af667db, official Home Assistant 2026.11 backup and Marketplace guidance.
**Branch:** main documentation only; develop unchanged.

> All requirements are future PlayStation Hub **candidate** contracts, not existing Home Assistant guarantees. No fixture, code, migration, integration, HACS release or hardware test has been created or executed.

## 1. Purpose and ownership invariants

The product must continue to manage multiple physical consoles and optional PSN accounts, one historical ledger, and one sidebar panel without MQTT/add-ons. This spec resolves *what must be proved* before choosing a durable location, deciding the restoration source and authorizing an archive-only configuration entry.

**ST-01** Single authoritative live history ledger per HA instance and application ledger_uuid. External backup files or old staging files are never simultaneously accepted as writers.

**ST-02** App-owned history must be stored outside HACS-managed integration executable assets; its path is resolved via supported HA runtime API, never by hardcoding HA OS host directories.

**ST-03** The authoritative storage layout must document the actual backup scopes: HA config, Recorder DB, share/media, add-ons and user exports. An installation's selected backup options can omit data.

**ST-04** A file being copied by the backup subsystem cannot mutate unless snapshot consistency is independently guaranteed for that file.

**ST-05** A manifest and staged SQLite snapshot are treated as one logical publication transaction, with generation-specific immutable filenames and validation. An interrupted publication cannot masquerade as a completed generation.

**ST-06** A snapshot's committed cursor and ledger_uuid are read/verified from *the snapshot itself* after copying; do not borrow a possibly later live-writer cursor.

**ST-07** A restored SQLite DB that is valid but older than the prior operational database may be indistinguishable from a naturally quiet ledger without an independent signal. Never promise automatic lossless detection or reconstruction.

**ST-08** A custom application DB inside config is not excluded merely because the user unchecks HA Recorder history in backup.

**ST-09** Any live DB outside config must have a documented backup policy and identity reconciliation with restored Config Entries; a backup of config alone can roll back the entry mapping.

**ST-10** Cached game artwork must be evictable, excluded from authoritative backups, and never a necessary condition for sessions/statistics restore.

**ST-11** Every entry kind has a separate stable Config Flow unique-ID namespace, independent of IP, PSN name and integration control singleton. A hub entry is not a physical device or console monitor.

**ST-12** One panel registration is owned by the integration controller, not by hub/console/PSN entries. A single Hub/Archive entry can maintain it through a reboot with no console, subject to code and HA tests.

**ST-13** Archive-only report requests have authorization, pagination, query leases, immutable read views, and no wake/standby actions or LAN polling.

**ST-14** Removing the final entry never implicitly removes private history; explicit purge/export/removal policy must be user-confirmed.

**ST-15** An incomplete restore, untrusted snapshot or ledger UUID mismatch triggers RECOVERY_HOLD and preserves original bytes. It cannot silently create a new empty ledger, overwrite an existing one, or merge physical console history.

**ST-16** All specified behaviors must work under the supported Home Assistant Core/OS and Container path matrix, not just a developer workstation.

## 2. Candidate directory model and safety gates

Proposed application-private directory under the HA configuration root, resolved through hass.config.path with fixed internally defined path segments:

    <ha-config>/.playstation_hub/
      ledger/history.sqlite3
      backup/pending/<generation>/
      backup/staged/<generation>/snapshot.sqlite3
      backup/staged/<generation>/manifest.json
      backup/staged/<generation>/complete-marker
      recovery/reports/<safe-diagnostic>.json

Not implemented; not an adopted final path. The SQLite WAL and SHM files, if selected, remain owned by SQLite. Transient cache should instead resolve under hass.config.cache_path, not inside the backed-up tree.

**Proposed path-safety validation:** no absolute/user-provided path components, no symlink traversal outside the private root, writable permissions, local filesystem for WAL, sufficient free space for live DB+snapshot+temporary archive, protected metadata, bounded staging. A source path outside HA configuration is a separately authorized advanced option and is not portable by default.

## 3. Backup consistency and restoration authority

### Option A: write quiescence for archive — BLOCKED until safe-resume proof

Pre-backup stops new DB admissions, drains accepted writes, closes all reader/writer connections, checkpoints under safe SQLite runtime and freezes the database until archive completion. If post-backup never arrives, resumption must not silently occur while the archive is still copying; design backup failure/abort/recovery and require a robust lifecycle handshake. Hardware probes may continue only if historical omission is represented as explicit UNSAVED/gaps, without unbounded buffering.

### Option B: stage immutable Online Backup API snapshot

Pre-backup creates a consistent destination snapshot, reads cursor and ledger identity from that snapshot, validates and publishes a manifest; live DB may resume. However the Supervisor may still archive raw live SQLite DB/WAL files from the same config tree. The destination snapshot alone is not a reliable restored-live authority until a one-shot explicit restore selector or a tested outside-config live path is established.

### Option C: two roots with live DB outside config

Live DB in a verified writable *private local* location and staged snapshot under config; no arbitrary NAS WAL, no assumption share/media always backed up, and no assumption external live data and restored config are compatible. Identity epoch checks are mandatory after partial restore. Container deployment paths must be supported independently.

### Restore selector

- Ordinary start + valid current live DB: use it; never promote an old snapshot merely because it exists.
- Missing/corrupt live DB + snapshot: enter read-only recovery hold and offer authorized confirmation; do not wipe original data.
- Explicit user-selected snapshot: check schema, ledger identity, provenance, digest, snapshot's cursor, SQL integrity and foreign keys, permissions and backup scope; preserve pre-existing files, exclusive restore lease, versioned new runtime epoch.
- Suspected Supervisor restore where files have already been replaced: report only the committed history actually present; missing future rows cannot be recreated, and no local restored marker is trusted unless separately verified.
- External live DB + old config: refuse to assign data to mismatched console/PSN identities until explicit association review.

## 4. Hub/Archive entry: proposed contract

An optional explicit **hub** entry type under the SAME playstation_hub domain provides long-lived archive-only lifecycle. It is a user-approved native Config Entry, separate from independently owned physical-console and PSN-account entries. One hub unique ID in a reserved namespace; multiple concurrent hub flows deduplicate; it never starts PlayStation network monitoring and never masquerades as a hardware device.

The integration-wide HubController still owns singleton registration/SQLite manager. Hub/Archive entry is a **load anchor** and receives read/report leases only. It must survive after the last physical console is removed if the user retains the hub entry.

Lifecycle constraints:
- Hub-only startup registers one panel and authenticated API without any console requests.
- A new physical console can still be discovered despite the existing hub entry: dedicated async_step_dhcp with explicit stable-ID verification is required.
- Removing one console leaves the hub, panel and remaining consoles unchanged; removing the hub while physical entries remain cannot break them.
- Removing last entry leaves private history unless explicit purge is authorized, but the UI may no longer load on restart. Offer re-add/recover guidance.
- On reinstall, no implicit merge with a foreign snapshot simply because one hub ID matches; ledger_uuid and config epoch must agree.
- Disabled hub entry is not proof of loaded panel or backup hooks. Documentation must explain disabled/removed behavior.
- Account-only configurations may still load a panel if the account entry is enabled. A hub is the deliberate archive-only long-term option, not an account substitute.

## 5. Acceptance matrix (all cases NOT_RUN)

### 5.1 Path, filesystem and backup-scope tests — 16

| ID | Fixture | Expected result |
| --- | --- | --- |
| ST-PATH01 | Core config path on HA OS | Private root resolved under actual config, not OS host /mnt/data |
| ST-PATH02 | Container config remapped to unusual host directory | Runtime path derived from hass.config.path; same contract |
| ST-PATH03 | Marketplace replaces custom_components | Ledger remains separate and unchanged |
| ST-PATH04 | HACS persistent_directory exists but ledger external | Update cannot overwrite private ledger |
| ST-PATH05 | Cache artwork inside hass.config.cache_path | Artwork omitted; historical rows retained in backup |
| ST-PATH06 | Private root path component symlinked to unsafe location | Reject / fail closed |
| ST-PATH07 | Path with user-supplied ../ segment | Rejected or never admitted |
| ST-PATH08 | Permissions deny read/write | No false new empty ledger, error classified |
| ST-PATH09 | Free space insufficient for staging | No incomplete artifact advertised as finished |
| ST-PATH10 | User excludes Recorder DB | Custom SQLite inclusion matches actual backup scope; no incorrect privacy promise |
| ST-PATH11 | Partial backup excludes Home Assistant config | Not falsely represented as backing up the ledger |
| ST-PATH12 | /share not selected in default automatic backup | App data there correctly reported missing from backup |
| ST-PATH13 | External network mount with WAL candidate | WAL blocked unless tested-supported local-fs semantics |
| ST-PATH14 | HA OS on separate machine | No expectation of prior host-only external directory |
| ST-PATH15 | Snapshot staging fills quota | Bounded cleanup while preserving last known good snapshot |
| ST-PATH16 | Stored DB and snapshot present in archive | Both categorized; restore source not silently guessed |

### 5.2 Backup, snapshot promotion and restore tests — 16

| ID | Fixture | Expected result |
| --- | --- | --- |
| ST-BK01 | Online snapshot while writer commits | Internally consistent snapshot and its own cursor |
| ST-BK02 | Cursor advances between snapshot start and completion | Manifest uses committed cursor from resulting snapshot |
| ST-BK03 | Crash during snapshot file creation | No valid completed manifest |
| ST-BK04 | Crash after SQLite snapshot but before manifest | Uncommitted generation ignored, not promoted |
| ST-BK05 | Crash between two atomic renames | No partial two-file generation accepted |
| ST-BK06 | Immutable staged generation during archive | No mutation of included snapshot/manifest files |
| ST-BK07 | Backup post-hook absent after A quiescence | Does not resume writes and invalidate running archive silently |
| ST-BK08 | Backup pre-hook fails | Visible failure; no archive incorrectly advertised consistent |
| ST-BK09 | A archive interrupted | Safe policy for reopening and incomplete backup classification |
| ST-BK10 | B archive contains raw DB/WAL and staged snapshot | No automatic preference for raw or staged without authority |
| ST-BK11 | Normal restart with live cursor 180 + snapshot cursor 100 | Live 180 remains authoritative |
| ST-BK12 | Full restore older config, no external newer data | Old cursor accepted only as current available history, lost interval unknown |
| ST-BK13 | Full restore restores old config, newer external ledger survives | Entry/ledger identity mismatch detected |
| ST-BK14 | Archive encrypted / recovered after relocation | Correct credentials/privacy/format compatibility policy |
| ST-BK15 | Snapshot digest valid but different ledger_uuid | Reject auto-promotion, no cross-instance merge |
| ST-BK16 | Latest valid recovery snapshot is removed by retention | Forbidden without another verified recovery copy |

### 5.3 Hub/Archive Config Entry tests — 16

| ID | Fixture | Expected result |
| --- | --- | --- |
| ST-HUB01 | Fresh install, user creates Hub entry | One instance and one panel; no physical console invented |
| ST-HUB02 | Two concurrent hub creation flows | Unique ID dedupe, exactly one Hub entry |
| ST-HUB03 | Hub only after HA restart | One panel, archived stats available, zero LAN probes |
| ST-HUB04 | Hub + first PlayStation discovery | Dedicated DHCP flow offers console confirmation |
| ST-HUB05 | Hub + second physical PlayStation discovery | New independent console entry, no generic already-configured abort |
| ST-HUB06 | One console removed while Hub remains | History readable and panel alive |
| ST-HUB07 | Hub removed while two consoles remain | No shutdown of console writer/pollers |
| ST-HUB08 | Last console removed, Hub remains | Still browse archived reports, no commands |
| ST-HUB09 | Hub disabled before HA restart | No unsupported guarantee panel loads; bytes retained |
| ST-HUB10 | Hub deleted as last entry | No history purge; UI next-restart policy explicit |
| ST-HUB11 | Account-only + Hub entry | Distinct owner/ACL, one panel |
| ST-HUB12 | Hub restored from different instance with same reserved unique ID | Ledger UUID mismatch blocks silent adoption |
| ST-HUB13 | 100 hub reloads | One panel, handler set and writer, no orphan leases |
| ST-HUB14 | Hub setup fails after DB query lease | Cleanup releases lease without closing console users |
| ST-HUB15 | Historical query on Hub with no console | Bounded read lease, no network activity |
| ST-HUB16 | Multiple frontend connections to archived history | Authorized pagination; no duplicate writer/monitor |

### 5.4 Reconciliation, privacy and removal tests — 12

| ID | Fixture | Expected result |
| --- | --- | --- |
| ST-REC01 | Old Config Entry E1 restored; newer ledger has E2 console K2 | Identity conflict not silently mapped |
| ST-REC02 | Console rename or IP change | Stable canonical identity retains history |
| ST-REC03 | Hub ledger migrated to new hardware via backup | Import validates lineage/schema and rejects credential ownership confusion |
| ST-REC04 | Snapshot missing after full restore | No false claim of complete multi-year recovery |
| ST-REC05 | Invalid schema/foreign keys in externally stored ledger | Recovery hold, originals retained |
| ST-REC06 | Export history with private account references | Permission and redaction policy applied |
| ST-REC07 | Delete one console entry | No implicit SQL cascade deleting historical rows |
| ST-REC08 | Unlink PSN account | Tokens removed per policy; LAN historical evidence unaffected |
| ST-REC09 | User explicitly deletes all history | Confirm scope, precise deletion and audit, no accidental credentials leak |
| ST-REC10 | HACS integration uninstalled, archive retained | Document supported reinstallation and recovery path |
| ST-REC11 | Public static asset route probed for SQLite file | No history file served |
| ST-REC12 | Automatic backup with personal history and Recorder excluded | Privacy notice clear: custom history may still be in config backup |

**Initial suite: 60 proposed cases** (16 PATH + 16 BK + 16 HUB + 12 REC). They refine and overlap SPEC-008/009/010; the enumerated count is not the number of distinct executable tests and no cases have run.

## 6. Sign-off gates (all OPEN)

| Gate | Definition | Status |
| --- | --- | --- |
| ST-G01 | Authoritative storage root accepted with OS/Container compatibility matrix | PROPOSED |
| ST-G02 | Private filesystem permissions/path traversal and symlink protections | NOT_RUN |
| ST-G03 | Explicit Core/OS backup scope and Recorder exclusion documented/tested | BLOCKED_HA_OS |
| ST-G04 | Consistent quiesced backup or authoritative snapshot under final writer model | BLOCKED_HA_OS |
| ST-G05 | No ambiguous DB/WAL/snapshot authority on restore | PROPOSED |
| ST-G06 | Crash-safe snapshot/manifest publication and cursor provenance | NOT_RUN |
| ST-G07 | Valid live DB always preserved on ordinary restart | NOT_RUN |
| ST-G08 | External-live-ledger/old-config split-brain identity handling | NOT_RUN |
| ST-G09 | Portable restore to different hardware without silent history loss | BLOCKED_HA_OS |
| ST-G10 | Explicit Hub/Archive Config Entry or alternate no-console UX selected | PROPOSED |
| ST-G11 | Hub-only startup and panel/backup platform in HA OS | NOT_RUN |
| ST-G12 | Dedicated DHCP discovery unaffected by existing Hub entry | NOT_RUN |
| ST-G13 | Last-entry removal, private retention, explicit purge/export | PROPOSED |
| ST-G14 | No token exposure, safe archived report ACL and static paths | NOT_RUN |
| ST-G15 | Bounded resource cost, disk quota, cache and backup size | NOT_RUN |
| ST-G16 | Reinstall/uninstall and multi-branch upgrade/rollback migration | NOT_RUN |

## 7. Approval/implementation distinction

- Documentation and upstream research may be committed to main now.
- A candidate Hub/Archive root is **NOT** automatically accepted as part of the first implementation; it changes the onboarding workflow and needs maintainer acceptance recorded in ADR-0011.
- SQLite storage location and backup strategy remain conditional pending real HA OS/Container validation. HACS update safety is not a substitute for restore safety.
- No requirement to implement the 60 tests until an authorized implementation work package is created. Existing WP-01 LAN protocol work stays separate.
- Never claim a passed test or a working PlayStation Hub runtime from this specification.

## 8. References

- [Storage/restore/archive source audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md)
- [ADR-0011 decision proposal](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [SPEC-010 crash recovery](SPEC-010-crash-recovery-restore-provenance-and-archive-access.md)
- [SPEC-009 shared lifecycle](SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md)
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/integration_platform.py
- https://www.home-assistant.io/common-tasks/general/backups/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html

**Current evidence state:** 64 proposed cases including four P0 failure cases in §9, all unrun; 16 gates open; no code or physical HA OS tests.


## 9. P0 pre-backup orphan-freeze cases — 2026-11-06

Pinned Core BackupManager awaits all pre-backup integration-platform hooks and raises on any failure. Pinned Supervisor awaits begin_backup **before** the try/finally that calls end_backup. A successful PlayStation Hub quiesce followed by another integration's pre-hook failure can therefore lack a corresponding post hook. The review now treats prolonged write freeze **BLOCKED_PENDING_SAFE_RESUME_PROTOCOL** and emphasizes immutable snapshot investigation instead of accepting S1 as a safe baseline.

| ID | Fault injection | Expected outcome |
| --- | --- | --- |
| ST-BK17 | Our pre hook quiesces; different integration pre hook raises | Detect lack of guaranteed post; no indefinite silent freeze and no unsafe automatic resume |
| ST-BK18 | Supervisor begin_backup fails after Core pre hook | Abort/compensate with a proven lifecycle policy; no successful-backup claim |
| ST-BK19 | WebSocket connection is lost between successful pre and end | Source remains safe; recovery cannot mutate while archive copying may be active |
| ST-BK20 | Local watchdog fires while Supervisor is still archiving | Must not unfreeze into unsafe live raw DB copy; error/recovery path explicit |

**Revised total: 64 NOT_RUN cases** (previous 60 + four explicit failure-mode cases); no cases executed and all 16 approval gates remain OPEN. Gate ST-G04 now explicitly requires this cross-platform failure test.


## 10. Maintainer acceptance and new immutable snapshot dependency — 2026-11-06

The maintainer accepted the proposed **product-level** Hub/Archive entry, separate console/account ownership, one panel/controller and private storage direction. [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06) now records the acceptance and remaining technical blockers. The initial 64 SPEC-011 tests remain unrun. New [immutable snapshot research](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md) and [SPEC-012](SPEC-012-immutable-snapshot-publication-and-backup-admission.md) add source-backed constraints: Online Backup API may restart copying under concurrent writes; published snapshot cursor comes from the snapshot itself; source DB/WAL may remain in the HA archive; Core/Supervisor provide no established custom per-file exclude return contract; no cross-platform post hook is guaranteed after a pre-hook failure. These are operational NOT_TESTED gates and are NOT automatically approved.


## 11. Immutable snapshot source implementation boundary (2026-11-06)

[ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md), [source audit](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md), and [SPEC-012](SPEC-012-immutable-snapshot-publication-and-backup-admission.md) add 64 NOT_RUN cases and 16 OPEN technical gates, without altering this spec's 64 cases/16 gates. Maintainer product-level acceptance of the Hub entry is recorded in ADR-0011 §12. Current research **does not** approve a backup/restore implementation. The pinned Core/Supervisor pre/post API does not expose a custom live DB/WAL exclusion; a completed Online Backup API snapshot can coexist with archived raw database files. Formal release needs archive member inspection, explicit recovery source authority, and bounded snapshot publication while LAN monitoring continues. Active writer must not be frozen waiting for an optional post hook. No tests executed.
