# SPEC-018 — First-boot ledger classifier, explicit provisioning and no-create reopening

**Date:** 2026-11-06
**Status:** PROPOSED / ALL_TESTS_NOT_RUN / NO_IMPLEMENTATION_AUTHORIZED
**Source research:** [Home Assistant/SQLite/Python first-boot audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md)
**Technical ADR:** [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md) PROPOSED
**Prior accepted product architecture:** ADR-0011 one user-confirmed Hub/Archive Config Entry, independently configured PS5/PSN entries and one global controller/panel.
**Prior technical contracts:** SPEC-008–017, ADR-0004/0008/0009/0013/0015/0016/0017.
**Pinned source baseline:** HA Core 2026.11.0, SQLite official open_v2/URI, Python 3.14 os/sqlite3, pinned Supervisor restore route.
**Git:** main documentation only; develop unchanged.

> These contracts are **future acceptance criteria**, not software already implemented, tested or product policies newly accepted by the maintainer. No executable fixture is created by this specification.

## 1. Goal

The Home Assistant PlayStation Hub must never silently create a new empty SQLite history merely because an expected file is missing, unreadable, a Config Entry exists, a current data path changed, or an older configuration backup was restored.

A brand-new logical Hub can be configured without physical PlayStations. Historical ledger creation is a separate, privileged and idempotent operation following non-destructive source inspection and explicit administrative intent. If an attempted initialization is interrupted, the system must resume/classify that *same* operation, not allocate a second ledger UUID or generation.

## 2. Proposed invariants

| ID | Required proposed behavior |
| --- | --- |
| FB-I01 | All existing-ledger opens use SQLite URI mode=rw or mode=ro; no create-if-missing default. |
| FB-I02 | SQLite mode=rwc is restricted to a positively authorized *new isolated staged generation* under an exclusive provisioning lease. |
| FB-I03 | Missing path, permission error, corrupt DB, unsupported schema, missing mount and unknown inventory are different results; none silently means new history. |
| FB-I04 | A Hub Config Entry existing does not certify that its ledger was successfully initialized. |
| FB-I05 | A missing Hub Config Entry does not authorize deleting or overwriting old retained history. |
| FB-I06 | First-run UI presents new vs recovery/import alternatives and requires an explicit authorized CREATE_NEW selection. |
| FB-I07 | No local evidence is described as "no local history found", not proof that the user never had historical data. |
| FB-I08 | A known pointer, journal, staged generation, old flat DB, published snapshot, ledger UUID or associated old entry blocks ordinary first-run create. |
| FB-I09 | All file inventory must be bounded to private known roots and distinguish errors from confirmed absence. |
| FB-I10 | Unexpected symlinks/hardlinks, permission or path containment mismatches fail closed rather than enabling creation. |
| FB-I11 | No unrestricted recursive scan, arbitrary URL or untrusted browser path is used to detect history. |
| FB-I12 | The logical Hub unique ID is separate from ledger_uuid, active generation UUID, HA entry_id, console and PSN unique IDs. |
| FB-I13 | The integration manifest must permit multiple independent Config Entries; single_config_entry cannot be used for a domain that also supports console/account entries. |
| FB-I14 | Config Flow uses official stable unique ID and abort-if-already-configured behavior, including concurrent duplicates. |
| FB-I15 | HA Config Entry creation and SQLite ledger provisioning are independent, recoverable phases, not falsely treated as one atomic transaction. |
| FB-I16 | Hub can be HA LOADED with internal INITIALIZATION_REQUIRED/RECOVERY_HOLD and one admin UI without any historical SQL writer. |
| FB-I17 | An idempotent CREATE_INTENT is durably published before new SQLite generation creation, with generated operation/ledger/generation UUIDs. |
| FB-I18 | New staging generation is exclusively created; an existing unexpected generation directory triggers conflict, not overwrite. |
| FB-I19 | An empty or incomplete staged SQLite file is not an active trusted historical database. |
| FB-I20 | New schema and genesis metadata commit atomically inside the new SQLite generation before it is selected. |
| FB-I21 | The new generation is independently closed, integrity/FK/schema/UUID validated and durably published before active pointer selection. |
| FB-I22 | Only a verified active pointer, completed journal and canonical owner mapping may open the global DURABLE_WRITE gate. |
| FB-I23 | After a crash, same provision_op_uuid can resume/classify one initialization; no second ledger_uuid is silently generated. |
| FB-I24 | If pointer committed but UI acknowledgement was lost, new operation retry returns existing selected ledger after validation. |
| FB-I25 | If pointer still old or absent while new staging exists, user/admin reconciliation may be required; no automatic destructive selection. |
| FB-I26 | Simultaneous Hub entries, console setup and two admin creation attempts cannot create parallel live writers or genesis ledgers. |
| FB-I27 | sqlite3.connect default create semantics are never used in generic history preflight; use explicit SQLite non-create modes. |
| FB-I28 | Preserve SQLite native hot WAL/journal companions, never remove them to force a new empty file. |
| FB-I29 | Existing legacy flat-format data requires a separate migration/import decision and no empty reset. |
| FB-I30 | A new logical ledger does not create Sony credentials or assert physical console identity. |
| FB-I31 | Any first-run consent is bound to a current user/preview/controller generation and must revalidate inventory before committing. |
| FB-I32 | A full Home Assistant backup restore may roll back all local files; the application never claims to recover absent later commits. |

## 3. State classifier and precedence

**Evidence input types:** native Hub entry (exists, enabled, newly created, restored); known ledger association; application storage root inspection result; pointer/journal presence/validity; selected/current generations; standalone snapshots; legacy data; SQLite non-creating open result; HA backup/restore hints; permission/storage errors; source identity/worker state.

**Candidate classifier states:**

- NO_HUB_CONFIGURED
- HUB_CONFIGURED_UNPROVISIONED
- CANDIDATE_FRESH (requires admin choice, not empty directory alone)
- PROVISIONING_IN_PROGRESS
- PROVISIONING_COMMIT_UNCERTAIN
- READY_EXISTING
- LEGACY_DATA_PRESENT
- RECOVERY_REQUIRED
- STORAGE_INACCESSIBLE
- CORRUPT_OR_UNSUPPORTED
- FOREIGN_OR_FORKED
- RESTORE_AMBIGUOUS
- NO_ENTRIES_ENABLED

Higher-severity preservation evidence wins: permission/mount uncertainty, prior journal or snapshot, current DB corruption, lineage mismatch or unknown restore state must prevent auto-new. READY_EXISTING requires positive pointer/DB/identity validation. If nothing local is observed, UI still offers recovery/import and requires CREATE_NEW consent. A durable Create Intent plus an unselected staged generation is a provisioning recovery problem, not a fresh second install.

## 4. Config Flow and ledger provisioning protocol

**A. Home Assistant logical Hub Config Flow (official mechanism, future app behavior):**
1. User chooses Hub/Archive; official UI creates a stable reserved Hub unique ID, with duplicate-flow and duplicate-entry abort, independent of console/PSN keys.
2. HA persists entry according to its own lifecycle; no SQLite history is presumed to exist solely from entry creation.
3. The entry may load a typed control-plane runtime in INITIALIZATION_REQUIRED or RECOVERY_HOLD without historical writer. It offers the administrative options "Create new history" and "Recover or import existing history".
4. A console Config Flow remains separate and may also exist before the historical ledger is ready; source observations cannot write history before global gate opens.

**B. Application-controlled CREATE_NEW_HISTORY (PROPOSED):**
1. Admin requests initialization; backend checks current HA admin ACL and generates a short-lived choice/preview receipt after bounded read-only inventory.
2. On confirmation, a single process-global provisioning lease revalidates root state, absence/conflict and operation generation. If any prior evidence appears, deny and switch to recovery inventory.
3. Reserve unique provision_op_uuid, ledger_uuid and generation_uuid; durably publish CREATE_INTENT before writing new SQLite data.
4. Exclusively create a new generated staging generation directory; only within this strictly new stage may SQLite use create mode (rwc). Ordinary existing-source opens always use rw/ro.
5. Create versioned genesis schema, empty evidence cursor, lineage metadata, association revision and provision operation identity in a single SQLite transaction. No physical PlayStation/PSN owner invented.
6. Explicitly close and validate new SQLite DB, integrity_check, foreign_key_check, schema and UUID match; ensure no live handle or hot unresolved destination.
7. Durably publish generation completion and READY_TO_COMMIT journal revision; select one generation with ADR-0015's atomic active pointer after confirming all old workers closed and current intent is still valid.
8. Validate selected pointer and DB, reconcile Hub entry association and enable historical write gate only after completed active-source checks.
9. Return a durable receipt for the same provision_op_uuid; reconnect/retry must never create another ledger if active pointer already selected.
10. Error at any stage means preserve candidate bytes/intents, classify INITIALIZATION_INTERRUPTED or RECOVERY_HOLD, no unconditional fallback into a fresh create.

No unsafe assumption that an async Home Assistant Config Entry save and an app-owned SQLite file/pointer can form one atomic commit. Config Flow duplicates must be guarded both by official unique ID and a controller-scoped provisioning lease.

## 5. Test matrix: 80 cases, all NOT_RUN

### 5.1 Classifier, missing path and permissions — 20 NOT_RUN

| ID | Future scenario | Expected behavior |
| --- | --- | --- |
| FB-CLASS01 | No Hub entry, no local data seen | Offer Config Flow; no proof historical data never existed |
| FB-CLASS02 | New Hub entry exists but no Create Intent | INITIALIZATION_REQUIRED, no auto-created SQLite |
| FB-CLASS03 | Existing Hub entry, expected DB absent | Prior provenance/inventory determines recovery, not blind new |
| FB-CLASS04 | Pointer present, selected generation missing | RECOVERY_REQUIRED; preserve known files |
| FB-CLASS05 | Pointer missing, completed snapshot exists | Recovery candidates; no blank DB |
| FB-CLASS06 | Old hot WAL and absent/old main file | CORRUPT/INCOMPLETE; do not delete WAL |
| FB-CLASS07 | Existing file zero-byte/not valid SQLite | Incomplete/corrupt, never automatically CREATE TABLE |
| FB-CLASS08 | Permission denied while stat/open root | STORAGE_INACCESSIBLE, not fresh |
| FB-CLASS09 | Unmounted storage or I/O error | STORAGE_INACCESSIBLE, retry/Repair |
| FB-CLASS10 | Root is unexpected symlink | Fail closed, no traversal |
| FB-CLASS11 | Existing file is wrong type or link | Reject, preserve and report |
| FB-CLASS12 | Unsupported/newer schema | Hold; no destructive downgrade |
| FB-CLASS13 | No current DB but old legacy flat DB exists | LEGACY_DATA_PRESENT, offer migration |
| FB-CLASS14 | Hub deleted but archived generation retained | Existing data discovered on explicit re-onboarding |
| FB-CLASS15 | Config restored older than external ledger | RESTORE_AMBIGUOUS, identity reconciliation |
| FB-CLASS16 | Snapshot foreign ledger UUID | FOREIGN_OR_FORKED; no adoption |
| FB-CLASS17 | Empty readable private directory, admin not confirmed | No database created |
| FB-CLASS18 | Empty readable private directory, admin confirms | Authorized candidate fresh path, not global proof |
| FB-CLASS19 | os.path.exists returns false while permissions differ | Explicit open/stat exception wins |
| FB-CLASS20 | Unknown inventory due timeout/race | UNKNOWN/RECOVERY_HOLD, not fresh |

### 5.2 Create Intent, genesis and crash points — 20 NOT_RUN

| ID | Future scenario | Expected behavior |
| --- | --- | --- |
| FB-CREATE01 | Config Entry saved, crash before Create Intent | Hub unprovisioned; recover UI, no DB |
| FB-CREATE02 | Intent temp file partially written | No valid intent; preserve and classify |
| FB-CREATE03 | Intent durable but staging absent | Resume same operation IDs |
| FB-CREATE04 | Staging directory exclusive mkdir finds existing | Conflict rather than overwrite |
| FB-CREATE05 | Mode=rwc used on unapproved existing main path | Contract rejects |
| FB-CREATE06 | Mode=rw used on missing prior DB | Fails non-destructively |
| FB-CREATE07 | Crash after SQLite file created before schema BEGIN | Partial stage never selected |
| FB-CREATE08 | Crash between schema statements | Entire schema genesis rolled back or untrusted |
| FB-CREATE09 | Crash after schema COMMIT before connection close | No pointer until closure/verification |
| FB-CREATE10 | New ledger UUID disagrees with persisted intent | Reject |
| FB-CREATE11 | Integrity succeeds but FK check fails | Staged candidate invalid |
| FB-CREATE12 | Disk full before staged generation published | Preserve intent/old copies, no READY |
| FB-CREATE13 | Crash after validated generation before metadata marker | No unverified activation |
| FB-CREATE14 | READY_TO_COMMIT durable, active pointer absent | Safe approval/resume, no second ledger UUID |
| FB-CREATE15 | Pointer swap succeeds but acknowledgment lost | Retry returns already-selected ledger |
| FB-CREATE16 | Pointer new while app journal stale | Validate selected source, reconcile idempotently |
| FB-CREATE17 | Pointer old while staged candidate exists | Keep old; no automatic overwrite |
| FB-CREATE18 | Multiple retries same provision_op_uuid | Exactly one genesis ledger and pointer |
| FB-CREATE19 | Process kill while worker still closing | Failed unsafe-to-reopen; preserve native sidecars |
| FB-CREATE20 | 100 repeated boot loops mid provisioning | No extra ledger UUID/genesis or fake history |

### 5.3 Config Flow, concurrency and entry ownership — 20 NOT_RUN

| ID | Future scenario | Expected behavior |
| --- | --- | --- |
| FB-FLOW01 | First user creates logical Hub via UI | One stable Hub unique ID, independent of ledger UUID |
| FB-FLOW02 | Two simultaneous Hub Config Flows | One entry, duplicate abort |
| FB-FLOW03 | Entire manifest marks single_config_entry=true | Rejected for accepted multi-console design |
| FB-FLOW04 | One Hub + two physical consoles | Three independent entries, one global controller |
| FB-FLOW05 | Hub + PSN account Config Entry | Account distinct, no credentials from history |
| FB-FLOW06 | Console discovery with existing Hub | Dedicated stable-ID flow still available |
| FB-FLOW07 | Same Hub unique ID created twice | Existing entry preserved; no Core fallback replacement |
| FB-FLOW08 | Two admins request Create New concurrently | One global provisioning lease and operation |
| FB-FLOW09 | One admin imports archive while other creates new | Conflict/serialize, no competing active pointer |
| FB-FLOW10 | Browser disconnect after Create Intent | Backend durable operation survives/reconciles |
| FB-FLOW11 | Hub setup retries while provision ongoing | No second SQLite manager or Create Intent |
| FB-FLOW12 | Console entry loads before Hub completes | No durable write lease before global READY |
| FB-FLOW13 | Hub entry LOADED with SQLite unavailable | Admin recovery remains, no false empty stats |
| FB-FLOW14 | Native Hub Config Entry migration fails | MIGRATION_ERROR, no hidden bypass |
| FB-FLOW15 | Last console removed, Hub remains | Historical ownership retained |
| FB-FLOW16 | Hub removed as last entry, data remains | No silent purge, re-onboarding can find old history |
| FB-FLOW17 | Old entry E1 with new physical console same IP | No history reassignment |
| FB-FLOW18 | Prior account token restored from backup | No implicit authorization |
| FB-FLOW19 | Unloaded/disabled Hub and no other entries | No guarantee panel on restart |
| FB-FLOW20 | Controller crashes during duplicate flow resolution | Entry unique ID and journal reconciled, no data loss |

### 5.4 Restore, security and release regression — 20 NOT_RUN

| ID | Future scenario | Expected behavior |
| --- | --- | --- |
| FB-OS01 | Supervisor restores empty old config over new ledger | No claim missing newer commits recovered |
| FB-OS02 | Only /share restored but config current | Split-brain detected, not fresh |
| FB-OS03 | Backup contains snapshot but no active DB | Offer recover/import, not new |
| FB-OS04 | Full restore removes both DB and journal | UI says no local history found, asks user action |
| FB-OS05 | Private storage root changes after update | Do not silently initialize different directory |
| FB-OS06 | Linked SQLite version differs after HA update | No schema/durability bypass |
| FB-OS07 | Network filesystem path unexpected | Reject unsafe WAL/runtime assumptions |
| FB-OS08 | User chooses explicit fresh ledger beside retained old | Separate reviewed namespace only, no overwrite |
| FB-OS09 | Unprivileged user requests Create New | Denied with no file effects |
| FB-OS10 | Old preview confirmed after new snapshot appears | Stale preview rejected |
| FB-OS11 | Symlink swap between inventory and creation | Safe generated dir/no-follow protection |
| FB-OS12 | Failure creating file due EACCES | STORAGE_INACCESSIBLE, no fallback |
| FB-OS13 | Incorrect O_EXCL handling or race | No reused generation metadata |
| FB-OS14 | New ledger file appears with unexpected owner/permissions | Reject, never mark READY |
| FB-OS15 | Diagnostics under first-run failure | No personal history, credentials or raw paths |
| FB-OS16 | Concurrent backup while provisioning | Do not archive an incomplete stage as valid snapshot |
| FB-OS17 | Restore after successful creation | Ledger lineage and cursor/source revalidated |
| FB-OS18 | Large legacy flat DB import candidate | No auto migration/destruction, bounded inspection |
| FB-OS19 | Multiple HA installation types | Exact path, permissions and SQLite non-create behavior verified |
| FB-OS20 | Three-year historical data re-onboarded after Hub reinstall | Old records preserved and correct owner association |

**Exactly 80 proposed cases** (20 CLASS, 20 CREATE, 20 FLOW, 20 OS), all NOT_RUN. These intentionally overlap earlier SPEC-008–017 and must not be counted as 80 independent executable tests until deduplicated.

## 6. Approval gates — 20 OPEN

| Gate | Required evidence | Status |
| --- | --- | --- |
| FB-G01 | First-run UI Create vs Recover/Import policy approved | PROPOSED |
| FB-G02 | Hub Config Flow independent from explicit ledger genesis | PROPOSED |
| FB-G03 | Missing/corrupt/inaccessible/unknown classifier deterministic | NOT_RUN |
| FB-G04 | Existing ledger opened with SQLite non-create modes | SOURCE_VERIFIED, NOT_RUN |
| FB-G05 | mode=rwc restricted to exclusive new staging generation | NOT_RUN |
| FB-G06 | Safe private path, permissions, symlinks and fsync | BLOCKED_HA_OS |
| FB-G07 | Durable idempotent CREATE_INTENT with genesis IDs | NOT_RUN |
| FB-G08 | Atomic schema genesis and self-validated metadata | NOT_RUN |
| FB-G09 | Completion marker and pointer selection crash-safe | NOT_RUN |
| FB-G10 | No second ledger on retry after uncertain commit | NOT_RUN |
| FB-G11 | Stable Hub unique ID and separate console/account IDs | NOT_RUN |
| FB-G12 | Duplicate Config Flows and concurrent admin creation | NOT_RUN |
| FB-G13 | Old retained history found after Hub reinstall | NOT_RUN |
| FB-G14 | Legacy flat DB import/migration safety | NOT_RUN |
| FB-G15 | Full/partial HA OS restore classification and limits | BLOCKED_HA_OS |
| FB-G16 | No overwritten original after permissions/IO/storage errors | NOT_RUN |
| FB-G17 | Admin ACL/preview/confirm and bounded inventory | NOT_RUN |
| FB-G18 | Per-console source and PSN auth independent of provisioning | NOT_RUN |
| FB-G19 | HA OS/Container linked SQLite/WAL/permissions/mount matrix | BLOCKED_HA_OS |
| FB-G20 | Explicit maintainer acceptance and later fault-injection results | OPEN |

## 7. No-code authority boundary

ADR-0011 remains ACCEPTED only for high-level Hub/Archive product architecture. The specific Create New vs Import UX, ledger ID fields, path, CREATE_INTENT, lifecycle, SQLite worker and default state classification are **PROPOSED**, not automatically accepted. No new feature branch, runtime Python, Config Flow implementation, test fixtures, files on the user's Home Assistant installation or real data migrations were made. The legacy develop branch remains intact.

## 8. Sources

- [Source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md)
- [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md)
- [SPEC-017](SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md)
- https://www.sqlite.org/uri.html
- https://www.sqlite.org/c3ref/open.html
- https://www.sqlite.org/howtocorrupt.html
- https://docs.python.org/3.14/library/sqlite3.html
- https://docs.python.org/3.14/library/os.html
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/architecture/core/registries/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/storage.py

**Evidence state:** 80 NOT_RUN cases, 20 OPEN gates, no implementation or tests.
