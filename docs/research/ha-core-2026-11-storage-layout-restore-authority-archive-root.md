# PlayStation Hub — HA OS storage layout, restore authority, and archive-only lifecycle audit

**Date:** 2026-11-06
**Status:** Research / DESIGN_PROPOSAL / NOT_IMPLEMENTED / NOT_TESTED / NO_ADR_APPROVAL
**Official baseline:** Home Assistant Core tag 2026.11.0; Home Assistant Supervisor commit 69848689a1e982ebe92d80e344fc086d8af667db; SQLite upstream documentation; Home Assistant contributors and backup/user documentation reviewed 2026-11-06.
**Target:** One PlayStation Hub Marketplace/HACS custom integration; independently owned physical console and optional PSN account Config Entries; one full-page sidebar panel; no mandatory MQTT/add-on/external DB.
**Branch:** main documentation only. Frozen develop unchanged.
**Companion:** [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md).

> Evidence labels: CORE_PINNED / SUPERVISOR_PINNED / SQLITE_OFFICIAL / HA_OFFICIAL_DOC / PROJECT_PROPOSAL / OPEN_HARDWARE. Directly inspected source is not proof of an integration that does not exist. User choices, test execution and deployment are separate from documentation.

## 1. Executive findings

1. A path *outside HACS-managed source* protects application files from integration replacement, but does NOT necessarily protect them from a Home Assistant configuration restore. Whether it is included in a backup is defined by the selected backup scope and the archive producer, not by the name chosen for the folder.
2. Core 2026.11.0 hass.config.path generates a path inside the configuration directory. Its cache_path generates a path inside .cache, explicitly documented as regenerable and excluded from backups. Neither helper itself provides journaling, encryption or guarantees of atomic backup.
3. Home Assistant OS user documentation distinguishes configuration, Recorder history, share, media and applications as separately selectable backup parts. Recommended automatic backup settings do not automatically include share/media. Placing sole authoritative data in /share or /media therefore risks omission from default backups and may create unexpected exposure or network filesystem concerns.
4. Core internal .storage stores registries and Store-managed JSON. An application-owned SQLite file **could** live under a new dedicated private configuration subdirectory, distinct from .storage, /config/www, .cache and custom_components. This is a project candidate path, not a Home Assistant-mandated directory.
5. Pinned Supervisor HomeAssistant.restore can replace the configuration tree and preserve only specifically matched Recorder files under its database exclusion mode. A backup can also omit Home Assistant config completely. Thus restoring old config can replace newer PlayStation Hub data; restoring an older backup does not by itself guarantee a reliable *notification to the custom integration* that a restore occurred.
6. A backup created from a live SQLite database via Online Backup API yields a consistent snapshot, but if the live source remains inside the Supervisor's archived config tree, the archive can contain **both the authoritative staged snapshot and an independently copied, potentially inconsistent live DB/WAL**. They must not be silently conflated.
7. A permanent **Hub/Archive Config Entry** would ensure the integration can load after restart without any console entries and can offer an archived-history panel. It is technically compatible with HA's Config Entry model, but it changes setup/removal UX and must remain a proposal until explicitly approved.
8. A robust restore strategy must be safe both for an **ordinary reboot with an old snapshot present** and for a **true backup restore where the previous live files have already been overwritten**. A local marker in the same restored folder cannot distinguish these reliably; full machine migration cannot recover commits that were never backed up anywhere.

## 2. Source inspection register

| ID | Evidence | Pinned or canonical source | Consequence |
| --- | --- | --- | --- |
| PL-01 | CORE_PINNED | homeassistant/core_config.py, Config.path / Config.cache_path | Fixed application path anchored at the configuration directory; never use cache for durable history |
| PL-02 | HA_OFFICIAL_DOC | Architecture: Registries and storage | .storage is HA-managed internal JSON/Store area; keep custom SQLite logically separate |
| PL-03 | HA_OFFICIAL_DOC | Marketplace custom integration publishing | Integration folder can be replaced; hacs.json persistent_directory preserves specified folder over upgrades only |
| PL-04 | HA_OFFICIAL_DOC | Home Assistant backup guide | Config and Recorder history are selectable; share/media can be omitted; encrypted local/remote backup options |
| PL-05 | CORE_PINNED | backup/manager.py and backup/websocket.py | Backup pre/post integration platform callbacks via authenticated backup/start and backup/end |
| PL-06 | SUPERVISOR_PINNED | homeassistant/module.py, backup() | Archive generation traverses HA config tree after pre hook; excludes *.db-shm and selected standard paths |
| PL-07 | SUPERVISOR_PINNED | homeassistant/module.py, restore() | Config tree removed/replaced, with Recorder-specific preservation in exclude_database mode |
| PL-08 | SUPERVISOR_PINNED | backups/backup.py and backups/manager.py | Full/partial backup scope and Supervisor archive/restore selection are not identical |
| PL-09 | CORE_PINNED | config_entries.py and integration_platform.py | Loaded integration is scoped by Config Entries; backup integration platforms attach to loaded integration components |
| PL-10 | HA_OFFICIAL_DOC | Config entries; Routing and panels | Entries are persisted and loaded again; integrations register panels in Core |
| PL-11 | SQLITE_OFFICIAL | SQLite WAL / Online Backup API | Online backup is coherent, arbitrary live .db and -wal copies are not necessarily coherent |
| PL-12 | HA_OFFICIAL_DOC | Home Assistant OS common tasks | Host-side /mnt/data/supervisor/... paths are distinct from the Core container path; do not hardcode host partitions |

## 3. Persistent path classification: do not confuse lifecycle boundaries

| Candidate | Survives Marketplace source update? | Included with HA config backup? | Survives restoring older config on same host? | Portability / risks | Assessment |
| --- | --- | --- | --- | --- | --- |
| Integration folder, unspecified files | No reliable promise | May be archived if config included | May be replaced | HACS update overwrites source; data/code mixed | REJECT |
| Integration persistent_directory | Marketplace moves specified subtree across updates | Potentially if config included | Not guaranteed | Does not solve consistency or user-code mixing | Reject as default ledger placement |
| Configuration-root dedicated private subdir | Yes (separate from integration source) | Pinned Supervisor scans config except exclusions | **No: old config restoration can overwrite** | Portable on Container/OS but backup must be made consistent | PREFERRED FIRST-RELEASE CANDIDATE |
| Home Assistant .storage Store JSON | Yes | Yes with config | No | Appropriate for small versioned Store data; not high-volume SQLite ledger | SETTINGS ONLY |
| Home Assistant .cache | Regenerable | Excluded | No dependable restoration | Officially excluded from backups | CACHE ONLY |
| /config/www static | Yes until config restore | Usually config scope | No | Public serving exposure and URI access | REJECT for private DB |
| /share | Outside integration source | Only if share backup selected; not in recommended default automatic scope | Depends on share restore and machine | Access/backup exposure, portability, network mounts | Not default authoritative ledger |
| /media | Outside integration source | Only if media backup selected | Depends on media restore | Media-browser exposure; alternate mounts may be networked | REJECT for private live DB |
| /backup | Separate local backup destination | Backup repository, not an application transaction store | Varies | Lifecycle/retention controlled by HA backups | Not default live DB |
| Custom external filesystem / remote NAS | Potentially | Outside standard config backup | Independent where actually mounted | HA OS access, security, WAL network filesystem limitation, data migration | Explicit advanced option only, BLOCKED |
| Host /mnt/data/supervisor path | Not a public Core API | Host-specific | Host-specific | May not exist in Core container; upgrades could change mapping | NEVER hardcode |

**IMPORTANT:** "Included with HA config backup" means source-scoped inclusion according to the cited backup implementation. It is **not a claim that raw live SQLite bytes are a consistent, restorable snapshot**.

## 4. Concrete proposed directory hierarchy, not approved or created

An application-private subdirectory resolved under the Home Assistant configuration directory by the official hass.config.path method:

    <ha-config>/.playstation_hub/
      ledger/
        history.sqlite3                 # Live database, never served as a static asset
        history.sqlite3-wal             # SQLite-owned transient companion in WAL mode
        history.sqlite3-shm             # SQLite-owned transient companion in WAL mode
      backup/
        staged/
          snapshot.sqlite3              # Committed, immutable copy created via SQLite
          manifest.json                 # Describes EXACTLY snapshot.sqlite3
        pending/                       # Incomplete, never authoritative
      recovery/
        reports/                       # Sanitized metadata only, bounded
      cache/
        game_artwork/                  # Evictable; would otherwise enter config backups

**Better cache separation:** Instead of using the illustrated cache/ directory under .playstation_hub, resolve evictable files via hass.config.cache_path("playstation_hub", ...). Cached artworks are not required to restore gameplay history and should not make backups huge. Never use the generic HA public /config/www for credentials or history.

**Snapshot/manifest caveat:** With the proposed hierarchy both the staged snapshot and live DB/WAL remain in the config backup scope. Treat the live files as a possible **untrusted source after archive extraction** unless their consistent source-of-truth has been established. Need a policy to prevent ambiguity; do not claim path layout alone solves it.

**Security/path rules:** relative segments must be fixed and internally defined, no user-controlled ".." or absolute path joining; canonicalize and enforce containment; reject unexpected symlinks, enforce private directories and non-public serving, restrictive filesystem permissions where supported, bounded file counts, quotas, free-space reservations, no raw secrets in the SQLite history ledger. Do not assume ordinary file permissions encrypt data at rest. Do not expose private history from static asset URLs.

## 5. Storage option decision matrix

**Option S1 — Stable live SQLite inside HA config plus quiesced backup.**
- Best portability and straightforward inclusion in HA configuration backups.
- At pre-backup: fence new SQL admissions and monitoring-derived commits; await all accepted transactions and reads; checkpoint/close all SQLite connections and keep DB immutable until post-backup. Work from an explicitly bounded global backup lease; verify failure/cancel behavior.
- No raw live WAL writes may resume during archive. An unanswered post hook creates a serious liveness trade-off; if a timed auto-unfreeze happens while the backup still copies, the consistency guarantee fails. Define fail-safe backup cancellation, timeout, repair state, and guarded recovery.
- **BLOCKED_PENDING_SAFE_RESUME_PROTOCOL**, because §15 identifies a source-backed missing-post-hook failure path. Not approved.

**Option S2 — Online snapshot and live DB inside same HA config backup.**
- Snapshot + manifest are internally consistent and history can continue while Supervisor archives.
- However, the archive includes uncontrolled live DB/-wal unless a supported exclusion is demonstrated. Backup restore can yield old/partial live files and a valid snapshot.
- On normal restart, never automatically promote old snapshot. On actual backup restore, no always-available trusted restore marker has been proven.
- Promising as a **future enhancement**, blocked by definitive restore authority and file-selection semantics.

**Option S3 — Live DB in an OS-provided outside-config path, immutable staged snapshot inside config.**
- Clean separates live writer from standard config archive **if** a stable, private, local, writable and accessible path is proven on each supported install type.
- If live DB outside config survives restoring an older configuration, config entry IDs, aliases, schema, PSN association and secret-store keys may be rolled back and conflict with new live rows; the apparent preservation creates **split-brain metadata**.
- On new hardware, the outside-config path is absent. Migration must select validated staged snapshot explicitly.
- /share cannot automatically be treated as private/always included, and /media may be public to authenticated browsers/network-backed; not a default without tests.

**Option S4 — Manual application history export/import.**
- Can use a validated versioned SQLite snapshot+manifest with explicit administrator action and unambiguous selection.
- Cannot substitute for automatic HA OS backup UX but is a prudent disaster-recovery escape hatch. Must validate exports against privacy, file size, integrity and provenance.

## 6. The metadata split-brain problem

Example: 2026-11-01 console key K1 paired with config entry E1; on 2026-11-03 user replaces the console and new hardware is K2/E2; ledger outside config records K2 through 2026-11-05. Restoring 2026-11-02 HA config brings back E1 but leaves external ledger containing K2.

A naïve process might assume E1 is the writer owner for K2, overwrite names, import credentials from the older snapshot or silently attribute live data to K1. This is unsafe even when the external SQLite file itself is internally consistent.

**Required invariant:** runtime association between HA Config Entries, stable console/account identity and ledger namespaces is explicit and validated. HA entry_id is *not* a physical console key and cannot be the authoritative ledger key. Each persisted association has an epoch/revision. Restore mismatches trigger an administrative repair/association review; they cannot silently merge history by IP, PSN name or entry title. Credential ownership remains separate and must never be "recovered" by copying historical associations.

**Important consequence:** "Put live DB outside /config" is not automatically safer than keeping everything in config. It trades lost newer data after old restore for potential metadata divergence.

## 7. Restore authority: formal ordered decision table

| Current live source | Snapshot | Trusted restore intent / administrator action | Outcome |
| --- | --- | --- | --- |
| Valid and current, normal restart | Valid older staged snapshot | None | Use live DB; ignore staged snapshot |
| Valid and current, normal restart | Invalid or missing | None | Use live DB; report staging health separately |
| Valid but older due to HA OS restore | Valid snapshot with matching lineage | No trusted intent | Do **not** claim automatic detection; use valid live DB conservatively, flag evidence age; offer administrator recovery if distinguishable |
| Missing DB, first-ever onboarding | None | Explicit create-hub/new-ledger action | Create new ledger only if absence is verified and no recovery candidates |
| Missing DB, retained settings or recovery files exist | Valid snapshot | None | RECOVERY_HOLD; never silently create an empty ledger |
| Corrupt/incompatible DB | Valid snapshot | None | RECOVERY_HOLD; preserve originals; require verified/manual restore decision |
| Valid live DB with newer cursor | Older snapshot | Intent present | Require explicit loss-of-newer-data confirmation; prefer export/merge review, not overwrite |
| Valid snapshot, different ledger_uuid | Any | Any | Reject cross-instance auto-promotion; controlled import/identity resolution only |
| Both live and snapshot inconsistent | Any | Any | Preserve all candidate bytes, no auto-repair |
| External live DB with rolled-back config metadata | Snapshot any | Any | Identity/config reconciliation required before writes |

**Strong impossibility statement:** if the Supervisor replaces the whole configuration folder and no independent trusted metadata survived, a valid older live DB may be indistinguishable from a naturally quiet DB purely by examining files. Timestamps, snapshot UUID, hashes and commit cursors do not prove a restore occurred. Without a copy of newer commits, those commits cannot be reconstructed. Therefore automatic lossless restore across arbitrary full-configuration replacement is **not guaranteed** by any file layout contained wholly in that restored folder.

## 8. Proposed snapshot authority and version handshake

Use separately versioned records:
- ledger_uuid (unique identity of historical database)
- snapshot_uuid (unique snapshot artifact)
- schema_version and accounting_policy_version
- committed_cursor **read from the completed snapshot itself**, not only from a live writer read before copying: with concurrent writes these can differ
- stable identity namespace and per-owner evidence high-water hints
- created_utc, SHA-256, exact filename, file length and completeness state
- snapshot_package_format and restore/import compatibility range
- optional external backup/job correlation **only where official API exposes one**; no invented IDs
- provenance (source mechanism: quiesced file, Online Backup API, explicit manual export)
- restore_epoch and parent snapshot lineage recorded only after an authorized promotion.

**Production contract proposal:** A snapshot is staged to a temporary file, SQLite backup completes, source connections are released, integrity_check and foreign_key_check pass, the snapshot's own committed_cursor is read, checksum and manifest are produced, and both are promoted with a crash-safe publication protocol. A manifest digest is not authentication; authorizations are verified independently.

**A subtle correctness risk:** Publishing snapshot.sqlite3 then manifest.json as two independent file renames is not an atomic two-file transaction. Use generation-specific subdirectories and a final completion marker/index, or test a documented equivalent. Never accept a manifest that exists without its exact validated snapshot; after process crash, discard incomplete generations without deleting originals. On copy/archive of directory trees, ensure the files remain immutable for the full archive lifecycle.

**Snapshot retention:** Reserve disk capacity for at least live DB + one in-progress snapshot + one last known good archive as appropriate, then enforce bounded retention and clean up failed staging. Do not delete the only good recovery copy. Keep caches outside the backup tree. Distinguish source file size, snapshot file size and tar compression.

## 9. Hub/Archive Config Entry design, still PROPOSED

**Motivation:** Native HA custom integrations with config entries are loaded when at least one entry is configured. Removing the final physical console leaves no guaranteed domain setup on next reboot and hence no guaranteed sidebar registration. Persistent history on disk by itself does not recreate runtime UI.

**Candidate B (preferred for archive-first product):** one explicit durable Hub/Archive Config Entry, created through a user-confirmed UI flow, plus one separate entry per physical console and optional PSN account. The Hub entry is a **configuration/lifecycle anchor**, not the sole object owning the SQLite writer. The integration-wide HubController remains one per HA process; each entry retains its independent lease.

- Entry kind: hub, unique ID from a reserved namespace (for example hub:default for a single native HA instance, NOT a PlayStation identifier).
- A single hub entry permitted; concurrent initial/manual flows dedupe using official unique-ID Config Flow rules.
- Hub entry does not represent a physical PlayStation DeviceEntry, does not create a synthetic PS5, and must not start LAN probes or PSN token jobs.
- After successful setup it allows safe archive-only panel operation and an authenticated history service with **short bounded query leases**, not a permanently open reader.
- Console and account entries still own sensors, device identities, optional Remote Play/PSN tasks; deleting a console never deletes the hub or other consoles.
- Removing hub while consoles remain must not close their writer or panel. With no entries remaining, the panel may disappear on next restart; retained archives require supported reinstall/import path.
- The first UI may offer "Create PlayStation Hub" then "Add console" and "Link PSN account"; initial bootstrap with zero hardware works.
- No silent automatic creation of a config entry from a background discovery; protect user consent and explicit configuration workflows.
- Restore of a hub entry from another HA installation must validate ledger lineage; neither matching hub unique ID nor restored entry_id proves same underlying history.

**Candidate A:** no hub anchor; panel follows configured console/account entries, with retained archive only after re-adding a console or manual export/import. Lower config complexity but poor archive-only UX.
**Candidate C:** archive as Config Subentry of a single principal entry. Changing physical root ownership violates per-console isolation and creates harder removal semantics; not preferred without a core-native subentry lifecycle study.

**Recommendation:** document candidate B as the better long-term user experience; leave ADR-0011 Proposed until explicit maintainer approval and targeted Config Flow lifecycle tests. Do not claim it is already accepted.

## 10. Hub root lifecycle matrix

| Event | Desired contract |
| --- | --- |
| Install custom integration, no devices yet | User can create one hub entry via UI; no background discovery silently makes a root |
| First PS5 discovered | Dedicated DHCP step verifies it, permits separate console entry even with hub existing |
| Second PS5 discovered | Independent physical entry; no false generic "already configured" abort |
| Hub-only restart | Hub setup alone can register exactly one sidebar and expose authorized archive, without polling |
| Hub entry disabled | No guaranteed panel/backup platform; historical bytes remain, admin guidance is needed |
| A console disabled | Its LAN probe stops; hub and other console entries continue |
| Last console removed | Hub persists and historical report remains accessible according to retention settings |
| Hub removed with consoles present | Console entries keep working; global controller retains them; policy for UI routing explicit |
| Hub removed as last entry | No guaranteed menu next boot, no implicit deletion of ledger |
| HA backup while hub only | If hub loaded, pre/post backup hooks can service SQLite snapshot; no console monitor ownership |
| Restore with hub unique ID collision | Do not silently merge a different ledger UUID or account identities |
| User reinstalls HACS code | May discover retained data only after explicit compatible entry/bootstrap; never auto-overwrite foreign history |

## 11. Why a hub anchor helps backup as well as UX

Home Assistant's integration platform helper processes **loaded** integrations. A persistent, enabled hub Config Entry raises the likelihood that the PlayStation Hub component is loaded and its backup.py platform can be registered even without a console. If all entries are disabled or missing, the integration may not be loaded and its pre-backup hook might not run; if there is a static unmodified DB with no worker, backing up that file may be less hazardous but still must be tested. A hub entry is not proof that all types of HA backup always invoke the hook; custom installation, Core/Supervisor versions and interrupted startup remain acceptance gates.

## 12. Security, migrations and permissions

- History, sessions, game titles, console identities and player attributions are private; admin-only panel is current safe candidate, with backend authorization independent of menu visibility.
- Never expose ledger or snapshot via static frontend assets, public /local URLs or unrestricted media browser.
- Hub-only archived reports are read-only unless the user separately authorizes purge/import; no console wake/standby without an active, verified per-console entry.
- User can export before deleting all entries; a dangerous "Delete all data" action must confirm exactly which files and records are removed and cannot be coupled to HACS uninstall.
- Token stores belong to PSN/Remote Play owners under ADR-0007, not the general history snapshot. Restoring old tokens can need reauthentication and must not authorize previously unlinked accounts without review.
- No destructive schema upgrade, file copy or promotion on ambiguity; quarantining corrupted files must not put sensitive payloads under a world-readable or generally backed-up diagnostics path.
- Warn that Home Assistant backups can contain private gaming histories regardless of Recorder-history exclusion; educate users about encryption/retention before export.

## 13. Highest-priority unresolved proofs

P0:
1. Decide whether the first release uses configuration-root SQLite + entire-archive quiescence (S1), or an externally located database and staged snapshot (S3) after actual supported-path checks. Online snapshot S2 cannot be claimed as independently restoreable without authority.
2. Confirm private directory location, permissions, atomic rename/fsync/backup inclusion under Core and HA OS.
3. Determine how to avoid two conflicting live and staged SQLite candidates after restore. A one-time explicit admin import is the safe fallback.
4. Verify supervisor backup source filter and full/partial restore behavior on supported HA OS versions and installed current runtime.
5. Verify whether a hub-only config entry survives ordinary restart, provides a single panel and registers custom backup.py hooks.

P1:
6. Test concurrent first-time Hub/PS5/PSN config flows (the generic DHCP fallback is **insufficient** after any entry exists).
7. Verify stable ledger_uuid, console identity/HA entry associations across backup/restore, migration and HACS reinstall.
8. Decide export, retention, snapshot rotation, quota and privacy policy for three-plus years of history.
9. Define recovery UI when user restores an older archive and asks to keep newer external data; never auto-merge by IP.
10. Ensure containers and OS installation types are supported independently (some paths exist only with explicit mounts).

## 14. References

### Official Home Assistant
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/integration_platform.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://contributors.home-assistant.io/architecture/core/registries/
- https://contributors.home-assistant.io/frontend/architecture/routing-and-panels/
- https://contributors.home-assistant.io/marketplace/guides/integrations/
- https://contributors.home-assistant.io/marketplace/reference/hacs-json/
- https://www.home-assistant.io/common-tasks/general/backups/
- https://www.home-assistant.io/common-tasks/os/

### Pinned Supervisor
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py

### SQLite
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/pragma.html

### Project
- [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md)
- [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md)
- [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [ADR-0008](../decisions/ADR-0008-storage-persistence-and-backup.md)
- [ADR-0010](../decisions/ADR-0010-sidebar-panel-and-backend-api.md)

**Outcome:** A source-backed storage/restore/HUB-entry architecture comparison. No user data, runtime code, tests, migrations, PS5 communication, file contents or HA OS storage have been changed or inspected on the user's actual installation.


## 15. New P0 discovery — pre-backup can succeed without matching post-backup

**CORE_PINNED and SUPERVISOR_PINNED — cross-integration race:** Pinned Core BackupManager.async_pre_backup_actions uses asyncio.gather over *all* registered backup platforms, then raises if any platform reported Exception. The Core backup/start WebSocket command returns that error. In pinned Supervisor HomeAssistant.backup, the await for begin_backup occurs **before** the try/finally that calls end_backup. If the PlayStation Hub pre hook has successfully stopped/frozen its SQLite writer and another integration's pre hook fails, begin_backup raises **before the finally is entered**, and HomeAssistant.end_backup is not guaranteed to execute for that attempted archive.

This is a **source-demonstrated failure path** in the reviewed versions. It does NOT prove the actual PlayStation Hub hook exists or is installed. No executable failure injection was run.

**Consequence:** Option S1 / ADR-0011's initial preference for a prolonged pre-to-post write freeze MUST be downgraded to **BLOCKED_PENDING_SAFE_RESUME_PROTOCOL**, not called the simplest safe first-release architecture. A mere local timeout is also unsafe: if it resumes writes while an archiver is still reading files, the archive can become inconsistent. A comprehensive solution requires explicit backup job state/cancel completion, guaranteed cross-platform error compensation, or an equivalent contract that can prove the archive no longer reads the DB.

**Revised preferred research direction:** produce a bounded **immutable SQLite Online Backup API snapshot** without holding live writes frozen for the entire archive. BUT the live DB and WAL may still be included by Supervisor when both are inside /config, so backup correctness still requires an authoritative restore policy and potentially a safe, private, verified out-of-config live store. Snapshot immutability reduces pre/post liveness risk; it does not solve restore provenance.

**Important additional nuance:** CoreBackupReaderWriter has its own try/finally around pre/post and cannot be generalized to Supervisor's different path. The exact nested placement matters.

**Mandatory future fault cases:** Other-platform pre hook fails after ours succeeds; Supervisor begin_backup errors; WebSocket connection lost; post hook absent; timeout while archiver may still run. Verify state never silently transitions to a claimed safe resume, and no partial backup is advertised successful.

Pinned evidence:
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/websocket.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Correction:** Throughout earlier candidate comparisons, references to S1 as "preferred minimal safe" are historical preliminary assessments now **superseded by this section**, pending new source/tests.


## 16. Maintainer approval overlay and immutable snapshot deep audit — 2026-11-06

**Status overlay:** The maintainer approved the product direction after the initial research, so prior "Hub entry still PROPOSED" remarks are historical. [ADR-0011 §12](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06) records the exact approval. One logical Hub/Archive entry, per-console/account separation, single panel/controller, private app-owned HA configuration-root storage direction and retaining archived history are accepted as goals. This does NOT prove technical availability or fix the backup.

The next [source audit](ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md) and [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md) identify no supported custom file-exclusion parameter in reviewed pre/post hook or pinned archive filter. A live DB within the selected config backup tree can be archived alongside a verified immutable snapshot; authority at restore remains unresolved. Online Backup API may restart if other connections modify the source, so bounded termination is required. Snapshot publication requires destination closure, integrity + FK checks, cursor read from snapshot, and a generation-scoped atomic visibility marker. This is still source research with no HA OS tests.
