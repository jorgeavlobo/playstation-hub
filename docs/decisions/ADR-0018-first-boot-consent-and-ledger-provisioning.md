# ADR-0018 — First-boot consent, explicit ledger creation and missing-history recovery

**Status:** PROPOSED — exact first-run and provisioning policy NOT ACCEPTED/TESTED
**Review date:** 2026-11-06
**Scope:** Native Hub/Archive onboarding; distinguishing no local history from missing/corrupt/restored SQLite; safe first creation of durable ledger and genesis metadata.
**Primary evidence:** [First-boot source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md)
**Test plan:** [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md), 80 NOT_RUN / 20 OPEN.
**Accepted scope:** ADR-0011 one logical Hub/Archive Config Entry, separate physical-console/PSN entries, one global controller/panel, historical data retained upon entry removal.
**Related technical proposals:** ADR-0004/0008/0009, ADR-0013/0014/0015/0016/0017; SPEC-009/010/011/015/016/017.
**Official baselines:** HA Core 2026.11.0, SQLite URI/open_v2, Python 3.14 os/sqlite3 and Home Assistant Config Flow.
**Branch:** main documentation only, develop frozen.

> The maintainer asked for the next documentation/research priority. No implementation work was authorized, and no final product policy for onboarding an empty history has been explicitly accepted.

## 1. Decision problem

PlayStation Hub is intended to accumulate years of physical-console/game session evidence in private SQLite storage. Its logical Hub Config Entry is persistent Home Assistant configuration, but the database, application recovery journal, active generation pointer and immutable snapshots are separately managed files.

If a previous database disappears due to backup restore, failed mount, permission problem, interrupted migration or operator action, a normal sqlite3.connect create-capable open can produce a valid empty DB and erase evidence of the missing historical source. Conversely, a genuinely new Hub needs an authorized path to create its first ledger and accept future sessions without requiring any console to be online.

We must distinguish **user intent to create a new ledger** from mere existence of a Hub Config Entry or absence of a file.

## 2. Official facts

- SQLite's documented mode=ro and mode=rw do not create a missing DB; mode=rwc may create it. Standard SQLite open without an explicit existing-only mode is create-capable.
- Python sqlite3.connect supports URI mode with uri=True, permitting the non-create checks when used deliberately.
- Core persists Config Entries and Home Assistant Store JSON separately from integration-owned SQLite; no combined transaction covers all of them. runtime_data is ephemeral.
- Official Config Flow unique ID checks and aborts avoid duplicate entries, while creating a colliding entry in the pinned Core flow path can replace the old one if the integration ignores the guidance.
- Manifest-wide single_config_entry would conflict with the accepted one Hub plus independent multiple physical consoles/account entries.
- os.open O_EXCL and exclusive directory creation are candidate safe filesystem primitives, but need real OS/permission testing; Python existence checks do not remove TOCTOU races.
- HA OS full restore can replace old configuration and in-config history together; the absence of a more recent copy cannot be reversed by application logic.

## 3. Alternatives

| Approach | Benefits | Main risk | Proposed status |
| --- | --- | --- | --- |
| A. Auto-create DB whenever expected path missing | Easy first install | Silent reset after restore, corruption, wrong mount or permissions | REJECTED as design |
| B. Create SQL DB automatically inside the Config Flow | Fewer user steps | HA entry and DB save are not atomic, interruption can orphan files/duplicate ledgers | REJECTED as default |
| C. User creates logical Hub; later explicitly chooses new history or import; app records durable genesis intent | Clear authorization and interrupt-safe resume | Additional first-run UX and application journal complexity | RESEARCH_PREFERRED, NOT_ACCEPTED |
| D. No ledger until first physical console pairs | Less upfront setup | No Hub-only archive/restore onboarding; history can be created from discovery unintentionally | REJECTED for default |
| E. Use a Store JSON only to declare history exists | Simple versioned state | Store/SQLite/pointer are separate systems and can roll back independently | ADVISORY ONLY |
| F. Create a separate new ledger namespace while retaining old candidate | Allows intentional fresh start without overwriting old | Long-term multiple ledgers, quota, UI lineage/ACL complexity | DEFERRED user-authorized advanced workflow |

## 4. Preferred two-phase onboarding

**Phase 1 — user-confirmed Hub Config Flow (already accepted conceptual component):** Create one logical Hub entry with a reserved stable unique ID, perform official duplicate checks, and provide a restricted admin user interface even when history has not yet been provisioned. A Hub Config Entry must not be named after a PS5, PSN account, IP, filesystem path or mutable device nickname.

**Phase 2 — user-authorized ledger genesis (this ADR's candidate):**
- Inventory only known private roots and their pointer, journal, complete/partial generations, snapshots and legacy data; distinguish confirmed absence from I/O/permission/root errors.
- Present choices to authorized administrator: CREATE NEW HISTORY, RECOVER/IMPORT EXISTING HISTORY or cancel. Explain that an empty known root is not proof that the user has never had historical data on a prior HA installation or backup.
- Under an exclusive HubController provisioning lease and a current confirmation/preview revision, publish one durable CREATE_INTENT before writing SQLite. Reserve a unique operation ID, ledger UUID, new generation UUID and requested schema/policy revisions.
- Create a fresh exclusive staging generation and permit SQLite create mode only within that new, proven staging path. All regular/reopen calls to selected historical data must use non-create mode.
- Write schema, empty genesis cursor, history/lineage and operation IDs transactionally in SQLite; close/validate, durably publish generation metadata, then select the new generation through ADR-0015's controlled active pointer.
- Confirm active pointer/source and current Hub controller association before opening the writer gate and returning an idempotent creation receipt.
- If interrupted before or after pointer selection, inspect existing intent/generation/pointer and reconcile rather than allocating a second ledger.

This design does not require any physical PlayStation to be online and does not create Sony credentials or PSN account permissions.

## 5. First-boot classifier and precedence

The backend must not call mode=rwc just because a FileNotFoundError happened. It must determine whether expected storage metadata/old associations exist and whether the inventory can be trusted. Candidate states include INITIALIZATION_REQUIRED, CREATE_IN_PROGRESS, CREATE_COMMIT_UNCERTAIN, READY_EXISTING, RECOVERY_REQUIRED, STORAGE_INACCESSIBLE, LEGACY_DATA_PRESENT, CORRUPT, FOREIGN/FORKED, RESTORE_AMBIGUOUS and NO_ENTRIES_ENABLED.

**Precedence:** any previous-data evidence or unverified root condition blocks fresh creation by default. Corrupt existing SQLite, partial schema, missing selected generation, unsupported schema, hot journal uncertainty, a known old ledger UUID or a published recovery snapshot are not new installations. File-mode exceptions must be classified by type.

A single empty directory on a machine that was restored is not sufficient proof of prior-data nonexistence. With zero detectable local evidence, the user may still explicitly choose new history after being offered import/recover, and we must avoid claiming that this action recovers data from older backups.

## 6. Crash and concurrency semantics

**Hub entry persisted, CREATE_INTENT absent:** control plane can load INITIALIZATION_REQUIRED; no database automatically created.

**Intent exists, SQLite staging absent:** same operation IDs are authoritative for a safe resume/inspection, not an excuse to generate a second ledger.

**Staging DB partial/zero-byte:** never mark READY or move into active path before independent SQLite verification.

**Committed schema, pointer not selected:** generation is not active, even if its SQL is valid; controlled selection with current admin intent.

**Pointer new, journal last phase old:** validate selected pointer and generation, then complete same operation without blind rollback.

**Two admins/two Config Flows:** reserved Hub unique ID and controller provisioning lease are independent guards; one normal Hub entry plus one ledger genesis operation is the goal.

**Old data after hub uninstall/reinstall:** discover retained history in known roots and require safe association/rebind instead of creating empty history. Removal of the final Hub entry never implicitly deletes the database under ADR-0011.

**Full HA OS restore that removed all local hints:** local absence cannot recover missing newer records. Present no-local-history wording and allow explicit restore/import or create; never claim otherwise.

## 7. Filesystem and security model

- Use a fixed, private, canonical configuration-root path resolved by supported HA runtime API; no user-controlled relative traversal, symlink alias or filesystem URL.
- Prefer generated UUID generation directories created with exclusive semantics. Metadata files may use O_CREAT|O_EXCL and O_NOFOLLOW where the supported OS allows, but SQLite itself must use its own supported database filename/VFS API; do not pretend a Python descriptor becomes an sqlite3 connection.
- Preserve hot SQLite -wal/-journal and old active generations. Never silently delete/overwrite a previous DB to create a new one.
- No unbounded filesystem scans or reliance on inaccessible directories returning "empty".
- A versioned Home Assistant Store may support non-authoritative UI metadata but is not an atomic history creation journal.
- The CREATE_NEW administrative action must be server-authorized, idempotent and tied to current controller generation; no unprivileged automation/service may bootstrap new history.
- Protect persistent historical data, snapshots, keys and identities separately; a new ledger never imports Sony credentials automatically.
- Quotas, permissions, schema migration and backups require HA OS/Container fault tests.

## 8. Decision status and next research

**Already ACCEPTED:** logical Hub/Archive entry, one sidebar, independent physical-console/PSN entry ownership, private retained history and no extra service/MQTT requirement.

**PROPOSED in this ADR:** a separate explicit ledger-creation confirmation; first-run source classifier, durable CREATE_INTENT, genesis staging, non-create modes on reopen, exact menu states and consent wording.

**Not selected:** final SQLite version/path/worker, safety on target HA OS, schema layout, automatic old-backup restoration, automatic alternate-ledger creation or library packaging.

**Next priority after this research:** investigate precise migration and reconciliation of legacy flat databases/old Config Entries into the new ledger-generation layout without silently converting historic recordings or Sony identities. Alternatively, close the remaining First Boot Config Flow and backup archive source evidence through target HA OS verification when testing is authorized. No executable work under this ADR.

## 9. References

- [Source audit](../research/ha-core-2026-11-first-boot-ledger-provisioning-and-missing-data-audit.md)
- [SPEC-018](../specifications/SPEC-018-first-boot-ledger-provisioning-and-recovery-classifier.md)
- [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md)
- [ADR-0015](ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md)
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

**Outcome:** Proposed first-boot/ledger genesis design; 80 SPEC-018 tests NOT_RUN and 20 gates OPEN. Nothing implemented, tested or migrated.
