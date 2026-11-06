# SPEC-013 — Restore authority, storage topology and ledger/config reconciliation

**Date:** 2026-11-06  
**Status:** PROPOSED / NOT_IMPLEMENTED / ALL_TESTS_NOT_RUN  
**Primary source audit:** [HA Core/Supervisor restore authority](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md)  
**Pinned baseline:** Home Assistant Core 2026.11.0 and Supervisor 69848689a1e982ebe92d80e344fc086d8af667db  
**Previous constraints:** SPEC-008 (multi-console), SPEC-009 (global lifecycle), SPEC-010 (crashes), SPEC-011 (paths), SPEC-012 (immutable snapshots), ADR-0004/0006/0007/0008/0010, ADR-0011 (accepted product directions), ADR-0012 (snapshot implementation proposed), ADR-0013 (restore strategy proposed).
**Git:** main documentation only; develop frozen.

> A planned test is not a passed test. The user approved further **investigation**; this does not authorize implementation or silently approve a technical restore strategy. The conceptual Hub/Archive architecture accepted in ADR-0011 remains in force.

## 1. Requirement and guarantee boundary

The future product should maintain one private, owner-validated multi-year history ledger across independent console and optional PSN account entries, with one global HubController and one sidebar. It should never silently replace a valid newer live ledger with an old snapshot, treat an unverified raw archived DB as authoritative, reassign history to a different console/account or fabricate time across an outage.

A full/partial Home Assistant OS backup can select HA config, share/media and other scopes independently. A user or automatic backup can omit data outside config. The OS can replace a configuration folder with an old backup. No source-confirmed universally usable "backup restored" token was found for a custom integration's pre/post hook. If every surviving copy is older than the last committed data, those missing commits are unrecoverable from that archive.

## 2. Authoritative data model (proposals)

| Field | Rule |
| --- | --- |
| home_assistant_instance_id | Diagnostic environment identity; cloned restores are possible, not sole authority |
| hub_config_entry_unique_id | One reserved logical Hub entry ID; not a PlayStation or a ledger |
| hub_config_entry_id | HA's mutable local lifecycle ID; never the historical primary key |
| ledger_uuid | Durable application history namespace |
| lineage_epoch | Versioned restore/fork lineage of the ledger, not a simple timestamp |
| parent_snapshot_uuid | Parent artifact of a *verified* explicit restoration/import (nullable for fresh ledger) |
| stable_source_key | Validated console physical or PSN account namespace |
| source_association_revision | Time- and provenance-scoped relation to HA Config Entries, not interchangeable with physical identity |
| commit_cursor | Monotonic within one valid lineage only; not a cross-fork global ordering |
| snapshot_uuid / hash | Verified immutable source artifact; hash detects accidental mismatch, not origin authorization |
| admitted_runtime_generation | Current source authority fence; invalidated on unresolved restore mismatch |
| restore_decision_id | Explicit authorized user/host decision for selecting a non-live source |
| coverage_revision | Records known committed ranges and unknown gaps without inventing usage |

A cursor and a ledger UUID do not by themselves prove two histories are the same. If branches diverge after the same backup (same ledger_uuid, different contents), larger cursor is NOT an acceptable source-selection algorithm.

## 3. Source authority classifications

- LIVE_VALID: normal SQLite recovery succeeded, schema/integrity/FK and application identity checks passed; preferred for ordinary startup **unless independent evidence of configuration/ledger incompatibility exists**.
- VERIFIED_SNAPSHOT: immutable, locally validated SQLite with exact manifest, readable cursor/UUID, never automatically promoted just by existing.
- VERIFIED_ARCHIVED_SNAPSHOT: snapshot exact bytes were confirmed inside the target archive; no automatic proof that restore happened.
- RAW_ARCHIVED_SQLITE: live DB/sidecars copied during tar; never treated as **known-consistent backup source** merely because it opens.
- EXTERNAL_LIVE: private outside-config live DB requiring a mounted local filesystem and Config Entry/ledger reconciliation; no default backup guarantee.
- FOREIGN_OR_FORKED: different ledger UUID, different lineage or post-ancestor divergence; no automatic append/merge.
- RECOVERY_HOLD: corrupt or ambiguous source, stale entry identities, unsupported schema or missing backup scope; no new historical writes or privileged cross-identity actions until resolved.

**Do not fabricate a "RESTORE_COMPLETED" signal in the backend when only a file timestamp changed.** No official universal source for this signal has been confirmed.

## 4. Candidate storage modes

**Mode T1 (current default direction, conditional):** private /config directory resolved via hass.config.path, outside HACS code; live DB and immutable generations within configuration backup scope. Benefits: portable path, default backup includes snapshot. Failure: raw DB/-wal may also be archived; automatic restore not guaranteed. Permit fail-closed/manual recovery, not unsafe guessing.

**Mode T2 (advanced, optional):** live DB in a verified local private /share subdirectory on HA OS and immutable snapshots in config. Benefits: source not in *config-only* archive. Limitations: Core mount exists in pinned OS, but /share is commonly shared with other apps, can contain network mounts, and is omitted from recommended automatic backups; user-selected share backup can also archive mutable live DB; restoring share/config independently creates two temporal axes; Container may lack share mount.

**Mode T3 (future platform-specific):** dedicated user-configured local private persistent volume and configuration snapshot. Benefits: possible physical isolation from config archive; limitations: installation/mount, OS API, portability, backup selection, privacy, lineage mismatch. Reject requirement for a mandatory volume.

**Mode T4 (not acceptable):** Home Assistant Recorder tables, /config/www, HACS executable directory, .cache as canonical ledger, cloud-only source or NAS WAL by default.

No mode is declared release-ready or universally compatible. The expected initial product should not require the user to provision external databases/mounts.

## 5. Proposed reconciliation process, no executable API yet

1. Acquire an integration-global **recovery gate** and fence new persistence actions for affected owners. Do not block unrelated already-verified source-only current LAN reads longer than needed; never attribute data to an unknown physical console.
2. Enumerate *only* configured, trusted storage roots and user-imported candidate artifacts; no arbitrary scanning of system paths.
3. Inspect each candidate in isolation, respecting SQLite WAL/native recovery. Validate schema, ledger UUID, full integrity_check, foreign_key_check, snapshot manifest digest, source sequence/owner and permitted schema migration.
4. Classify current HA Config Entry identities, disabled/missing entries and source associations against ledger metadata. A restored old entry_id or old IP must not claim a different physical console.
5. Verify common-ancestor or fork status when comparing multiple candidates with the same ledger UUID. An equal cursor with a different event sequence or lineage is divergent; no automatic merge. Hash chain is a potential aid, not guaranteed provenance/authentication.
6. If a live ledger is healthy and mappings are consistent on ordinary start, use live source; don't replace it based on a dormant older snapshot.
7. If provenance is ambiguous, show admin RECOVERY_HOLD with bounded candidate summaries; allow export of existing data before irreversible steps. Verify auth/ACL and consent; warn of lost later records.
8. For approved replacement, fence all SQLite connections, create isolated validation copy, preserve original files, and promote the selected candidate under tested atomic filesystem rules.
9. Record a new restore epoch and parent snapshot only after successful promotion; prevent repeat promotion after reboot. Config Entry registry changes and SQLite ledger promotion are **not** one atomic Home Assistant transaction; stage and reconcile carefully.
10. Resume only for validated console/account owners; use a new runtime generation and mark absent periods UNKNOWN. No automatic credential restoration from a gameplay-history snapshot.
11. Keep explicit diagnostic metadata: source class, chosen committed cursor, backup scope, last evidence time and conservative loss-of-coverage statement, without raw history or tokens in ordinary logs.

## 6. Test catalogue — all NOT_RUN

### 6.1 Topology, mounts and backup scope — 16

| ID | Future scenario | Expected outcome |
| --- | --- | --- |
| RA-PATH01 | Standard HA OS /config source | Supported path, private data outside HACS source |
| RA-PATH02 | Docker HomeAssistant /share bind mount present | Mount is detected, not assumed cross-platform |
| RA-PATH03 | Container installation without /share | No required external path; T1 fallback |
| RA-PATH04 | Recommended automatic backup | Confirm config included, share/media omitted |
| RA-PATH05 | Manual full backup with share selected | Raw live share DB might also be archived; no false authority |
| RA-PATH06 | Backup excludes Recorder history | PlayStation Hub in config not incorrectly treated as excluded |
| RA-PATH07 | Core config-only backup | Immutable snapshot included only if actual archive verified |
| RA-PATH08 | share-only partial backup | No false claim that config snapshot/Hub settings were included |
| RA-PATH09 | Nested network mount inside /share | Identified as unsuitable for default WAL, despite path prefix |
| RA-PATH10 | /share symlink to path outside expected root | Path validation prevents escape and unsafe exposure |
| RA-PATH11 | Local private ext4/btrfs mount candidate | Runtime permissions/fsync/SQLite version validation required |
| RA-PATH12 | /media path with media browser/external mount | Rejected or guarded by privacy and optional backup choice |
| RA-PATH13 | Config restore onto second HA OS device | No assumption former local /share volume transferred |
| RA-PATH14 | Corrupt/incomplete archive member | Doesn't silently become authoritative SQLite |
| RA-PATH15 | Local disk full during snapshot publication | Original live and last good snapshot preserved |
| RA-PATH16 | Backups outside HA's official pipeline | No automatic assumption that pre/post hooks ran |

### 6.2 Lineage, authority and fork detection — 16

| ID | Future scenario | Expected outcome |
| --- | --- | --- |
| RA-ID01 | Same ledger_uuid, same cursor, different events | Fork detected; no automatic selection |
| RA-ID02 | Same ledger_uuid, cursor 200 vs 100, but incompatible lineage | Larger cursor NOT automatically chosen |
| RA-ID03 | Different ledger_uuid, same HA Hub unique ID | Foreign history rejected from automatic adoption |
| RA-ID04 | Same ledger_uuid, verified parent snapshot, validated descendant | Relationship recognized, no claims beyond evidence |
| RA-ID05 | Manifest hash matches but creator untrusted | Byte integrity not treated as authenticity |
| RA-ID06 | Normal restart with valid live cursor 180 and old snapshot 100 | Keep live 180 and don't rewrite it |
| RA-ID07 | Raw archived DB passes integrity_check but differs from validated snapshot | Raw copy classified uncertain |
| RA-ID08 | Snapshot has invalid foreign keys | Reject despite parseability/checksum |
| RA-ID09 | New physical console at old IP after restored config | No old history or keys inherited |
| RA-ID10 | Same PSN account associated with two consoles | No physical ownership inferred from account alone |
| RA-ID11 | Old Config Entry E1 with newer external ledger E2/K2 | Reconciliation required before new attributions |
| RA-ID12 | Same HA instance identity cloned to different hardware | Instance ID alone not authority |
| RA-ID13 | Unsupported newer schema on restore | Read-only/hold; no automatic downgrade |
| RA-ID14 | Snapshot lacks expected committed cursor | Reject as incomplete provenance |
| RA-ID15 | Per-console event sequence gap during restored merge | Mark UNKNOWN and do not invent segments |
| RA-ID16 | Credentials restored to account previously unlinked | Require explicit reauth/review; no silent privilege expansion |

### 6.3 Full/partial restore and crash recovery — 16

| ID | Future scenario | Expected outcome |
| --- | --- | --- |
| RA-REST01 | Full old config restore with live DB in config | Stale historical cursor handled honestly |
| RA-REST02 | Config-only restore with live DB in share | Split-brain older mapping/newer ledger detected |
| RA-REST03 | share-only restore with current config | Inverse split-brain detected |
| RA-REST04 | Config+share restore from same old backup | Selected archive consistency checked; no automatic raw SQLite trust |
| RA-REST05 | New machine config restore, missing external data | Only valid snapshot restored via authorized selection |
| RA-REST06 | Restore archive with valid snapshot+raw main DB/-wal | No blind largest-cursor choice |
| RA-REST07 | Restore archive without snapshot and damaged raw DB | Hold; never create empty ledger |
| RA-REST08 | Restore older snapshot when later independent ledger exists | Explicit loss-of-newer-data warning and pre-restore export |
| RA-REST09 | Process crash mid promotion | Original or fully committed new source, never half-restored state |
| RA-REST10 | Restore marker absent or not trustworthy | No fabricated evidence of restore event |
| RA-REST11 | Multiple repeated boots after authorized restore | One-time promotion and stable lineage |
| RA-REST12 | Hard crash before acknowledged commit | Idempotent replay; no fake seconds |
| RA-REST13 | Untrusted snapshot imported from another HA instance | Validate, isolate and require admin consent |
| RA-REST14 | Backup excludes share but DB lives there | Explicit backup coverage warning |
| RA-REST15 | Rolling back newer code with newer ledger schema | No destructive schema downgrade |
| RA-REST16 | Restoring a 3-year synthetic ledger on HA OS | Data/usage checks against exact snapshot cursor |

### 6.4 Recovery UI, privacy, removal and operations — 16

| ID | Future scenario | Expected outcome |
| --- | --- | --- |
| RA-UX01 | Hub-only archive and no console | Panel loads once, readable authorized reports |
| RA-UX02 | Suspected provenance conflict after startup | "History recovery required", no false empty library |
| RA-UX03 | Unprivileged user requests source listing | Denied; no file enumeration/data leak |
| RA-UX04 | Admin compares two candidates | Bounded sanitized summaries and clear source trust |
| RA-UX05 | Admin chooses older replacement | Explicit confirmation and backup of existing valid data |
| RA-UX06 | Admin keeps current source | No overwrite; restoration warning can be acknowledged |
| RA-UX07 | Admin leaves recovery unresolved | No writing under uncertain owner; read-only as safe |
| RA-UX08 | Auth expires during import | Operation denied/fenced; no partial promotion |
| RA-UX09 | Frontend disconnect during long verification | Bounded operation lease, cleanup/reconnect status |
| RA-UX10 | Export path requested with traversal / symlink | Rejected; no arbitrary filesystem access |
| RA-UX11 | Last physical console entry removed | Archive retained independently of monitor |
| RA-UX12 | Hub entry removed as last entry | No implicit purge; menu behavior documented |
| RA-UX13 | Imported history contains raw Sony tokens | Reject secret leakage and protect separate token store |
| RA-UX14 | Clock jumps after restored backup | UNKNOWN gap and no negative/huge fabricated playtime |
| RA-UX15 | Same game title mapped to different locale/metadata | Stable historical title ID, no cross-owner reassignment |
| RA-UX16 | Backup contains personal history with Recorder excluded | Privacy notice remains accurate |

**Total SPEC-013: 64 newly enumerated planned scenarios** (16 PATH + 16 ID + 16 REST + 16 UX). All NOT_RUN. Previous SPEC-008/009/010/011/012 cases intentionally overlap; never equate enumerated count with unique executable coverage.

## 7. Sign-off gates — 16 OPEN

| Gate | Required evidence | Status |
| --- | --- | --- |
| RA-G01 | Supported private storage topology chosen without extra mandatory service | PROPOSED |
| RA-G02 | Core OS mounts and Container path compatibility tested | BLOCKED_HA_OS |
| RA-G03 | Automatic and partial backup scope verified | BLOCKED_HA_OS |
| RA-G04 | Actual archive members and mutable DB/WAL handling characterized | BLOCKED_HA_OS |
| RA-G05 | Verified immutable snapshot + manifest source integrity | NOT_RUN |
| RA-G06 | Normal startup vs Supervisor restore intent separated or documented limitation approved | PROPOSED |
| RA-G07 | Stable ledger identity and branch/fork reconciliation | NOT_RUN |
| RA-G08 | Config Entry/physical/account identity mismatch safety | NOT_RUN |
| RA-G09 | No automatic historic overwrite on old snapshot | NOT_RUN |
| RA-G10 | Non-destructive admin-guided candidate selection | PROPOSED |
| RA-G11 | Original-files preservation and atomic promotion | NOT_RUN |
| RA-G12 | User-facing gaps, restore-as-of and provenance classes | NOT_RUN |
| RA-G13 | No secret/ACL bypass in recovery API, export and imports | NOT_RUN |
| RA-G14 | Hub-only and zero-entry conditions across restart | NOT_RUN |
| RA-G15 | Live SQLite version/WAL/local filesystem/recovery reliability | BLOCKED_HA_OS |
| RA-G16 | Full/partial restore on two independent installs and future regression | BLOCKED_HA_OS |

## 8. Approval and source boundary

- Maintainer **accepted the research priority** and product-level Hub/Archive architecture previously recorded in ADR-0011.
- Technical topology T1/T2/T3, default restore mode, automatic recovery guarantee, exact path, staging strategy and UI flows are **PROPOSED or BLOCKED**, not silently accepted.
- Do not present lack of a custom archive-filter argument in a pinned implementation as a universal impossibility for future Home Assistant versions.
- No code/test/backup/SQLite file, HA OS host or PlayStation console has been touched.
- If fully automatic lossless restore is later required, upstream API enhancements or a separate user-authorized topology may be needed.

## 9. Sources

- [Deep source audit](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md)
- [ADR-0013 proposal](../decisions/ADR-0013-restore-authority-and-storage-topology.md)
- [SPEC-012 immutable snapshots](SPEC-012-immutable-snapshot-publication-and-backup-admission.md)
- https://www.home-assistant.io/common-tasks/general/backups/
- https://www.home-assistant.io/common-tasks/os/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/backup.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html

**Current result:** 64 NOT_RUN, 16 OPEN, no implementation authorization.


## 10. Administrator-native recovery flow and official restore event qualification — 2026-11-06

[Source-pinned native recovery audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) and [SPEC-014](SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) refine this specification with **72 more NOT_RUN scenarios and 18 OPEN gates**. Prior 64 SPEC-013 cases remain unrun. A new evidence finding is that Supervisor starts Core with a restore job ID and Core's Hassio backup integration can resume restore progress via BackupManager RestoreBackupEvent; this is **real first-party functionality** in pinned 2026.11.0, but not a documented guarantee that a custom integration receives a durable, pre-ledger-open restore-intent token identifying its SQLite snapshot. A stream-only event subscription may miss completed progress before the Hub loads. Default to admin-only source inventory and a two-phase preview/confirm bound to candidate digest, ledger lineage, controller revision and current identity checks. Recovery remains HubController-owned and independent of frontend WebSocket disconnects. Global Repairs must not depend on any removable PS5 entry. No new automatic import/merge or restore authority is approved.


## 11. Local crash-atomic promotion is distinct from source authenticity — 2026-11-06

[ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md), [SPEC-015](SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) and [source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md) propose a generation-based SQLite live cutover rather than replacing an open main DB in place. A pointer and application recovery journal only determine WHICH locally validated working-generation path should be opened and whether the authorized replacement may have committed before the last journal phase. They do not authenticate foreign snapshots, repair old Config Entry associations, guarantee consistent raw SQLite/WAL archive copies or restore commits erased by a whole-config old backup. On pointer/journal discrepancy, validate the referenced SQLite generation, allow native WAL recovery at its unchanged original path, preserve both generations and enter protected RECOVERY_HOLD if trust/identity remains ambiguous. All 64 SPEC-013 cases and 16 approval gates remain unrun/open.
