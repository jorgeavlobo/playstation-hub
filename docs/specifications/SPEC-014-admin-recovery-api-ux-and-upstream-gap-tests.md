# SPEC-014 — Administrator-guided recovery, WebSocket API, ledger reconciliation and upstream backup interface tests

**Date:** 2026-11-06
**Status:** PROPOSED / NOT_IMPLEMENTED / ALL_TESTS_NOT_RUN
**Research:** [Official-source admin recovery and upstream API audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md)
**ADRs:** [ADR-0014 PROPOSED](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md), [ADR-0013 PROPOSED](../decisions/ADR-0013-restore-authority-and-storage-topology.md), [ADR-0011 ACCEPTED product architecture](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md).
**Previous specifications:** SPEC-006/008/009/010/011/012/013. Latest previous reference: [SPEC-013](SPEC-013-restore-authority-storage-topology-and-reconciliation.md).
**Pinned upstream:** Home Assistant Core 2026.11.0, Supervisor 69848689a1e982ebe92d80e344fc086d8af667db.
**Branch:** main documentation only; develop remains frozen.

> The maintainer requested continuing the research and documentation. That does NOT accept the technical recovery algorithm or authorize running tests, writing code, filing upstream issues or changing an installation.

## 1. Acceptance objective

The **approved one-panel Hub/Archive integration architecture** must eventually support a first-party-compatible administrator-only recovery interface without generating physical LAN traffic from its Hub-only mode, without violating Home Assistant authentication/authorization or losing valid historical evidence during a stale backup restore.

All proposed operations are under a single integration-global HubController and durable RecoveryManager; the WebSocket client is never the sole lifetime owner of a potentially destructive file replacement.

## 2. Proposed invariants

| ID | Future mandatory requirement |
| --- | --- |
| AR-I01 | Recovery is accessible through the same authenticated PlayStation Hub sidebar; no external server or MQTT required |
| AR-I02 | In RECOVERY_HOLD the Hub/Archive entry may remain loaded with limited safe API even if ledger cannot open; no silent empty DB |
| AR-I03 | Repair issue representing global history cannot be deleted with one removable console entry |
| AR-I04 | Privileged recovery reads, imports, previews, exports, confirmations and cancellations require backend admin authorization |
| AR-I05 | Candidate IDs and job IDs are opaque; browser never receives writable path, OAuth token, full SQL data or private raw trace |
| AR-I06 | Candidate inventory and validation are bounded and read-only, with filesystem/traversal/symlink and DoS protection |
| AR-I07 | Snapshot cursor, ledger UUID and integrity evidence must originate from independently validated candidate bytes |
| AR-I08 | Matching ledger UUID or high-water cursor is never proof that two histories are identical |
| AR-I09 | Preview token binds candidate digest, generation, admin principal, current ledger revision and expiry |
| AR-I10 | Confirm acquires global recovery gate and REVALIDATES all authority and ACL before any promotion |
| AR-I11 | An expired, stale or replayed confirmation cannot replace a newer live ledger |
| AR-I12 | Exactly one active promotion per ledger; other competing requests join same idempotent job or fail clearly |
| AR-I13 | Original live data is preserved before promoting a chosen candidate; progress is recorded safely across crash |
| AR-I14 | Cancellation is allowed only in explicitly reversible phases; after promotion starts it must reach safe terminal/recovery state |
| AR-I15 | Browser disconnect removes its subscriptions, never implicitly aborts a database promotion |
| AR-I16 | Admin revocation or session expiration disables new privileged requests, not the integrity of an already admitted atomic operation |
| AR-I17 | Hardware/PSN identity mismatch fences control and new attribution, never silently reattaches history to an IP/name |
| AR-I18 | Recovery to old snapshot results in UNKNOWN intervals and new generation, not retroactive playtime |
| AR-I19 | Selected data source classification remains visible: live valid, published snapshot, archive verified, raw untrusted, external/forked or corrupt |
| AR-I20 | Published local snapshot is not automatically a completed HA backup or authorized restore |
| AR-I21 | No upstream restore event is assumed universal; Supervisor job env/progress is first-party evidence only within its documented scope |
| AR-I22 | No custom per-file archive exclusion is claimed from existing pre/post backup hook or BackupAgent |
| AR-I23 | Diagnostics and Repairs are sanitized, stable, scoped and refreshed only after real verification |
| AR-I24 | Imported archive is parsed as hostile data with strict size/decompression/time, permissions, schema and path protections |

## 3. Future UI workflow (one panel, no implementation)

    Archive / Recovery
       -> HEALTHY, ordinary historical browsing
       -> RECOVERY_REQUIRED, explicit banner + Repairs link
       -> Candidate inventory (read-only, source class, date, durable cursor)
       -> Inspect candidate (bounded validation + sanitized summary)
       -> Compare current vs selected (lineage + coverage + affected console IDs)
       -> Preview generated (opaque TTL, expected controller revision)
       -> Second confirmation (possible irreversible loss of newer records)
       -> Server-owned job admitted (exclusive restore lease)
       -> Progress subscription OR reconnect/status polling (no duplicate job)
       -> Identity reconciliation (strict canonical keys, no assumed credentials)
       -> Final verification / success, safe failure, or recovery hold

Only an administrator may access the default recovery flows. Never expose raw SQLite paths or allow a browser to provide unreviewed filesystem path input. Read-only archived reports can remain available where the candidate is independently validated and the user's data-access policy permits it, but require explicit provenance labelling and never enable wake/standby under an identity conflict.

## 4. Proposed backend command contract (not registered)

| Proposed type | Operation | Allowed state / critical validation |
| --- | --- | --- |
| playstation_hub/recovery/status | Read sanitized controller and job status | Admin-only; small response |
| playstation_hub/recovery/list_candidates | Paged known candidates | Admin-only; server-owned paths and scope |
| playstation_hub/recovery/inspect_candidate | Read-only independent verification | Candidate lease, size/time limit |
| playstation_hub/recovery/preview | Prepare candidate impact diff and ephemeral preview | Bind candidate hash, ledger generation, ACL, expiry |
| playstation_hub/recovery/confirm | Admit exclusive persistent recovery job | Reverify admin/expected revision/digest/lineage/remaining space |
| playstation_hub/recovery/job_status | Status after browser reconnect | Admin-only, known opaque job ID |
| playstation_hub/recovery/subscribe_job | Progress subscription | Connection-owned unsubscribe only; bounded event buffer |
| playstation_hub/recovery/cancel_job | Safe cancel request | No cancellation in irreversible transaction phase |
| playstation_hub/recovery/keep_current | Explicitly retain verified live ledger | Reject invalid/unverified source and clear issue only after health checks |
| playstation_hub/recovery/export | Secure scoped export | Separate reviewed authorized transfer; no raw path |
| playstation_hub/recovery/acknowledge_warning | UI acknowledgement only | Cannot dismiss an active corruption or identity conflict |

All commands are design identifiers, not part of Home Assistant. Every command requires a versioned schema and translated messages, and server-side authority independent of UI visibility.

## 5. Job and file promotion safety contract

A RecoveryManager operation must be owned by the global HubController, not by one console Config Entry, WebSocket handler task or browser. It uses an idempotent job ID, a durable intent/recovery journal, bounded query and backup leases, a generation fence, pre-promotion preservation of original data and post-promotion revalidation. The browser may subscribe/unsubscribe without changing database mutation ownership. A browser refresh cannot accidentally trigger second apply; a Power failure must leave an original copy or a fully verified new generation and trigger safe recovery on next start.

The proposed preview token binds expected current controller revision, candidate file UUID/hash, expected ledger UUID/lineage/cursor, permissions and expiry. A different candidate file, snapshot publication, console identity change, live commit or already running job invalidates it. Confirming a stale preview returns a conflict; the UI must rerun inspection. Do not hold an asyncio lifecycle lock during SQLite I/O, hash computation or user approval.

After promotion begins, an arbitrary cancellation or permission revocation must not interrupt the transaction mid filesystem replacement and claim success. The safety outcome depends on proved file atomicity, WAL close, idempotent recovery journal and explicit reconcile state; this is an implementation test gate, not guaranteed by HA.

## 6. Test matrix: 72 NOT_RUN cases

### 6.1 HA WebSocket ACL, recovery UI and Repairs — 18 NOT_RUN

| ID | Future test | Expected behavior |
| --- | --- | --- |
| AR-UX01 | Hub entry only, valid archived DB | One sidebar and read-only history; no LAN probe |
| AR-UX02 | Hub-only with corrupted ledger | Hub loads RECOVERY_HOLD UI, does not create empty DB |
| AR-UX03 | Global repair issue while PS5 A removed | Repair stays while shared history problem exists |
| AR-UX04 | Per-console repair issue when that entry removed | Correct scoped issue removed without affecting global repair |
| AR-UX05 | Non-admin invokes each recovery command | Rejected, no candidate enumeration/side effects |
| AR-UX06 | Admin with current auth previews a candidate | Response sanitized, bounded and with provenance class |
| AR-UX07 | UI refresh while recovery running | Reattaches to same job without new promotion |
| AR-UX08 | Two browser tabs subscribe to same job | One backend job, independent subscriptions |
| AR-UX09 | Mobile app suspend/disconnect mid recovery | Backend operation continues safely, subscription unsubscribed |
| AR-UX10 | Candidate contains personal game/player titles | Generic diagnostics exclude private data |
| AR-UX11 | Global repair issue is ignored by user | Actual unresolved corruption remains fenced |
| AR-UX12 | Recovery verifies fully healthy after restore | Issue deleted or properly cleared, no premature success |
| AR-UX13 | Invalid unsupported frontend API version | Error/refresh prompt without mutation |
| AR-UX14 | Frontend shows snapshot locally published, not archived | No "verified HA backup" claim |
| AR-UX15 | Unsupported custom recovery file path supplied | Reject; no local file exfiltration |
| AR-UX16 | Backend auth revoked during preview | New confirmation denied |
| AR-UX17 | No available safe recovery source | Explain hold/available export path; no fabricated history |
| AR-UX18 | UI translation and screen reader accessibility | Clear safety/irreversible-warning localized controls |

### 6.2 Preview, confirm, job ownership and crash safety — 18 NOT_RUN

| ID | Future test | Expected behavior |
| --- | --- | --- |
| AR-JOB01 | Admin creates preview with valid current revision | Opaque scoped expiring token issued |
| AR-JOB02 | Candidate file content changes after preview | Confirm rejects stale hash/size |
| AR-JOB03 | Current live ledger advances after preview | Confirm rejects outdated controller/cursor |
| AR-JOB04 | Device/Config Entry association changes after preview | Confirm rejected until new identity review |
| AR-JOB05 | Preview expired or used twice for new promotion | No double restore |
| AR-JOB06 | Two admins confirm different candidates concurrently | One exclusive job; conflict response for other |
| AR-JOB07 | Browser closes immediately after confirm | Job continues or safely aborts under manager ownership |
| AR-JOB08 | Admin revokes during admitted promotion | No new authorization; admitted job reaches safe state |
| AR-JOB09 | Cancel during preflight/staging | Safely cancelled, original preserved |
| AR-JOB10 | Cancel after irreversible promotion begins | Not cancellable, safe completion/recovery required |
| AR-JOB11 | Process kill after original preservation | Startup finds recovery journal and keeps evidence |
| AR-JOB12 | Process kill between file promotions | No mixed half-promotion accepted |
| AR-JOB13 | Storage full during preservation | No destructive action, recoverable error |
| AR-JOB14 | Worker thread remains active after cancel | No unsafe reopen of same database path |
| AR-JOB15 | Reload one console during recovery | Other source/Hub lifecycle safe, affected writes fenced |
| AR-JOB16 | Last configured console removed during job | Hub controller retains recovery lease and one panel |
| AR-JOB17 | Shutdown before job admission | Fences admission, preserves data and preview expiration |
| AR-JOB18 | 100 retries same idempotent job ID after reconnect | One resulting promotion and audited outcome |

### 6.3 Ledger candidates, physical identity and account privacy — 18 NOT_RUN

| ID | Future test | Expected behavior |
| --- | --- | --- |
| AR-ID01 | Two candidates same ledger UUID and cursor but different events | Fork/incompatibility detected |
| AR-ID02 | Candidate greater cursor but incompatible lineage | No "largest cursor" auto-choice |
| AR-ID03 | Foreign ledger UUID with same Hub unique ID | No auto-adoption; admin import policy only |
| AR-ID04 | Hash matches but attacker controls both manifest and payload | No claim of authenticated origin |
| AR-ID05 | Current valid live ledger and old dormant snapshot | Keep current on ordinary reboot |
| AR-ID06 | Raw DB/WAL from tar opens normally | Remains untrusted as application-consistent backup |
| AR-ID07 | SQLite integrity passes, foreign_key_check fails | Candidate rejected |
| AR-ID08 | Older HA Config Entries but newer external ledger | Reconciliation hold for affected identities |
| AR-ID09 | Different physical console at same IP | No history or credential inheritance |
| AR-ID10 | Same PSN account linked to two consoles | No automatic attribution to one physical console |
| AR-ID11 | Account token restored after unlink | No silent reauthorization or history proof |
| AR-ID12 | No hardware available during recovery | Read-only archive where safe, no control |
| AR-ID13 | Restore with missing recent observations | Explicit UNKNOWN coverage, no backfill |
| AR-ID14 | Snapshot from newer SQL schema | Read-only/unsupported, no destructive migration |
| AR-ID15 | Candidate from alternate HA instance | Explicit import and identity review required |
| AR-ID16 | One owner corrupted but others sound | Bounded isolation/repair versus global corruption policy |
| AR-ID17 | Candidate import with symlink/path traversal | Reject unsafe paths and sidecar inclusion |
| AR-ID18 | Candidate decompression bomb / huge file | Size/time/ratio caps, no HA event loop starvation |

### 6.4 Restore signals, backups and proposed upstream extension tests — 18 NOT_RUN

| ID | Future test | Expected behavior |
| --- | --- | --- |
| AR-UP01 | Supervisor restarts Core during restore with job env | Pinned backup integration reads job; not assumed custom stable API |
| AR-UP02 | BackupManager emits RestoreBackupEvent after restart | Subscriber can observe when loaded, order verified |
| AR-UP03 | Restore finished before PlayStation Hub loads | Must not rely solely on transient subscription |
| AR-UP04 | Direct Core .HA_RESTORE used | Distinct mechanism, not confused with Supervisor job |
| AR-UP05 | External backup restoration bypasses HA | No invented restore event/authority |
| AR-UP06 | Config-only restore from Supervisor | Scope metadata correct, ledger source inspected |
| AR-UP07 | Share-only restore | Conflicting Config Entry/ledger revisions detected |
| AR-UP08 | Backup already contains raw DB and immutable snapshot | Does not automatically trust raw files |
| AR-UP09 | Custom platform pre/post tries to supply exclusions | No assumed supported API in pinned implementation |
| AR-UP10 | BackupAgent used as destination | Not treated as source tar filter |
| AR-UP11 | Provisional upstream file-include/exclude API contract modeled | Only own verified data files, no global arbitrary paths |
| AR-UP12 | Malicious integration attempts to exclude another domain's files | Source ownership validation rejects |
| AR-UP13 | Proposed restore intent callback delivered before first DB open | Can fence safely, startup ordering test |
| AR-UP14 | Proposed callback arrives after app setup | Fail-safe detection/recovery, no stale auto-promotion |
| AR-UP15 | Backup excludes PlayStation data under new policy | Backup metadata clearly marks not covered |
| AR-UP16 | Hook succeeds but Supervisor tar fails | Published != archived; not advertise success |
| AR-UP17 | Restore progress says completed but snapshot hash invalid | No automatic promotion |
| AR-UP18 | Two consecutive restores/backups with different scopes | No confusion between jobs, consent, lineage and source metadata |

**Exactly 72 test definitions** (18 UX + 18 JOB + 18 ID + 18 UP), all NOT_RUN. Intentionally overlaps SPEC-008 through SPEC-013. This count is not executable coverage.

## 7. Sign-off gates: 18 OPEN

| Gate | Evidence required | Status |
| --- | --- | --- |
| AR-G01 | Hub RECOVERY_HOLD loads with no console and one sidebar | NOT_RUN |
| AR-G02 | Stable integration-level Repairs lifecycle across console unload | NOT_RUN |
| AR-G03 | Admin-only WS recovery commands and backend permission checks | NOT_RUN |
| AR-G04 | Privacy-safe, bounded candidate inventory/diagnostics | NOT_RUN |
| AR-G05 | Two-phase preview/confirm with revision and digest revalidation | PROPOSED |
| AR-G06 | One manager-owned recovery job independent of browser disconnect | NOT_RUN |
| AR-G07 | Safe cancel, shutdown and interrupted promotion recovery | NOT_RUN |
| AR-G08 | Same UUID/cursor fork detection, no silent merge | NOT_RUN |
| AR-G09 | Physical console/PSN identity and credential separation | BLOCKED_HARDWARE |
| AR-G10 | Existing live bytes protected before restore | NOT_RUN |
| AR-G11 | Restored gaps and historical coverage verified | NOT_RUN |
| AR-G12 | Schema, SQLite integrity/FK, lineage and checksum validations | NOT_RUN |
| AR-G13 | Pinned Supervisor restore job ID and BackupManager event source verified | SOURCE_REVIEWED / HA_OS_NOT_RUN |
| AR-G14 | Event ordering and missed startup events characterized | NOT_RUN |
| AR-G15 | Current archive excludes and upstream gaps documented exactly | SOURCE_REVIEWED / HA_OS_NOT_RUN |
| AR-G16 | Feasibility of upstream include/exclude / restore intent extension reviewed | PROPOSED |
| AR-G17 | Real HA OS full/partial restore and cross-install simulation | BLOCKED_HA_OS |
| AR-G18 | Explicit maintainer acceptance of recovery policy, docs, UX, export and safe restoration limits | OPEN |

## 8. Design review only — explicit non-goals

- No implementation, no Python/SQL/TS/JS source, no new feature branch, no real PS5 communications.
- No GitHub issues/PRs opened in Home Assistant Core/Supervisor; upstream suggestions are research artifacts.
- No claim that a restore event exists for every method, that all backups contain application snapshots, or that a snapshot eliminates raw live DB archive ambiguity.
- No automatic reading of unknown local files; never accept arbitrary browser-supplied paths or private history in a URL.
- No claiming official Bronze/Silver/Gold/Platinum certification for custom integration.
- Product-level Hub/Archive architecture remains ACCEPTED from ADR-0011; technical recovery remains PROPOSED.

## 9. Sources

- [Primary source audit](../research/ha-core-2026-11-recovery-admin-api-ui-and-upstream-backup-gaps-audit.md)
- [ADR-0014 proposal](../decisions/ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md)
- [ADR-0013 topology/authority](../decisions/ADR-0013-restore-authority-and-storage-topology.md)
- [SPEC-013 restore lineage](SPEC-013-restore-authority-storage-topology-and-reconciliation.md)
- https://contributors.home-assistant.io/frontend/extending/websocket-api/
- https://contributors.home-assistant.io/core/internals/permissions/
- https://contributors.home-assistant.io/core/integrations/repairs/
- https://contributors.home-assistant.io/core/integrations/diagnostics/
- https://contributors.home-assistant.io/core/integrations/backup/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/decorators.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/websocket_api/connection.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/issue_registry.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/hassio/backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/tests/components/hassio/test_backup.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/backup/manager.py

**Result:** 72 NOT_RUN scenarios and 18 OPEN gates; documented source evidence, no code/tests/HA OS install or upstream issue submission.


## 10. Crash-atomic journal and promotion linkage — 2026-11-06

[Official SQLite/POSIX audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](../decisions/ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) and [SPEC-015](SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) now specify the candidate durable backend behind this admin preview/confirm workflow. A RecoveryManager confirmation is not completed merely when the WebSocket handler returns or os.replace runs: live SQL connections and workers must be positively closed; recovery intent and phase revisions are durable; candidate lives at a distinct SQLite path; one small active pointer publication chooses the generation; the journal can lag the pointer after crash. Admin reconnection must inspect selected pointer/journal and never replay an already selected new generation or destroy an older valid source. Host HA Config Entries remain independently reconciled, and a restored older /config may roll pointer+journal+data back together. SPEC-014 retains its own 72 unrun tests and 18 open gates; SPEC-015 adds 80 distinct enumerated fault cases and 20 gates, all unrun.


## 11. Separate administrator ledger genesis vs restore/import — 2026-11-06

[First-boot source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md), [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md) and [SPEC-018](SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) distinguish one new proposed administrator CREATE_NEW_HISTORY operation from RECOVERY_PREVIEW, RESTORE_COMMIT, ARCHIVE_IMPORT and ordinary Hub Config Entry creation. A new Hub can be LOADED internally INITIALIZATION_REQUIRED without live SQL history; no create-capable existing SQLite open is allowed. Any prior pointer/journal/snapshot/legacy file or inaccessible root requires recovery classification, not an implicit new ledger. User must explicitly choose Create New after a privacy-safe inventory and current admin preview/confirm.

Provisioning is one manager-owned idempotent job: durable CREATE_INTENT with op/ledger/generation UUIDs -> isolated exclusive SQLite stage -> transactional genesis and empty durable cursor -> close/independent validation -> selected active pointer -> backend acknowledgment. A browser disconnect, duplicate Hub Flow or competing admin Create/Import cannot create a second ledger UUID. Prior SPEC-014 72 cases and 18 gates remain NOT_RUN/OPEN; the new SPEC-018 defines 80 additional cases and 20 open gates. No WebSocket command exists yet.
