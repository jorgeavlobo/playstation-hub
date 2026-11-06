# ADR-0014 — Administrator-guided history recovery, native HA API and upstream backup gaps

**Status:** PROPOSED — recovery policy and API pending maintainer sign-off; no implementation/tests
**Review date:** 2026-11-06
**Purpose:** Define the preferred user recovery workflow and source-of-truth model without assuming automatic restoration of arbitrary old SQLite copies.
**Primary evidence:** [Pinned Home Assistant source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md)
**Acceptance plan:** [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md) (72 NOT_RUN cases, 18 OPEN gates).
**Existing accepted architecture:** [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md) — logical Hub/Archive entry, separate physical console/account entries, one integration/panel/controller, retained private history.
**Depends on:** ADR-0004/0006/0007/0008/0010, ADR-0012/0013, SPEC-006/008–013.
**Pinned evidence:** Home Assistant Core 2026.11.0; Supervisor SHA 69848689a1e982ebe92d80e344fc086d8af667db.
**Git:** documentation main only; legacy develop unchanged.

> The maintainer asked to document and advance research. No user approval of the exact recovery API, automatic promotion policy or upstream feature request is implied. The previous ADR-0011 conceptual acceptance remains binding; this ADR remains PROPOSED.

## 1. Context and non-negotiable boundary

PlayStation Hub's user may have multiple PS5 consoles, PSN accounts, years of durable sessions and a logical Hub-only archive after physical console removal. Normal restarts, corrupted DB, old Home Assistant full/partial restore, imported archives, or out-of-config external data could leave different live and snapshot histories.

A current live SQLite DB and an old snapshot may both be internally consistent. Even files with the same ledger UUID and commit cursor can diverge after a restore fork. A raw DB copied by the Home Assistant directory archiver alongside a validated immutable snapshot is **not** a proven consistent backup source. No automated algorithm based only on file mtime, largest cursor, HA Config Entry ID or matching PSN names is safe.

We need an administrator-only guided recovery protocol that can preserve current evidence, validate source authority and reconcile console identity before enabling more historical writes or hardware control. Requiring external servers would violate the accepted product architecture.

## 2. Preferred architecture (PROPOSED, not implemented)

- **HubController** remains the only process-wide lifecycle singleton. Owns the ledger, recovery gate, panel and namespaces, but the Hub Config Entry is just a persistent configuration/load anchor, not a SQLite writer.
- **RecoveryManager** is an internal conceptual service within HubController, with one durable recovery job per ledger generation and bounded read-only candidate inspectors.
- **RecoveryCatalog** enumerates only expected safe internal storage roots, immutable published snapshots and explicitly imported validated archives. No arbitrary path scanning.
- **AuthorityEvaluator** validates DB integrity, foreign keys, schema, ledger/lineage, committed cursor and current console/account association revisions; does not infer cryptographic identity from LAN host-id alone.
- **RecoveryJob** preserves originals, stages the authorized replacement, reconciles schema/associations, records a new restore epoch and unknown historical gaps. The durable job is not tied to WebSocket connection lifetime.
- **Hub Panel** presents a localized, admin-only Recovery Required/Compare/Preview/Confirm/Progress/Review flow. Never exposes raw paths, tokens or unrestricted history in candidate summaries.
- **Repairs** posts a global shared-ledger issue with stable issue ID; removing one PS5 must not delete it. Per-console identity repairs may be scoped to the corresponding entry.
- **Diagnostics** returns a strict allowlist of versions/error classifications/counts without user history or account identifiers.

All components are conceptual, not requests to create placeholder files.

## 3. Evidence for native WebSocket and first-party restore progress

**Official Core 2026.11.0 facts:**
- WebSocket decorators support validated domain-prefixed command schemas, require_admin, async_response and subscriptions.
- Connection close removes WS subscriptions, not a proven cancellation of an independent background recovery job.
- BackupManager exposes async_subscribe_events, last_action_event and RestoreBackupEvent.
- The Supervisor provides SUPERVISOR_RESTORE_JOB_ID to Core at startup when restoring; the official Hassio backup integration resumes tracking the job, and tests prove this path exists in the pinned version.
- Repairs supports config_entry_id-scoped issue cleanup; global ledger issues must not depend on a removable console's entry.
- Diagnostics must avoid private contents that users could publish in bug reports.

**Critical qualification:** Supervisor job progress and BackupManager events are **real**, but not a guaranteed authenticated per-integration, durable, pre-ledger-open restore intent with a snapshot digest and archive member provenance. They do not cover every external restore method or every partial scope and may arrive before PlayStation Hub setup. The internal SUPERVISOR_RESTORE_JOB_ID environment variable is not an advertised public API for custom components. Evaluate a documented BackupManager event subscription as optional advisory evidence only, under pinned HA lifecycle tests, not as sole restore authority.

## 4. Preferred recovery lifecycle and two-phase confirmation

**State model proposal:**

    HEALTHY
      -> SUSPECTED_INCONSISTENCY
      -> RECOVERY_HOLD
      -> VALIDATING_CANDIDATES
      -> PREVIEW_READY
      -> AWAITING_ADMIN_CONFIRMATION
      -> EXCLUSIVE_REVALIDATION
      -> PRESERVE_OLD_SOURCE
      -> STAGE_AND_PROMOTE
      -> REOPEN_AND_RECONCILE
      -> HEALTHY | RECOVERY_HOLD

**Evidence source selection order:**
- Normal startup with unambiguously valid current live ledger and consistent mapped identities: do not replace it due to a dormant staged snapshot.
- Verified immutable snapshot: valid source candidate, not an automatic command to restore.
- Raw tar-copied DB/WAL: untrusted for backup consistency until independently validated and explicitly accepted under a supported import policy; do not rank above snapshot just by a newer cursor.
- Foreign or diverged same-UUID lineage: hold; no auto-merge; user must be shown impact and provenance.
- Corrupt/unreadable data: preserve bytes and hold; never fabricate a fresh empty ledger in place.

**Two-phase admin operation:**
1. The server enumerates, validates and calculates a preview. It generates an opaque short-lived preview ID bound to admin, current source/candidate digest, ledger generation, expected state revision, identity associations and scope.
2. On confirm, admin privileges and all bound facts are rechecked under the controller's exclusive recovery gate. Any concurrent observation/candidate change, incompatible schema, revoked permissions or expired preview invalidates confirmation.
3. Before promotion, preserve original live data and write a crash-recoverable job intent. Close/verify all SQLite handles and worker generations. Stage and validate new data in a separate file; only then promote using filesystem operations proven safe on the supported target.
4. After promotion, new runtime generation/restore lineage and uncertainty gaps. Bind only independently verified console/account identities; no automatic Sony token reauthorization. Clear global repair only after verification. Do not treat UI request completion as proof of durable success.

**Cancellation:** Cancel safely before irreversible phase; once promotion begins, return NOT_CANCELLABLE and allow owner to finish/rollback safely according to a tested journal. Browser disconnect does not revoke atomic operations. A client refresh can query existing job by opaque ID. A repeated confirm must not double-promote.

## 5. Native user experience and access

The future panel shows source trust class, schema, last confirmed committed cursor/as-of timestamp, missing coverage and identity conflicts. A potentially destructive button requires clear confirmation when newer valid records may be lost. "Keep current" is available only for a positively validated source; it cannot silence a detected corruption issue. Never include private gameplay history in global Repairs text.

Administrator-only commands initially. Read-only archive access for other HA users may be an explicitly reviewed future feature, not an automatic inheritance of administrator privileges. The frontend sends only opaque object IDs and expected revision, never filesystem paths or untrusted URLs.

## 6. First-party upstream API gaps (PROPOSED research only)

**Gap A: app-scoped backup source filter / immutable artifact.** Reviewed pre/post hooks do not accept a per-integration include/exclude mapping for mutable application DB/WAL. The upstream feature candidate is an ownership-scoped registration of an immutable application snapshot and its manifest, with exclusion of only app-owned live files within selected backup scopes. It must defend against malicious integrations excluding other components' files, and make snapshot preparation failures visible to the backup job.

**Gap B: trusted restore intent/provenance on integration boot.** Supervisor Core has a restore job environment and backup manager progress events, but an app-level, durable, pre-database-open callback or query returning restored archive/scope identity is not documented. A possible upstream extension could expose a one-shot, integration-scoped restore manifest/intent with selected scope and completion state, surviving Core restart, before the integration accesses restored app files.

**Priority judgment:** Do not file public issues yet. A first implementation may be possible with honest administrator-guided restoration and verified snapshot exports. If effortless, always-correct restore is required, upstream API design may become a blocking dependency. No claim that upstream maintainers have approved these ideas.

## 7. Rejected or deferred alternatives

| Alternative | Why |
| --- | --- |
| Browser-side SQL or file replacement | Breaks backend data security, consistency and permissions |
| One WebSocket coroutine directly owns promotion | Disconnect/reload cannot be treated as safe transaction lifecycle |
| Arbitrary raw file paths or URLs from browser | Path traversal, data disclosure, SSRF and malicious archive input |
| Snapshot present = restore requested | Normal restart could erase newer valid records |
| Same ledger UUID or max cursor = same history | Forked post-restore histories can differ |
| Unverified old Config Entry matching IP = physical-console identity | Can reattribute history and authorize wrong console |
| Automatically re-link Sony tokens from gameplay archive | Violates credential isolation and scope |
| Global Repairs issue attached only to PS5 A | Removing PS5 A could delete an unresolved shared issue |
| Assume BackupManager event is guaranteed before storage setup | Unsupported in the pinned integration lifecycle evidence |
| Promise full auto recovery of unavailable post-backup commits | Impossible without surviving newer copy |

## 8. Approval checklist

Before this ADR can become ACCEPTED technically:
- Maintainer approval of explicit admin-guided recovery limits, source comparison, loss-of-newer-data confirmation and no silent multi-ledger merge.
- Source/test proof of Hub RECOVERY_HOLD load, global Repairs issue, per-entry issue cleanup and correct browser authorization/reconnect.
- Verified archive candidate safety, lineage and identity gates, including real PS5 identity blockers.
- Manager-owned job durability, cancel/retry/restart behavior and atomic file promotion on target HA OS.
- Pre-backup published snapshot vs raw file authority, encrypted export and secret/privacy controls.
- Optional BackupManager progress subscription tested across Core restart; no assumed internal environment contract.
- HA OS/Container installation matrix and custom frontend localization/accessibility.
- All relevant SPEC-014 test cases and release gates executed in future authorized implementation.

**Status:** ADR-0014 PROPOSED, SPEC-014 72 cases NOT_RUN / 18 gates OPEN, ADR-0011 product choices ACCEPTED. No implementation permission or upstream submission.

## 9. Primary references

- [Source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md)
- [SPEC-014](../specifications/SPEC-014-admin-recovery-api-ux-and-upstream-gap-tests.md)
- [ADR-0013](ADR-0013-restore-authority-and-storage-topology.md)
- https://contributors.home-assistant.io/frontend/extending/websocket-api/
- https://contributors.home-assistant.io/core/internals/permissions/
- https://contributors.home-assistant.io/core/integrations/repairs/
- https://contributors.home-assistant.io/core/integrations/diagnostics/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/connection.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/issue_registry.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/docker/homeassistant.py

**Research outcome:** first-party-compatible recovery architecture proposed and documented, no code/tests/real backup or upstream issue created.
