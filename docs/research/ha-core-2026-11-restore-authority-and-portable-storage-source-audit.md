# Home Assistant Core 2026.11 — Restore authority, backup source selection and portable private storage

**Review date:** 2026-11-06
**Status:** Source-backed research, design recommendations, not implementation or tests
**Pinned Home Assistant Core:** 2026.11.0
**Pinned Supervisor:** 69848689a1e982ebe92d80e344fc086d8af667db (exact SHA; not a claim about the user's running Supervisor)
**Upstream public documentation:** Home Assistant backups, OS storage and developer backup platform, reviewed 2026-11-06
**Scope:** One PlayStation Hub custom integration, one panel, one integration-global controller/history ledger; a logical Hub/Archive Config Entry and separate console/account entries, as conceptually accepted in ADR-0011
**Related:** [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md), [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md), [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md).
**Git policy:** documentation edits on main only; frozen develop untouched.

> Evidence tags: CORE_SOURCE, SUPERVISOR_SOURCE, OFFICIAL_DOC, SQLITE_OFFICIAL, PROJECT_PROPOSAL, OPEN. Direct reading of upstream source establishes only behavior for the pinned versions, not interoperability or backup correctness of an unimplemented integration. An architectural recommendation is not proof of runtime support.

## 1. Executive result and hard guarantee boundary

**There is no source-confirmed universal, automatic, lossless restore authority for a custom SQLite database from all Home Assistant OS backups through a normal custom integration's pre/post backup hooks.** The hooks prepare/finish backup; in pinned Core and Supervisor they do not accept a per-integration list of arbitrary files to omit from the Home Assistant configuration archive. A valid immutable SQLite Online Backup API snapshot may therefore be present alongside mutable live database/WAL copies. The backed-up raw file must not automatically be treated as an equally trusted recovery candidate.

Moving the live database to a location outside the archived configuration tree could eliminate that particular raw-copy ambiguity, but **introduces other problems**: backup selection, privacy, filesystem support, compatibility across installation types, and a newer external ledger paired with old restored Home Assistant Config Entries. No documented cross-machine portable app-private filesystem root with a first-party automatic backup contract was confirmed for arbitrary custom integrations.

**Important impossibility boundary:** If an old backup overwrites the only authoritative database and all local metadata, and there is no newer independent copy or trusted out-of-band marker, neither commit cursor, last-modified time, nor a snapshot checksum can recover later commits or prove that restore occurred. User-facing guarantees must explicitly acknowledge this.

**Recommended path after research:** keep ADR-0011's accepted private/config-root *direction* as the default candidate without falsely approving a specific path; prioritize independent immutable snapshot production and an explicit, administrator-controlled recovery procedure; document that full automatic restore correctness is **OPEN**, and continue investigating optional more isolated storage only where supported by target installation/testing.

## 2. Pinned official evidence matrix

| ID | Classification | Source/behavior | Implication |
| --- | --- | --- | --- |
| RA-01 | CORE_SOURCE | homeassistant/core_config.py Config.path resolves inside config, cache_path under .cache (regenerable; omitted from backups) | No blessed generic private app data directory outside config or guarantee for arbitrary absolute paths |
| RA-02 | SUPERVISOR_SOURCE | supervisor/docker/homeassistant.py mounts /config read-write, /share read-write and /media read-write, /ssl read-only | OS Core can reach share/media but availability/privacy/backup semantics are different |
| RA-03 | OFFICIAL_DOC | Backup guide: automatic recommended includes HA settings, normally not share/media | /share or /media alone is NOT a default protected 3-year history store |
| RA-04 | SUPERVISOR_SOURCE | supervisor/homeassistant/module.py backup has fixed filename exclusion patterns and copies config tree | No public pre/post customization of per-file exclusion in this route |
| RA-05 | CORE_SOURCE | components/backup/manager.py CoreBackupReaderWriter has fixed exclusions and can separately exclude Recorder files | Home Assistant Recorder exclusion does not imply PlayStation Hub history exclusion |
| RA-06 | OFFICIAL_DOC | Contributor backup agent saves/serves backup destinations; pre/post hooks prepare source integrations | Backup Agent is NOT a documented custom Core config tar file-filter plug-in |
| RA-07 | SUPERVISOR_SOURCE | supervisor/backups/backup.py store_homeassistant -> sys_homeassistant.backup | Archive reads HA config after source pre-hook |
| RA-08 | SUPERVISOR_SOURCE | supervisor/homeassistant/module.py backup await begin_backup before try/finally end_backup | Successful prehook + another prehook failure can leave an unmatched post |
| RA-09 | SUPERVISOR_SOURCE | supervisor/homeassistant/module.py restore replaces config tree; special database exclusion matches Recorder names | Application-owned SQLite in config may be overwritten even when HA history unchecked |
| RA-10 | SUPERVISOR_SOURCE | supervisor/backups/manager.py _do_restore has independently selectable folder_list and homeassistant flag | Restored config and /share may come from different generations or one may remain untouched |
| RA-11 | SUPERVISOR_SOURCE | supervisor/backups/backup.py _folder_restore clears selected target directory before archive extraction and coordinates nested /share/media network mounts | /share is not a simple guaranteed persistent excluded directory; selective restore may replace its contents |
| RA-12 | OFFICIAL_DOC | OS storage can mount external disks or NFS/CIFS under share/media or backup usage | Do not assume a path below /share is local/fsync-safe for WAL |
| RA-13 | SQLITE_OFFICIAL | WAL requires appropriate local shared-memory/filesystem semantics and doesn't support arbitrary network filesystems | Verify path filesystem, mount type, actual SQLite runtime and only one writer/checkpointer authority |
| RA-14 | SQLITE_OFFICIAL | SQLite Online Backup API creates consistent snapshot, but concurrent source writes may restart incremental copies | Snapshot must be independent, bounded and validated by its own cursor |
| RA-15 | CORE_SOURCE | backend backup/start/end dispatches pre/post platform hooks, but no trusted per-integration restore intent is exported in this interface | Cannot equate a stale staged snapshot with an intended restore |
| RA-16 | CORE_SOURCE | Core backup_restore.py .HA_RESTORE is a separate Core restoration mechanism | Do not claim it is a universal Supervisor restore marker visible to all integrations |

Sources are catalogued in §16. No live Home Assistant OS archive, installed SQLite version or filesystem mount was inspected.

## 3. Storage topology matrix

Each option must be scored against *source-update survival, automatic backup inclusion, WAL/filesystem suitability, privacy, restore effects, portability, and recovery authority*. A path may satisfy one dimension and fail another.

| Candidate | Scope/lifetime | Automatic Core config backup | Risks | Assessment |
| --- | --- | --- | --- | --- |
| Dedicated private /config/.playstation_hub/ledger | Home Assistant config volume, HACS source separate | Source file included if config selected; live copy may be incoherent | Config restore overwrites DB; raw DB/WAL and staged snapshot both archived | Current default candidate only; needs explicit recovery policy |
| /config/.playstation_hub/backup/staged | Application snapshot subtree | Included if config selected, provided final generation is not excluded | Immature staging, archive copy/GC race, private content | Approved product direction; implementation still open |
| /config/.cache/playstation_hub | Regenerable files | EXCLUDED | Can be cleared; catastrophic for live authoritative ledger | Reject as canonical data; disposable staging only |
| /config/custom_components | Integration source | Source replacement/Marketplace lifetime | HACS update overwrites, permissions/code/data mixed | Reject |
| /config/www / local static paths | Web-served content | Config selected | Exposes private history unless protected | Reject |
| HA Store/.storage | HA-managed small JSON | Config selected | Whole-object JSON not suitable for high-volume SQLite | Settings/checkpoints as justified, not SQL ledger |
| /share/playstation_hub | Supervisor separately backed-up folder, read-write mounted in Core | Recommended automatic settings OMIT share | Other apps may access; network mounts; partial restore replaces selected share; cross-install portability | Conditional *advanced* topology; not blanket private default |
| /media/playstation_hub | Separate media scope | Recommended automatic settings OMIT media | Media integrations/mounts, privacy, optional backup | Not default |
| /backup | Supervisor backup artifact target, not live state API | Not automatically appropriate for source data | Retention/backup agent semantics | Reject as live SQL storage |
| Arbitrary Core /data or host /mnt/data/supervisor | Not portable across HA install types, may not be mounted | Unspecified | Undocumented path, isolation and permissions | Reject without specific supported mount |
| External user-mounted local private path | Separately administered volume | Not in config backup unless a controlled snapshot staged | No guaranteed binding on HA OS/Container, user maintenance, identity split-brain | Optional future feature only |
| NAS/CIFS/NFS live WAL | Potentially remote | Independent | SQLite WAL unsupported for general network filesystem | Reject as WAL target absent exceptional official guarantees; local snapshot export may be fine |

The "private" word in a folder's name does not grant secrecy; OS sharing, process permissions and backups must be reviewed. If /share is selected during a full backup then the mutable live DB may be archived there too, recreating the dual-authority problem; do not assume out-of-config always means outside **all** selected backup scopes.

## 4. Full/partial restore combinations

Two independently selectable restored things: HA configuration (Config Entries/settings/etc.) and separately backed-up share/media/apps. Sensitive credentials and the private SQLite historical ledger may occupy different selected scopes.

| Scenario | Restored HA config | Restored /share | Consequence |
| --- | --- | --- | --- |
| Normal reboot | none | none | Validate current live ledger; dormant old snapshot is not an instruction to overwrite |
| Restore old config only, live DB in config | old | untouched | DB/snapshot under config replaced; later commits may be lost |
| Restore old config only, live DB in share | old | current | Config Entries may be older than newer live DB associations -> split-brain |
| Restore old config AND share from same backup | old | old | Can still contain mutable raw SQLite copied mid-operation; directory selection not SQL transaction |
| Restore only share, live DB in share | current | old | New Config Entries + older ledger -> inverse split-brain |
| Restore only share, live DB in config | current | old | Config-root ledger unaffected but other app data changes |
| Restore config onto new OS install | old | possibly absent | No claim an external live DB survived; only backed-up snapshot available |
| Restore pre-removal backup onto user with deleted account | old | varies | Sensitive older association and token state must not silently gain authorization |
| Restore config with Recorder DB excluded | old except named Recorder files | varies | PlayStation Hub SQLite in config is NOT excluded |
| Restore with hub-only Config Entry | old hub | varies | Hub can show archive if loaded, but cannot invent missing console observations |

These are design implications and test fixtures from pinned paths, not measured user data.

## 5. Three distinct identifiers, and a fourth provenance dimension

- **Home Assistant instance identity**: HA-generated install identity; can be cloned by a whole-system restore and is not by itself proof of a unique physical home.
- **Hub Config Entry unique ID / entry_id**: logical configuration anchor for startup and UI; **not** ledger identity or Sony hardware.
- **Ledger UUID**: application-owned durable logical database; persists through approved snapshot import or controlled schema migration, not derived from hostname/IP.
- **Ledger lineage (epoch, parent snapshot, fork/cursor/digest)**: needed to distinguish two diverged histories, especially if a newer ledger and older config survive together.

Physical console canonical keys and PSN account keys remain separate namespaces under ADR-0004/0007, and must not be reattributed by restoring older display names or addresses.

**Subtle risk:** Two files can carry the same ledger_uuid and each show cursor 150, yet contain different operations after a restore/fork. "Largest cursor wins", equal UUID, equal dates and even a green integrity_check are insufficient for deciding authority. A future ledger lineage/fork protocol and semantic validation are necessary before any automatic merge. Do not call a hash chain a proof of origin if the attacker/user can alter both DB and manifest. Hash lineage may help detect divergence, not magically restore missing operations.

## 6. Authority classes and trust classification

| Class | Provenance | Permitted actions |
| --- | --- | --- |
| LIVE_VALID | Database opened with SQLite recovery, passes chosen schema/ledger/relational checks, expected runtime ownership | May be used at normal startup when not known to have been replaced; never implies an old snapshot should win |
| SNAPSHOT_PUBLISHED | App-produced immutable generation, manifest+integrity valid | Candidate for explicitly authorized restore, not proof it is in an HA backup |
| SNAPSHOT_IN_ARCHIVE_VERIFIED | Archive was actually inspected and exact artifact matched | Stronger evidence of inclusion, still not automatic authority over live |
| RAW_BACKUP_COPY | Mutable database file/sidecars copied by directory archiver | Untrusted *as a backup-consistent source* until independently validated; never choose by filename or newer cursor alone |
| EXTERNAL_LIVE | Live data on separate volume | May be newer than restored HA config; stop writes on identity/config mismatch |
| FOREIGN_LEDGER | Different ledger_uuid or untrusted instance lineage | Reject automatic adoption/merge; explicit import workflow required |
| CORRUPT_OR_AMBIGUOUS | Invalid integrity, mismatch, uncertain partial restore | RECOVERY_HOLD, preserve originals, admin repair and diagnostic metadata only |

A snapshot can be the *best independently validated backup artifact* without the application being able to conclusively identify that the host has just performed a restore.

## 7. Proof boundary: what can and cannot be automated

**Can be automated in a future implementation, after testing:**
- Use SQLite's Online Backup API to produce a coherent self-contained immutable generation.
- Validate digest, schema, foreign keys, actual snapshot cursor and ledger UUID.
- Confirm that a chosen Home Assistant backup archive includes the named snapshot through an authorized file-level archive inspection, if a supported secure interface exists.
- Prefer a healthy current live ledger on a confirmed ordinary restart.
- Detect obvious schema/ledger/identity mismatches and fail closed; warn about history missing since last committed cursor.

**Cannot be guaranteed in this source baseline without more support or independent evidence:**
- Exclude arbitrary app-owned active SQLite files from a Supervisor config backup via pre/post hook.
- Tell from a restored directory alone whether an old valid SQLite file was naturally quiet or was copied by a restore.
- Reconstruct commits after the most recent available snapshot if all other independent copies were destroyed.
- Trust an older Config Entry to authorize controls for a surviving newer or unrelated physical console/account.
- Assume a local /share path is always local, private, automatically backed up, or present on a migrated Container instance.
- Guarantee backups performed outside HA's orchestration triggered app-specific snapshot hooks.

**Proposed honest release behavior:** Do not advertise universal automatic lossless restoration. Ship, after future approval/testing, verifiable snapshots and an explicit administrator-guided recovery workflow. If the project requires fully automatic recovery as a non-negotiable release requirement, this remains a P0 blocker needing supported upstream API change or a separately approved storage architecture.

## 8. Recommended controlled recovery protocol (architecture only)

1. **Preflight**: protect existing on-disk candidates, fence all new writes and console/account control attribution while in recovery mode, record sanitized case ID.
2. **Inventory**: discover live SQLite, local published snapshots, authorized imported archives and any verified off-host copies; do not search/modify arbitrary files.
3. **Independent validation**: read each source in isolation with SQLite native recovery where appropriate; integrity_check, foreign_key_check, schema and version, ledger UUID, cursor, semantic identity, optional lineage.
4. **Classify provenance**: identify whether it is LIVE_VALID, SNAPSHOT_PUBLISHED/VERIFIED, RAW_BACKUP_COPY or FOREIGN_LEDGER; absence of a trusted restore intent is explicit.
5. **Decision**: default to keeping an unambiguously healthy live ledger during normal startup; if suspected restore or divergent candidate data, require administrator confirmation with loss-of-newer-history warning. Never automatically merge a foreign ledger or import credentials from history.
6. **Non-destructive staging**: preserve original live files as a protected recovery copy, create an isolated copy of selected candidate and validate again before making it operational.
7. **Transactional logical promotion**: close all current SQLite handles, use tested same-filesystem atomic replacement/move semantics (including WAL/SHM), install a new runtime restore epoch and capture parent snapshot metadata. Native HA Config Entry storage is a separate transactional system: cannot pretend this promotion atomically updates HA registries and SQLite together.
8. **Identity reconciliation**: map ledger canonical console keys only to validated physical consoles and approved account associations. If stale HA Config Entries are present, keep operations disabled until reconciled.
9. **Resume**: start new monitoring only for authorized entries and explicit read/write-capable current ledger; old live segments stop at last durable evidence and new observations open a new coverage range.
10. **Audit and user messaging**: store sanitized repair decision, source UUID, committed cursor and reported missing coverage. No raw tokens/private full history in generic logs.

**No automatic multi-ledger merge.** A future separate import tool may support append-only immutable event reconciliations, but only with strict common-ancestor validation, dedupe, schema/policy compatibility, overlapping segment conflict resolution, and explicit human authorization. This is not part of an accepted plan.

## 9. Recovery UI proposal for the single panel

If the approved Hub/Archive entry loads and sees uncertain restoration:
- Show a **History recovery required** state, not an empty new library or guessed online console.
- Explain what is known: last validated source, snapshot timestamp and verified committed cursor; what is unknown: missing time, whether raw copy was complete, latest backup status.
- Offer privileged actions to inspect candidate summaries and select an authorized recovery source, plus backup/export existing bytes before replacement.
- Show a diff of expected impacts (different ledger UUID, additional/recent history possibly lost, console associations mismatched) WITHOUT exposing sensitive account IDs in public diagnostics.
- Disallow Wake/Standby/history mutation if restored console identity or source attribution is unresolved. Read-only archive views may be allowed when provenance is adequate and ACL permits.
- Reject any attempt to treat the presence of a staged snapshot as proof of backup/restore success.
- Make "keep current" an explicit choice when diverged histories exist; provide a separate export before choosing "replace with older".
- No file chooser/URL from unprivileged browser can read arbitrary SQLite backup paths; use server-side bounded secure import.

## 10. Controlled storage topology candidates for ADR-0013

**T1: Configuration-root live ledger + immutable snapshots under config (initial/default direction).** Portable; backups include staged artifact, but may also contain raw live DB/WAL. Recovery must be conservative and potentially admin-guided. Protect from HACS updates. Not automatically lossless.

**T2: Live under /share on HA OS + immutable snapshots under config.** Source-snapshot separation for the default recommended backup selection, but /share is accessible to other apps and may be excluded from backups or also included by user; network mounts and partial restore create split-brain. Not the standard choice without permission/mount isolation guarantees. For Container installations, share may not exist.

**T3: Private, OS-supported persistent external volume + snapshot under config.** Separates source from Core config archive when private local mount validated. Requires explicit installer-managed configuration, permissions, hardware migration and independent backup. Not a mandatory dependency for a one-click HACS integration.

**T4: Store in Home Assistant Recorder or Store rather than SQLite.** Does not satisfy the dedicated indexed multi-year per-game session ledger contract as currently modelled; not proposed as a drop-in replacement.

**T5: Backup agent implementation to filter files.** Existing BackupAgent is a destination/transport plugin, NOT source archive filter in pinned documented API. Do not misuse it to invent exclusions; would need an alternative supported data export route.

**Preferred recommendation:** retain T1 as the *product default direction* pending target HA OS verification, explicitly document limited automatic restore assurances and require safe admin recovery. Keep T2/T3 as separately approved advanced options only if their privacy and backup contracts can be proven. Do not implement unsafe file monkey-patching, symlink tricks or hidden manipulation of Supervisor exclusion constants.

## 11. Backup policy and user promises

Recommended future plain-language limitations:
- "PlayStation Hub prepares a verified history snapshot when the Home Assistant backup integration invokes the hook and the operation succeeds."
- "The Home Assistant backup settings determine whether the configuration and snapshot are included."
- "Restoring an old backup cannot reconstruct observations recorded later without another newer backup."
- "The recovery screen may require an administrator to choose an archived copy if several plausible databases are present."
- "The Home Assistant 'History' checkbox primarily applies to Home Assistant's Recorder; it is not a general exclusion of all custom application histories."
- "External copies, app-specific exports and backups on another device are important for protection against hardware loss."
- "Published snapshot means locally verified, not necessarily included in a completed remote backup."

No claim of "automatically recovers exactly every session on any restore", and no claim that unreadable/corrupt files are repaired by replacement with empty databases.

## 12. Remaining proofs and potential upstream feature requirement

**P0 source/HA OS proof:** run a real HA OS backup with an active SQLite WAL writer and verify exact tar members (app DB, -wal, staged snapshot, metadata) and selected scopes; verify Core 2026.11.0 and actual installed Supervisor match the pinned contract. Use synthetic data only.
**P0 restore tests:** full config restore, partial config-only restore, share-only restore and both-folder restore with older/newer ledger combinations; include a different target HA OS machine.
**P0 provenance:** investigate a first-party restore-event/intent API with semantics surviving Supervisor file replacement. If absent, maintain explicit admin-guided recovery, or propose upstream extension rather than inventing one.
**P0 storage:** inspect /share/mount path privacy, optional network mounts, Linux filesystem type and SQLite linked version before any T2/T3 support.
**P0 identity:** validate post-restore Config Entry unique IDs, console physical ID, account/token ownership and history ledger UUID association.
**P1 resilience:** source/manifest retention and off-host backup design; restore rehearsals and corrupted/partially completed tar cases.
**P1 UX:** test mobile/admin recovery accessibility, permission revocation and no-console Hub mode without making network calls.
**P1 release:** measure snapshot sizes, backup time, disk quota and 3-year synthetic dataset; no performance numbers claimed now.

## 13. Official primary sources

- https://www.home-assistant.io/common-tasks/general/backups/
- https://www.home-assistant.io/common-tasks/os/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/const.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/pragma.html

## 14. Result and next priority

**Results:** Proven source topology and a conservative authority/reconciliation contract; lack of a general app-specific archive filter in reviewed interfaces; real OS Core mounts for /config, /share, /media; independently selectable folder restores; a concrete split-brain matrix and impossible-lossless-restoration boundary. Not a working implementation or successful backup.

**Next priority:** formalize a first-party-compatible **administrator recovery UX/API** and the source/ledger/Config Entry identity reconciliation contract (including imported backups from another Home Assistant installation). In parallel, determine whether an upstream feature request for selective backup exclusions or a documented restore-intent callback is necessary. No code has been authorized.
