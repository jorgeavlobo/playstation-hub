# ADR-0020 — Greenfield SQLite v1 canonical history, identity and report schema

**Status:** PROPOSED — logical model/release schema NOT APPROVED or implemented
**Date:** 2026-11-06
**Scope:** Initial NEW PlayStation Hub history schema, independent console/account/title identities, accepted evidence, deterministic local sessions and reports
**Official-source research:** [SQLite v1 schema audit](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md)
**Acceptance specification:** [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md), 96 NOT_RUN cases, 24 OPEN gates
**Dependencies:** ADR-0004 (identity), ADR-0005 (source reconciliation), ADR-0006 (session accounting), ADR-0007 (secrets), ADR-0008 (storage), ADR-0011 (ACCEPTED product architecture), ADR-0018 (greenfield genesis); Protocol 10 (game IDs), SPEC-008–018.
**Official baseline:** SQLite official documentation, pinned Home Assistant Core 2026.11.0.
**Branch:** main documentation only; develop frozen.

> This ADR proposes logical entities and strong invariants, not runnable DDL or an approved physical SQLite schema. The user confirmed the old develop App never deployed and had synthetic-only data: NO legacy import/migration. Product-level Hub/Archive architecture is ACCEPTED under ADR-0011; this technical database model remains PROPOSED.

## 1. Problem

The new integration must keep trustworthy local console/game activity for years with multiple physical PlayStations and optional PSN accounts, survive restarts/backups and report day/week/month/year usage. It must distinguish physical-console power/awake evidence, cloud account presence, player/game attribution, provider cumulative usage and unknown periods.

The old prototype's SQLite schema/data is irrelevant: no production rows, old identity migration, import compatibility or App/MQTT transition must be supported. We can design the NEW schema specifically for correctness, privacy, modularity and future versioned upgrades.

## 2. Decision candidates and recommendation

| Model | Strength | Risk | Proposal |
| --- | --- | --- | --- |
| One table combining consoles, accounts, games, totals | Small initially | Identity collisions, false attribution, difficult provenance and repair | REJECT |
| One SQLite DB per console or account | Isolation | Duplicates titles, breaks cross-console reporting and one writer/backup lifecycle | REJECT for default |
| One application-owned SQLite ledger, normalized owners/evidence/segments | Clear FK and idempotency, one writer and backup source | More tables, careful reducer/domain transactions | PREFERRED, NOT_ACCEPTED |
| Use Home Assistant Recorder's internal DB | Existing stats engine | Schema/retention owned by HA, no custom durable game ledger | REJECT |
| Separate PostgreSQL/MySQL service | Powerful querying | Mandatory extra service/config contrary to product scope | REJECT |
| Provider lifetime playtime as primary local session data | Easy cloud report | Not local console evidence, different scope/units and platform history | REJECT |

**Recommendation:** one private SQLite database with a normalized 12-table core plus opt-in metadata/PSN provider modules. Keep SQL writes behind one serialized repository manager, not a Config Entry, entity getter or browser. Final v1 DDL is blocked until this ADR/SQLite runtime and tests are approved.

## 3. Core relational shape (12 proposed entities)

| Logical table | Key/relationship | What it owns |
| --- | --- | --- |
| ledger_meta | One persistent ledger UUID | v1 schema, lineage, policy version, genesis and durable cursor |
| schema_revisions | Unique migration ID | Future upgrades of this NEW app, applied schema versions |
| runtime_epochs | Unique run UUID | Process/storage generation provenance, last clean/interrupted runtime |
| console_owners | Stable console key | Validated physical console identity, retirement, optional display label |
| psn_account_refs | Stable account key | Account identity reference/status only; NO credentials |
| console_account_links | Link UUID to console and account | Many-to-many temporal/provenance relationship |
| game_titles | Namespaced immutable game key | Provider title identifiers independent of localized metadata |
| observations | Idempotent observation UUID | Source-scoped accepted facts, precision, confidence, sequence and digest |
| domain_events | Event UUID referencing observation | Normalized accepted transitions and interpretation revision |
| session_segments | Segment UUID referencing source/owners | Half-open covered awake/game/attribution intervals and checkpoints |
| unknown_intervals | Gap UUID referencing owner/evidence | Coverage not observed, explicitly NOT OFF or gaming |
| source_checkpoints | Unique typed source owner key | Last durable accepted sequence/observation/cursor in same commit |

**Relationship policy:**
- Hub Config Entry is a load anchor, not a physical console, account or ledger row and not another writer.
- console_owners, psn_account_refs and game_titles have separate namespaces and must not be keyed by mutable IP, display name, HA entity_id or account nickname.
- Removing a console Config Entry or unlinking PSN does not cascade-delete historical facts.
- A console-account link is an attribution possibility, not evidence of a session on that device.
- Observation and event provenance must distinguish LAN, Remote Play, PSN presence and user-declared evidence as actually authorized by protocols.
- If attribution cannot be verified, keep nullable account/title in relevant segment with explicit unknown/ambiguous type, rather than fabricate a player or game.

## 4. Optional modules (not required for v1 LAN-only function)

- game_metadata_locales: title name/artwork references by locale/source, freshness and rights; changing a name must not change history.
- game_title_crosswalk: source-supported aliases/concepts/edition mappings; never merge titles solely by name.
- provider_entitlement_snapshots: account title entitlement at an observed time; not permanent ownership or installation.
- provider_playtime_snapshots: provider cumulative duration in exact reported units/scope; never summed with locally observed time.
- evidence_corrections: revisioned, audited correction to derived interpretation without erasing source observations.
- retention_tombstones: user-authorized deletion records subject to privacy/backup implications.

Do not call Sony undocumented providers or force PSN linking to build the LAN-only v1 schema. Each optional family requires separate authorization, version and data lifecycle before activation.

## 5. Types, constraints and IDs

**Candidate stored time:** INTEGER UTC epoch microseconds, with source time precision separately recorded. Avoid float elapsed seconds and hard-coded local time-zone boundaries. All interval semantics are half-open [start,end).

**STRICT typing:** Prefer SQLite STRICT tables only if installed linked SQLite >=3.37, application compatibility and older-backup/downgrade constraints are verified. STRICT supports native typed column names, not arbitrary SQL DECIMAL/DATETIME. If runtime unsupported, gate or use a tested alternative; do not silently change data types.

**Foreign keys:** Enable PRAGMA foreign_keys=ON and verify on every SQLite connection (writer, reader, snapshot-inspection). FK parent keys are explicitly named, stable, NOT NULL and UNIQUE. Default historical relationships to RESTRICT/NO ACTION rather than cascading deletion on Config Entry removal.

**Uniqueness and CHECK:** Unique observation UUID and typed provider title tuple with all components non-null. CHECK nonnegative times, end>=start, bounded checkpoint when end exists, enum values. SQLite CHECK may evaluate to NULL without failing, and SQLite UNIQUE treats multiple NULL values as distinct. Use explicit NOT NULL and reviewed predicates.

**Open segment exclusivity:** Consider PARTIAL UNIQUE on console_key for open exclusive console-awake segments only, not all game/account segments. Enforce overlaps of different closed intervals through the single reducer/transaction and validated queries, not a row CHECK.

**Schema migration history:** New app starts at its OWN v1. No old develop SQLite v1/v2/v3 importer. Later real-data migrations after the first release must use exact version transition, backup, transactional upgrade or generation replacement and recovery journal; never silent downgrade/reset.

## 6. Atomic ingest and data reproducibility

One logical accepted observation operation is atomic:
- verify canonical source identity, runtime generation, sequence, observation UUID/digest;
- insert observation + permitted domain events;
- update/create/close bounded session segments and explicitly unknown gaps;
- update source_checkpoints and ledger_meta durable cursor;
- COMMIT once, acknowledge receipt only after durability.

A late COMMIT whose async receipt was lost is reconciled by observation UUID and payload digest. Same UUID/same digest returns existing receipt; same UUID/different digest is a hard conflict. UPSERT cannot silently hide FK/CHECK errors or override original source data.

Derived session durations must never exceed last committed evidence frontier. Unchanged heartbeats may extend checkpoint without incrementing a session count; missing polls are unknown coverage, not OFF. A physical power segment, a game attribution segment and provider account presence are incomparable until source/owner/time scope is verified.

**No independent durable rollup counters** for day/month/year in v1. Materialized/disposable cache can be added later with ledger UUID, cursor, policy version and reporting timezone, and must invalidate on new evidence or restoration. HA native sensors are projections only.

## 7. Reporting and indexing

- Query clipped UTC intervals for local calendar day/week/month/year using IANA reporting timezone, including 23- or 25-hour DST days.
- Use an explicit scope console/account/title/all-consoles. Two simultaneous consoles may legitimately sum to more than one wall-clock day; optional wall-clock union is a distinct metric.
- Record unknown gaps separately and expose coverage/as-of cursor. Provider lifetime playDuration remains separate in verified provider units.
- Start with unique observation/event keys; console+time segment and source+time observation indexes; optional account/title+time, last provider snapshot and partial unique open segment indexes only when supported.
- Validate with EXPLAIN QUERY PLAN and deterministic synthetic 36-month workloads; no guessed database size, polling interval or latency claim.
- Use PRAGMA optimize only after checking actual linked SQLite version and performance budgets; no blind index permutations.

## 8. Privacy and retention

No Sony OAuth, NPSSO, refresh token, Remote Play secret, raw network packet, unredacted provider response, passwords or browser tokens in history tables. Treat account identifiers, activity titles and timestamps as personal; scope archive report permissions and default diagnostic redaction. No implicit deletion of history after console/account Config Entry removal.

User-requested purge is separately authorized and its interaction with snapshots, WAL and external backups explained; SQL DELETE alone is not proven secure erasure. Game artwork stays optional, licensed and cacheable; metadata removal cannot affect historical session duration.

## 9. Technology and release gates

| Decision | State |
| --- | --- |
| One private logical ledger with normalized owners/evidence/segments | PREFERRED / NOT_APPROVED |
| 12 core tables and optional modules | PROPOSED / DDL_NOT_AUTHORIZED |
| UTC integer microseconds and half-open intervals | PROPOSED / NOT_TESTED |
| STRICT table use | CONDITIONAL_LINKED_SQLITE_VERSION |
| One serialized writer, DB receipts, per-connection foreign keys | REQUIRED_CORRECTNESS_TARGET / NOT_TESTED |
| WAL, synchronous level and version fixes | ADR-0008/0010 OPEN_HA_OS |
| Exact PSN title/provider keys and authorization | Protocol 09/10 OPEN |
| Local reports and unknown coverage | ADR-0006 PROPOSED |
| Optional caches/retention/aggregation | OPEN |
| Future version migration | NEW_APP_ONLY, NOT_IMPLEMENTED |
| Test catalogue | SPEC-020, 96 NOT_RUN scenarios / 24 OPEN gates |
| Old develop App import/cutover | NOT_APPLICABLE / NEVER_DEPLOYED |

Approve the conceptual schema before generating executable SQL migrations or declaring any table/constraint actually present. Maintaining the current documentation-only boundary is separate from approval of this ADR.

## 10. Sources

- [Source research](../research/sqlite-greenfield-v1-schema-and-query-model-source-audit-2026-11.md)
- [SPEC-020](../specifications/SPEC-020-greenfield-sqlite-v1-schema-integrity-and-reports.md)
- [ADR-0004](ADR-0004-identity-and-multi-console-ownership.md)
- [ADR-0006](ADR-0006-sessions-and-usage-statistics.md)
- [ADR-0008](ADR-0008-storage-persistence-and-backup.md)
- [ADR-0018](ADR-0018-first-boot-consent-and-ledger-provisioning.md)
- https://www.sqlite.org/foreignkeys.html
- https://www.sqlite.org/lang_createtable.html
- https://www.sqlite.org/stricttables.html
- https://www.sqlite.org/partialindex.html
- https://www.sqlite.org/lang_upsert.html
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/pragma.html
- https://github.com/home-assistant/core/blob/2026.11.0/homeassistant/components/recorder/db_schema.py

**Outcome:** schema and constraints recommendation only; no DDL/code/DB/test executed or created, and develop remains unchanged.

## 11. Upstream deep audit: LAN-running-application observation (2026-11-06)

The [pinned cross-repository source review](../research/upstream-source-deep-audit-lan-remoteplay-psn-ha-2026-11-06.md) uncovered optional `running-app-titleid`/`running-app-name` fields recognized by Chiaki-ng's **physical LAN discovery** response parser. Model a future accepted `LAN_RUNNING_APP` sample as a console-scoped evidence payload when actual PS5 firmware semantics are verified, **not** as PSN account presence or automatically measured per-player gameplay. Keep the title ID namespace explicit until independently matched to provider catalog identifiers; absent app header is unknown, not `no game`.

**DDL effect:** The proposed twelve logical tables need not change solely because of this field. The existing `observations` + `domain_events` + `game_titles` / optional metadata could represent source-scoped title evidence, pending physical schema review. Do not add a mandatory title FK to every LAN power observation, rewrite the old greenfield session proposal, or automatically create `player_game` duration. Require real firmware fixtures including home screen, PS5 native games, backwards-compatible PS4 titles, media apps and standby. This ADR remains PROPOSED.
