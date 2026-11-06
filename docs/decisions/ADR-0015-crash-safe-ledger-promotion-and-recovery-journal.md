# ADR-0015 — Crash-safe ledger promotion, recovery journal and generation pointer

**Status:** PROPOSED — research-preferred F2, technical implementation NOT APPROVED / NOT_TESTED
**Date:** 2026-11-06
**Scope:** Application crash, Core termination and power-failure recovery during a user-approved SQLite history replacement
**Primary research:** [SQLite and filesystem source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md)
**Acceptance tests:** [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)
**Depends on:** ADR-0011 ACCEPTED product architecture; ADR-0004/0006/0007/0008, ADR-0012/0013/0014 PROPOSED technical implementation; SPEC-009/010/012/013/014.
**Pinned Home Assistant:** Core 2026.11.0; Supervisor 69848689a1e982ebe92d80e344fc086d8af667db.
**Git policy:** main documentation only, develop legacy frozen.

> The maintainer asked to DOCUMENT and RESEARCH the crash-safe recovery journal, not to implement a restoration subsystem. This ADR remains PROPOSED. It cannot turn source-derived filesystem behavior into a tested guarantee on Home Assistant OS.

## 1. Situation

Admin-guided recovery is a product-sensible response to ambiguous or forked SQLite histories after a Home Assistant restore. A selected immutable SQLite snapshot can be verified independently, but it must eventually become an active, writable ledger. Changing the active database source involves SQLite file handles, its WAL/rollback companions, the private application journal and metadata, HA Config Entries/physical console associations, potentially two frontend administrators and a user confirmation.

There is no single cross-product transaction covering all these. SQLite COMMIT protects one DB's transactions; POSIX os.replace provides an atomic one-path rename in the supported case; Home Assistant Config Entries store data separately; and filesystem durability may depend on fsync of file and parent directories.

A trivial procedure that renames the live main .db and replaces it with a snapshot is UNSAFE. Official SQLite warnings explicitly cover open-connection file unlink/rename and hot WAL/journal mismatch.

## 2. Accepted project invariants, independent of this ADR

- Exactly one PlayStation Hub integration, one sidebar, one integration-global HubController.
- One logical user-created Hub/Archive Config Entry (already accepted in ADR-0011) plus independently owned console and optional PSN account entries.
- No mandatory MQTT broker, standalone add-on, external database server or special external disk.
- Private historical data outside HACS executable files, with safe retention after removing console entries.
- No silent restore from a dormant older snapshot, no automatic fork merge by largest cursor, no invented duration across gaps or automatic Sony credential authorization.

These do NOT imply this ADR's generation-pointer recovery technique is accepted.

## 3. Options reviewed

| Model | Benefit | Critical problem | Proposed decision |
| --- | --- | --- | --- |
| F1 Rename live database and snapshot in place | Small directory structure | Multiple renames; cannot safely touch active file/hot WAL; unsafe interruption | REJECT FOR DEFAULT |
| F2 New independent generation + atomic active pointer | Never rename active DB; one small logical cutover file; preserve prior generation | Extra disk and pointer/journal durability protocol, boot reconciliation | PREFERRED TO TEST, NOT ACCEPTED |
| F3 Direct SQL import into current live DB | Uses SQLite transaction for some row-level updates | Schema divergence, history forks, identity conflicts, large import | Separate future import, not universal restore |
| F4 Most recent snapshot/file auto selection | Simple algorithm | Deletes valid newer history after ordinary restart | REJECT |
| F5 External filesystem whole-config atomic snapshot | Potential consistency | No portable supported app-facing OS primitive across installations | Not a default release dependency |
| F6 Symlink/hardlink trick | One link switch | SQLite locking/journal naming ambiguity and alias hazards | REJECT |

**Proposed direction:** F2, subject to OS/SQLite/Supervisor fault tests. The old generation is never renamed while open. New candidate receives a distinct directory and namespace. A single active pointer file is atomically published **only after** a completed independently validated generation exists, and a durable operation journal describes the intent and expected phases.

**Safety boundary:** the single pointer alone does not guarantee crash durability or atomic HA Config Entry/SQLite updates. The active mutable generation is not an immutable snapshot. F2 is a live replacement strategy, not the solution to raw SQLite files appearing in Home Assistant backup archives.

## 4. Conceptual contracts

**Active pointer**: one privately stored, tiny versioned record of ledger UUID, active generation UUID, expected schema/lineage and last committed promotion job ID. Internal generated directory names only, no user-supplied paths. Atomic same-filesystem os.replace after syncing its temporary file; sync parent directory to address rename durability on the tested OS.

**Recovery journal**: application-owned versioned durable records recording admin decision ID, old/new generation, source immutable snapshot, candidate digest and cursor, phase, revision, and expected previous pointer. It is distinct from SQLite's internal rollback journal/WAL. Journals are not an override that can silently supersede an already committed active pointer.

**Independent generation**: unique private path containing the active candidate SQLite file and its own SQLite-managed sidecars if and when it becomes live. Prior active generation is retained intact until a later safely authorized retention/GC operation. A snapshot copy is verified and closed before being selected.

**Controller lifecycle**: single exclusive recovery lease, generation fencing, bound readers/writers and positive worker/connection closure before promoting. Browser disconnect does not interrupt an already admitted critical cutover.

**HA identity**: canonical physical-console keys and PSN accounts remain independent of HA entry_id and ledger UUID; after pointer commit, Config Entries are reconciled in a separate step. An older Config Entry can require RECOVERY_HOLD even if the new database is valid.

## 5. Proposed phase ordering

1. Verify explicit admin preview/confirm and expected ledger state/candidate digest; acquire one global RecoveryManager job lease.
2. Fence new historical writes, queue admissions and privileged operations for affected console/account owners.
3. Await/classify accepted commits, queries, exports, backups and all SQLite connections. If a worker does not close, enter FAILED_UNSAFE_TO_REOPEN.
4. Durably publish recovery journal PREPARING with old pointer and candidate ID, without modifying the old DB path.
5. Copy the verified immutable snapshot to a new generation directory; use a trusted, distinct SQLite namespace and allow SQLite to validate/recover that candidate, then close.
6. Verify schema, lineage/ledger UUID, snapshot-contained cursor, integrity_check and foreign_key_check. Preserve original and stage generation with file/directory fsync guarantees verified on OS.
7. Publish READY_TO_COMMIT journal revision. Confirm preview and original pointer have not become stale.
8. Atomically replace the single active pointer using same-filesystem, supported os.replace and required directory sync. This is the intended **selection commit**, NOT a multi-file SQL transaction.
9. Verify selected generation is readable/opened by one new writer only. Reconcile console/account mappings against HA's separately stored entries; quarantine conflicts.
10. Durably mark VERIFIED_COMPLETE only after checking current selected pointer/ledger and identity; resume permitted operations under new runtime generation. Keep old original until retention clearance.

If power fails between step 8 and 10, restart must not blindly replace the newly selected generation with the old one merely because journal status appears outdated. If power fails before step 8 and the old pointer is still selected, restart must not silently complete a destructive operation based on an expired old administrator confirmation. Both cases require pointer/journal reconciliation and independence from the browser.

## 6. Mandatory crash behavior

**Before active pointer selection**: old valid generation remains authoritative, pending new candidate can be validated/discarded, and admin reconfirmation may be necessary. Do not auto-complete a destructive job on reboot based on PREPARING or READY_TO_COMMIT alone.

**After a newly selected pointer is durable**: the candidate may be the real selected ledger despite a stale journal; verify the pointed-to generation and reconcile/finalize the journal idempotently. Do not roll back to old automatically once new writes might have been admitted.

**If pointer durability is uncertain (rename returned, parent fsync failed)**: next start reads what actually exists and validates it. Never claim either old or new committed merely because an unacknowledged callback said so.

**If any selected SQLite sidecar/journal is hot**: open at the original generation path with SQLite native recovery; do not delete/rename -wal/-shm/-journal or swap other generations' companions.

**If the HA OS Supervisor restores an older entire configuration folder**: active pointer, application journal and data generations can all rewind. No local protocol can reconstruct newer writes absent from every surviving copy. Clear as UNKNOWN, preserve backup lineage and offer admin-guided recovery; not universal automatic lossless restore.

**If HA Config Entry registry and ledger disagree**: retain DB in RECOVERY_HOLD for affected owners and require independently validated canonical identity mapping, not heuristic IP/name/entry_id relinking.

## 7. Durability and filesystem guarantees that are NOT established

- os.replace on POSIX atomicity applies to one entry on the same file system; it is not automatically portable to a different mount or a directory containing mutable SQLite sidecars.
- Linux fsync(file) does not imply directory metadata persisted; fsync of parent directory is needed under the documented model.
- SQLite atomic commit and WAL/native recovery do not make an application pointer+journal+HA registry a unified atomic transaction.
- A timeout/cancelled Python coroutine does not prove a SQLite executor thread has stopped touching the old path.
- Directory fsync, atomic rename, write-cache behavior, file permissions, available space and different filesystem types on HA OS/Container must be tested.
- This design cannot automatically distinguish all full-folder restores or arbitrary foreign/older history.

Until measured, this ADR shall not use phrases such as guaranteed power-cut recovery, zero-data-loss, always-safe automatic restore or proven WAL-clean promotion.

## 8. Operational cost and retention trade-offs

Keeping a prior live generation plus immutable snapshot can multiply disk use. Before commit, preflight capacity should account for current mutable DB, WAL, new working copy, immutable source, journal/temp writes and safe backup reserve. Quotas must preserve last known good history rather than deleting it automatically to make space.

GC cannot remove generations referenced by active pointer, recovery journal, running HA backup/archiver, valid export or a user-authorized rollback reservation. Missing post-backup event is not proof that tar no longer reads. If disk full while publishing the pointer/journal, keep current verified data and report it as degraded, never silently overwrite or drop original history.

An application journal is potentially personal metadata: keep minimal opaque IDs, bounded audit evidence, no Sony credentials, raw player data or unrestricted diagnostic paths.

## 9. Approval gates

This ADR can become technically ACCEPTED only after:
- maintainer explicitly chooses F2 or a source-supported safer alternative, approves filesystem layout and data-loss limitations;
- Core/HA OS/Container tests prove pointer+journal publication and power-loss behavior at every phase;
- SQLite linked-version/WAL bug/runtime worker and positive connection closure verified;
- reconciliation after HA registry version drift, disabled consoles and PSN account unlinks verified;
- admin preview expiry, double-confirm idempotency, browser disconnect and global shutdown tested;
- privacy/path/hostile import protections, file permissions and safe retention/GC tested;
- full/partial Supervisor restore and storage scope documentation validated;
- all 80 SPEC-015 scenarios and 20 OPEN gates reviewed with reproducible evidence.

The product-level Hub/Archive acceptance of ADR-0011 remains intact regardless of the outcome of this proposed technical method.

## 10. Sources and evidence links

- [Pinned SQLite/POSIX research](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md)
- [SPEC-015 tests and gates](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md)
- [ADR-0014 admin recovery](ADR-0014-admin-recovery-authority-and-upstream-api-requirements.md)
- https://www.sqlite.org/howtocorrupt.html
- https://www.sqlite.org/atomiccommit.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/backup.html
- https://docs.python.org/3/library/os.html#os.replace
- https://man7.org/linux/man-pages/man2/fsync.2.html
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/config_entries.py
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/core.py
- https://github.com/home-assistant/supervisor/blob/69848689a1e982ebe92d80e344fc086d8af667db/supervisor/homeassistant/module.py

**Status:** PROPOSED. No executable code, database migration, test, HA OS event, new feature branch or changes to develop.
