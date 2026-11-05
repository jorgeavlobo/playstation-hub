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
5. Coordinate with HA backup lifecycle using an actual supported API for this type of integration; **do not invent a backup hook or assume Home Assistant invokes it**.
6. Avoid snapshot file accumulation; securely clean temporary files and handle full disk, interrupted backup or stopped integration.
7. Ensure credentials are protected and backed up separately according to ADR-0007, never copied into public session exports.
8. Verify archive restore in an isolated Home Assistant OS test: database opens, indexes and constraints work, history matches the high-water mark, and pending observations are not counted twice.

**Important unresolved integration constraint:** If Home Assistant's normal backup mechanism does **not** invoke a custom integration pre-backup hook, a periodic snapshot or a persistent consistent copy inside the backup scope may be necessary. This must be tested rather than promising transparent seamless snapshot coordination.

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
- [ ] Confirm whether an official supported pre-backup hook exists and is called for custom integration storage.
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
| Consistent backup mechanism and HA hook support | **OPEN** |
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
