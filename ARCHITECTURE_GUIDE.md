# PlayStation Hub — Architecture & Standards Guide

> **Status:** Planning / living specification  
> **Document version:** 0.1.0 — 2026-11-05  
> **Repository:** https://github.com/jorgeavlobo/playstation-hub  
> **Public name:** PlayStation Hub  
> **Integration domain:** `playstation_hub` (planned; verify before release)  
> **Distribution target:** One HACS **Integration**, including its frontend  
> **Languages:** Code, comments, identifiers, and repository documentation in English.

## 1. Purpose and non-negotiable principles

This document is our single source of truth for the planned architecture, publication requirements, implementation milestones, and open decisions. Update it after **each detailed documentation review**, recording sources, date, evidence, decisions, and any superseded proposals.

- Build a **new Home Assistant custom integration from scratch** using current official conventions.
- Preserve the previous app/card code on the `develop` branch **as reference only**; never merge it wholesale into the new integration.
- Develop the replacement on `next`, and release reviewed, tested code through `main`. The branching policy can be revised before the first release.
- One GitHub repository, one HACS integration, one shared release version for Python and JavaScript.
- No requirement for a separate Supervisor App/add-on.
- Modular and extensible, with clearly separated responsibilities, strict lifecycle management, and detailed **English** code comments.
- Do not publish private snapshots, SQLite data, Home Assistant `.storage` files, IDs, credentials or real-world user configuration.
- No empty “placeholder” modules solely to imitate a directory tree. The tree below is a **target roadmap**, not the minimum release structure.
- The first release must be **functional, installable, configurable, removable, and tested**. A blank integration must not be submitted just to reserve a name.
- Require compatibility checks against a declared, supported Home Assistant Core version; prefer current stable APIs.

## 2. Branch and release policy

| Branch | Responsibility | Rule |
| --- | --- | --- |
| `develop` | Frozen legacy Python add-on + Lovelace implementation | Reference only; no automatic merges to the new integration |
| `next` | Clean-room-style reimplementation and integration tests | Feature branches / PRs encouraged |
| `main` | Release-ready integration and public documentation | Merge only after CI and review |

- Use GitHub Releases with semantic versions (initial version still to be decided); the `manifest.json` version must match the released integration.
- GitHub commits alone do not imply installed upgrades. HACS uses its repository/release update mechanism.
- Dashboard assets ship **inside the custom integration package**; the integration must register/serve the frontend with compatible Home Assistant APIs.
- Cache-busting and recovery after upgrades must be tested. Browser refresh and Home Assistant restart may still be necessary.

## 3. Proposed repository tree (target, not all files immediately required)

```text
playstation-hub/
├── ARCHITECTURE_GUIDE.md                 # This living guide
├── README.md                             # Public overview and installation instructions
├── LICENSE                               # License to be selected before public release
├── hacs.json                             # HACS repository metadata
├── pyproject.toml                        # Tooling / formatting / test configuration
├── .gitignore
├── .gitattributes                        # Consistent line endings across platforms
├── .github/
│   ├── workflows/
│   │   ├── validate.yml                 # HACS Action, Hassfest, style/static checks
│   │   └── tests.yml                    # Python and frontend tests
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── custom_components/
│   └── playstation_hub/
│       ├── __init__.py                   # async_setup, setup_entry, unload_entry
│       ├── manifest.json                 # domain, name, version, docs, issue tracker, owners
│       ├── const.py                      # Domain, constants, defaults
│       ├── config_flow.py                # UI setup, reconfigure, options (as needed)
│       ├── strings.json                  # Base user-facing strings
│       ├── translations/
│       │   └── en.json                   # Additional languages only when supported
│       ├── coordinator.py                # Shared push/poll lifecycle where appropriate
│       ├── data.py                       # Typed runtime data / per-config-entry state
│       ├── diagnostics.py                # Privacy-safe diagnostics
│       ├── sensor.py                     # HA-native statistics / operational sensors
│       ├── binary_sensor.py              # Console/activity state, when applicable
│       ├── button.py                     # Discrete actions, if applicable
│       ├── switch.py                     # Only for appropriate reversible controls
│       ├── services.yaml                 # Document integration actions when added
│       ├── transport/                    # External communication and adapters
│       │   └── ...                       # MQTT and/or other supported source, TBD
│       ├── domain/                       # Pure business logic, without HA dependencies
│       │   ├── sessions.py
│       │   ├── statistics.py
│       │   ├── games.py
│       │   └── models.py
│       ├── persistence/                  # Storage abstraction / migrations / retention
│       │   ├── repository.py
│       │   ├── native_store.py
│       │   └── sqlite_repository.py      # ONLY IF a dedicated database is approved
│       ├── frontend/                     # Frontend shipped and versioned with integration
│       │   ├── playstation-hub.js
│       │   ├── components/
│       │   ├── services/
│       │   └── styles/
│       └── brand/
│           └── icon.png                  # Brand rules to verify
├── tests/
│   ├── conftest.py
│   ├── test_config_flow.py
│   ├── test_init.py
│   ├── test_unload.py
│   ├── test_diagnostics.py
│   ├── domain/
│   ├── persistence/
│   └── frontend/
├── docs/
│   ├── installation.md
│   ├── configuration.md
│   ├── architecture.md
│   ├── data-and-privacy.md
│   ├── backup-and-restore.md
│   ├── release-process.md
│   └── standards-review-log.md
└── scripts/
    └── ...                               # Local development tools (not runtime dependencies)
```

**HACS packaging constraint:** Exactly one integration under `custom_components/`; all runtime-required files must be within `custom_components/playstation_hub/`. Do not put runtime dependencies in a top-level `frontend/` or `backend/` folder. Test and documentation files may live outside.

**Home Assistant conventions:** File roles are conditional: `coordinator.py` is appropriate when coordination is required; entity platforms are created only for genuinely suitable entity semantics; actions are not automatically `switch` entities.

## 4. Publication and compliance gates

### Gate A — Valid integration

- [ ] Domain is unique and checked against Home Assistant Core and community projects.
- [ ] Correct `custom_components/playstation_hub/` structure.
- [ ] `manifest.json` contains `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, and `version`, plus current Home Assistant manifest requirements.
- [ ] Functional `async_setup_entry`, safe unload/reload, errors and reconnect handling.
- [ ] A working UI configuration flow when applicable; no unnecessary YAML configuration.
- [ ] Correct translations, entity identifiers, device information and diagnostics.
- [ ] Brand icon and branding requirements verified.
- [ ] Frontend resources are registered only once and versioned consistently.

### Gate B — Quality and CI

- [ ] HACS Action runs with no errors **and no ignored checks** for catalog inclusion.
- [ ] Hassfest passes.
- [ ] Backend tests, frontend tests, style and type checks pass.
- [ ] Test configuration, duplicate configuration, unavailable source, reconnect, restart, unload and remove.
- [ ] Storage durability, corruption and migration/recovery tests where applicable.
- [ ] HA Core version compatibility tested; automated releases are reproducible.
- [ ] Documentation, screenshots, security/privacy review, license, and repository topics.

### Gate C — Distribution

- [ ] Install as a **custom repository in HACS** and verify it can be installed/updated.
- [ ] Verify one release updates both Python and dashboard assets.
- [ ] Create a real GitHub **Release** after validation; tags alone are insufficient for catalog submission.
- [ ] Submit to `hacs/default` integration list with a complete, truthful PR.
- [ ] Catalog admission is subject to review; it does **not** reserve exclusive ownership of the name/domain.

## 5. Data architecture — provisional recommendation, not yet finalized

**Decision status: OPEN.** Storage choice must follow a specific documented and measured comparison before implementation.

Separate data into three different classes:

| Data class | Preferred starting approach | Reason |
| --- | --- | --- |
| Integration setup / source options | **Home Assistant config entries and options flow** | Native configuration lifecycle and user experience |
| Small durable settings, checkpoints, schema metadata | **HA `Store` helper** in the HA configuration storage area | Native JSON-serializable versioned persistence |
| Long-duration, detailed PS5 sessions and game history | **Evaluate a private SQLite database** if HA recorder/statistics cannot meet data/query/retention requirements | Transactional queries, indexes and explicit long-term retention |
| Metrics represented as HA entities | **Home Assistant entities and Recorder/statistics when suitable** | Native automations and HA history |
| CSV / JSON exports | **Optional import/export only** | Not suitable as primary concurrent transactional storage |

**Recommended direction (subject to formal review):** Prefer native config entries and Store for low-volume state. For a detailed, multi-year session/event ledger, a **dedicated SQLite file belonging to PlayStation Hub** is a plausible option, but not a guaranteed best practice for every use case. Do **not** access or modify the user's Recorder database tables directly; that database is managed by Home Assistant and its schema, retention and migration rules are not ours.

A dedicated SQLite file is different from a separate database server: it is local, portable and generally does not require another add-on. The design must be checked for Home Assistant's event-loop constraints and lifecycle.

If SQLite is chosen:
- Place mutable data under the HA configuration/data area, **never** inside the HACS-managed integration code directory. Determine exact path using supported HA APIs and document backup coverage.
- Isolate all database I/O behind a repository interface; avoid blocking the HA event loop. Use appropriate async/executor/thread scheduling and explicit write serialization.
- Design schema migrations, transactions, WAL/locking policy, busy timeouts, retention, integrity checks and safe backup/export.
- Decide per-config-entry databases versus a shared **application-owned** database with strict logical separation; account for multiple consoles and players.
- Prefer canonical UTC timestamps plus explicit local timezone handling for daily/weekly/monthly summaries.
- Ensure database recreation/recovery cannot silently destroy stored history and removal/uninstall behavior is documented.
- Avoid personally identifying data in exports and diagnostics unless explicitly authorized.
- Test upgrade, downgrade limits, backup/restore and Home Assistant restart while data is being written.

**What we do NOT recommend by default:**
1. Writing our custom tables into the Home Assistant Recorder database.
2. A separate PostgreSQL/MySQL server as a requirement for an ordinary HACS integration.
3. CSV files as the main session/event database.
4. Placing SQLite files, raw history or credentials in the public repository.

### Storage decision gate: research and proof

Before creating `sqlite_repository.py`, investigate:
- Official `homeassistant.helpers.storage.Store` API and semantics.
- Recorder retention/purge and long-term statistics API and appropriate sensor state classes.
- Backup and restore behavior of custom integration storage under the active Home Assistant installation types.
- Scale tests against ~36 months of representative sessions, multi-console load, startup time, and history queries.
- Threading/concurrency restrictions, SQLite WAL and consistent backup procedures.
- Multiple config entries, unlink/removal behavior and privacy.

Deliver a signed-off **storage architecture decision record** documenting options, evidence and migration strategy.

## 6. Official documentation reading list

These are official primary-source URLs. **Not all subpages have yet been exhaustively reviewed.** Read each one deliberately in future sessions; do not mistake this index for completed compliance certification.

### 6.1 HACS — user-provided entry points

- https://www.hacs.xyz/
- https://www.hacs.xyz/docs/use/
- https://www.hacs.xyz/docs/publish/
- https://www.hacs.xyz/docs/contribute/

### 6.2 HACS — targeted requirements

- https://www.hacs.xyz/docs/publish/integration/ — integration layout and manifest
- https://www.hacs.xyz/docs/publish/plugin/ — dashboard/plugin distribution (compare, **not** our packaging mode)
- https://www.hacs.xyz/docs/publish/include/ — submission and catalog criteria
- https://www.hacs.xyz/docs/publish/action/ — HACS validation Action
- https://www.hacs.xyz/docs/use/repositories/type/integration/ — integration installation behavior (verify exact destination if changed)
- https://www.hacs.xyz/docs/use/repositories/type/dashboard/ — dashboard repository behavior (verify exact destination if changed)
- https://github.com/hacs/default — default catalog submission repository
- https://github.com/hacs/action — HACS validation Action source
- https://github.com/hacs/integration — HACS implementation and releases

### 6.3 Home Assistant — integration development

- https://developers.home-assistant.io/
- https://developers.home-assistant.io/docs/creating_component_index/
- https://developers.home-assistant.io/docs/creating_integration_file_structure/
- https://developers.home-assistant.io/docs/creating_integration_manifest/
- https://developers.home-assistant.io/docs/config_entries_index/
- https://developers.home-assistant.io/docs/data_entry_flow_index/
- https://developers.home-assistant.io/docs/integration_setup_failures/
- https://developers.home-assistant.io/docs/integration_fetching_data/
- https://developers.home-assistant.io/docs/integration_listen_events/
- https://developers.home-assistant.io/docs/core/entity/
- https://developers.home-assistant.io/docs/core/entity/sensor/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
- https://developers.home-assistant.io/docs/core/platform/application_credentials
- https://developers.home-assistant.io/docs/dev_101_services/
- https://developers.home-assistant.io/docs/creating_integration_tests_file_structure/
- https://developers.home-assistant.io/docs/core/diagnostics/
- https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/runtime-data/

### 6.4 Home Assistant — persistence, Recorder, backup and frontend

- https://developers.home-assistant.io/blog/2022/07/08/generic-store/ — Store helper background (verify current source/API)
- https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py — current Store implementation
- https://www.home-assistant.io/integrations/recorder/ — Recorder retention and settings
- https://developers.home-assistant.io/docs/core/entity/sensor/ — native sensor semantics
- https://developers.home-assistant.io/docs/frontend/custom-ui/custom-card/ — custom cards (verify current path)
- https://developers.home-assistant.io/docs/frontend/custom-ui/registering-resources/ — resource registration (verify current path)
- https://developers.home-assistant.io/docs/frontend/custom-ui/ — official frontend customization index
- https://developers.home-assistant.io/docs/core/backup/ — backup architecture (verify current path)
- https://github.com/home-assistant/core — Core source and actual integration patterns
- https://github.com/home-assistant/frontend — frontend source and current APIs
- https://github.com/home-assistant/brands — integration branding requirements
- https://github.com/home-assistant/actions — automation and Hassfest references

**Link status:** Some URLs above are *reading candidates* with paths not yet individually verified; confirm availability and redirect targets before treating them as authoritative requirements. The earlier `developers.home-assistant.io/docs/api/helpers/storage/` path was inaccessible during initial research, so use the current official helper source above instead.

## 7. Review protocol for the next sessions

For each official website / subsection:

1. Open the current page, inspect all relevant child pages and last-updated dates.
2. Extract explicit **MUST**, **SHOULD**, **MAY**, and **not applicable** rules.
3. Record the exact URL, requirement, interpretation, proof/test, and date in `docs/standards-review-log.md`.
4. Update this guide's affected section and identify any changed architecture decision.
5. Write a test or CI check where practical; don't claim a rule is met without evidence.
6. Note uncertainty and version dependencies; revisit at each significant HA/HACS release.

### Initial source-verified findings (2026-11-05)

- HACS integration publishing requires one integration under `custom_components` and all its runtime-required files inside that integration directory.
- HACS specifies the manifest keys `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`.
- HACS catalog inclusion requires the HACS Action and Hassfest to pass, a GitHub Release, a public repository and correct submission. Reviews may be slow.
- HA identifies integrations by a unique, effectively permanent domain.
- HA config entries are persistently stored configuration created through UI flows.
- HA has a typed `Store` helper for JSON-serializable data; that alone does not prove it suits long-duration event logs.

Source links: sections 6.2–6.4 above.

## 8. Open architecture decisions

- [ ] Official connector/source strategy for PS5 discovery/status/control, without assuming PS5-MQTT is universal.
- [ ] Supported Home Assistant versions / Python version.
- [ ] Multi-console and multi-player modeling and attribution.
- [ ] Recorder/statistics vs private SQLite proof-of-concept (see section 5).
- [ ] Whether the interface is a custom Lovelace card, sidebar panel, or both.
- [ ] Exact frontend serving, resource lifecycle, versioning and cache policy.
- [ ] Integration unloading / uninstall storage retention and cleanup policy.
- [ ] Branding/logo, license, release automation, screenshots, documentation translations.
- [ ] Minimum real feature set needed for the first acceptable catalog submission.

**Next action:** Exhaustively review the official documentation page by page, then refine this guide **before** constructing the initial integration skeleton.
