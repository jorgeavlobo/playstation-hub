# ADR-0013 — Restore authority, portable SQLite storage topology and administrator recovery

**Status:** PROPOSED — technical decisions pending maintainer approval and tests
**Date:** 2026-11-06
**Scope:** Choosing an authoritative historical database after OS backup restore, while respecting approved independent physical-console/PSN entries and the logical Hub/Archive entry
**Related:** [Source audit](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md), [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md), [ADR-0011 ACCEPTED product architecture](ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0012 proposed snapshots](ADR-0012-immutable-snapshot-backup-and-restore-authority.md), ADR-0004/0006/0007/0008/0010.
**Pinned source:** Core 2026.11.0; Supervisor 69848689a1e982ebe92d80e344fc086d8af667db; official HA OS/backup guidance
**Branch:** main documentation only, develop unchanged.

> The maintainer accepted proceeding with this priority, NOT a final automatic restore algorithm or external mount requirement. Product decisions approved in ADR-0011 remain accepted. This ADR is a *technical proposal*, separate from those decisions. No code/tests or user data has been changed.

## 1. Decision problem

A future PlayStation Hub user expects uninterrupted multi-year historical storage, backups included with normal Home Assistant OS configuration backups and correct restore, while LAN monitors continue and the integration requires no extra database service. We can create a validated immutable SQLite snapshot, but the Supervisor can still archive live SQLite files alongside that snapshot. At restore time configuration and /share can be replaced separately. A copy from a different time may be physically valid and yet incompatible with restored console/account configuration or other database copies.

The project needs explicit definitions for **which source is operational**, **which is merely a recovery candidate**, **when automatic selection is safe**, and **what happens when evidence is missing**.

## 2. Existing binding product invariants

**ACCEPTED already (ADR-0011):** one HACS/Marketplace custom integration; one full-page panel; one process-global HubController; independent physical-console and optional PSN account entries; a user-confirmed logical Hub/Archive Config Entry; private app data outside HACS source with configuration-root storage as the preferred direction; retention after entry removal until explicit deletion; no mandatory MQTT/add-on/external SQL service.

**NOT implied by that acceptance:** a specific SQLite backend/worker, absolute file path, HA OS SQL implementation, guaranteed automatic backup/restore, network mount, secret store, recovery UX or preservation of commits that were never backed up.

## 3. Source facts relevant to the choice

1. Pinned Supervisor's Docker HomeAssistant mounts /config read-write, /share and /media read-write, /ssl read-only. **This proves reachability only for this image, not cross-install support or privacy.**
2. The official recommended HA OS automatic backup includes configuration but normally omits share/media; manual and partial backups choose scopes separately.
3. Pinned Supervisor config restore removes/copies selected config tree. Folder restore similarly replaces selected folder content, handles nested network mounts and can be selected independently of config.
4. Pinned Core/Supervisor backup filters are fixed in these implementations and the documented custom pre/post platform hook does not provide an arbitrary file-exclusion return contract. Backup agents provide backup destination agents, not source tar filters.
5. SQLite WAL live DB and -wal cannot safely be assumed an application-consistent copy just because the directory archiver finished. An immutable Online Backup API snapshot is an independently validated source.
6. Core .HA_RESTORE is a separate Core restoration route; no universal, verified per-integration Supervisor-restored-intent notification has been demonstrated.

## 4. Options considered

| Candidate | Main benefit | Main risk | Position |
| --- | --- | --- | --- |
| T1: Private /config live ledger and immutable snapshots in /config | Portable default and snapshot in normal HA config backup | Raw DB/WAL also archived; selected restore may overwrite newer history | Preferred default *direction*, technical validation still conditional |
| T2: Live /share database, snapshot in /config | Separates live source from config-only archive on HA OS | share not backed up by default; multi-app access; user can include share; old config/new share split-brain | Advanced candidate, not default |
| T3: External user-provided private local volume + config snapshots | Potential physical isolation of live source | No universal HA Core mount/API or backup selection, high setup burden, reinstall/migration issues | Optional future feature only |
| T4: App-owned data in HACS source, .cache or /config/www | No separate integration data setup | Update/deletion risk, ephemeral cache, public exposure | Rejected |
| T5: Backup Agent as dynamic config tar exclude | Has supported agent API | Agent stores/transports backups and does not define input exclusions in reviewed API | Rejected as claimed solution |
| T6: Monkey-patch Supervisor filters, symlink tricks, rename live WAL mid-archive | Might avoid one particular archive member | Unsupported/unreliable under upgrades and file locking | Rejected |

**Recommendation:** keep T1 as the default *storage direction* for a first integrated product, but explicitly limit any restore promise to verified backup snapshots and admin-assisted candidate selection until an independently trustworthy restoration authority protocol is available. No automatic choice based on "largest cursor", "most recent mtime", same HA instance ID, or same ledger UUID alone.

## 5. Proposed recovery authority hierarchy

1. An unambiguously valid live ledger on ordinary restart with consistent current identity/config mapping is the operational source, not an old dormant snapshot.
2. A published immutable snapshot with validated manifest, matching snapshot-contained ledger UUID/cursor/integrity/FK is a **verified recovery candidate**, not a self-executing restore instruction.
3. Source archive file membership may further verify the copy was in the archived backup, but does not by itself establish that a restore just occurred.
4. Raw live SQLite files copied during tar are **not proven coherent backup artifacts**; do not automatically outrank the verified snapshot because they contain a higher cursor.
5. An external live ledger paired with restored older HA config needs identity revision reconciliation; neither side silently wins.
6. Foreign/forked ledgers require protected admin review and cannot be auto-merged; matching ledger UUID/cursor does not prove matching events.
7. Without trusted signal or user approval, uncertainty enters RECOVERY_HOLD. Preserve existing bytes and offer read-only, redacted diagnostics while protecting control operations.
8. Successful user-authorized promotion installs a fresh runtime generation, records restore lineage and unknown historical gaps, without inventing data from after an old backup's committed cursor.

**No false guarantee:** If only an old snapshot survives, data from after that snapshot is irrecoverable from it. Requiring an administrator to select the source prevents silent loss but does not create absent data.

## 6. The Config Entry / ledger split-brain scenario

Suppose the old configuration contains console entry E1 mapped to canonical physical console K1. A separate /share ledger contains newer E2/K2 association after replacement of the console. Restoring only config from an old archive leaves E1 paired with the newer ledger. Auto-reassigning that ledger to E1 because its friendly name or IP matches can corrupt historical attribution or grant unintended Remote Play/PSN control rights.

**Proposed invariant:** physical console and account identities remain canonical, Config Entry IDs are lifetime owners, and the ledger stores independent association revisions. On mismatch, affected write attribution and privileged actions are fenced until the administrator confirms an identity-safe reconciliation. The logical Hub/Archive entry can stay available for historical read-only reports.

## 7. Recovery user experience and operational policy

The single accepted sidebar should be able to present:
- An explicit "History recovery required" state, rather than blank statistics.
- A short, privacy-safe comparison of available source types, validated cursor, snapshot time, schema and which scopes were selected in the backup where known.
- A warning before overwriting a source with later records or diverged lineage.
- Protected export of current original bytes before an authorized replacement.
- A clear "Keep current" / "Recover from validated snapshot" administrative choice **only when safely applicable**; avoid unapproved imported binary paths and unauthorized requests.
- Unobserved elapsed intervals clearly marked UNKNOWN, not inferred playtime, after restoring an older copy.
- Separate credential reauthentication/re-pairing, not automatic authorization copied from the historical ledger.

This UI/API design is still a proposal. Backend authorization, revocation, bounded file parsing and import validation need tests before use.

## 8. Explicit research decisions for this phase

| Decision aspect | Status |
| --- | --- |
| Continue research on storage topology and restore authority | ACCEPTED_BY_MAINTAINER |
| Existing ADR-0011 conceptual Hub architecture | ACCEPTED (already) |
| T1 portable private /config default as a direction | CONDITIONAL, not final path or backup guarantee |
| Immutable SQLite snapshot as preferred backup research mechanism | ACCEPTED_RESEARCH_DIRECTION, ADR-0012 proposed implementation |
| Raw file archive automatically selected as authoritative | REJECTED_DESIGN_PROPOSAL |
| Automatic restore from largest cursor or newest file | REJECTED_DESIGN_PROPOSAL |
| Automatic external /share as live SQL home on all install types | NOT_APPROVED |
| Administrator-guided fail-closed recovery | PROPOSED, recommended |
| Ledger-fork detection and Config Entry reconciliation | PROPOSED, required correctness target |
| Guaranteed lossless automatic restore of any full/partial HA backup | NOT_SUPPORTED_BY_REVIEWED_SOURCE; remains OPEN |
| Executable work/feature branch/HA OS restore tests | NOT_AUTHORIZED |

## 9. Acceptance criteria

- Source and backup scopes must be verified on targeted HA Core/OS and Container instances with synthetic files.
- One unambiguous source or admin decision after every simulated full/partial restore, including restored share without config and vice versa.
- Current live DB never overwritten merely by presence of older staged snapshots.
- No history grafting based on IP/PSN display name, no privileged action under identity conflict.
- No silent raw-live SQLite tar copy promoted as backup-consistent.
- Restore selected under an exclusive controller recovery gate; original files preserved, one-time decision and post-restore unknown gaps.
- Unsupported/foreign schema or SQLite library cannot cause destructive automatic migration.
- Privacy-safe snapshot import/export/admin ACL, no Sony credentials in history backups.
- Support paths and permission requirements documented honestly and no mandatory extra service.

A future test plan may be approved independently from implementation. None of these criteria is currently tested.

## 10. Source register

- [Research](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md)
- [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md)
- [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [ADR-0012](ADR-0012-immutable-snapshot-backup-and-restore-authority.md)
- https://www.home-assistant.io/common-tasks/general/backups/
- https://www.home-assistant.io/common-tasks/os/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/backups/manager.py
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html

**Outcome:** Technical ADR remains PROPOSED and unimplemented. main-only documentation; develop untouched. No manual user decision was silently inferred about the final backup topology.


## 11. Official Supervisor restore-progress mechanism and native admin recovery — 2026-11-06

**ADR-0013 remains PROPOSED.** The [new pinned Core/Supervisor source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md), [ADR-0014](ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md) and [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) refine the source evidence. In the pinned Supervisor, Core is launched with SUPERVISOR_RESTORE_JOB_ID during an active restore; the official Hassio backup integration reads RESTORE_JOB_ID_ENV, resumes job progress and sends RestoreBackupEvent through BackupManager. Tests in Core 2026.11.0 verify this first-party behavior. Earlier statements in this ADR that **no restoration event has been shown** must be read as **no verified, universal custom integration pre-database-open restoration authority with snapshot provenance**; a first-party restore-progress mechanism DOES exist.

The backup manager also offers async_subscribe_events, but a custom integration cannot assume it will subscribe before an event is emitted, that an event identifies which application SQLite bytes were restored, or that a non-Supervisor restore uses it. For ambiguous/corrupt/forked source selection the preferred technical option remains administrator-guided RECOVERY_HOLD, provenance validation, two-phase preview/confirm, original-file preservation and identity reconciliation, rather than a silent highest-cursor selection. Hub-only loading and one panel remain approved at product level through ADR-0011. No new technical decision, code or test was accepted.


## 12. Crash-atomic active generation pointer and journal follow-up — 2026-11-06

**ADR-0013 remains PROPOSED.** [Official SQLite/POSIX audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) and [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) propose a separate live SQLite generation per user-approved promotion, a single small atomic active pointer and an independently durable application recovery journal. These solve a narrower issue than ADR-0013: safe cutover between already validated local sources while preserving old bytes. They do NOT make an archived raw SQLite/WAL copy consistent, prove that a Supervisor restore happened, or recover records absent from every surviving backup.

Source boundaries: official SQLite warns that renaming an open database, detaching its hot WAL/journal or reusing the same filename with stale connections may corrupt it. POSIX os.replace provides one-entry atomicity, and parent-directory fsync is needed to make rename durable on the tested storage. HA Config Entry registry and the SQLite pointer cannot be atomically promoted together; require identity reconciliation and RECOVERY_HOLD on mismatch. A full config restore may replace pointer, journal and selected-generation directories as one older set, so fresh lineage and independent backup copies remain necessary. F2 remains unapproved technical research; one logical Hub/Archive entry and separate physical-console entries remain accepted conceptually.


## 13. First installation cannot be inferred from a missing restored SQLite file — 2026-11-06

[Official first-boot/SQLite source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018](ADR-0018-first-boot-consent-and-ledger-provisioning.md) and [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) clarify the recovery source problem after a full or partial Home Assistant restore. A restored old config may have a Hub Config Entry with no current live ledger, or the opposite: retained private history after the Hub was removed. Neither case is a safe reason to create a new empty SQLite file. Existing selected data must open with non-creating URI mode and positive schema/ledger lineage validation. Permission denied, incorrect mount, symlink, missing old generation or snapshot, and inherited CREATE_INTENT all require their own classification rather than a "fresh installation" result.

If all local evidence vanished in an older backup restore, no program can infer with certainty that prior history never existed; the user must be offered import/restore as well as a deliberate new ledger option. An explicit administrator CREATE_NEW decision can create a distinct, new empty lineage after a bounded trustworthy inventory, but cannot recover erased sessions. A new Hub Config Entry's reserved logical unique ID does not grant authority to attach an old different ledger UUID or reauthorize a physical console/PSN account. The final restore authority method in ADR-0013 remains PROPOSED; no tests have been run.
