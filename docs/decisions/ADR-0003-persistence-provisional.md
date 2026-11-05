# ADR-0003 — Application-owned SQLite (provisional)

**Status:** Proposed, not approved — 2026-11-05.

A dedicated SQLite database outside HACS-managed source but inside the Home Assistant configuration backup scope is the preferred candidate for detailed multi-year history. Native Config Entries hold setup data; Recorder handles eligible HA sensors.

Backup hooks, snapshot consistency, exact path, WAL behavior and restore tests are unresolved. Do not implement until approved.

See [architecture guide](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md).
