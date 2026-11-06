# ADR-0008 — Storage architecture, durability, backup and restore

**Status:** Proposed for architectural approval; not implemented or benchmarked  
**Date:** 2026-11-05  
**Applies to:** The single HACS PlayStation Hub integration on Home Assistant Core/OS, with multiple physical consoles and optional PSN accounts  
**Inputs:** ADR-0003 (provisional SQLite), ADR-0004 (identity), ADR-0005 (observations), ADR-0006 (sessions), ADR-0007 (credentials)  
**Downstream:** ADR-0009 (Home Assistant entities and actions), ADR-0010 (panel and WebSocket API), release and data-privacy documentation  
**Research branch:** `main` only; no executable code on `next`, no changes to `develop`

> **Evidence boundary:** This ADR compares storage mechanisms using Home Assistant documentation and current `core/dev` `homeassistant/helpers/storage.py`, Recorder documentation and legacy source, but does **not** prove backup behavior, filesystem durability or performance on the user's Home Assistant OS installation. In particular, no database migration, volume benchmark, live backup or restore has been executed. The design is a **proposal**, not a completed security or reliability certification.

## 1. Problem, requirements and non-goals

PlayStation Hub needs reliable long-lived, multi-console/multi-account history (including observation evidence, bounded sessions, uncertain gaps and game metadata), native HA entity statistics, small user preferences and **separately protected** PSN/Remote Play credentials. A single format must not be imposed on every category, and Home Assistant's Recorder must not be modified with our own tables.

### Mandatory requirements

1. Persist session evidence and checkpoints transactionally and idempotently; avoid inventing elapsed time after shutdown, crash or an offline interval.
2. Support three or more years of records for multiple consoles, players and games with predictable range queries.
3. Do not block Home Assistant's event loop with sqlite3, JSON serialization or filesystem operations.
4. Keep HACS-managed code directories **immutable** with respect to user data; upgrades must never overwrite the ledger.
5. Use HA Config Entries and Options for integration lifecycle and relevant small configuration, not as arbitrary bulk event logs.
6. Keep secrets logically and physically separable from historical sessions, cache and user exports.
7. Preserve data when one console/account fails; support safe multi-entry unload/reload and shared-manager lifecycle.
8. Provide integrity checks, schema migrations, explicit errors and user-authorized backup/restore/export/delete behavior.
9. Support Home Assistant backups where applicable, including consistent SQLite snapshots while the integration is active.
10. Avoid requiring PostgreSQL, MySQL, Mosquitto or any extra application/container.
11. Provide useful HA sensors and long-term statistics where their semantics fit, without treating Recorder as the entire multi-year event ledger.
12. Define a clear distinction between complete, partial, historical last-known, stale and unsaved data.

### Non-goals

- Writing SQL tables into Home Assistant's own Recorder database.
- Treating the default HA entity history retention as a full game-session ledger.
- Assuming local `.storage` files are encrypted secrets vaults.
- Requiring the user to run a separate database service.
- Claiming that WAL mode alone makes an arbitrary file-copy backup consistent.
- Guaranteeing that remote Sony refresh-token rotation and a local disk commit are one atomic transaction.
- Deleting private historical data automatically merely because a HACS code folder is removed.

## 2. Data classification and proposed owners

| Data class | Example | Proposed owner | Lifecycle / sensitivity |
| --- | --- | --- | --- |
| Integration entry configuration | Console/account IDs, preferred address, options | HA Config Entries | Native setup/reconfigure/unload; moderate sensitivity |
| Secrets | NPSSO, PSN refresh/access, RP keys | Credential repository chosen by ADR-0007/0008 | Highly sensitive; versioned per owner |
| Small preferences/checkpoints | Sidebar settings, schema/index sync metadata | HA `Store` candidate | Small versioned JSON; not bulk time series |
| Raw accepted evidence / domain events | Observation IDs, scope, source, UTC receipt, accepted state | App-owned ledger candidate | Time-indexed personal use data |
| Bounded session segments | Per-console interval, inferred player, title and gaps | App-owned ledger candidate | Durable, transactional, multi-year |
| Game metadata / title mappings | Names, title IDs, source, locale | Catalog repository (cache or DB) | Provider rights and staleness |
| PSN account library snapshots | Titles, entitlements, provider times | Separate account-scoped tables or cache | Private, optional, permission gated |
| Artwork binaries | Provider-approved icon/cover | Bounded cache if rights permit | Evictable; not essential to restore |
| HA sensor/entity history | Current state and eligible numerical statistics | Home Assistant Recorder | HA-managed schema/purge/statistics |
| Exports/backup archives | User-authorized CSV/JSON/snapshot | Controlled export/backup service | Private, authenticated and temporary |

**Isolation invariant:** Secrets never enter the game-history SQLite tables, entity extra attributes, frontend bundles, logs or generic export formats. Even a shared physical storage directory must maintain separate logical owners and deletion behavior.

## 3. Options comparison

| Mechanism | Strengths | Weaknesses / risks | Recommended role |
| --- | --- | --- | --- |
| HA Config Entries | Native config/reauth/unique ID lifecycle | Not designed for high-frequency event ledger; storage is not automatically encrypted | Setup/identity/options only; secrets considered separately |
| Home Assistant `Store` | Versioned JSON, integrated `.storage`, async save/load, atomic-write option | Whole-object JSON, costly for large collections, no indexed range queries or multi-record SQL transactions | Small preferences/settings and potentially reviewed credentials |
| HA Recorder & long-term statistics | Native HA timeline, automations, numerical sensor aggregates | Default raw history retention, HA-managed schema, not arbitrary joins/segments; no custom SQL | Selected HA-native entities/aggregates |
| Dedicated SQLite file | Transactions, indexes, concurrent bounded reads, migrations, portable local single-file DB | Need dedicated async-safe owner, WAL/snapshot strategy, backup, integrity and recovery policy | **Preferred candidate for detailed history**, provisional |
| CSV/JSON files as main history | Human-readable, trivial export | Concurrent writes, recovery, indexing and schema evolution weak | Export/import only |
| Extra PostgreSQL/MySQL | Strong server DB capabilities | Extra service/credentials/ops burden, contrary to one HACS integration target | Reject as mandatory |
| One external/cloud database | Potential remote history | Privacy, network dependency and third-party service | Not required |

### Selection recommendation (still proposed)

Adopt a **hybrid architecture**:
- Native Config Entries/Options for per-console and per-account entry configuration.
- Versioned HA `Store` for small settings/operational metadata where its exact semantics fit.
- A **dedicated application-owned SQLite database** for authoritative local events, segments, uncertainty and bounded historical queries, subject to benchmark/backup approval.
- Home Assistant Recorder for native sensor state/history and long-term statistics where applicable, without direct custom table manipulation.
- A distinct, strongly scoped credential repository, to be selected after security and backup review; do not assume ordinary `Store` JSON is encrypted.
- A bounded metadata/artwork cache outside HACS-managed code, with explicit provider permissions and eviction.

This **does not yet approve** dedicated SQLite or supersede ADR-0003. Accept this ADR only after the validation gates below.

## 4. Official Home Assistant `Store` implementation findings

Inspected `homeassistant/helpers/storage.py` on the current Core `dev` branch (2026-11-05):

- Storage directory `STORAGE_DIR = ".storage"`; `Store.path` is derived from `hass.config.path(STORAGE_DIR, key)`.
- `Store` supports storage schema versions/minor versions and migration.
- `async_save` performs an awaited immediate write path; `async_delay_save` schedules/coalesces writes, so a delayed call is **not a durable acknowledgement**.
- Current constructor supports `private`, `atomic_writes` and `serialize_in_event_loop` options. `atomic_writes` is **False by default in the inspected source**, so do not assume writes are atomic unless configured and verified.
- The implementation has a per-store `asyncio.Lock` for writes; this does not automatically create a transaction spanning **multiple different Store keys**, nor does it solve concurrent owner updates in our application domain.
- `private=True` affects filesystem privacy handling but is **not equivalent to encryption at rest**.
- For large JSON payloads, serialization on the event loop may be costly. `serialize_in_event_loop=False` is only safe when serialized input is immutable/thread-safe; do not share mutable dictionaries and expect race-free writes.
- Current code contains specific handling for corrupted store data, which is further evidence that corruption/recovery must be handled rather than silently replacing a damaged store.
- The precise durability semantics of `write_utf8_file_atomic` / filesystem `fsync`, and whether they meet credential rotation requirements on all HA OS filesystems remain an **implementation-stage source and test gate**.

**Proposed use:** A few versioned, bounded settings and small metadata records. No per-observation JSON append or unbounded history arrays. An explicitly awaited immediate save may be appropriate for a reviewed credential store, but durable-write guarantees must be tested and documented; HA `Store` is not a magic transaction or secret vault.

## 5. Home Assistant Recorder and long-term statistics

Official HA documentation states:
- The Recorder records entity state changes/events and its raw history is kept for **10 days by default**, configurable.
- Eligible numeric sensors with a `state_class` receive five-minute short-term statistics and hourly long-term statistics. Hourly long-term statistics are **not automatically purged**, but this does not preserve the full per-game/player event timeline.
- HA also supports integration-provided long-term statistics in suitable cases; consult supported API and state-class semantics rather than using undocumented Recorder tables.
- Disabling/excluding an entity from Recorder changes whether its statistics are collected; user Recorder configuration belongs to Home Assistant, not our persistence engine.

**Project boundary:** Use appropriately modeled sensors for console availability, aggregate observed durations and other stable metrics; let HA manage their recording and statistics. Keep authoritative multi-year detailed sessions in the private ledger. Do **not** read/write Recorder tables as part of game-history SQL joins, manually insert entities' history, or assume a sensor's `total_increasing` state class suits resettable daily/session counters.

### Long-term statistics caveat

Recorder hourly aggregates are excellent for charts and Home Assistant automations, but cannot reconstruct the identity, uncertainty and provenance of every game segment. They may also remain when an entity is removed. Define explicit deletion/export/privacy semantics for our own DB separately from HA's Recorder history.

## 6. Dedicated SQLite candidate — ownership and file placement

**Preferred logical store:** One **application-owned history database** per Home Assistant installation, with `console_id`/account title keys in indexed tables, rather than a separate SQLite database per console. This allows consistent cross-console queries, association joins and one schema migration owner. It also increases shared-manager lifecycle responsibilities and requires isolation by canonical IDs.

**Proposed location:** A dedicated PlayStation Hub data path within the Home Assistant configuration tree, e.g. a private data directory resolved through supported `hass.config.path(...)`, **outside** `custom_components/playstation_hub/` and separate from the Recorder database. Exact path, backup coverage, permission and cleaning semantics are **OPEN** pending supported HA Core/OS validation.

**Single database owner:** A shared integration-scope `HistoryRepositoryManager`, not the first config entry that starts. Config entries reference it through controlled runtime ownership. Unloading console A cannot close a database still being used by console B; panel/history APIs must stop safely on last owner/integration teardown.

**Connection policy:** Do not share one unrestricted sqlite3 connection across unrelated asyncio tasks. Use a dedicated serialized writer (worker/executor-thread actor, or vetted async SQLite library with controlled queue), bounded reads/connection pool, no event-loop blocking, well-defined teardown and explicit transaction boundaries.

## 7. Logical schema proposal (not SQL implementation)

```text
schema_meta
  schema_version, application_version, last_migration_id

console_identity
  console_key, type, validated_host_id, created_at_utc, inactive_at_utc

psn_account_reference
  account_key, optional display name, linked_at_utc, inactive_at_utc
  NO OAuth credentials or NPSSO

console_account_association
  association_id, console_key, account_key, relation, provenance, active_range

observation_index
  observation_id, run_id, source, target_key, observed_at_utc
  source_generation, acceptance_revision, sanitized fact, valid_until

domain_events
  event_id, observation_id, console_key, event_type, event_at_utc, revision

session_segments
  segment_id, console_key, optional account_key, optional title_key
  session_type, start_utc, end_utc, last_checkpoint_utc
  attribution, boundary_quality, closed_reason, revision

unknown_intervals
  interval_id, console_key, start_utc, end_utc, reason, evidence_refs

game_identity
  provider, namespace, title_id, platform_scope, mapping_version

game_metadata
  game_key, locale, fields, source, fetched_at_utc, freshness, rights_status

account_library_snapshot
  account_key, title_key, relation, snapshot_at_utc, provider_playtime
  provider_time_units, entitlement_status, provenance

retention_tombstone / audit_revision (if approved)
  owner, revision, deletion/reassignment reason, timestamp
```

**Model principles:** Immutable canonical owner keys (ADR-0004); source observation IDs and generations (ADR-0005); half-open UTC segments and uncertain intervals (ADR-0006); explicit metadata namespaces (Protocol 10). Every table, index and foreign key must be specified in a reviewed SQL migration, with synthetic fixtures before implementation.

**Indicative indexes:** `(console_key,start_utc,end_utc)`, `(account_key,start_utc)`, `(title_key,start_utc)`, `(event_at_utc)`, unique observation/event IDs, association keys, and `(source,target_key,observed_at_utc)`. Benchmark and tune rather than creating every possible index or storing duplicate summary counters by default.

## 8. SQLite transaction/locking design

- **Atomic ingest:** Validate and accept an observation, apply event/segment transitions and advance durable checkpoint/last accepted cursor **within one transaction**. If any write fails, no part of that logical state change may be committed.
- **Single writer:** Serialize writes by explicit queue/actor or equivalent. Reads must see committed snapshots, never intermediate partially migrated state.
- **Idempotency:** Unique event/observation IDs, version numbers and SQL constraints prevent duplicated minutes on replay, restart or repeated API callbacks.
- **WAL candidate:** SQLite `journal_mode=WAL` can improve concurrent reads/writes, but introduces `-wal` and `-shm` files and backup consistency concerns. Test WAL settings, checkpoint policy, rollback and shutdown behavior before deciding PRAGMAs.
- **Durability:** Explicitly choose `synchronous` level, busy timeout and write batching through controlled tests. Do not silently trade away durable historical evidence to gain superficial throughput.
- **Integrity:** Controlled `PRAGMA quick_check` on bounded intervals and `integrity_check` during repair/export as supported, plus SQLite exception classification and non-destructive quarantine.
- **No auto-recreate on failure:** An unreadable database must be quarantined or put into read-only recovery, not overwritten with a fresh empty DB without user awareness.
- **No raw secrets:** SQLite historical records contain no OAuth tokens, Remote Play keys, PINs, raw full HTTP payloads or unredacted private diagnostics.

### Runtime backpressure

A 30-second polling interval is not a promise that every UDP heartbeat becomes a durable event row. Deduplicate identical state transitions, update checkpoint/snapshot only as needed for ADR-0006, bound write queue depth and reject/mark unsaved data on overload rather than blocking the HA event loop indefinitely.

## 9. Home Assistant OS backup and snapshot consistency

**Key distinction:** An HA backup includes only the configured data/settings/categories, and a directory living beneath `/config` is not by itself an evidence-based guarantee of an **application-consistent SQLite snapshot** while a write transaction or WAL checkpoint is active.

**Preferred implementation candidate:** Quiesce ingestion or use SQLite's supported **online backup API** to generate a consistent read-only snapshot of the history DB before packaging; checkpoint/backup must include a clear high-water mark. Use Home Assistant's supported backup integration APIs if applicable to a custom integration on the pinned Core release, or document a user-triggered coherent snapshot/export path. Never assume simply zipping the main `.db` file is sufficient in WAL mode.

### Backup consistency design

1. Identify the exact installed Home Assistant OS/Core backup behavior and if custom-integrations' `/config` data directory and separate credential store are included in the relevant backup type.
2. Define a **snapshot barrier**: choose a durable observation/event high-water mark and commit outstanding writes to that point before snapshot.
3. Produce a consistent SQLite snapshot with the officially supported sqlite3 backup mechanism (or proven coordinated quiescence/checkpoint approach) to a temporary, protected target outside HACS code.
4. Check snapshot integrity/version and record snapshot timestamp, schema version and high-water mark.
5. Use the officially documented Home Assistant `backup.py` platform pre/post hooks where appropriate. Their existence and the pinned Core 2026.11.0 manager invocation are source-confirmed; actual registration and PlayStation Hub snapshot safety must still be tested.
6. Avoid snapshot file accumulation; securely clean temporary files and handle full disk, interrupted backup or stopped integration.
7. Ensure credentials are protected and backed up separately according to ADR-0007, never copied into public session exports.
8. Verify archive restore in an isolated Home Assistant OS test: database opens, indexes and constraints work, history matches the high-water mark, and pending observations are not counted twice.

**Important unresolved integration constraint:** The official pre/post backup platform hooks exist at Core 2026.11.0, but a consistent SQLite WAL snapshot, archive inclusion, cancellation, restore and recovery have not been demonstrated on PlayStation Hub. Hook existence is not an approved backup architecture.

## 10. Encryption and privacy boundaries

- Home Assistant encrypted backup archive != runtime on-disk encryption of ordinary `.storage` or SQLite files.
- Set protected filesystem permissions for secret records and private history as supported; limit access through authenticated HA server APIs.
- Encrypting an application file with a key stored next to it offers limited protection against a compromised HA host. Do not invent an encryption system without an independently justified key-custody strategy.
- History itself is potentially personal information (timestamps, games, players, minors); redact exports and diagnostics unless explicitly user-authorized.
- Artwork and external URLs may have licensing and privacy restrictions; metadata cache is not necessarily safe for public distribution.
- Do not store a Sony credential merely for convenience if it can be discarded after an authorized bootstrap; balance token recovery and minimization according to ADR-0007.
- Separate account removal from console removal: deleting a Sony account must not destroy independent LAN session evidence unless user explicitly chooses deletion of identifiable history.

## 11. Migrations, upgrades, rollback and compatibility

- Maintain monotonically versioned **database schema migrations**, separate from integration/release version and credential-store schema version.
- Every migration runs in a controlled transaction where SQLite supports it, with validation, checksum/expected-schema checks and a recoverable pre-migration snapshot.
- Do not destructively migrate to unsupported newer schema when running older code after a downgrade. Mark read-only/unsupported and instruct user on safe restore/upgrade.
- Test incremental migrations `v1 -> v2 -> v3` and direct supported upgrades, failure mid-migration, duplicate ids, constraints, rollback and restart.
- Historical `develop` DB `SCHEMA_VERSION=3` is **not** our v3 target schema. Do not implicitly adopt the old numbering or import legacy real user data. Any migration must be a separate opt-in import pathway with source validation.
- HACS updates may replace integration source; mutable DB and `.storage` data must not be inside HACS managed source path.
- Preserve canonical console/account identity and title mapping, otherwise upgrades may split or merge history incorrectly.
- Treat source application and HA Core minimum version as explicit compatibility gates.

## 12. Recovery and failure policy

| Incident | State handling | Durable history | Repair |
| --- | --- | --- | --- |
| Ordinary HA restart | Restore latest committed checkpoints; current live state stale until new probes | Preserve and idempotently close incomplete sessions at last persisted evidence | Normal |
| Power failure during transaction | SQLite rollback/recovery policy | No partial logical observation write | Verify opening and integrity |
| Crash after PSN refresh before credential commit | Auth may need reauth | Unrelated history preserved | Targeted reauth only |
| Disk full / denied write | Live state may remain in memory but flagged unsaved | **No** false committed history claims | Local storage repair |
| DB malformed or unsupported schema | Stop writes, quarantine/read-only as suitable | Never silently reset | Backup/repair |
| Old HA backup restored | Rehydrated history only up to backup high-water mark | Missing interval reported as unknown | Reauth/repair credentials separately |
| Console removed | Console runtime/entities removed | Retention/archive or explicit user deletion | User-controlled |
| PSN unlinked | PSN polling stops | LAN history remains, account-associated records policy explicit | Remove scoped secrets |
| Cache corrupt | Reset only evictable metadata cache | History untouched | Regenerate if permitted |
| HA Recorder purged | HA entity raw states removed per HA settings | PlayStation Hub ledger preserved | No database side effects |
| HACS uninstall | Executable source removed | Auxiliary data may remain until explicit removal | Document cleanup policy |

**Consistency rule:** The displayed statistics must not silently include unsaved in-memory segments. Surface `persistence_health`, `data_as_of` and gaps as specified in ADR-0006.

## 13. Retention, user control and deletion semantics

A default **multi-year** retention target is part of product requirements, but exact time and disk quotas are configurable decisions. Proposed:
- Session segments and their provenance: long-lived with user-selectable retention/export/purge.
- Raw transport diagnostics/failed packets: do not persist arbitrarily; bounded sanitized metadata only.
- Stable identity/association registry: persist while referenced by active or retained history; use tombstones rather than accidental cascades.
- PSN library/account metadata: retain only with user consent and explicit account unlink behavior.
- Artwork: bounded evictable cache; no indefinite copying without source rights.
- Access/refresh tokens: replace on rotation, delete on unlink, never include in generic exported sessions.
- Full uninstall: guide user through `keep history / export history / delete integration-owned data`, with protected admin-only operations and clear warning about HA Recorder's separate data ownership.
- Session account removal must not cause orphaned foreign keys or silently relabel previously attributed activity to a different user.

An SQL foreign-key `ON DELETE CASCADE` can cause unintended loss of historical observations; do not enable cascading from active console/account identity into session ledger by default without explicit privacy and retention policy.

## 14. Capacity model and performance budgets

**Scenario assumptions, not benchmark results:**
- 4 consoles, one status observation every 30 seconds, 24 hours/day, 365 days/year for 3 years: **12,614,400 raw observations** if every poll were persisted individually.
- If only 10% became durable rows: ~1,261,440 rows, but the true rate depends on source changes and checkpoint policy.
- Metadata/entitlements and sessions add additional rows; images can dominate disk if cached without limits.
- A separate configuration with more consoles or more frequent observations can greatly exceed those numbers.

**Required measured benchmarks**:
1. Startup and migration with 0, 100k, 1M and ~13M synthetic observations/rows.
2. 36 months of session ranges with indexed daily/week/month/all-console queries.
3. Concurrent writers (simulated consoles) and dashboard readers, plus UI pagination.
4. Durable write latency p50/p95/p99 under storage contention; no HA event-loop blocking.
5. Disk usage, WAL growth/checkpoint behavior and bounded metadata/image caches.
6. Backup creation and restore duration/size; verify integrity under active writes.
7. Stress corrupt DB, interrupted migration, disk full and concurrent recovery.
8. Battery/RAM/CPU consumption on representative Home Assistant OS hardware rather than a desktop-only test environment.

**No claimed performance numbers:** None of these benchmarks has yet been executed. The capacity calculation is a planning upper bound, not a projected actual database size.

## 15. Repository boundaries and conceptual interfaces

```text
StorageCoordinator
  open_schema_and_migrate()
  acquire_shared_owner()
  close_after_last_consumer()
  prepare_consistent_backup()
  recover_from_interrupted_session()

SessionLedgerRepository
  commit_observation_and_segments(expected_generation, event, checkpoint, segments)
  get_segments(console/account/title, start, end, cursor, max_results)
  get_unknown_gaps(...)
  get_recovery_marker(...)

GameCatalogRepository
  upsert_metadata_with_source_and_locale(...)
  find_by_namespaced_title_identity(...)
  evict_expired_cache(...)

PsnCredentialRepository / RemotePlayCredentialRepository
  load(owner_key)
  compare_and_replace(owner_key, old_generation, new_secret)
  delete(owner_key)

HistoryReportService
  summarize_intersected_half_open_period(...)
  provider_lifetime_totals_separate(...)
  split_by_configured_local_timezone(...)
```

These are abstract contracts. File/folder names are **roadmap suggestions**, not requests to create empty modules in `next`. Storage is independent of HA entity getters and transport packet parsing. Every user-facing query must be bounded, authorized, and paginated as appropriate.

## 16. Validation matrix and acceptance gates

### A. HA Store and credentials
- [ ] Confirm `private` and `atomic_writes` behavior on the targeted supported HA Core version; no assumption of encryption.
- [ ] Test immediate vs delayed saves; ensure a reported credential rotation awaits a successful durable commit.
- [ ] Test two concurrent owner records, generation conflicts and corrupt versions.
- [ ] Test permissions and redaction in debug, diagnostics, frontend and backups.
- [ ] Test backup restore of rotated/expired tokens without erasing LAN data.

### B. SQLite ledger
- [ ] Transaction injects failure after event insert but before checkpoint: no partial commit.
- [ ] Duplicate `observation_id` replay cannot double-add seconds.
- [ ] A known console with an altered IP retains history; a different identity at that IP cannot inherit it.
- [ ] Crash during active sessions closes at last durable checkpoint, and records gap.
- [ ] Multi-console transaction isolation, concurrent range queries, WAL growth and checkpoint tested.
- [ ] Schema migrations, unexpected version, failed disk write and integrity check handled.
- [ ] Query by console/account/title/local calendar period remains bounded and performant.
- [ ] No secrets in history tables or SQL query logs.
- [ ] Cache eviction cannot erase historical sessions or immutable title identity.

### C. HA backup / restore
- [ ] Verify exact inclusion of app DB and credential store in selected HA OS backup type.
- [ ] Validate the documented backup platform pre/post hooks in a running custom integration, including cancellation and failure, archive inclusion and consistent SQLite WAL restore (hook existence is source-confirmed).
- [ ] Produce an SQLite consistent snapshot under active writes and verify matching high-water mark.
- [ ] Restore into isolated HA OS, compare reports and integrity, and detect missing intervals.
- [ ] Interrupted backups and storage-full conditions produce clear errors and no corrupted accepted backup.
- [ ] Verify encrypted and differently configured backup destinations; never confuse archive encryption with runtime encryption.
- [ ] Restore into an upgraded/downgraded schema under documented supported policy.

### D. HA Recorder and frontend
- [ ] Native sensor states and long-term statistics agree with ledger's bounded metrics, without false resets.
- [ ] Recorder purge/restart does not alter application ledger.
- [ ] WebSocket report APIs read pagination-controlled, authorized data without accessing SQLite on event loop.
- [ ] Admin/user permissions restrict private account/history/exports.
- [ ] Integration unload/reload and one-console removal do not close shared history manager prematurely.

**Approval evidence required:** Pinned HA Core version, source read of backup/restore interfaces, proof-of-concept with only synthetic data, complete reproducible benchmark and recovery results, reviewed threat model and explicit user approval of storage policy. Without this, SQLite remains provisional and Store secret handling remains unresolved.

## 17. Proposed decisions and blockers summary

| Choice | Current status |
| --- | --- |
| One HACS integration, no required external DB | Existing project direction |
| HA Config Entries/Options for setup | Proposed implementation of established HA norms |
| Versioned Store for small JSON | Preferred candidate |
| Separate credential repository | Security requirement from ADR-0007; concrete backend open |
| Dedicated SQLite per installation for detailed history | **Preferred candidate, not approved** |
| Direct writes into HA Recorder tables | Rejected |
| HA Recorder for eligible sensors/statistics | Preferred HA-native complement |
| WAL and synchronous transaction mode | To benchmark and approve |
| Consistent backup mechanism and HA hook support | Hook existence source-confirmed at Core 2026.11.0; snapshot/restore **OPEN** |
| Runtime at-rest encryption/key custody | **OPEN** |
| Automatic deletion of data when HACS source uninstalled | Not assumed |
| Restore with old Sony tokens / Remote Play credentials | Revalidate and reauth/re-pair when needed |
| Multi-console schema, index and retention policy | Proposed, test required |
| Maximum supported HA version range | To declare before implementation |

## 18. Sources and traceability

### Internal
- [ADR-0003 Provisional SQLite](ADR-0003-persistence-provisional.md)
- [ADR-0004 Identity](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0005 Observation](ADR-0005-observation-and-state-reconciliation.md)
- [ADR-0006 Sessions](ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0007 Credentials](ADR-0007-credentials-and-token-persistence.md)
- [Cross-protocol review](../architecture/cross-protocol-review-01-10.md)
- [Architecture guide](../../ARCHITECTURE_GUIDE.md)

### Official Home Assistant documentation and source
- https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py
- https://developers.home-assistant.io/docs/config_entries_index/
- https://www.home-assistant.io/integrations/recorder/
- https://www.home-assistant.io/docs/configuration/long-term-statistics/
- https://contributors.home-assistant.io/architecture/core/history/
- https://www.home-assistant.io/common-tasks/general/backups
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/

### SQLite official reference
- https://sqlite.org/backup.html
- https://sqlite.org/wal.html
- https://sqlite.org/pragma.html#pragma_integrity_check
- https://sqlite.org/pragma.html#pragma_synchronous

### Legacy reference (do not import production data)
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/session_tracker.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/usage_statistics.py

**Outcome:** Hybrid architecture preferred; concrete SQLite, Store secret policy and backup orchestration remain subject to source-verified and synthetic HA OS tests. Nothing was implemented or validated on the user's installation.

## 19. Official-source update — Home Assistant 2026.11 and Marketplace

The [2026.11 official-source re-audit](../research/official-source-reaudit-home-assistant-2026-11.md) confirms official `backup.py` pre/post hooks and their pinned Core backup manager invocation. The previous uncertainty about the hooks' **existence** is now closed at source level; PlayStation Hub snapshot/backup/restore correctness remains untested. Marketplace `hacs.json.persistent_directory` can preserve integration-owned user files across updates, but it does not prove transactionally safe SQLite backup or encryption. Prefer mutable data outside HACS-managed source until the storage policy has been approved and tested. This ADR remains Proposed.


## Source audit addendum — 2026-11-06: shared writer and HA OS backups

**Status unchanged: PROPOSED, not implemented/tested.** See the [Core 2026.11 shared-services and SQLite audit](../research/ha-core-2026-11-shared-services-lifecycle-and-sqlite-audit.md) and [SPEC-009](../specifications/SPEC-009-shared-service-lifecycle-concurrency-and-sqlite.md).

- A single serialized writer is insufficient without a **global single-flight initializer**, a manager-controlled state machine, pending/active entry leases, bounded query/snapshot leases and a non-overlapping writer-generation close/reopen fence. Core's entry-local setup locks do not serialize different Config Entries.
- Initial schema migration and writer startup must run once; a setup cancellation must not cancel initialization needed by other entries. An unload failure leaves a tracked owner until actual cleanup is proven, not a fake zero reference count. Durable commits and history gaps must be distinct from live LAN observations.
- The pinned CoreBackupReaderWriter invokes backup platform pre/post hooks, but **HA OS uses SupervisorBackupReaderWriter**; callback invocation, archive filtering and restore semantics on HA OS are not validated by the generic Core path.
- The generic Core backup exclusion list ignores arbitrary custom SQLite data and WAL: it excludes *.db-shm and conditionally the HA Recorder DB, but not automatically our future DB and -wal. A consistent additional SQLite snapshot could be included alongside an unsafe raw copy; an explicit authoritative restore selection protocol is required.
- SQLite upstream Online Backup API and VACUUM INTO provide candidate consistent snapshots; WAL synchronous=FULL and bounded snapshot/query/backup leases are candidates requiring OS-level tests, integrity checking, backup manifest and recovery-on-crash review.
- No claim of successful multi-year history backup or restore, no approved storage path/PRAGMA setting and no change to the current ADR decision state.


**Additional source verification (2026-11-06):** The exact Supervisor-to-Core pre/post hook *mechanism* has now been traced: pinned Supervisor module begin_backup/end_backup sends Core WebSocket backup/start/end, and pinned Core backup/websocket.py invokes BackupManager's pre/post actions. Thus do not interpret the preceding uncertainty as absence of source evidence. **Unresolved and untested:** actual custom platform registration on the target HA OS, snapshot/archive consistency, custom live .db/-wal inclusion, snapshot provenance, safe restore, and interrupted-backup failure modes. Details: [audit §17](../research/ha-core-2026-11-shared-services-lifecycle-and-sqlite-audit.md#17-supervisor-to-core-backup-handshake-re-audit--2026-11-06-stronger-source-evidence). This clarification does not approve ADR-0008.


## Crash, WAL-reset bug and restore-provenance source checkpoint — 2026-11-06

**ADR state remains PROPOSED.** The new [recovery source audit](../research/sqlite-crash-restore-provenance-and-archive-access-2026-11.md) and [SPEC-010](../specifications/SPEC-010-crash-recovery-restore-provenance-and-archive-access.md) refine the earlier shared-lifecycle audit.

**New P0 SQLite gate:** Upstream SQLite officially documents a rare concurrent WAL checkpoint/write corruption bug in versions through 3.51.2, fixed in 3.51.3+ and selected backports 3.44.6/3.50.7. Validate the actual C SQLite library in the target HA OS Python runtime; Python or HA Core versions alone do not prove this fix. A single serialized writer plus single checkpoint authority are necessary architectural controls but must not be presented as a substitute for a patched library.

**No automatic snapshot-on-startup:** a fully valid old snapshot can coexist with a newer fully valid live ledger after an ordinary Home Assistant reboot. Reapplying the old snapshot merely because its manifest exists silently erases recent sessions. A restore needs trustworthy one-time intent or an explicit user action, exclusive resource fence, schema/ledger identity/cursor validation and non-destructive original-file preservation. Hash matching is not a proof of freshness or authorization. SQLite integrity_check does not replace foreign_key_check.

**Two alternative backup candidates:** (A) stop new writes and close/checkpoint all SQLite connections for the entire Supervisor config archive; simple restore authority but sustained monitoring gaps. (B) stage immutable Online Backup API snapshot+manifest while writes resume; requires separate authoritative source selection because Supervisor may also copy active DB/WAL. A and B are unapproved and untested; do not treat a generic HA backup's Recorder exclusion as excluding our application SQLite.

**Pinned restore source behavior:** Supervisor's full/selected partial Home Assistant configuration restore clears/copies configuration files, preserving only explicitly named Recorder files when its exclude_database mode is enabled. It can overwrite custom PlayStation Hub history. Pinned Core .HA_RESTORE is a distinct restore path; not a universal marker for Supervisor restoration.

**No empty reset:** on corruption, lost acknowledgement, failed restore or unknown-version schema, preserve old files and enter guarded recovery instead of creating a blank replacement history. Keep live current power/availability distinct from persisted historical coverage. No actual HA OS version, filesystem snapshot, power-cut or recovery test has been performed.


## Storage-location and backup-hook correction (2026-11-06)

**This ADR remains PROPOSED.** [Source audit](../research/ha-core-2026-11-storage-layout-restore-authority-archive-root.md), [ADR-0011](ADR-0011-storage-layout-restore-authority-archive-hub.md) and [SPEC-011](../specifications/SPEC-011-storage-roots-restore-authority-archive-hub-lifecycle.md) supersede any active language calling a whole-archive SQLite write freeze the straightforward safe default.

1. hass.config.path resolves the configuration directory; hass.config.cache_path is explicitly excluded from backup. Dedicated private configuration-root SQLite remains a candidate, separate from HACS assets, HA Store-managed .storage JSON and public /config/www.
2. Full/selected-partial Supervisor restore may replace the entire application folder under config; database exclusion targets Recorder files only. /share and /media can be excluded from recommended automatic backups, and out-of-config live data can conflict with older restored Config Entry associations.
3. **P0 backup hook asymmetry:** Core pre hooks run concurrently and may return a collective failure; pinned Supervisor awaits begin_backup before the matching end_backup try/finally. If another pre hook fails after ours quiesces, our post hook may never run. Long-held pre/post SQLite freeze is BLOCKED until explicit rollback/end-of-archive proof; a timer-based unfreeze may invalidate active archive consistency.
4. Online Backup API immutable snapshot + manifest is the preferred next research direction but still requires excluding/disambiguating the raw live DB/WAL from the archive, trusted restore selection and target HA OS validation. Snapshot cursor must be obtained from the completed snapshot itself.
5. Snapshot/manifest two-file renames are not atomic as a pair; use a generation-scoped completed-publication contract. Protect the current ledger, last known good copy and private sensitive history; no silent auto-recovery by overwriting the valid live file.
6. Pending ADR-0011 decides an optional explicit logical Hub/Archive Config Entry for archive-only browsing and backup integration setup. No SQLite path, PRAGMA, worker, backup strategy or Hub entry is now approved or implemented.


## 2026-11-06 — Maintainer acceptance scope and immutable SQLite snapshot source audit

**ADR-0008 stays PROPOSED** for the final SQL storage and backup implementation. The maintainer accepted *product-level* choices recorded in [ADR-0011 §12](ADR-0011-storage-layout-restore-authority-archive-hub.md#12-maintainer-acceptance-register--2026-11-06). The exact SQLite backend, PRAGMAs, file path and automatic restore method remain conditional. See the independent [ADR-0012](ADR-0012-immutable-snapshot-backup-and-restore-authority.md), [official-source deep dive](../research/ha-core-2026-11-immutable-sqlite-snapshot-protocol-source-audit.md) and [SPEC-012](../specifications/SPEC-012-immutable-snapshot-publication-and-backup-admission.md).

- Pinned Core and Supervisor archive filters have fixed exclusions; the documented pre/post hooks do not supply a custom per-file exclude contract. Under backed-up /config, live SQLite DB/WAL might be included in the same archive as a valid immutable app-owned snapshot. A successful app pre-hook is NOT a proven whole-archive restore guarantee.
- SQLite Online Backup API has distinct source/destination connection ownership; incremental copy can restart under concurrent source writes. Bound duration and memory, close destination, verify integrity_check+foreign_key_check, ledger UUID and DB-owned durable cursor. Only then publish a generation-specific immutable snapshot+manifest with a final completion barrier.
- Two independently renamed files are not an atomic pair; never accept partial artifact publication. Safe storage sync/rename behavior must be tested on the supported filesystems.
- No archive-long write freeze: Supervisor may fail begin_backup after our pre-hook already froze writes if another integration pre-hook errors; no matching post is guaranteed. Live writes must not depend on a callback that can be absent.
- No automatic overwrite of a valid live DB just because an older published snapshot exists. Restore intent, full-config restore, copied live DB/WAL, lineage mismatch and admin-guided recovery remain open.
- Snapshots and historical data contain personal usage information; protect with private paths, scoped API authorization and separate credential store. No production snapshot/backup/restore has run.


## Restore authority, external storage portability and split-brain — 2026-11-06

**ADR-0008 remains PROPOSED for operational storage and backup design.** The official [source audit](../research/ha-core-2026-11-restore-authority-and-portable-storage-source-audit.md), [ADR-0013](ADR-0013-restore-authority-and-storage-topology.md) and [SPEC-013](../specifications/SPEC-013-restore-authority-storage-topology-and-reconciliation.md) establish that pinned Supervisor Core mounts config/share/media but the restored config and separately selected share/media folders are independent backup scopes. Default recommended automatic HA OS backups omit share/media, so a default share-hosted authoritative ledger would be exposed to backup omission unless every installation is configured and tested correctly. A selected share backup may itself archive active SQLite DB/WAL, recreating the multi-file consistency risk. Network mounts nested under share/media require additional WAL/locality verification; never infer local file system from path text.

Current portable design direction remains a private config-root app-owned history ledger outside HACS executable code, alongside a separately published immutable snapshot, with honest limits on automatic recovery. No custom integration source-file exclusion was identified in pinned pre/post or BackupAgent interfaces. Raw tar-copied SQLite is not automatically authoritative. An ordinary reboot with an unambiguous valid live ledger must not roll back to an old staged snapshot; a suspected restore/conflicting lineage must preserve originals and be handled with an approved, admin-guided recovery policy. A ledger UUID and largest cursor alone are insufficient to resolve forked histories or Config Entry mapping mismatches. A newer external ledger plus older HA configuration may require reconciliation before writes or hardware controls resume. No backup/restore execution, schema or linked SQLite runtime was verified.


## Crash-atomic file promotion and SQLite sidecar safety — 2026-11-06

**ADR-0008 remains PROPOSED for concrete SQLite implementation.** [Source audit](../research/ha-core-2026-11-crash-atomic-recovery-journal-and-generation-promotion-audit.md), [ADR-0015](ADR-0015-crash-safe-ledger-promotion-and-recovery-journal.md) and [SPEC-015](../specifications/SPEC-015-crash-atomic-recovery-journal-and-generation-promotion.md) identify a new P0 safety constraint: official SQLite warns that renaming/unlinking an open database, moving/deleting hot WAL or rollback journal companions, or reopening the original pathname with stale connections can corrupt data. A production recovery must wait for positive closure of all writer/reader/backup/executor handles, not only cancellation of an async wrapper, and must allow native SQLite recovery at unchanged generation paths.

Preferred research candidate: a versioned new SQLite working generation copied from a separate validated immutable snapshot, with the old active generation preserved, a tiny atomically replaced active-generation pointer and a separate application recovery journal with durable phase revisions. This is **not** SQLite's own WAL and cannot make SQLite and Home Assistant .storage registry changes atomic. Python os.replace on POSIX is a one-entry atomic rename, requires same-filesystem support and does not guarantee directory entry durability without tested file and parent-directory fsync. Pointer and journal can disagree after crash: never blindly replay or roll back a successful pointer selection. Do not assume a directory containing multiple SQLite generations is compact, automatically backup-consistent or protected by an arbitrary file-exclusion API.

The user-approved ADR-0011 product architecture remains accepted while this operational strategy, fsync/worker behavior, storage path, retention and power-cut guarantees remain unapproved and untested. No backup/archive or recovery was executed.


## Recovery-Hold startup and worker cancellation source checkpoint — 2026-11-06

**ADR-0008 remains PROPOSED.** [Core 2026.11 / Python sqlite3 / aiosqlite v0.21.0 source audit](../research/ha-core-2026-11-recovery-hold-bootstrap-and-sqlite-worker-lifecycle-audit.md), [ADR-0016](ADR-0016-recovery-hold-startup-and-sqlite-worker-ownership.md) and [SPEC-016](../specifications/SPEC-016-recovery-hold-boot-order-and-worker-termination.md) distinguish control-plane LOADED and SQLite writer READY. A historical storage error can be a recoverable **internal** RECOVERY_HOLD while the approved Hub/Archive Config Entry and admin panel remain LOADED, provided domain control-plane setup succeeded. No fresh database may be silently created over corrupted/missing-with-recovery-evidence files. Physical-console/source observations remain separate from durable committed history.

The standard Python ThreadPoolExecutor cannot cancel running SQLite functions, and sqlite3.Connection.interrupt is only a statement-interruption tool, not worker/thread/connection closure evidence. The aiosqlite v0.21.0 candidate uses a serial queue per connection; enqueued functions may continue despite cancelled awaiting Futures, and close is itself queued. An active SQLite generation switch under ADR-0015 requires **positive** connection close + no executing/queued writer operations + worker terminal/join evidence, not only asyncio cancellation or Core's timed unload task waits. Dedicated ThreadPoolExecutor vs aiosqlite remain competing candidates, neither selected; actual HA OS Python-linked SQLite C version, WAL patch and performance testing remain open. If the worker does not stop, fail closed (FAILED_UNSAFE_TO_REOPEN), preserve original WAL and journal, and never invent durable history.


## Worker closure proof and aiosqlite 0.22.x version comparison — 2026-11-06

**ADR-0008 remains PROPOSED for SQLite implementation.** [Pinned worker/capability source audit](../research/ha-core-2026-11-degraded-capabilities-worker-proof-and-aiosqlite-022-audit.md), [ADR-0017](ADR-0017-degraded-operation-capabilities-and-sqlite-close-evidence.md) and [SPEC-017](../specifications/SPEC-017-degraded-capability-matrix-and-sqlite-close-proofs.md) revise the previous comparison restricted to aiosqlite v0.21.0. Version v0.22.0 stops inheriting Thread directly and v0.22.1 adds stop() and enhanced close/destructor fallback. In the pinned v0.22.1 worker code, a stop Future result is scheduled before the worker breaks its thread loop, so an awaited stop Future is not automatically a public Thread.join guarantee. Enqueued SQL may still run after its awaiting Future was cancelled. Neither v0.22.1 nor stdlib ThreadPoolExecutor is selected; runtime HA OS packaging, actual linked SQLite version, cancellation, queue draining and terminal proof must be tested.

Every committed observation, source-state refresh and read-only backup connection is independently tracked. FENCING -> DRAIN -> CLOSE CONNECTIONS -> POSITIVE WORKER TERMINAL -> CLOSED_VERIFIED is required before the ADR-0015 generation pointer can change. A failed close preserves original SQLite WAL/journal and moves to FAILED_UNSAFE_TO_REOPEN, not a false successful restore. An entity showing available state does not authorize a DB write; historian permission is separate from physical source freshness. No tests or source code have been executed.
