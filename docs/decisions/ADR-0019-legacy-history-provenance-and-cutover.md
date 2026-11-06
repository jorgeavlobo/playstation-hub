# ADR-0019 — Legacy history provenance, cautious import and staged MQTT retirement

**Status:** PROPOSED — historical attribution, migration and decommission decisions NOT APPROVED / NOT_TESTED
**Date:** 2026-11-06
**Legacy source:** jorgeavlobo/playstation-hub develop, read-only old App v0.5.0 / Lovelace v1.1.2, NOT actual deployed private data.
**Evidence:** [Legacy source/provenance audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md)
**Acceptance plan:** [SPEC-019](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md), 80 NOT_RUN, 20 OPEN.
**Dependencies:** ADR-0011 ACCEPTED product architecture; ADR-0004/0006/0008/0009/0010 and ADR-0015/0018 technical proposals; SPEC-008–018.
**Git:** main documentation only; develop unchanged.

> The maintainer requested investigation and documentation only. No authority exists to alter an installed Home Assistant App, SQLite source, Mosquitto retained topics, Lovelace dashboard, entity registry, physical PS5 or user automations. This ADR is not a migration approval.

## 1. Problem

The old App's source models a single configured PS5-MQTT subscription and one selected player. It stores session timestamps and usage statistics in SQLite and publishes a synthetic MQTT monitoring device plus ten statistics sensors. The new native Home Assistant integration will have independent physical-console and optional PSN account Config Entries, direct LAN evidence, its own one-panel backend API, a shared long-lived ledger and no mandatory MQTT.

An incorrect direct SQL import could silently rewrite historical usage, misattribute sessions to new physical hardware, create duplicate gaming totals or expose Sony credentials. Removing the old App/MQTT too early could delete the user's only source copy or break HA automations. Conversely, no migration support would prevent preserving legitimate historical records.

## 2. Source-backed facts

- The old App version and configuration path are defined by develop/backend/config.yaml, with database path under the Supervisor App private /data volume and default template /data/ps5_monitor.db. The real installed path or whether a DB exists has not been inspected.
- develop/backend/app/database.py manages schema versions 1/2/3, with events, sessions, checkpoints and monitoring_state. Its Database constructor can CREATE/ALTER and must not be used for read-only migration inventory.
- Session records use console or gaming types with UTC REAL times, optional player_name/title_id/title_name/title_image and no immutable physical PS5 owner column. Events are sparse state changes, not periodic heartbeats. Open session last evidence comes from checkpoints.
- develop/backend/app/main.py passes max_gap_seconds=30.0 in the real source startup path, not helper defaults of 90. Reports use half-open UTC and Europe/Lisbon calendar boundaries; 36 months is a UI index window, not a proven retention cutoff.
- develop/backend/app/mqtt_publisher.py creates ten retained single-component MQTT Discovery sensors on a synthetic monitor device, unique ID pattern ps5_monitor_<key>. The old card hardcodes a prefix but installed HA entity IDs may differ.
- Official MQTT docs confirm retained Discovery messages can re-add entities after App stop; empty retained payloads on exact matching discovery topics remove single-component discovery entries, which is a separate, authorized and potentially destructive broker operation.

No physical console or player association has been authenticated using actual runtime data.

## 3. Preferred archival import policy — PROPOSED

**Proposed rule: import verified legacy SQLite as a provenance-labelled, physically UNATTRIBUTED archive scope by default.** Preserve original rows, bounded session intervals, title metadata where valid and source policy; do not convert player_name or mqtt_topic to a new canonical physical console key or PSN credential. The historical archive may have a human-friendly legacy description without representing a current, authenticated console.

An eventual physical linking action requires independent evidence and explicit administrator review, with the original legacy provenance left unchanged and the uncertainty displayed. If proof is insufficient, legacy history stays unassigned forever; it is better to preserve accurate source records than falsely claim a specific physical PS5.

Legacy account/player names are private labels, not OAuth credentials or proof of ownership. Title artwork URLs are untrusted metadata and not auto-fetched. No old MQTT password, broker identity or options.json is copied into the new history database.

## 4. Source-to-target migration sequencing

1. Inventory the actual installed App and obtain an authorized protected, WAL-consistent SQLite backup/export before uninstalling or stopping old data ownership. The old source remains separate and immutable during migration.
2. Inspect a COPIED source in SQLite non-creating read-only mode, validate integrity_check, foreign_key_check, exact versioned schema, source table counts, UTC bounds, event JSON and checkpoint consistency. Do not invoke the old Database class constructor, whose initialization mutates schema.
3. Create a reviewed migration preview: number of legacy sessions/events/checkpoints, account labels/titles, unsupported rows and total time using original 30-second / Lisbon report semantics. A preview writes neither source nor target.
4. On explicit admin consent, stage an independently verified target ledger generation under a stable batch/source manifest, preserving original table/row ID and source SHA as provenance. Namespace legacy IDs; forbid duplicate imports and overlapping unintended double counts.
5. Validate mapping, quota, private data, source-vs-import totals, time gaps and ledger lineage, then use the approved ADR-0015 promotion protocol after positive worker closure. New native monitoring begins from fresh evidence; old data is not replayed as if it were a direct native UDP observation.
6. Preserve original legacy export and at least one independent recovery copy. Do not delete newer native commits through a blind rollback to a pre-import pointer.
7. Only after verifying native reports, entities and the old source backup, authorize retirement of the old App's OWN monitoring discovery messages and Lovelace resource as a separate work package.

A direct native import from Supervisor App /data is NOT assumed possible: App storage and Core custom integration configuration have different namespaces. The existing README's private operational snapshot is NOT in Git and has not been inspected.

## 5. Entity and broker retirement

The old monitor's MQTT Discovery topics use the known prefix homeassistant/sensor/ps5_monitoring_service/ and one topic per old sensor key. It is NOT the same as PS5-MQTT's device power/activity entities. Do not clear MQTT discovery or device registry by name pattern without verifying the live broker/registry, topic ownership and dependent automations.

Home Assistant official MQTT guide documents removing single-component Discovery using an empty retained message on the exact old discovery topic; this should only be done after a backup of current retained config and explicit owner consent. Retiring MQTT broker or external PS5-MQTT is a separately scoped decision; the new integration is independent of them, but unrelated devices/automations may still need them.

The synthetic old monitor device registry identity must not be adopted as the new physical-console Device Registry identifier. New native sensor IDs may differ; a migration UI should map dependencies and warn about automations, scripts, dashboards and user-customized entity IDs before anything is disabled. Old retained live MQTT payload is not evidence of current PlayStation status after cutover.

## 6. Rejected or deferred alternatives

| Alternative | Decision rationale |
| --- | --- |
| Automatically claim legacy history for the first newly discovered PS5 | No hardware ID in legacy sessions, source may have changed |
| Use old player_name as current PSN account unique ID/token | Display label is not authenticated account identity |
| Derive continuous sessions by replaying sparse state_update events | Missing heartbeats/checkpoints would invent time |
| Recalculate sessions with new continuation threshold | Changes source history and may fill excluded gaps |
| Use the old Database constructor on actual source | It can create/migrate schema and mutate original |
| Copy live old DB main file without WAL safety | May produce inconsistent archive |
| Automatically import MQTT retained live state into historical tables | Not durable session evidence |
| Delete all retained MQTT topics starting with ps5 | Can destroy unrelated PS5-MQTT entities or other integrations |
| Reuse old MQTT synthetic monitor identifier for new native physical console | Identity is not hardware stable |
| Uninstall old App before exporting and verifying data | Risk losing only historical copy |
| Migrate old Lovelace JS directly as the new sidebar | Keeps hardcoded one-console MQTT transport, conflicts with architecture |

## 7. Identity, statistics and rollback invariants

- Imported rows have source namespace legacy_source_uuid + table + original row ID, alongside migration_batch_uuid, source snapshot digest and original schema version; IDs are not globally unique without the source namespace.
- New physical owner starts NULL / LEGACY_UNATTRIBUTED; source player_name and title metadata remain optional private history.
- An open session's effective end is last valid persisted checkpoint, or start if checkpoint missing; never current migration time.
- Half-open UTC session boundaries are preserved; import and report timezone policy record old Europe/Lisbon semantics and 30-second continuity.
- The 36-month legacy UI index does not trim imported rows outside its display range.
- Historical duplicate import or new source snapshot of the same old DB requires ancestry/overlap checks; no largest-cursor merge.
- Old and new data may overlap at cutover; never silently sum them twice across a selected user report.
- Rollback is source/target preservation plus explicit re-selection, not an atomic inverse of App, MQTT broker, HA entity registry and the native SQLite pointer.
- All user data, including game titles, player labels and historical time records, is protected private data; credentials stay in separate stores.

## 8. Decision status

**ACCEPTED previously:** ADR-0011 product Hub/Archive, independent console/PSN entries, one panel/controller, no required MQTT/add-on.
**PROPOSED here:** migrate historical source as archival LEGACY_UNATTRIBUTED, legacy-source manifest and idempotent batch, dry-run and report comparison, phased MQTT entity retirement and source backup obligations.
**OPEN:** actual installed legacy DB records/schema, actual App storage/HA entity registry, console/account identity evidence, imported historical report policy, legacy player privacy, any physical attribution rule, cutover timing, MQTT broker cleanup consent, migration runner and rollback.
**NOT TESTED:** 80 SPEC-019 scenarios and 20 gates. None of the legacy source test files were executed during this investigation. No current user data was read.

No technical decision is automatically approved by a request to continue research. No implementation branch or code change.

## 9. Sources

- [Legacy source-backed audit](../research/legacy-develop-to-native-migration-provenance-audit-2026-11.md)
- [SPEC-019 planned validation](../specifications/SPEC-019-legacy-history-migration-and-mqtt-retirement.md)
- [Existing backend source review](../research/legacy-code-review-and-refactoring-blueprint-2026-11.md)
- [Existing frontend audit](../research/legacy-frontend-source-audit-2026-11.md)
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/database.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/session_tracker.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/backend/app/mqtt_publisher.py
- https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js
- https://www.home-assistant.io/integrations/mqtt/
- https://www.sqlite.org/backup.html

**Outcome:** Proposed migration policy, not data migration, executable code or verified user installation.
