# Home Assistant Core 2026.11 — First-boot identity, ledger provisioning and missing-data source audit

**Research date:** 2026-11-06
**Status:** OFFICIAL_SOURCE_RESEARCH / PROPOSED_DESIGN / NO_EXECUTABLE_CODE / NO_TESTS
**Pinned Home Assistant:** Core tag 2026.11.0. Supervisor commit 69848689a1e982ebe92d80e344fc086d8af667db for background restore findings; actual HA OS environment not inspected.
**SQLite:** Official URI filename/open_v2, transactions, backup, WAL and corruption guidance.
**Python:** Official Python 3.14 sqlite3, os, pathlib, file/permission semantics.
**Product decisions already accepted:** ADR-0011 logical Hub/Archive entry (not another PlayStation), independent console/account Config Entries, one process-global HubController and one panel, private history retained after entry removal, no MQTT/add-on/external database requirement.
**Companions:** [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md) and [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md).
**Related:** ADR-0004, ADR-0008, ADR-0011, ADR-0013, ADR-0015, ADR-0016, ADR-0017; SPEC-009, SPEC-010, SPEC-011, SPEC-015, SPEC-016, SPEC-017.
**Branch rule:** main documentation only. Legacy develop unchanged. No installation data accessed.

> Separate what official code guarantees from the proposed PlayStation Hub policy. This audit neither selects a final SQLite library/path nor proves that a user has never owned historical data. In particular, absence of local files cannot prove that an earlier HA installation or off-host backup never existed.

## 1. Principal findings

**FB-01 — SQLite can silently create an apparently empty historical ledger if opened incorrectly.** Official SQLite URI mode=ro means existing read-only, mode=rw means existing read-write without creation, and mode=rwc means create if absent. The standard sqlite3_open() is create-capable; Python sqlite3.connect without an explicit non-creating URI mode must not be the default read/reopen path for an existing historical ledger. A mistaken create can replace a meaningful missing-history failure with a valid-looking empty SQLite file.

**FB-02 — A Hub Config Entry does not prove an SQLite file is already provisioned.** Home Assistant persists Config Entry data and runtime_data differently; the former survives restarts, the latter does not. ConfigEntry creation, private filesystem initialization, SQLite schema transaction, journal publication and active pointer selection are distinct operations and are NOT committed atomically together. A crash may occur after an entry exists but before the ledger exists.

**FB-03 — A missing file is NOT proof of first install.** A previously provisioned history might be absent because an old backup was restored, a directory or volume was renamed/unmounted, a permissions error occurred, a previous migration was interrupted, storage root changed, or someone removed the last Hub entry without deleting data. If Config Entry, pointer, recovery journal, generation metadata, snapshot or a known previous persisted ledger UUID exists, new empty ledger creation is unsafe.

**FB-04 — Even zero local evidence is not definitive proof of no historical ownership.** A full old configuration restore may replace the Hub entry and all local control files. A machine migration might contain no existing data yet the user has an external backup. User confirmation of creating new history plus a clear import/recover alternative is necessary. We cannot automatically search every mounted path or reconstruct erased history.

**FB-05 — Consent and creation need two separate phases.** Recommended design: a user-confirmed native Hub Config Flow (unique logical hub ID, no PS5 identity) followed by a separately authorized First Ledger Provisioning flow. The latter must only create new history after a bounded, non-destructive inventory and explicit choice (CREATE_NEW vs IMPORT/RECOVER vs CANCEL). This separates HA entry persistence from the ledger transaction and makes interrupted bootstrap classifiable.

**FB-06 — A provisional new database must not become live on file creation alone.** Create an isolated generated generation ID and a durable CREATE_INTENT before creating a new SQLite database; initialize schema/ledger UUID, validate and close, publish generation metadata, then select the new generation through ADR-0015's versioned active pointer. Only after confirming the pointer and verifying canonical associations can the writer gate open. An interrupted creation remains resumable/inspectable and cannot be advertised as new healthy history.

**FB-07 — File absence and permission errors are different.** Official Python EAFP file APIs raise FileNotFoundError vs PermissionError/other OSError when appropriate. Prechecking os.path.exists or Path.exists is insufficient to establish writable/private file authority or to avoid a time-of-check/time-of-use race. Unexpected symlink or mount behavior also requires a fail-closed path check. Do not turn permission denied or I/O error into "no database, create it."

**FB-08 — Atomic filesystem creation is narrower than whole-ledger provisioning.** A generated directory created exclusively, a file opened with exclusive flags where suitable, and same-filesystem atomic pointer publication are candidate building blocks. None makes HA Config Entry JSON, new SQLite database, recovery journal and active pointer one atomic transaction. User consent, idempotent operation ID, durable phase revisions and positive worker closure still matter.

**FB-09 — Duplicate Hub Config Entries are a distinct failure mode.** The official flow documentation requires stable unique IDs and abort of duplicate entries or flows. Our logical Hub should use a reserved unique ID (example logical-hub:default), while consoles and PSN accounts have disjoint identity namespaces. The integration manifest cannot simply declare single_config_entry for the whole domain if independent physical/account entries must coexist. This is an internal model proposal, not proof of flows implemented.

**FB-10 — A first-boot repair UI must not require the ledger to be writable.** ADR-0016's Hub LOADED plus internal RECOVERY_HOLD is the preferred path when control plane is healthy but ledger existence/authority is uncertain. If the Hub entry exists but ledger does not, show explicit INITIALIZATION_REQUIRED/RECOVERY_HOLD rather than empty charts. Creating an empty database merely because Hub setup ran would be data loss disguised as successful installation.

## 2. Source evidence register

| ID | Evidence type | Official source | Direct fact / project implication |
| --- | --- | --- | --- |
| FB-S01 | SQLITE_OFFICIAL | sqlite.org/uri.html and c3ref/open.html | mode=ro/rw do NOT create missing DB; mode=rwc CAN create |
| FB-S02 | PYTHON_OFFICIAL | Python sqlite3.connect URI parameter | sqlite3 URI modes are used when uri=True; default connection path is not an explicit existing-only policy |
| FB-S03 | CORE_PINNED / HA_DOC | config_entries.py, contributors config entries guide | entry data persisted, runtime_data ephemeral, domain setup precedes each enabled entry setup |
| FB-S04 | CORE_PINNED / HA_DOC | config_entries.py and contributors config flow guide | async_set_unique_id and duplicate abort are the correct flow pattern |
| FB-S05 | CORE_PINNED | config_entries.py flow manager | creating an entry with existing unique ID may cause replacement in examined path; project must abort duplicates explicitly |
| FB-S06 | HA_DOC | registries & storage | config entries, registries and Store-managed JSON are in .storage; separate from custom SQLite |
| FB-S07 | CORE_PINNED | helpers/storage.py | Store supports versioned data and async_save; delayed save coalesces writes, unsuitable as an implicit durable multi-file transaction |
| FB-S08 | CORE_PINNED | core_config.py | hass.config.path resolves within configuration; cache_path is regenerable and excluded from backups |
| FB-S09 | PYTHON_OFFICIAL | os.mkdir, os.open, os.O_EXCL, os.O_NOFOLLOW where supported | exclusive creation and no-follow are candidate protection primitives with OS compatibility conditions |
| FB-S10 | PYTHON_OFFICIAL | file exceptions, os.stat, EAFP guidance | FileNotFoundError differs from PermissionError/other OSError; existence checks do not avoid races |
| FB-S11 | SQLITE_OFFICIAL | WAL/corruption guidance | never delete a hot WAL, overwrite an existing DB or rename open database merely to repair absence |
| FB-S12 | PROJECT_PROPOSAL | ADR-0015 generation-pointer design | new initialized generation must be independently validated before active pointer publication |
| FB-S13 | PROJECT_PROPOSAL | ADR-0016 Hub Recovery Hold design | UI/Repair may load while writer remains DENY_WRITE |
| FB-S14 | SUPERVISOR_PINNED | Supervisor config restore | restoring older config can replace entry metadata, journal, pointer and generations together |
| FB-S15 | HA_DOC | unique config entry quality rule | entire-domain single_config_entry would prevent multiple console/account entries |
| FB-S16 | PROJECT_PROPOSAL | ADR-0018 | user-confirmed bootstrap, not implicit SQLite creation from ordinary setup |

All source pins are referenced in §16. No actual Linux storage root, SQLite open or Config Flow has been tested.

## 3. Evidence inventory: bounded and non-destructive

Only inspect the configured private root derived from hass.config.path and the integration's known internal generation/snapshot layouts, plus already configured Hub/console/account metadata. A separately imported user-selected backup belongs to a protected import workflow, NOT an arbitrary recursive filesystem search.

**Inventory inputs:**
- Is there a logical Hub Config Entry? Is it enabled, disabled, newly created or restored? What stable hub unique ID and entry data version?
- Is there any known association with a persisted ledger UUID, selected generation, snapshot or restore epoch?
- Does the **expected** private root exist? Is it a real directory, trusted owner, writable/local filesystem, symlink or unavailable/permission-denied path?
- Is the active pointer present, valid, incompatible version, missing, corrupt or referring to a nonexistent generation?
- Does any known recovery journal contain PREPARING, NEW_GENERATION_STAGED, READY_TO_COMMIT or COMMITTED phase?
- Are there known completed generation files, partial staging, published immutable snapshots or retained older original generations?
- Does the selected SQLite exist? Does it open in NON-CREATING mode and verify ledger UUID, schema and committed cursor?
- Is the chosen ledger missing but a WAL/rollback journal or backup copy exists? Preserve companions; do not auto-repair.
- Are known HA backup/restore progress hints available? First-party Supervisor job status is advisory, not universal proof of custom SQLite restoration.
- Is the inventory **complete enough** for classification? Missing permission, unknown mount or interrupted file enumeration => UNKNOWN, not ABSENT.

**Do not** take os.path.exists returning false as permission to create: it can be racy, and existence alone tells nothing about provenance. Use explicit errors and confirmed root ownership. The manager's state remains DENY_WRITE during every inventory stage.

## 4. Proposed first-boot classifier states

| Internal state | Evidence | Allowed next action |
| --- | --- | --- |
| NO_HUB_CONFIGURED | No enabled logical Hub entry; no definitive assertion about old history | User may open native Config Flow; no silent file deletion |
| HUB_CONFIGURED_UNPROVISIONED | Hub entry present, no committed ledger pointer and no completed CREATE_INTENT | Show admin onboarding/recovery choice, deny historical writes |
| CANDIDATE_FRESH | No known prior ledger/restore artifacts in a bounded readable root AND an explicit current user action chooses new history | Acquire exclusive provisioning lease, publish CREATE_INTENT |
| PROVISIONING_IN_PROGRESS | Valid CREATE_INTENT, staged new generation, no committed active pointer | Resume safe validation or ask admin, never create duplicate |
| PROVISIONING_COMMIT_UNCERTAIN | Pointer publication may have happened while journal final status absent | Read pointer and validate actual selected generation before replaying |
| READY_EXISTING | Valid active pointer, generation, ledger UUID, schema and associations | Normal open-existing mode=rw and durable writer gate when ready |
| LEGACY_DATA_PRESENT | Old flat DB/legacy branch artifacts not in new generation layout | Read-only inventory; migration/import decision, no auto-create |
| RECOVERY_REQUIRED | Missing selected DB but existing metadata/snapshot/generation/Config Entry lineage | RECOVERY_HOLD with admin recovery options |
| STORAGE_INACCESSIBLE | Permission, I/O, unknown root/mount or path ownership problem | Fail closed with Repair; never label "fresh" |
| CORRUPT_OR_UNSUPPORTED | Existing ledger unreadable, malformed schema/version, hot journal uncertainty | Preserve bytes; recovery hold, no empty creation |
| FOREIGN_OR_FORKED | Ledger UUID/lineage inconsistent or another HA instance candidate | Explicit import/reconciliation; no automatic merge |
| RESTORE_AMBIGUOUS | Evidence incomplete after a known/suspected HA restore | Explain uncertainty, prefer safe admin inventory |
| NO_ENTRIES_ENABLED | No enabled Config Entries load integration | Files retained; no guarantee of panel after restart |

**State precedence:** STORAGE_INACCESSIBLE / CORRUPT / RESTORE_AMBIGUOUS / FOREIGN / INCOMPLETE_PROVISIONING outrank any superficial no-file observation. READY requires positive validation; CANDIDATE_FRESH requires affirmative admin choice in addition to an empty known root.

Do not infer a previous PlayStation physical identity from a Hub unique ID. The Hub entry identifies a logical integration configuration anchor, not a historical ledger or Sony hardware.

## 5. First Hub onboarding and explicit consent

**Phase U — Config Entry creation (Home Assistant-managed):**
1. User selects PlayStation Hub in the official UI and chooses logical Hub/Archive onboarding; integration can be installed with zero consoles.
2. Config Flow sets a stable reserved Hub unique ID and aborts if already configured or another matching flow exists; no manifest-wide single_config_entry because console/account entries must coexist.
3. Explain that creating the Hub is *not* the same thing as proving a blank historical ledger exists; offer restore/import recovery route in the UI.
4. HA persists the Hub Config Entry through its own lifecycle. Do not store the unverified ledger UUID as "fully provisioned" merely because this entry exists. Runtime can be LOADED with internal INITIALIZATION_REQUIRED/RECOVERY_HOLD.
5. Physical console discovery uses its own explicit flow and stable console identity; cannot piggyback automatic history creation.

**Phase P — Privileged ledger provisioning (application-owned):**
1. Administrator selects CREATE_NEW_HISTORY (not just "add Hub"), having seen any existing local candidates and warning about restoring old data.
2. Revalidate role, current Hub/controller generation and bounded inventory completeness, candidate absence and no existing active pointer.
3. Obtain one process-level **exclusive provisioning lease**; reject concurrent new/create/import/restore operations from second browser/tab or another entry.
4. Allocate an idempotent provision_op_uuid and durable CREATE_INTENT with configured ledger policy/schema and fresh proposed ledger UUID and generation UUID. Use distinct IDs for Hub entry, ledger and generation.
5. Create a fresh staged generation in a new exclusive directory. SQLite mode=rwc is permitted ONLY inside this authorized isolated staging generation, never for ordinary live reopen. On unexpected existing path, stop and inspect rather than overwrite.
6. Create schema and metadata in a transaction, record ledger UUID/lineage genesis, schema revision, empty durable cursor and creation intent reference. Close/validate SQLite, including integrity/foreign key checks and acceptable WAL state.
7. Publish completed generation metadata with tested file+parent-directory durability and internal fixed path protection. No live pointer yet.
8. Use ADR-0015's versioned active pointer protocol to select the generation, with a durable PREPARED/READY_TO_COMMIT journal record and one atomic pointer swap.
9. Confirm selected pointer, ledger UUID/schema and worker/connection close; publish provisioning final acknowledgement and enable historical writer gate under a new manager generation only when consistent.
10. If any phase fails, preserve known metadata/partial generation, remain INITIALIZATION_REQUIRED/RECOVERY_HOLD and expose a safe administrator retry/resume. No further implicit empty create is allowed.

**No lock held across long SQLite I/O**; short manager transitions and fencing tokens are distinct from awaited disk work. Operation UUID retries must return the existing transaction state rather than create a second ledger UUID.

## 6. Crash matrix and idempotency

| Interruption point | Surviving possibilities | Recovery behavior |
| --- | --- | --- |
| Before Hub entry exists | No entry, perhaps old archived data from prior install | Offer normal setup and import, never erase retained data |
| Hub Config Entry saved, before CREATE_INTENT | Hub exists, DB absent | INITIALIZATION_REQUIRED, not automatic sqlite3.connect-create |
| CREATE_INTENT partially written | Old/no pointer, invalid intent | Preserve; no duplicate creation until classification |
| CREATE_INTENT durable, generation absent | Operation ID + IDs known | Admin-safe resume with same op ID, not fresh different ledger |
| Generation directory allocated but SQLite absent | Reserved staging and intent | Validate op ownership; resume or classify incomplete |
| SQLite file created but schema transaction absent | Partial/empty SQLite artifact | Untrusted staging, not READY |
| Schema committed but SQLite destination remains open | Complete-looking DB but worker live | No pointer publication until closed and verified |
| Generation verified, metadata publish interrupted | Staged unselected generation | Validate again/complete publication; no accidental second active DB |
| READY_TO_COMMIT durable, pointer old | Old/no generation selected yet | Do not auto-finish destructive selection without current authorization |
| Pointer new, final acknowledgement missing | New selected generation and stale journal | Validate pointer and selected DB, finish idempotently, don't recreate |
| New selected generation, Hub entry metadata out of date | Different persistence authorities | Reconcile entry/ledger mapping without new ledger creation |
| HA config restore rewinds Hub entry, pointer and DB | Old consistent-looking data | Do not infer new install; lost later evidence cannot be reconstructed |
| Root path becomes unreadable/mount missing | No reliable inventory | STORAGE_INACCESSIBLE, never CREATE_NEW |
| Another administrator starts import during provisioning | Competing operations | One exclusive lease; explicit CONFLICT rather than multi-ledger race |
| Console setup before Hub ledger creation | Valid physical entry possible | No writer until global ledger READY |
| Hub entry deleted but archive retained | Retained data, no load anchor | Future explicit re-add detects old candidate, no silent reset |

### Idempotent bootstrap outcome

Creation success requires BOTH an independently verified active-generation ledger and an operation/journal identity that resolves the creation attempt. Config Entry presence alone is insufficient, and a file called history.sqlite3 with a valid SQLite header is not proof of schema/lineage. A crash after pointer selection but before frontend reply is an acknowledgement ambiguity: return the already-created ledger on retry, not a second newly initialized ledger.

## 7. Storage root and namespace safety

**Default physical location remains a candidate** from ADR-0011: a private subdirectory derived via hass.config.path, outside custom_components code and public /config/www. The final layout and file modes are not approved.

- Use fixed internal relative paths and generated safe UUID basenames; canonicalize/validate root containment, no symlink/hardlink escape, and check the final opened file rather than relying solely on an earlier path test.
- Newly provisioned generation directory should use an exclusive creation operation (fail if already exists), with restrictive permissions subject to platform umask. Never blindly use exist_ok=True on a generation directory whose existence would indicate a concurrent/old operation.
- Exclusive os.open O_CREAT|O_EXCL and O_NOFOLLOW may be useful for *application-owned metadata files*, but SQLite must use its supported filename/VFS access. Do not pretend a Python file descriptor can simply be passed as a ready-made sqlite3.Connection.
- Reserve no-create mode (mode=rw or ro) for all existing selected SQLite generations. Use mode=rwc only in a proven fresh exclusive stage after CREATE_INTENT and under one provisioning owner. Verify the connection did not silently open read-only and reject unexpected schema/ledger version.
- Classify FileNotFoundError separately from PermissionError, SQLITE_CANTOPEN/READONLY/IOERR, zero-byte/corrupt file, wrong type, symlink and unexpected WAL companions.
- Refuse to "repair" with manual deletion of SQLite -wal, -shm or hot rollback journal. Let SQLite native recovery operate on an existing generation's original path when its evidence is coherent.
- Do not allow a different HA instance/process to share a writer path by accident; process-local HubController only prevents same-process races. Multi-process file locking/ownership requires a separate supported deployment contract.
- Don't put first-boot intent in evictable HA cache. A HA Store record may be a useful advisory for UI/flow options, but versioned Store JSON and SQLite/pointer are separate persistence systems, not an atomic cross-store commit.
- Reserve space and bound temporary generations; never delete the only old recoverable copy to make room for a new empty DB.
- Create no PSN credential or physical console identity just because a logical new ledger was provisioned.

## 8. Interaction with Config Flow uniqueness and account/console identity

**Unique ID namespaces (proposed; exact values not final):**
- hub:logical-default — one logical Hub Config Entry per HA integration installation.
- console:canonical-verified-key — each physical console independently verified using project protocol identity, not IP/name.
- psn:stable-account-key — account entry with separate authorization/privacy rules.

A single_config_entry manifest would stop a second physical/account entry, so it conflicts with the accepted multi-entry architecture. Use explicit Config Flow duplicate-ID checking and a process-level creation lease. The Core's historical fallback when creating an entry with an existing unique ID can replace it; do not rely on this fallback instead of aborting duplicate flows.

**Config Entry creation and SQL provisioning ordering:** Config Entry creation may complete first; then application ledger creation can remain pending. Do not assume that a Hub Config Entry must be discarded because SQL provisioning failed; this is the recovery user interface anchor. Conversely, don't set "new history ready" in a Config Entry and then try to create the database without a crash-safe recovery intent.

The Hub unique ID is not ledger_uuid. A restored prior ledger with different UUID must trigger import/reconciliation, not be adopted automatically because its Hub unique ID matches.

## 9. Proposed UI and privacy contract

- First-run screen: choose "Create new history" or "Recover/import existing history"; explicit warning that starting new history will not restore old backup data.
- If evidence indicates previous data, default to recovery inventory and block CREATE_NEW until a clear reviewed admin disposition. If a deliberate fresh ledger alongside old retained histories becomes a future product feature, keep it in a new namespace; never overwrite the old files.
- If files are missing but the root is inaccessible, show "Storage unavailable" and diagnostic guidance rather than the misleading empty-history onboarding.
- If a CREATE_INTENT exists, show "Initialization interrupted" and offer safe resume/review without creating a second database.
- If a valid ledger exists but Hub entry is missing/removed, show "Existing history found" and offer explicit binding after lineage checks, not automatic replacement.
- Repair issue identifiers should be global for shared-history provisioning failures, not attached to one removable physical console.
- All create/import/restore requests are administrator-only and use backend preview/confirm current generation and ACL. No private filesystem paths, Sony identifiers/tokens or entire game history in generic diagnostics.
- Snapshot backup state and first-run ledger state remain independent; a published immutable snapshot is not evidence that HA backup restored it.
- Avoid terms like "brand-new installation confirmed" if only evidence is a presently empty directory: use "no local history detected at this location."

## 10. Failure classification and trust

| Condition | Classification | Forbidden fallback |
| --- | --- | --- |
| sqlite3 mode=rw open returns CANTOPEN | Missing/inaccessible root depending OS cause | Retrying with mode=rwc without explicit intent |
| PermissionError on private root | STORAGE_INACCESSIBLE | Treating as never installed |
| Empty/uninitialized file at active pointer | CORRUPT_OR_INCOMPLETE | Applying default CREATE TABLE on live path |
| Old Hub entry but no expected ledger | RECOVERY_REQUIRED or UNPROVISIONED depending durable intent | Automatic empty history initialization |
| New Hub entry and no local artifacts, admin has not chosen | INITIALIZATION_REQUIRED | On-entry automatic SQLite create |
| Valid snapshot and no active pointer | RECOVERY_REQUIRED | Silent new ledger |
| Existing SQLite + malformed manifest | RECOVERY_HOLD | Select by filename/mtime only |
| Valid pointer and selected ledger | READY_EXISTING after identity checks | Recreate because app version changed |
| Unsupported schema/ledger UUID | RECOVERY_HOLD | Destructive migration/downgrade |
| Concurrent second CREATE_NEW | IN_PROGRESS/CONFLICT | Second ledger UUID |
| No evidence after full old-config restore | UNKNOWN_PREVIOUS_HISTORY | Claim no prior data existed |
| WAL sidecars without main file | INCOMPLETE/CORRUPT | Deleting sidecars and creating DB |

## 11. Remaining questions and explicit decision boundaries

**P0:** Approve UI first-run CREATE_NEW vs IMPORT/RECOVER semantics, especially after a full restore with no local evidence. Define what "user consent" means when old data may exist off-host.
**P0:** Decide first-boot bootstrapping order: Hub Config Flow creates entry, then administrator uses explicit separate history initialization (preferred).
**P0:** Verify exact physical path, permission and storage mount semantics on supported HA OS/Container; error differentiation using non-creating SQLite opens.
**P0:** Choose durable CREATE_INTENT journal encoding, generation-specific exclusive stage, schema first transaction, publication/fsync and replay under power loss.
**P0:** Validate concurrent Hub/setup/provisioning and two admin browser flows without double-creating a ledger.
**P0:** Validate migration from existing legacy code/flat DB, retained archive after last Hub removal and restore of older HA backup.
**P1:** Decide whether first-run UI may browse separately verified immutable snapshots before binding to a newly created ledger.
**P1:** Define policies for creating an explicitly separate fresh ledger alongside a preserved foreign/old one; not automatic.
**P1:** Recheck actual SQLite library WAL reset fix and supported HA minimum before selecting PRAGMAs/worker.
**P1:** Inspect crash-safety and path containment on actual HA OS filesystem, including backup archive scope and directory fsync.

## 12. Exact source register

SQLite official:
- https://www.sqlite.org/uri.html
- https://www.sqlite.org/c3ref/open.html
- https://www.sqlite.org/howtocorrupt.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/lang_transaction.html

Python official:
- https://docs.python.org/3.14/library/sqlite3.html
- https://docs.python.org/3.14/library/os.html
- https://docs.python.org/3.14/library/pathlib.html

Home Assistant official:
- https://contributors.home-assistant.io/core/integrations/config-flow/
- https://contributors.home-assistant.io/core/integrations/config-entries/
- https://contributors.home-assistant.io/core/quality-scale/unique-config-entry/
- https://contributors.home-assistant.io/architecture/core/registries/
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/helpers/storage.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core_config.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

Project:
- [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md)
- [ADR-0018](../decisions/ADR-0018-first-boot-consent-and-ledger-provisioning.md)
- [ADR-0011](../decisions/ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)

**Outcome:** Source-backed first-boot classification and initialization proposals only. No data inspected on the user's HA OS, no runnable code, Config Entry, SQLite file, tests or migrations created. 


## 13. Source nuance — read/write open does not certify a writable ledger

**SQLITE_OFFICIAL (sqlite3_open_v2):** An existing SQLITE_OPEN_READWRITE open can, for historical compatibility reasons, fall back to read-only when filesystem permissions prevent writing. The sqlite3_db_readonly API can distinguish the effective connection mode. The non-create URI mode=rw is useful for preventing accidental file creation, but the application must not treat successful connection creation as sufficient evidence of usable historical writing. Future initial preflight must separately validate permissions, effective SQLite connection mode, schema ownership, local filesystem and actual commit behavior with a controlled transaction model; none of this is a reason to run test writes against a suspect user ledger during a read-only recovery inventory.

**PROJECT_PROPOSAL:** New-generation bootstrap validates that its isolated staged SQLite connection is writable and belongs to the expected generation before schema commit; ordinary existing-source inventory may use read-only mode first and defer write admission until full verified LIVE_VALID. A readonly fallback is STORAGE_NOT_WRITABLE/RECOVERY_HOLD, not missing data or permission to create a fresh history. Source: https://www.sqlite.org/c3ref/open.html and https://www.sqlite.org/c3ref/db_readonly.html. No current DB connection has been opened.
