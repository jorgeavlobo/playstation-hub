# Legacy frontend inventory — corrected source availability

**Original review:** 2026-11-05  
**Correction date:** 2026-11-05  
**Status:** Superseded by a completed source-backed audit; old source-access blocker **UX-001 RESOLVED**  
**Source branch:** `develop` (read-only); **Documentation branch:** `main`

> **Correction:** The original version of this note incorrectly concluded that the `develop/frontend/` code was unavailable. That conclusion came from using GitHub `fetch_file` against a **directory**, an operation that returns `NOT_FOUND` for folders even when they exist. A subsequent inspection using GitHub's approved REST Contents/Tree endpoints verified the folder and enumerated its files. The earlier conclusion must not be repeated.

## Verified source

- [GitHub `develop/frontend` directory](https://github.com/jorgeavlobo/playstation-hub/tree/develop/frontend)
- [GitHub Contents API](https://api.github.com/repos/jorgeavlobo/playstation-hub/contents/frontend?ref=develop)
- [Recursive frontend Git tree](https://api.github.com/repos/jorgeavlobo/playstation-hub/git/trees/f4a8b76c5c0221fb3cd3671a4c631f5d275beb96?recursive=1)
- [Legacy frontend card](https://github.com/jorgeavlobo/playstation-hub/blob/develop/frontend/ps5-dashboard-card.js)

The frontend contains **21 files**: one dashboard card, two UI components, seven services, one stylesheet and **ten test files**. The ten tests contain **80 `test(...)` declarations**. These tests were counted and read, **not executed**, so their current passing status has not been established.

## Authoritative replacement review

See [Legacy Frontend Source Audit — Verified `develop` Branch](legacy-frontend-source-audit-2026-11.md) for:
- Exact source inventory and references.
- Verified feature and data-flow audit (live MQTT-over-HA-WebSocket, history, 36-month navigation, game library, charts and cancellation).
- 20 source-backed modernization and compatibility findings.
- Complete count of 80 test declarations and future behavior-test mapping.
- Migration blueprint toward the approved **single native Home Assistant sidebar panel** with authorized non-MQTT backend APIs, multiple consoles, source freshness and accessible, translated UI.

**Implementation status:** No code on `develop` or `main` was modified, no tests were executed, and no implementation branch was created. Future audit documents should cite the new source-backed review rather than the superseded conclusion.
