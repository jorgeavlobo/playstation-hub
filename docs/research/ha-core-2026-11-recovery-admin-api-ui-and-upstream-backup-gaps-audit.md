# Home Assistant Core 2026.11 — Administrator recovery UI/API, persistent ledger reconciliation and upstream backup gaps

**Research date:** 2026-11-06
**State:** OFFICIAL_SOURCE_AUDIT / PROJECT_PROPOSAL / NO_IMPLEMENTATION / NO_TESTS
**Project:** PlayStation Hub (one Marketplace/HACS custom integration and one full-page sidebar); Hub/Archive entry product decision accepted in ADR-0011; per-console and optional PSN account entries isolated.
**Pinned Home Assistant Core:** 2026.11.0 (API and source review, not an approved minimum HA version).
**Pinned Supervisor:** 69848689a1e982ebe92d80e344fc086d8af667db.
**Scope:** Recover historical SQLite evidence after unsafe/partial restore, compare candidates and ledger forks, administrator-only state/preview/confirm/reconciliation flows, sensitive exports, HA Repairs, and whether first-party backup/restore APIs could close a correctness gap.
**Source plan:** [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md), [ADR-0014](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md). Previous [ADR-0013](../decisions/ADR-0013-restore-authority-and-storage-topology.md), [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md), [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md), [ADR-0012](../decisions/ADR-0012-immutable-snapshot-backup-and-restore-authority.md), [SPEC-006](../specifications/SPEC-006-security-privacy-threat-model.md).
**Git policy:** main documentation only; legacy develop frozen.

> Evidence vocabulary: CORE_SOURCE = inspected Core tag; SUPERVISOR_SOURCE = inspected Supervisor SHA; OFFICIAL_GUIDANCE = Home Assistant contributor docs; PROJECT_PROPOSAL = a suggested PlayStation Hub contract; OPEN = unavailable evidence. Architectural review neither runs tests nor proves an integration is operational. Historical research is preserved with dated superseding corrections.

## 1. Executive conclusions

1. **The recovery console can be native.** Home Assistant provides authenticated WebSocket commands, administrator guard, async command handling, per-connection subscriptions, authenticated user context, Repairs and diagnostics. No separate web server, MQTT broker, add-on or external process is needed for the recovery UI itself.
2. **A browser is not the job owner.** The pinned WebSocket async_response decorator schedules a Home Assistant background task; a connection close removes subscriptions but does not demonstrate that a destructive restore task is automatically cancelled or safely completed. The integration-wide HubController must own recovery jobs, durable operation identity and phase transitions independent of the UI connection.
3. **An official Supervisor restore-progress signal DOES exist for the backup integration.** The pinned Supervisor starts Core with SUPERVISOR_RESTORE_JOB_ID while a restore is active; pinned Core hassio/backup.py reads RESTORE_JOB_ID_ENV and resumes observing the Supervisor job. BackupManager publishes RestoreBackupEvent and offers async_subscribe_events; official tests cover restart behavior. This refines prior broad "no restore notification exists" language. But it is **not yet a guaranteed custom integration restore-authority API**: arrival can occur before PlayStation Hub is loaded; events do not identify our snapshot/ledger or establish that a given file originated in that restore; alternative restore methods bypass this route; there is no verified atomic pre-DB-open integration hook. Do not read supervisor environment directly as an approved public API.
4. **Repairs must follow the correct owner.** Core 2026.11's issue registry supports config_entry_id-scoped issues (deleted when that entry is removed); global recovery of shared history must not be attached to the PS5 A entry, as removal could erase the issue while PS5 B/Hub history remains. Use an integration-level repair issue or deliberately attach to the stable logical Hub entry after evaluating its deletion behavior. Distinguish per-console identity conflicts from global ledger corruption.
5. **Recovery must be two-stage.** Candidate discovery/inspection creates bounded, sanitized, read-only summaries; selection must be reconfirmed against current manager generation, candidate bytes/digest, ledger UUID/lineage and source identity immediately before promotion. A stale preview, a revoked admin login or an entry changed mid-review must fail closed.
6. **Same UUID/cursor is not equal content.** Parent snapshot/fork epoch or verified event lineage and physical/PSN association revision are needed. No automatic union of divergent histories and no reassignment by IP, console name or an old Config Entry ID.
7. **No unconditional perfect backup.** The inspected official pre/post backup interface cannot provide a custom file exclusion for the live PlayStation SQLite file, and Core/Supervisor copy selected directories. The backed-up immutable snapshot is stronger than an uncoordinated raw DB copy, but a complete HA archive can still carry both. A successful, locally published snapshot is not necessarily present in a completed Home Assistant backup.
8. **Honest recovery UX is viable while automatic lossless restoration remains unproven.** A hub-only sidebar could remain loaded in a degraded RECOVERY_HOLD state, offer safe inventory and authorized repair without creating LAN probes or discarding persistent data. Closing an issue must require actual state validation, not merely a user's dismissal.

## 2. Official API/source evidence register

| ID | Classification | Pinned source or guidance | Confirmed property / design consequence |
| --- | --- | --- | --- |
| RECUI-01 | OFFICIAL_GUIDANCE | contributors: frontend/extending/websocket-api | Domain-prefixed WebSocket commands, validated schemas, admin decorator, async_response, subscriptions and frontend callWS/subscribeMessage |
| RECUI-02 | CORE_SOURCE | websocket_api/decorators.py at 2026.11.0 | require_admin checks authenticated user's is_admin; async_response schedules an HA background task |
| RECUI-03 | CORE_SOURCE | websocket_api/connection.py at 2026.11.0 | connection close calls unsubscribe cleanup; no automatic rollback/cancellation of an already admitted business recovery transaction is established |
| RECUI-04 | CORE_SOURCE | websocket_api/__init__.py at 2026.11.0 | async_register_command uses a global handler dictionary by command name (one-time integration registration needed) |
| RECUI-05 | OFFICIAL_GUIDANCE | contributors: core/internals/permissions | WebSocket connection.user is available; permissions and administrator checks must occur in backend |
| RECUI-06 | OFFICIAL_GUIDANCE | contributors: core/integrations/repairs | Repair issues may be scoped to a Config Entry, hidden when disabled, deleted when removed; global problems may remain unscoped |
| RECUI-07 | CORE_SOURCE | helpers/issue_registry.py at 2026.11.0 | async_create_issue has config_entry_id optional and async_delete_issue; config_subentry_id is not in pinned function, despite later documentation |
| RECUI-08 | OFFICIAL_GUIDANCE | contributors: core/integrations/diagnostics | Diagnostics files are commonly shared publicly; sensitive details must be redacted or omitted |
| RECUI-09 | SUPERVISOR_SOURCE | supervisor/docker/homeassistant.py pinned | Sets SUPERVISOR_RESTORE_JOB_ID environment for Core when starting with a restore job |
| RECUI-10 | SUPERVISOR_SOURCE | supervisor/homeassistant/core.py pinned | Launches Core with current Supervisor restore job ID when appropriate |
| RECUI-11 | CORE_SOURCE | components/hassio/backup.py 2026.11.0 | Reads RESTORE_JOB_ID_ENV; resumes restore job progress and marks completed/failed using Supervisor job events |
| RECUI-12 | CORE_SOURCE | components/backup/manager.py 2026.11.0 | BackupManager.async_subscribe_events, last_event, last_action_event and RestoreBackupEvent status exist |
| RECUI-13 | CORE_SOURCE | tests/components/hassio/test_backup.py 2026.11.0 | Tests of resuming restore progress after Core restart via environment-provided Supervisor job ID |
| RECUI-14 | CORE_SOURCE | homeassistant/backup_restore.py 2026.11.0 | .HA_RESTORE/.HA_RESTORE_RESULT are specific to the separate Core restore mechanism, not a universal custom integration marker |
| RECUI-15 | OFFICIAL_GUIDANCE | contributors: core/integrations/backup | Backup Agent manages destinations, pre/post platform hooks prepare/resume, no per-app source tar exclusion return documented |
| RECUI-16 | SUPERVISOR_SOURCE | supervisor/homeassistant/module.py pinned | Configuration archived with fixed exclusion patterns, and restored config may replace the directory |
| RECUI-17 | CORE_SOURCE | core.py 2026.11.0 | async_add_shutdown_job runs ahead of STOP background task cancellation; global recovery jobs require bounded shutdown fencing |
| RECUI-18 | OFFICIAL_GUIDANCE | contributors: security/guides/integrations | Administrator-only sensitive WS/actions, explicit trust boundaries, no secrets in UI |

### Source-scope caution: restore progress vs restore authority

The Supervisor job environment and BackupManager RestoreBackupEvent are **more than no signal**. They are real first-party mechanisms. Their current data do not independently furnish the identity/digest of the application's selected SQLite snapshot, the selected backup archive member, all host restore methods, or an atomic callback before PlayStation Hub first opens its data. A later integration can potentially listen through supported BackupManager interfaces once loaded, but must verify availability/order on the target Core version and safely handle missed historical events. **Do not depend on direct os.environ reads of an internal Supervisor variable for a public custom integration contract.** Never treat restore progress "completed" as permission to overwrite a healthy ledger.

## 3. Three separate state machines: source, operation and user interface

### 3.1 Durable history and control state (global per HubController)

    HEALTHY
       -> SUSPECTED_INCONSISTENCY
       -> RECOVERY_HOLD (writes and affected controls fenced)
       -> VERIFIED_CURRENT (admin may choose keep current when safe)
       -> RECOVERY_IN_PROGRESS (exclusive manager-owned lease)
       -> RECONCILE_IDENTITIES
       -> HEALTHY or RECOVERY_HOLD

A healthy current console's live source can remain separately observationally active if no identity/SQL write authority is violated; do not present fresh data as durably committed while history is gated. A compromised/unknown canonical identity disables privileged console control and attributed history writing regardless of UI presence.

### 3.2 Recovery job (durable logical operation, one per ledger)

    CREATED -> INVENTORYING -> VALIDATING_CANDIDATES -> PREVIEW_READY
           -> AWAITING_EXPLICIT_CONFIRMATION
           -> ACQUIRING_EXCLUSIVE_LEASE -> REVALIDATING
           -> PRESERVING_ORIGINAL -> STAGING_CANDIDATE
           -> PROMOTING -> REOPENING -> RECONCILING_ASSOCIATIONS
           -> SUCCEEDED or FAILED_SAFE / RECOVERY_HOLD

Allowed cancellations: before final irreversible promotion where all existing originals remain intact; after promotion begins, cancellation is a *request* and recovery/finalization must reach an explicitly safe point. A browser disconnect never silently implies cancellation. A new operation may proceed only if the prior job has a proved terminal state or a recovery-on-restart protocol.

### 3.3 Browser state (ephemeral)

    DISCONNECTED -> CONNECTED -> VIEWING_STATUS -> VIEWING_PREVIEW
                 -> CONFIRMING -> OBSERVING_JOB -> RECONNECT_RESYNC

Frontend controls are not the source of truth. A page refresh, mobile app suspend or two admin tabs must not start another recovery job, lose a committed decision or resume a half-promotion. Retrying a command with the same idempotency operation key returns the existing job state.

## 4. Proposed recovery authority and snapshot inventory

**Controller inventory, read-only:**
- Configured known live ledger root and its current open/closed manager generation.
- Generation-scoped, locally published immutable snapshot artifacts with complete marker.
- A securely imported candidate archive selected explicitly by an administrator (not an arbitrary filesystem path or URL).
- Any supported, independently verified archive membership metadata available from HA backup APIs.
- Optional mounted external source only when it is part of an approved topology; no recursive filesystem scanning.

**Candidate classes:** LIVE_VALID, VERIFIED_SNAPSHOT, VERIFIED_IN_ARCHIVE, RAW_ARCHIVED_SQLITE_UNTRUSTED, EXTERNAL_LIVE, FOREIGN_OR_FORKED, CORRUPT_OR_INCOMPATIBLE. No class proves time continuity beyond its own last committed source evidence.

**Validation layers:** byte-size/digest under stable immutable file assumption; SQLite integrity_check and foreign_key_check; supported schema and ledger UUID; committed cursor read from the candidate itself; optional lineage parent/epoch and event equivalence evidence; per-owner canonical console/account association checks, gaps and policy revisions. No Sony token import into the history database.

**Safety invariants:** candidate descriptors return opaque ID, not server path. A file hash or larger cursor does not authenticate a source or override an approved canonical identity. Preserve original live data before any replace, and explicitly disclose later records that might be lost when restoring an older snapshot. Never create an empty database over an unreadable or missing-with-recovery-evidence source.

## 5. Proposed future WebSocket API (design only)

Use domain-prefixed names in one global registration path; all recovery commands administrator-only at first release unless an explicitly reviewed read-only exception is accepted.

| Proposed command | Type | Server-side behavior |
| --- | --- | --- |
| playstation_hub/recovery/status | read | Current controller recovery phase, sanitized health, state_revision, active job reference and capability list |
| playstation_hub/recovery/list_candidates | read | Authorized paged candidate descriptions, source class, validity, schema/ledger lineage hints, as-of and uncertainty; **no paths/secrets** |
| playstation_hub/recovery/inspect_candidate | read | Bounded deeper validation on opaque candidate_id; request stays read-only and has a controlled query lease |
| playstation_hub/recovery/preview | read with job | Compare validated candidate against current authorized ledger; create short-lived preview_id bound to current revision, candidate digest and user/session |
| playstation_hub/recovery/confirm | mutation | Require preview_id, expected controller revision and explicit loss-of-recent-data acknowledgement; recheck admin, expiry, bytes, hashes and identity before starting a single manager-owned job |
| playstation_hub/recovery/job_status | read | State of approved job by opaque job_id after reconnect |
| playstation_hub/recovery/subscribe_job | subscription | Bounded progress events; WS close unsubscribes only and does not cancel a job |
| playstation_hub/recovery/cancel_job | controlled mutation | Cancel only in safe phases; otherwise report a recoverability-in-progress status |
| playstation_hub/recovery/keep_current | mutation | Allowed only when current ledger and canonical associations are positively valid; never blindly ignore a corrupt DB |
| playstation_hub/recovery/export | privileged operation | Export validated private history under safe short-lived transfer design; never return arbitrary local path |
| playstation_hub/recovery/acknowledge_warning | limited mutation | May mark a non-destructive advisory seen, but cannot clear a still-real Repairs issue or bypass failed safety gate |

These names and fields are **proposed PlayStation Hub contracts**, not existing HA APIs. HA's schema validation is not a substitute for server authority/lineage checks.

### Preview/confirm two-phase barrier

At preview, the server records an opaque preview token tied to:
- admin user and current Home Assistant authenticated session where supported;
- proposed source candidate ID + content digest/manifest UUID;
- current authoritative ledger UUID/lineage and high-water cursor;
- current HubController/Config Entry association generation and read-only state revision;
- expiry and operation type; no reusable generic permission token.

At confirmation, the backend acquires the global recovery lock and revalidates **all** referenced candidates against a stable filesystem view and current entry identity before admitting promotion. If a new observation, association change, backup restore, competing job or source-file edit occurred after preview, return a STALE_PREVIEW/CONFLICT response and require a new preview. Never trust the display's cached comparison.

Even correct backend ACL does not turn an unintentionally user-uploaded hostile archive into trusted history; scanning, extraction, path limits, decompression budgets and symlink protections are separate concerns.

### Error taxonomy (proposed)

UNAUTHORIZED, NOT_FOUND, INVALID_CANDIDATE, INTEGRITY_FAILED, FOREIGN_LEDGER, FORK_DETECTED, IDENTITY_CONFLICT, INCOMPATIBLE_SCHEMA, STALE_PREVIEW, BACKUP_SCOPE_UNKNOWN, OPERATION_IN_PROGRESS, NOT_CANCELLABLE, RECOVERY_HOLD, DISK_FULL, IO_ERROR, RETRY_AFTER_RESTART. Localized UI messages must not include raw credentials, private timelines or server paths.

## 6. Job ownership, cancellation and reconnect

- Controller-global RecoveryManager owns job identity and durable intent/journal and keeps a bounded operation registry independent of WebSocket connection objects. Exactly one exclusive promotion per ledger.
- Future code must not rely on WebSocket @async_response task cancellation/creation to serialize/finish a multi-minute file promotion. WebSocket disconnect automatically unsubscribes connection callbacks; active recovery remains a separately managed backend job.
- A restore job can outlive a browser; the same admin can reconnect and query status. An admin's revoked rights must prevent *new* commands, preview/confirm and sensitive reads, without creating an inconsistent half-restored DB.
- Lifecycle authority remains fenced across Config Entry reloads, all-console removal and global Home Assistant shutdown; on power loss the job journal must distinguish prepared/staged/promotion-in-progress vs committed restore generation.
- Source/candidate changes invalidate previews. New recovery process after restart does not blindly replay a destructive confirmation or interpret a pending client command as permission.
- Avoid unbounded queues, reader connections and JSON output; stream or paginate only reviewed safe metadata. A cancelled browser query releases its bounded read lease; an admitted durable promotion must settle explicitly.
- Shutdown and timeout warnings do not constitute proof that an executor thread stopped. Do not reopen the SQLite writer until prior worker closure is verified.

## 7. Identity and association reconciliation

Canonical physical console ID and optional PSN account ID remain separate from HA entry_id, logical Hub unique ID, ledger UUID and snapshot UUID. Restoring an old Config Entry may bring back an IP/name/PSN association that no longer corresponds to physical hardware.

**Authority constraints:**
- Do not use an old HA Config Entry ID to identify a physical console; only validated console identity binds it.
- If source hardware isn't online, archived records may be browsed with privacy controls, but no new attributions/control claims are made until verified.
- On mismatch, preserve independent historical segments and retain provenance; no bulk rewrite or delete of prior history.
- A different ledger UUID is a foreign import, not an automatically adopted continuation. Same ledger UUID with different lineage is a fork, not a union by max cursor.
- PSN credentials and Remote Play pairing material belong to dedicated repositories; restoring historical sessions never automatically relinks, reauthorizes or refreshes Sony tokens.
- Use explicit user decisions for mapping where supported after genuine hardware verification; absent hardware validation means hold, not arbitrary merge.

A separate repair type for one console's pairing problem may be attached to that console's Config Entry. A shared ledger recovery issue should be integration-global or attached only to the accepted Hub root with a documented behavior after Hub removal; never attach it only to one removable physical console.

## 8. Repairs, diagnostics and privacy

**Official Repairs**: create a stable issue_id, translated message, severity and supported learn_more_url to the recovery instructions; do not invent a private direct config-flow repair link. Core 2026.11 supports global issues and config_entry_id. A global ledger corruption issue should remain visible while relevant entries are loaded. Clear only after independent post-restore verification, not user dismissal. If the last entry is removed and integration stops loading, document recovery entry reinstallation and issue cleanup.

**Diagnostics**: prefer strict allowlist: HA source version, integration version, schema version, health state, numbers of candidates/owners, most recent verified snapshot status, error classes and sanitized operation phase. Exclude ledger rows, game title/player details, raw console/PSN identifiers, paths, SHA digests if linkable, tokens/keys, user identity, imported archive bytes and full stack traces. Existing diagnostics helper redact_data is helpful but not a substitute for allowlist.

**Privacy**: Archive upload/import is a potentially untrusted and personal data-bearing file. A production import pathway needs size/time/ratio/decompression limits, reject directory traversal/symlink/hardlink cases, file type/schema validation and administrator authentication. No arbitrary URL fetch, browser path, HTTP static serving or direct SQLite database export as an untrusted URL.

**Recommended default**: admin-only recovery and private archive reports until the historical data ACL/roles and multi-user privacy expectations are explicitly approved. Never expose private history merely because a sidebar is visible.

## 9. First-party backup gap assessment

### 9.1 Existing official capabilities (confirmed in pinned source)

- BackupAgent is a **destination transport**, not an application-specific filter for the source Home Assistant configuration archive.
- A custom integration backup.py platform has async_pre_backup and async_post_backup, but **no documented parameter** to return a file-exclusion set or snapshot-include mapping.
- Core and Supervisor use built-in excludes for the configuration archive. Live PlayStation Hub db/wal may be copied beside a verified immutable snapshot, so backup consistency still needs unambiguous authority.
- Supervisor restore job ID is passed to Core through an environment variable and the **backup integration** can resume job progress after restart. This is real but insufficient for a guaranteed custom, durable, pre-ledger-open restore intent.
- Core BackupManager exposes RestoreBackupEvent and async_subscribe_events for runtime observers. Its events do not prove exactly which custom DB/snapshot file is current or whether it was present and verified in the archive.
- Repairs and WebSocket/diagnostics provide first-party administrative building blocks, not complete multi-file application data restore transactions.

### 9.2 Possible upstream extension A — source archive inclusion/exclusion manifest

**Proposal only; no GitHub issue/PR created.** Add a documented integration-scoped backup artifact contract (perhaps platform metadata rather than an arbitrary blacklist) enabling integrations to present a verified immutable snapshot and explicitly omit only their own live, mutable SQLite files/sidecars **for the applicable backup scope**. Scope verification, file ownership and arbitrary-path protection are critical. Prefer allowlisted application-owned data directory and backup-time snapshot handle over a global user-supplied filesystem exclude, with OS/Container/Supervisor parity.

Constrain to a guaranteed *pre archive* snapshot-ready handoff; if the integration cannot prepare a consistent artifact, the backup must be able to mark app data as failed/incomplete, rather than simply archive a moving database and claim success. Design for cancellation and absent post hook.

### 9.3 Possible upstream extension B — restore provenance / integration lifecycle callback

**Proposal only; no GitHub issue/PR created.** Provide a stable, documented, integration-consumable restore operation identity plus selected backup/scope metadata, bound to the **Core startup and file replacement lifecycle** so a custom integration can choose safe recovery mode before it opens a backed-up private database. The signal must survive Core restart, work with enabled Hub-only entry and be idempotent, and must state when the configuration scope was restored vs when only share/media was restored. It must avoid leaking private filenames, credential contents or backup job tokens to arbitrary integrations.

The mechanism should be durable and structured (not a transient event lost before the integration loads), and distinguish restore intent, archive copy completion, and post-start restoration finished. A successful Supervisor job alone cannot prove a custom SQLite snapshot is valid; the application must still validate its own artifacts.

### 9.4 Practical recommendation

Do **not** open upstream issues before deciding requirements and verifying existing supported capabilities against the exact target release; issue text, threat model, failure cases and upstream routing should be reviewed by the maintainer. If the first release accepts administrator-guided recovery after unusual ambiguous restores, both extensions can remain optional upstream improvements rather than mandatory blockers. If automated, lossless, no-click recovery of arbitrary old HA OS backups is a hard product requirement, no source-supported guarantee is currently established and upstream work may be needed.

## 10. Remaining design questions for maintainer / next research

- Which recovery situations may load Hub/Archive as successful but RECOVERY_HOLD, instead of rejecting Config Entry setup and losing the panel?
- What storage survives a failed promotion and a new process startup, and which exact file operations are atomic on supported HA OS disks?
- What is the safe admin UX when candidate ancestry is unresolved, or two candidates claim the same ledger UUID but have diverged?
- Which reports remain readable in RECOVERY_HOLD without misrepresenting a tentative candidate as authoritative?
- What event subscriptions, if any, may be used safely from BackupManager when the integration loads after the Supervisor restore progress has already finished?
- Would dedicated upstream extensions materially improve the first release enough to justify maintenance burden? No filing authorized.
- How to avoid a long-lived private export/download leaking outside HA authentication or via cached browser/HTTP URLs?
- Which test fixtures can model a genuine hardware console identity change without needing real Sony credentials?

## 11. Primary official references

- https://contributors.home-assistant.io/frontend/extending/websocket-api/
- https://contributors.home-assistant.io/core/internals/websocket-api/
- https://contributors.home-assistant.io/core/internals/permissions/
- https://contributors.home-assistant.io/core/integrations/repairs/
- https://contributors.home-assistant.io/core/integrations/diagnostics/
- https://contributors.home-assistant.io/security/guides/integrations/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/connection.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/__init__.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/issue_registry.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/tests/components/hassio/test_backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/backup_restore.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/core.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py
- https://www.sqlite.org/backup.html
- https://www.sqlite.org/wal.html

## 12. Outcome

A first-party-compatible administrator recovery design, an explicit distinction between real Supervisor restore-progress support and unproven per-integration restore authority, and two *unfiled* upstream API enhancement proposals. **Nothing implemented, tested, uploaded to the user's HA installation, or filed upstream.** All technical ADRs remain PROPOSED pending maintainer approval/HA OS tests; only ADR-0011's product architecture is ACCEPTED.
