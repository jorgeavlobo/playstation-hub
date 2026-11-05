# PlayStation Hub — Architecture & Standards Guide

> **Status:** Planning / living specification  
> **Document version:** 0.20.0 — 2026-11-05  
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
- **Approved frontend decision (2026-11-05):** Exactly one supported UI: a full-page custom Home Assistant sidebar panel. No Lovelace custom card, dashboard strategy, or parallel card distribution is planned. Keep the frontend modular internally.
- No requirement for a separate Supervisor App/add-on.
- Modular and extensible, with clearly separated responsibilities, strict lifecycle management, and detailed **English** code comments.
- **Mandatory project policy:** Multilingual architecture from the first release, including integration configuration, entities, errors, diagnostics-facing labels where applicable, and all frontend text. English is the source language; translation files supply other locales. Never hardcode user-visible English strings into business logic.
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

- **Project decision (mandatory):** Use GitHub Releases with semantic versioning (first version TBD); keep the released integration `manifest.json` version aligned with its release. Create a full GitHub Release **only after** HACS Action and Hassfest have passed. This is both our selected quality policy and an explicit prerequisite for inclusion in the HACS default catalog (DOC-002).
- GitHub commits alone do not imply installed upgrades. HACS uses its repository/release update mechanism.
- **Official HACS Integration publication page:** GitHub Releases are **optional** for a valid repository. If releases exist, HACS can offer the five latest releases plus the default branch; otherwise HACS uses the default branch. We may still **choose** a release-first policy for production stability. Catalog inclusion requirements are a distinct review.
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
│       ├── translations/                 # Runtime translations for custom integrations
│       │   ├── en.json                   # Full English runtime translation
│       │   └── pt.json                   # Portuguese translation; locale policy pending
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
│       │   ├── i18n/                     # Frontend localization resources (design pending)
│       │   ├── playstation-hub-panel.js
│       │   ├── components/
│       │   ├── services/
│       │   └── styles/
│       └── brand/
│           └── icon.png                  # Proposed only: check exact branding path/rules
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
- [ ] Brand assets provided. HACS's Integration publication page explicitly requires a repository brand directory containing at least `icon.png`; exact acceptable placement, naming, dimensions and alternate routes await a separate branding-source review.
- [ ] Frontend resources are registered only once and versioned consistently.

### Gate B — Quality and CI

- [ ] HACS Action passes with **zero errors and zero ignored checks**, before catalog submission (DOC-002).
- [ ] Hassfest passes for the integration, before catalog submission (DOC-002).
- [ ] Backend tests, frontend tests, style and type checks pass.
- [ ] Test configuration, duplicate configuration, unavailable source, reconnect, restart, unload and remove.
- [ ] Storage durability, corruption and migration/recovery tests where applicable.
- [ ] HA Core version compatibility tested; automated releases are reproducible.
- [ ] Documentation, screenshots, security/privacy review, license, and repository topics.

### Gate C — Distribution

- [ ] Install as a **custom repository in HACS** and verify it can be installed/updated.
- [ ] Verify one release updates both Python and dashboard assets.
- [ ] **Required for default HACS catalog inclusion (DOC-002) and our project policy:** Create a full GitHub Release (not merely a tag) **after** HACS Action and Hassfest pass. DOC-001 alone makes releases optional for a manually added custom repository; this distinction is now verified.
- [ ] Submit a truthful, complete PR to **`hacs/default` → `integration`**, sorted alphabetically, from a new branch based on the fork's `master`; the PR must remain editable (DOC-002).
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
- **DOC-002 confirms** the separate default-catalog inclusion requirements: public GitHub repository, successful HACS Action without errors or ignored checks, successful Hassfest for integrations, and a full GitHub Release after successful actions. These are mandatory for the proposed default-catalog submission, though DOC-001 permits basic HACS custom-repository installation without releases.
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

## 9. Official document review register

### DOC-001 — HACS: Publish → Integrations

- **Source:** https://www.hacs.xyz/docs/publish/integration/
- **Official page title:** Integrations
- **Reviewed:** 2026-11-05
- **Status:** Reviewed in full for this page, including its repository structure examples, manifest minimum, branding, and release behavior.
- **Scope boundary:** Only this single page was reviewed in this iteration. Linked pages about general requirements, catalog inclusion, branding specifications, GitHub Actions, Home Assistant manifests, and dashboard plugins remain **pending**.
- **Impact:** Clarified mandatory packaging rules, corrected release requirements, and added a reproducible compliance checklist.

#### Evidence-based requirements

| ID | Classification | Rule directly stated by the page | Project implementation / verification |
| --- | --- | --- | --- |
| HACS-INT-001 | MUST | Only one integration subdirectory under repository `custom_components/`. With multiple, HACS manages only the first. | Exactly `custom_components/playstation_hub/`; validate directory count in CI. |
| HACS-INT-002 | MUST | All files required at integration runtime reside in `ROOT_OF_THE_REPO/custom_components/INTEGRATION_NAME/`. | Bundle Python, JS, CSS and other runtime assets inside the package; test installation from built repository. |
| HACS-INT-003 | MUST | Integration manifest located in the integration directory. | Ensure `custom_components/playstation_hub/manifest.json` exists and parses. |
| HACS-INT-004 | MUST | Manifest defines at least `domain`, `documentation`, `issue_tracker`, `codeowners`, `name`, `version`. | Verify all six keys are present with sensible values; refer to official HA manifest documentation for semantics. |
| HACS-INT-005 | MUST | Provide integration brand assets, e.g., a repository `brand` directory with at least `icon.png`. | Add legitimate branding; verify exact placement and image rules in the **next separate** branding-document review. |
| HACS-INT-006 | MAY | `content_in_root: true` in `hacs.json` allows a root-content exception to the normal examples. | **Do not use** this exception: follow normal `custom_components/` structure. |
| HACS-INT-007 | OPTIONAL | GitHub Releases are preferred, **not required**. Without releases HACS uses the default branch; with releases it offers the five latest releases and the default branch. | **Choose** releases for production even though not required for basic integration validity; distinguish catalog inclusion. |

#### Exact structural implications

```text
playstation-hub/
├── hacs.json
├── README.md
└── custom_components/
    └── playstation_hub/
        ├── __init__.py
        ├── manifest.json
        └── ...  # All runtime dependencies, including frontend assets
```

The page explicitly presents a root-level `README.md` and `hacs.json` in its valid example. It shows examples with integration files outside `custom_components/` as invalid, unless the documented `content_in_root` exception applies. We will not rely on that exception.

**Important boundary:** The `frontend/` directory under the integration is **our packaging design**, not an explicitly mandated folder name from this HACS document. Similarly, the page does not specify `config_flow.py`, entity platforms, SQLite strategy, CI implementation details or the registration API for Lovelace assets. Those belong to future official-source reviews.

#### Corrections made to previous guide

1. **Fixed:** Releases are not mandatory for basic HACS Integration repository validity. Keeping a release-first policy is a separate project decision.
2. **Clarified:** `hacs.json` with `content_in_root: true` is an explicitly documented exception; the project deliberately uses the standard layout instead.
3. **Clarified:** Branding is required, but the exact asset location/format must be determined from the linked branding standard, not guessed.
4. **Separated:** Catalog **inclusion** conditions from the Integration publication requirements. A separate official-document review will resolve them.

#### Acceptance criteria before moving to another document

- [ ] Exactly one integration directory under `custom_components/`.
- [ ] All integration runtime resources stay inside that directory.
- [ ] Manifest has the six listed minimum fields.
- [ ] Branding location and assets validated through the dedicated official standard.
- [ ] A working release/update workflow documented (a project choice).
- [x] Official source and outstanding dependencies logged.

**This document has now been reviewed separately as DOC-002 below.**

### DOC-002 — HACS: Include default repositories

- **Source:** https://www.hacs.xyz/docs/publish/include/
- **Official title:** Include default repositories
- **Reviewed:** 2026-11-05
- **Status:** Full document reviewed, including "Who can submit?", "Before you start", "Additional information", all enumerated review checks, and "After the PR is merged".
- **Scope boundary:** This entry covers **default-catalog admission**, not runtime architecture or Home Assistant integration implementation. Referenced HACS Action, Hassfest, and GitHub/brands specification pages are **not** treated as separately reviewed.
- **Project decision confirmed:** GitHub Releases are **mandatory in PlayStation Hub**, and a real release **is also mandatory for default-catalog submission**, although DOC-001 permits a basic custom HACS repository without releases.

#### Explicit admission and review requirements

| ID | Status | Official admission rule / reviewer check | Project implementation or proof |
| --- | --- | --- | --- |
| HACS-CAT-001 | MUST | Only the repository owner or a major contributor may propose the repository as a default. | Submit as repository owner `jorgeavlobo` or an eligible major contributor. |
| HACS-CAT-002 | MUST | Repository can first be added to HACS as a custom repository. | Perform and document real HACS custom-repository install test. |
| HACS-CAT-003 | MUST | Public GitHub repository. | Check repository visibility is `public`. |
| HACS-CAT-004 | MUST | HACS Action passes with no errors **and no ignored checks**. | Add official Action and retain green GitHub Actions result. |
| HACS-CAT-005 | MUST | Hassfest passes for integrations. | Add official Hassfest workflow and retain green result. |
| HACS-CAT-006 | MUST | Publish a **full GitHub Release**, not merely a tag, **after** successful actions. | Document release procedure, verify timestamp/order, tag, version and release URL. |
| HACS-CAT-007 | MUST | Submit to the appropriate file in `hacs/default`: `./integration` for custom integrations. | Open the inclusion PR targeting the integration list, not the plugin list. |
| HACS-CAT-008 | MUST | Insert repository entry in alphabetical order. | Validate sorted list in the submission diff. |
| HACS-CAT-009 | MUST | PR must be editable; documentation says not to submit from an organization account. | Use personal-account fork and enable maintainers to edit the PR. |
| HACS-CAT-010 | MUST | In a fork of `hacs/default`, create a **new branch from `master`**, never edit the fork's `master` directly. | Use an isolated submission branch. This refers to the `hacs/default` fork, not PlayStation Hub's own branch layout. |
| HACS-CAT-011 | CONDITIONAL | For a repository restricted to one country or a limited set of countries, include a `country` key in released `hacs.json`. | Global PlayStation Hub deployment planned; omit unless actual availability is country-limited. |
| HACS-CAT-012 | MUST | Complete the PR template accurately; misrepresentations or incomplete statements cause closure. | Evidence-based responses with links to passing checks; never claim unverified compatibility. |
| HACS-CAT-013 | MUST | Default catalog does **not** accept alpha/beta custom integrations for Core or integrations overriding Core. | Use own unique domain; not a replacement/testing fork of a Core integration. |
| HACS-CAT-014 | MUST | Reviewer requires branding: a brand directory with at least `icon.png`, or a matching domain in `home-assistant/brands`. | Prepare `icon.png`; separately research exact asset path and format. |
| HACS-CAT-015 | MUST | Integration manifest must validate. | Validate with Hassfest plus HACS checks; compare official Home Assistant manifest requirements in later DOC. |
| HACS-CAT-016 | MUST | HACS repository validation and `hacs.json` containing at least `name`. | Ensure `hacs.json` has `name: PlayStation Hub` as JSON, plus other fields if required by later research. |
| HACS-CAT-017 | MUST | Repository must not be archived. | Check `archived = false`. |
| HACS-CAT-018 | MUST | Repository has a description, Issues enabled, and GitHub topics. | Check GitHub repo settings; add meaningful topics (e.g. `home-assistant`, `hacs`, `playstation`). |
| HACS-CAT-019 | MUST | Submission files must contain valid JSON and be alphabetically sorted. | Let submission PR's `lint jq` and `lint sorted` pass. |
| HACS-CAT-020 | NOT APPLICABLE | README image checks documented for **plugins and themes only**. | We submit as **Integration**, with frontend bundled; useful README screenshots remain our own quality target. |

#### Submission sequence — mandatory ordering

1. Build a **real working** integration; do not submit a placeholder to reserve a domain.
2. Verify installation in HACS as a **custom repository**.
3. Ensure repository is public and active; description, issues, topics, valid branding/manifest/`hacs.json`.
4. Run HACS Action and Hassfest; require green results with no ignored HACS checks.
5. **Only then create the full GitHub Release**, not just a tag.
6. Fork `hacs/default` under the personal account; create a **new branch from its `master`**.
7. Add `jorgeavlobo/playstation-hub` to the alphabetically ordered `integration` list.
8. Open an editable PR, fully and accurately completing its template.
9. Monitor checks and review; address failures. If placed in draft for minor issues, mark ready when corrected. Major issues can cause closure.
10. After merge, HACS includes the repository at the **next scheduled scan**; approval does not imply instant catalog visibility.

**Timeline note:** The official document cautions that reviews and inclusion can take **months**. This is not a guaranteed review time or queue position.

#### Clarifications for our existing guide

- **Releases:** Required for catalog inclusion (DOC-002), optional for basic custom-repository use (DOC-001). **PlayStation Hub always uses Releases** by explicit project decision.
- **Branding:** This document allows the repository brand directory / `icon.png` or a `home-assistant/brands` matching domain. Exact paths and image specifications await a dedicated source review.
- **Dashboard:** We submit to the **Integration** list, not the Plugin list, even though our integrated Python package also distributes frontend assets. Runtime frontend registration still needs official Home Assistant API research.
- **Beta wording:** The actual restriction is on custom integrations used as alpha/beta testing of **Core integrations** or overriding them; do not incorrectly generalize this to a ban on all early-stage independent community projects.
- **Scope:** The document does not prescribe database selection or whether our code is implemented with a coordinator; those choices remain open.

#### Checklist after DOC-002

- [x] Catalog inclusion rules recorded separately from basic HACS installation.
- [x] GitHub Releases made a non-optional PlayStation Hub policy.
- [ ] Add HACS Action and Hassfest per their own official documents (not yet reviewed).
- [ ] Create valid integration manifest, `hacs.json` and branding.
- [ ] Verify custom-repository installation from GitHub.
- [ ] Configure GitHub Issues, description and topics.
- [ ] Release only after CI passes.
- [ ] Submit the catalog PR with the exact prescribed workflow.

**DOC-003 (HACS GitHub Action) has now been reviewed; see below.**


### DOC-003 — HACS: GitHub Action

- **Primary source:** https://www.hacs.xyz/docs/publish/action/
- **Official page title:** GitHub Action
- **Reviewed:** 2026-11-05
- **Review scope:** This page only, including action modes, inputs, optional checks, version selection, and the official workflow example. Linked Hassfest and Dependabot documents are **not yet reviewed**.
- **Source status:** Directly inspected official HACS documentation. This is a specification review, **not evidence that PlayStation Hub currently passes HACS validation**.

#### Official findings and application to PlayStation Hub

| ID | Classification | Official documented behavior | PlayStation Hub implementation / evidence |
| --- | --- | --- | --- |
| HACS-ACT-001 | FACT | The Action uses the same repository validation code as HACS. | Treat a passing HACS Action as the primary automated HACS compatibility check, not a substitute for a real installation test. |
| HACS-ACT-002 | FACT | For the HACS default catalog, it validates newly proposed default repositories. | Validate our project before catalog PR and let catalog checks run again during review. |
| HACS-ACT-003 | FACT | For repository validation, it checks the latest GitHub Release when releases exist; otherwise the default branch. | **Important:** after first Release, a green branch-only run does not prove the latest Release passes. Test the actual release artifact and record its URL/SHA. |
| HACS-ACT-004 | FACT | When configured for PR events, it validates the fork/branch that opened the PR. | Enable pull-request checks for proposed changes. |
| HACS-ACT-005 | FACT | When configured for push events, it validates the pushed branch. | Enable push checks; distinguish branch CI from release-validation semantics. |
| HACS-ACT-006 | INPUT | \`category\` selects repository type: \`integration\`, \`plugin\`, \`template\`, \`theme\`, \`appdaemon\`, or \`python_script\`. | Set **\`category: integration\`**, not \`plugin\`, even though we bundle frontend code. |
| HACS-ACT-007 | INPUT | \`ignore\` is a space-separated list of checks to skip. | **Project rule:** do not set \`ignore\`; DOC-002 catalog inclusion requires no ignored checks. |
| HACS-ACT-008 | OPTIONAL | Ignorable checks are \`archived\`, \`brands\`, \`description\`, \`hacsjson\`, \`images\`, \`information\`, \`issues\`, and \`topics\`. | Keep all checks enabled. Do not infer that every check is equally applicable to an integration; the Action handles category-specific behavior. |
| HACS-ACT-009 | EXAMPLE | Official workflow triggers on \`push\`, \`pull_request\`, a daily midnight cron, and \`workflow_dispatch\`. | Adopt all four triggers so regressions from HACS updates can be detected. |
| HACS-ACT-010 | EXAMPLE | Official workflow uses \`permissions: {}\` and an \`ubuntu-latest\` job. | Follow least-privilege example unless an evidenced permission requirement changes. |
| HACS-ACT-011 | EXAMPLE | Official action reference is \`hacs/action@main\`. | Start from the official example. Evaluate pinning to a version/SHA separately for supply-chain reproducibility. |
| HACS-ACT-012 | RECOMMENDATION | When pinning a specific action version, the documentation recommends enabling Dependabot. | If pinned, add Dependabot updates; verify against the official Dependabot documentation in a later review. |
| HACS-ACT-013 | RECOMMENDATION | HACS page recommends Hassfest for integration maintainers. | Hassfest remains a separate required CI gate under DOC-002; study its own documentation before implementing. |

#### Official minimal workflow for our chosen category

This is an adaptation of the page's official example with \`category: integration\` and no ignored checks. It is **planned** and must not be reported as passing until the integration exists.

\`\`\`yaml
name: Validate HACS

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions: {}

jobs:
  validate-hacs:
    runs-on: ubuntu-latest
    steps:
      - name: HACS validation
        uses: hacs/action@main
        with:
          category: integration
\`\`\`

**Design decision:** Keep this workflow conceptually separate from Python unit tests and Hassfest so failures have clear ownership. The actual filename, workflow duplication and branch triggers will be reconciled before implementation. A daily scheduled check may fail even without repository changes when HACS validation rules evolve; investigate such failures rather than disabling checks.

#### Release-gate implications

1. Validate pull requests and pushes.
2. Run HACS validation and Hassfest before producing a new Release (DOC-002).
3. Publish a **full GitHub Release**, as required by our project policy.
4. Confirm the published release contents and compatibility. The official page says the latest release is checked when releases exist; do not assume the new branch head alone is sufficient.
5. Record the successful workflow run and release reference in the release checklist.

#### Corrections and unresolved items

- **Clarification:** \`hacs/action@main\` is the documented example, not proof that following a moving branch is the only acceptable production pinning policy.
- **Clarification:** An \`ignore\` input exists, but we will **not** use it.
- **Clarification:** This page does not define the Home Assistant manifest format, branding image specifications, or Hassfest setup; those require separate source reviews.
- **Open:** Verify how the Action behaves with pre-release versions, tags, and its release selection once we have a real release.
- **Open:** Verify whether the current action supports a pinned immutable commit and whether that is preferable to \`@main\`.

#### Review checklist

- [x] Read one official document in full and record its scope.
- [x] Classify action inputs and supported triggers.
- [x] Document all eight ignorable check names without enabling any.
- [x] Record official example with \`category: integration\`.
- [x] Preserve GitHub Releases as mandatory project policy.
- [ ] Implement workflow when the initial valid integration skeleton is created.
- [ ] Obtain a real green run and link the evidence.
- [ ] Review Hassfest documentation separately.

**The next document was reviewed as DOC-004 below. Its actual topic is input validation, not Hassfest.**


### DOC-004 — Home Assistant: Validate the input

- **Source:** https://developers.home-assistant.io/docs/development_validation/
- **Official title:** Validate the input
- **Last updated (as shown by source):** 2026-06-15
- **Reviewed:** 2026-11-05
- **Scope:** This page addresses YAML configuration and platform input validation using \`voluptuous\` and Home Assistant's \`config_validation\` helpers. It does **not** describe Hassfest.
- **Review status:** Complete for this single page; the linked helper implementation and modern config-flow documentation require separate reviews.

#### Rules and observations

| ID | Classification | Source finding | PlayStation Hub implementation / verification |
| --- | --- | --- | --- |
| HA-INPUT-001 | DOCUMENTED PATTERN | Home Assistant validates \`configuration.yaml\` options with \`voluptuous\`, including required/optional values, types and enumerated options. | Apply equivalent strict input validation wherever the integration accepts external configuration. For UI config flows, research the dedicated official config-flow rules before deciding the exact schema. |
| HA-INPUT-002 | DOCUMENTED HELPER | \`homeassistant.helpers.config_validation\` offers typed validators for strings, booleans, positive integers, ports, URLs, entity IDs, time zones, and other values. | Prefer Home Assistant-provided validators over duplicate custom validators where suitable. |
| HA-INPUT-003 | DOCUMENTED HELPER | MQTT-specific helpers include \`valid_subscribe_topic\` and \`valid_publish_topic\`. | If MQTT topic configuration is exposed, validate topics using appropriate HA MQTT helpers; verify supported import/API paths in the current code before implementation. |
| HA-INPUT-004 | RECOMMENDATION | Use constants defined in \`const.py\`. | Keep configuration key names and defaults centralized. |
| HA-INPUT-005 | RECOMMENDATION | When extending a platform schema, import and extend the integration's \`PLATFORM_SCHEMA\`. | Only applicable if we actually implement YAML/platform schemas; not a mandate to introduce YAML configuration. |
| HA-INPUT-006 | RECOMMENDATION | Prefer required fields before optional fields in schema definitions. | Apply this convention to \`voluptuous\` schemas when applicable. |
| HA-INPUT-007 | RECOMMENDATION | Optional defaults must satisfy their declared validators. The page warns against \`default=None\` with a \`cv.string\` validator. | Unit-test default values and reject incompatible configurations early. |
| HA-INPUT-008 | EXAMPLE | Constrain options with \`vol.In\` or a list of known valid values. | Enumerated user-facing settings must reject unsupported values. |
| HA-INPUT-009 | EXAMPLE | Use \`cv.port\` for port numbers (valid range 1–65535). | Validate any configured port without accepting out-of-range values. |
| HA-INPUT-010 | EXAMPLE | Validate lists using \`cv.ensure_list\` and membership checks. | Apply only where list-valued settings are introduced. |

#### Implications for our planned integration

1. **No decision to introduce YAML:** The official page describes YAML validation. Our UI-first configuration approach remains planned, but requires a separate config-flow documentation review.
2. **Transport isolation:** If the PlayStation Hub uses MQTT, its transport configuration should validate publish and subscribe topics and reject malformed user input.
3. **Testability:** Each configuration field should have valid, invalid, boundary and default-value tests.
4. **Fail safely:** Reject invalid configuration without starting monitoring workers or corrupting stored settings.
5. **No invented dependencies:** The document does not prescribe SQLite, Recorder, frontend registration, entity lifecycle, or Hassfest commands.

#### Concrete acceptance checklist (planned, not yet implemented)

- [ ] Confirm the configuration mechanism from the official Config Entries / Data Entry Flow documentation.
- [ ] Identify every input field and choose an appropriate validator.
- [ ] Add tests for invalid ports, wrong types, invalid topics, invalid enum values and defaults where relevant.
- [ ] Ensure no credentials or sensitive input are logged on validation errors.
- [ ] Validate the integration setup and reconfiguration lifecycle separately.
- [x] Correctly classify this document as **input validation**, not Hassfest.

#### Correction to previous planning

The previous guide referred to this URL as if it were Hassfest documentation. That was inaccurate. This URL's current official page is **Validate the input**. Hassfest remains an independent research task.

**DOC-005 reviewed:** https://developers.home-assistant.io/docs/development_checklist/ — general pre-commit checklist, mainly oriented to Home Assistant Core contributions; see review register below.


### DOC-005 — Home Assistant: Development checklist

- **Official source:** https://developers.home-assistant.io/docs/development_checklist/
- **Page title:** Development checklist
- **Page last updated:** 2024-08-27 (as displayed by the official page)
- **Reviewed on:** 2026-11-05
- **Scope:** The introductory **Development checklist** page only. Its linked **Component checklist** and **Platform checklist** are separate documents and have **not** been reviewed in this iteration.
- **Source context:** This is a Home Assistant **Core contribution** pre-commit checklist. Some requirements concern the Core repository and do **not** directly apply to a standalone HACS custom integration.

#### Directly documented checklist items and applicability

| ID | Official checklist requirement | Applicability to PlayStation Hub | Planned implementation / evidence |
| --- | --- | --- | --- |
| HA-DEV-001 | All communication with external devices/services must be wrapped in an external Python library hosted on PyPI. | **Core submission requirement; voluntary architecture target for HACS.** | Design transport adapter around an independent reusable library where warranted. Verify PS5-MQTT integration strategy before choosing dependencies. |
| HA-DEV-002 | External library must have source distribution packages available; binary-only distributions are not permitted. | **Core requirement; voluntary HACS quality target.** | For any external communication library, verify PyPI source distribution and supported platforms/architectures. |
| HA-DEV-003 | External communication library must have an enabled issue tracker. | **Core requirement; voluntary HACS quality target.** | Verify issue tracker URL for chosen library. |
| HA-DEV-004 | If the external library mainly serves Home Assistant and integration authors own it, an issue-template picker linking to HA Core issues is encouraged. | **Optional / Core-context recommendation.** | Revisit only if we publish our own external library; do not create irrelevant Core issue links. |
| HA-DEV-005 | Add new dependencies to Core's \`requirements_all.txt\` via \`python3 -m script.gen_requirements_all\`, when applicable. | **Not applicable** to our separate HACS repository. | Define dependencies in our integration manifest per the separate official manifest document; do not modify HA Core files. |
| HA-DEV-006 | Add new codeowners to Core's \`CODEOWNERS\` via \`python3 -m script.hassfest\`, when applicable. | **Not applicable** to our separate HACS repository. | Set integration \`manifest.json\` codeowners; separately study Hassfest validation. |
| HA-DEV-007 | Update Core's \`.strict-typing\` when providing fully type-hinted source. | **Not applicable** as a Core file. | Prefer strict type hints and appropriate static checks in our own repository. |
| HA-DEV-008 | Format code with \`ruff format\`. | **Adopt as mandatory project quality policy.** | Run Ruff format checks in CI; document pinned tool version. |
| HA-DEV-009 | Develop documentation for \`home-assistant.io\`. | **Core contribution workflow; not a requirement to publish a HACS integration.** | Maintain clear repository docs, installation, troubleshooting and screenshots; separate review needed for catalog documentation rules. |

#### Practical project decisions from DOC-005

1. **Ruff is required for PlayStation Hub.** The official page explicitly names \`ruff format\`; configure CI to reject noncompliant formatting.
2. **Type hints are strongly preferred.** This is our own quality policy, not a direct command to edit the Core \`.strict-typing\` file.
3. **Isolate external communication.** Keep PlayStation protocol/MQTT transport separate from Home Assistant entity and domain logic. Whether an independent PyPI library is required for **HACS** is not established by this Core-focused page.
4. **Avoid false compliance claims.** We must not pretend that modifying \`requirements_all.txt\`, \`CODEOWNERS\`, or \`.strict-typing\` is required in our independent GitHub repository.
5. **Dependency provenance matters.** Prefer portable packages with source distributions and clear maintenance/issue reporting.

#### Acceptance checks (planned, not yet implemented)

- [ ] CI executes \`ruff format --check\` for Python.
- [ ] All external communication is isolated behind testable interfaces.
- [ ] Any chosen third-party communication library has a documented distribution and maintenance audit.
- [ ] Relevant integration dependencies are declared in the correct Home Assistant integration manifest format (review pending).
- [ ] Code uses appropriate type annotations and static checks.
- [x] Core-specific checklist items are explicitly marked not applicable instead of blindly copied.

#### Source boundaries and follow-up

This document **does not** establish HACS inclusion requirements, database architecture, dashboard distribution, GitHub Release rules, or the exact Python integration skeleton. These remain governed by other documents and our explicit project decisions.

**DOC-006 reviewed:** The previously proposed URL is not the actual destination. The official navigation links to https://developers.home-assistant.io/docs/creating_component_code_review/ (see DOC-006).



### DOC-006 — Home Assistant: Checklist for creating a component

- **Verified official source:** https://developers.home-assistant.io/docs/creating_component_code_review/
- **Official page title:** Checklist for creating a component
- **Source last updated:** 2024-08-27
- **Reviewed:** 2026-11-05
- **Scope:** All seven sections of this single document: Common, External requirements, Configuration, Component/platform communication, Communication with devices/services, Pull request scope, Event names, Tests.
- **URL correction:** The previously proposed \`/docs/development_checklist/component/\` did not resolve. This URL was obtained from the official Development Checklist navigation.
- **Applicability caveat:** Written for Home Assistant **Core contributions**. We adopt transferable quality practices for our independent HACS integration, but do not misrepresent Core-only processes as HACS mandates.

#### Requirements and project decisions

| ID | Source rule or recommendation | Applicability and PlayStation Hub policy |
| --- | --- | --- |
| HA-COMP-001 | Follow Home Assistant style guidelines. | **Adopt.** Research the dedicated style guide before implementing lint configuration. |
| HA-COMP-002 | Reuse existing constants from \`homeassistant.const\`; add widely shared constants to integration \`const.py\`, keeping local-only constants close to their users. | **Adopt.** Avoid a monolithic constants file. |
| HA-COMP-003 | Declare external requirements in \`manifest.json\`; legacy \`REQUIREMENTS\` constant is deprecated. | **Adopt.** No \`REQUIREMENTS\` global; validate manifest against current HA docs. |
| HA-COMP-004 | Pin each external requirement to a specific version (example: \`phue==0.8.1\`). | **Adopt.** Explicit pinned runtime dependency versions, compatibility and update reviews. |
| HA-COMP-005 | Requirements must satisfy Home Assistant library requirements. | **Adopt as quality goal.** Inspect the linked official library-requirements document separately. |
| HA-COMP-006 | Validate YAML configuration with Voluptuous, with defaults in the schema rather than \`setup()\`; prefer shared HA keys. | **Conditional.** We plan a UI-first config flow, not a YAML schema. Research config-flow guidance separately. |
| HA-COMP-007 | Platforms use \`PLATFORM_SCHEMA\` rather than \`CONFIG_SCHEMA\`; for \`EntityComponent\` inherit the appropriate base. | **Conditional / legacy YAML platform path.** Do not introduce platform YAML just to satisfy this checklist. |
| HA-COMP-008 | Do not require users to configure behavior through \`customize\`. | **Adopt.** Use proper integration configuration and options. |
| HA-COMP-009 | \`hass.data[DOMAIN]\` can share data with platforms; dispatcher can notify platform entities of changes. | **Documented option, not a mandate.** Prefer per-config-entry runtime data and current official APIs after reviewing Config Entries. |
| HA-COMP-010 | Device/service API-specific communication should be in a separate PyPI library. | **Core contribution requirement; voluntary architecture target for HACS.** Isolate communication in a transport adapter. Assess whether to create/use a PyPI library based on the final source protocol. |
| HA-COMP-011 | Keep PRs small: one platform and only the minimum valuable functionality; do not mix unrelated cleanup and features, multiple issues, or depend on unmerged work. | **Adopt.** Build a minimal useful first integration, then add monitoring, persistence, analytics and frontend in small reviewable increments. |
| HA-COMP-012 | Prefix emitted event names with the integration domain. | **Adopt.** Events, if introduced, must use \`playstation_hub_...\` and documented event data. |
| HA-COMP-013 | Add tests to minimize regressions. | **Adopt as mandatory project policy.** Test setup, config flows, reload/unload, failure handling, transport, storage, entity behavior and frontend where applicable. |

#### Important architecture implications

1. **The first submission must be useful, not an empty skeleton.** The Core checklist advocates the smallest functional feature set; we will use that approach without claiming a HACS reviewer is bound by the Core PR checklist.
2. **Dependencies are pinned** in \`manifest.json\`. Do not put dependency declarations in a legacy \`REQUIREMENTS\` constant.
3. **Config-flow-first remains the plan.** YAML-specific rules only apply if we later support YAML.
4. **Runtime sharing and updates must be lifecycle-safe.** \`hass.data\` and dispatcher are described as possibilities; the current best practice for config-entry runtime data must be verified in a separate source review.
5. **One GitHub repository and one HACS integration** remain our chosen architecture. This document does not prescribe packaging of the Lovelace frontend, SQLite location or Marketplace update behavior.
6. **Naming and testing become acceptance gates.** Domain-prefixed events and automated tests are non-negotiable project standards.

#### Verification plan

- [ ] Review Home Assistant style guidelines and apply Ruff/static checks.
- [ ] Review manifest and library requirements; pin dependencies.
- [ ] Review config entries/data entry flows and choose correct per-entry runtime data model.
- [ ] Implement first real platform with minimal useful behavior and full tests.
- [ ] Verify all emitted event names are domain-prefixed.
- [ ] Keep feature PRs small and separately testable.
- [x] Verify the document URL from official navigation and record Core-vs-HACS applicability.

**DOC-007 reviewed:** https://developers.home-assistant.io/docs/creating_platform_code_review/ — see the dedicated section below.


### DOC-007 — Home Assistant: Checklist for creating a platform

- **Official source:** https://developers.home-assistant.io/docs/creating_platform_code_review/
- **Page title:** Checklist for creating a platform
- **Source last updated:** 2026-06-15
- **Reviewed:** 2026-11-05
- **Scope:** All five numbered areas and the common section of this single page: Common, External requirements, Configuration, Setup platform, Entity, and Communication with devices/services.
- **Applicability:** Written as a Home Assistant **Core platform development checklist**. Adopt applicable quality standards for our HACS custom integration, without falsely labeling Core-only or YAML-only practices as mandatory HACS rules.

#### Source-derived requirements and project decisions

| ID | Official finding | Applicability and PlayStation Hub decision |
| --- | --- | --- |
| HA-PLAT-001 | Follow Home Assistant style guidelines. | **Adopt.** Apply official style conventions; inspect the dedicated style documentation separately. |
| HA-PLAT-002 | Prefer existing Home Assistant constants. Keep new constants at platform level unless broadly reused; prefer \`CONF_MONITORED_CONDITIONS\` to \`CONF_MONITORED_VARIABLES\`. | **Adopt conditionally.** Use standard constants and avoid unnecessary global constants. |
| HA-PLAT-003 | Declare external requirements in \`manifest.json\`, not the deprecated \`REQUIREMENTS\` constant. | **Adopt.** Validate manifest with official tools. |
| HA-PLAT-004 | Pin external dependency versions and use PyPI rather than GitHub-hosted dependencies; meet official library requirements. | **Adopt.** Verify portability and distribution of each selected dependency. |
| HA-PLAT-005 | Directly configurable YAML platforms need Voluptuous validation, platform-schema extension, schema defaults, and standard configuration keys. | **Conditional.** No YAML platform is currently planned; follow Config Flow guidance instead. |
| HA-PLAT-006 | Do not depend on users modifying \`customize\` to configure platform behavior. | **Adopt.** All supported options should have explicit configuration semantics. |
| HA-PLAT-007 | Verify credentials, host and other passed configuration during setup. | **Adopt.** Provide meaningful setup errors without exposing credentials. |
| HA-PLAT-008 | Group calls to \`add_entities\` where possible. | **Adopt.** Avoid unnecessary repeated platform entity registration. |
| HA-PLAT-009 | Register extra actions under the **integration's** domain, and verify permissions. | **Adopt.** Future controls should use \`playstation_hub.*\` with appropriate authorization. |
| HA-PLAT-010 | Extend the appropriate entity type for the platform. | **Adopt.** Use native \`SensorEntity\`, \`BinarySensorEntity\`, \`ButtonEntity\` or other suitable entity classes as supported by current HA APIs. |
| HA-PLAT-011 | Do not pass \`hass\` into entity constructors; it is provided when an entity is added. | **Adopt.** Use \`self.hass\` only after attachment to HA. |
| HA-PLAT-012 | Do not perform \`update()\` in an entity constructor; the page illustrates \`update_before_add=True\` when needed. | **Adopt principle.** Initial data retrieval belongs in the correct setup/update lifecycle; verify current async conventions separately. |
| HA-PLAT-013 | Do not perform I/O inside entity properties. Cache values during updates. | **Mandatory project quality policy.** Properties must be fast, deterministic and side-effect free. |
| HA-PLAT-014 | Store UTC timestamps rather than relative elapsed-time strings in entity state/attributes. | **Adopt.** Derive presentation durations in the frontend from absolute times; retain timezone-aware conversions for calendar aggregation. |
| HA-PLAT-015 | Use entity lifecycle callbacks for attaching listeners and cleaning up connections. | **Mandatory project quality policy.** Test setup, unload, reload and reconnect for leaked subscriptions/tasks. |
| HA-PLAT-016 | Core platforms should isolate API-specific communication in a third-party library hosted on PyPI. | **Core requirement / HACS architecture target.** Keep a transport abstraction; independently decide whether to publish/use a dedicated library. |

#### Concrete PlayStation Hub implementation implications

1. **Sensor properties are read-only projections.** They return cached coordinator/runtime data; they never query SQLite, MQTT, the network, or disk.
2. **Event-driven source updates:** MQTT callbacks or transport tasks update the runtime model, and the entity platform publishes state changes through supported HA lifecycle mechanisms.
3. **Timestamps:** Keep session starts, ends, and observations as absolute UTC times. Render a running duration from a timestamp in the frontend; do not persist continuously changing formatted elapsed strings.
4. **Controls:** Power, standby and other commands require verified capabilities and appropriate permission checks. Select entity platforms by semantics, not by convenience.
5. **Safe cleanup:** Register listeners on entity addition and unregister them on removal. Unload must not leave orphan subscriptions or tasks.
6. **No I/O in properties:** Enforce via code review and tests, especially for any history/analytics sensors.
7. **Config validation:** Do not introduce YAML solely because this checklist includes YAML examples; the config-flow review remains pending.

#### Acceptance checklist (not yet implemented)

- [ ] Each entity platform uses the appropriate HA entity base and lifecycle.
- [ ] Entity property access never performs disk, database, MQTT or network I/O.
- [ ] Initial setup validates connection details without logging secrets.
- [ ] External dependencies are declared in \`manifest.json\` and pinned appropriately.
- [ ] Actions are registered under \`playstation_hub\` with appropriate permission checks.
- [ ] UTC timestamps and timezone-aware aggregations are tested.
- [ ] Repeated setup/unload/reload leaves no listeners, tasks or resources behind.
- [ ] Tests verify cached-state semantics and disconnected-source behavior.
- [x] Document scope and Core-vs-HACS applicability.

#### Not established by DOC-007

This document does **not** select our database architecture, specify SQLite storage paths, define frontend packaging/registration, or replace the official Config Entries / Data Entry Flow documentation. Those topics remain open until separately researched.

**DOC-008 reviewed:** https://developers.home-assistant.io/docs/core/integration-quality-scale/ — see the dedicated review section below.


### DOC-008 — Home Assistant: Integration quality scale

- **Official source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/
- **Page title:** Integration quality scale
- **Source last updated:** 2026-04-16 (as displayed by the page)
- **Reviewed:** 2026-11-05
- **Scope:** Full overview document, including scaled tiers, progress tracking, tier adjustments and special tiers. The linked individual checklist and rules pages have **not** yet been reviewed.
- **Important classification:** PlayStation Hub is a **third-party custom integration**, distributed through HACS, not a Home Assistant Core integration. Its official category is **Custom**. We may voluntarily engineer to Platinum standards but **must not claim official Platinum status**.

#### Tier framework

The scaled tiers are cumulative: each tier requires its own rules and those of lower tiers. Their detailed per-rule criteria live in separate official documents.

| Tier | Official scope and characteristics | PlayStation Hub voluntary target |
| --- | --- | --- |
| Bronze | Baseline for **new Core integrations**: easy UI setup, basic code standards, automated setup tests, introductory documentation. | Require before the first usable public release. |
| Silver | Bronze plus robust offline/error/re-authentication behavior, active code ownership and troubleshooting documentation. | Build resilience early; test disconnect/reconnect and avoid noisy logs. |
| Gold | Silver plus streamlined user experience, discovery where possible, reconfiguration, translations, comprehensive documentation and broad test coverage. | Target as the first feature-complete community release. |
| Platinum | Gold plus comprehensive coding standards, full typing, fully asynchronous implementation and efficient data/network/CPU usage. | **Long-term engineering target from day one.** |

#### Explicit findings and implementation consequences

| ID | Classification | Source finding | PlayStation Hub interpretation |
| --- | --- | --- | --- |
| HA-IQS-001 | FACT | Bronze, Silver, Gold and Platinum are four cumulative scaled tiers. | Never claim a tier without satisfying all relevant lower-tier rules. |
| HA-IQS-002 | CORE REQUIREMENT | Bronze is the minimum for new integrations introduced into Home Assistant Core. | Adopt as our internal minimum, but do not misstate it as a HACS admission rule. |
| HA-IQS-003 | FACT | Silver emphasizes handling offline devices, authentication errors, recovery, active maintainers and troubleshooting. | Implement and test recovery behavior appropriate to our source protocols. |
| HA-IQS-004 | FACT | Gold emphasizes discovery when possible, reconfiguration, translations, documentation, diagnostics and extensive automated tests. | Plan these capabilities, but verify each detailed rule before coding. |
| HA-IQS-005 | FACT | Platinum emphasizes full typing, asynchronous code and efficient resource usage. | Adopt as explicit engineering goals; measure event-loop blocking and resource use. |
| HA-IQS-006 | TRACKING | Integrations working toward or claiming a scaled tier track rules and exemptions in \`quality_scale.yaml\`. | Maintain an internal rules tracker; consider \`custom_components/playstation_hub/quality_scale.yaml\` after reviewing its detailed schema. Do not imply Home Assistant has graded us. |
| HA-IQS-007 | CORE PROCESS | Official tier changes require a Home Assistant Core PR, full checklist and review; documentation updates follow approved changes. | Not applicable to our HACS-only publication; do not submit tier-upgrade claims. |
| HA-IQS-008 | FACT | Four special tiers exist: No score, Internal, Legacy and Custom. | Recognize that our distribution belongs to the **Custom** category. |
| HA-IQS-009 | FACT | Home Assistant does not review, audit, maintain or support third-party custom integrations. | Explicitly state community-maintained and unofficial status; conduct our own security and compatibility testing. |
| HA-IQS-010 | CORE PROCESS | Quality scale rules can change, requiring Core integrations to reassess compliance. | Recheck applicable standards at significant HA releases and document compatibility reviews. |

#### Architecture and quality decisions

1. **Internal quality ambition:** Design for Platinum from the outset, but require evidence before declaring any individual rule complete.
2. **Public labeling:** Never market PlayStation Hub as officially Bronze/Silver/Gold/Platinum-certified while it remains a third-party custom integration.
3. **Config flow:** Setup must be approachable through the Home Assistant UI; research the dedicated Config Flow documentation.
4. **Error resilience:** Test offline devices, reconnects, missing dependencies, setup failure, unloading and unexpected state transitions.
5. **Localization:** Make names and UI strings translatable; defer precise file formats to official translation documents.
6. **Diagnostics and privacy:** Provide troubleshooting information without exposing credentials, player identity or private device data.
7. **Performance:** Keep Home Assistant's event loop responsive; use fully async-compatible design and benchmark expensive persistence/statistics work.
8. **Rule tracking:** Add a traceable rule matrix with statuses \`planned\`, \`implemented\`, \`verified\` and \`exempt\`, plus justification and test links.
9. **Compatibility:** Quality standards evolve; perform periodic review instead of treating this document as a permanent frozen specification.

#### Verification checklist (not yet implemented)

- [ ] Read the official **Integration Quality Scale Checklist** as a separate document.
- [ ] Read detailed quality rules before creating an exact \`quality_scale.yaml\` schema.
- [ ] Adopt explicit automated tests for setup and unloading.
- [ ] Add typed, non-blocking, lifecycle-safe runtime code.
- [ ] Document recovery behavior, supported devices and limitations.
- [ ] Add diagnostics and reconfiguration support when the integration needs them.
- [ ] Document how rule compliance is verified without claiming official Home Assistant certification.
- [x] Record the difference between Core scaled tiers and the Custom category.

**DOC-009 reviewed:** https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/ — see below.

### DOC-009 — Home Assistant: Integration Quality Scale Checklist

- **Official source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/checklist/
- **Official page title:** Checklist
- **Page last updated:** 2024-11-20 (as displayed on the source)
- **Reviewed:** 2026-11-05
- **Scope:** Complete page, including all named rule identifiers in Bronze, Silver, Gold and Platinum. The individual detailed rule pages are **not yet reviewed**.
- **Applicability:** This checklist is the required evidence list when proposing an official **Home Assistant Core** quality-scale change. For PlayStation Hub (HACS custom integration) it is adopted as an **internal engineering matrix**, not a claim of official certification.

#### Complete rule inventory

**Exact rule counts:** Bronze: 20, Silver: 10, Gold: 21, Platinum: 3; **total 54 named rules**. The source additionally includes two nested checks under `config-flow` (field `data_description` and correct use of `ConfigEntry.data` / `ConfigEntry.options`).

##### Bronze — 20 rules

| Official rule ID | Tracking | Planned evidence / note |
| --- | --- | --- |
| `action-setup` | Not assessed | Register integration actions in `async_setup` when actions exist; read detailed rule. |
| `appropriate-polling` | Not assessed | Only relevant if integration polls; event-driven MQTT may not require polling. |
| `brands` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `common-modules` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `config-flow-test-coverage` | Not assessed | Test all configuration flow paths; detailed coverage semantics pending. |
| `config-flow` | Not assessed | UI configuration; include `data_description` and correct `ConfigEntry.data` vs `options` handling. |
| `dependency-transparency` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-actions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-triggers` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-conditions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-high-level-description` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-installation-instructions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-removal-instructions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-event-setup` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-unique-id` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `has-entity-name` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `runtime-data` | Not assessed | Use `ConfigEntry.runtime_data`; review dedicated rule before designing setup lifecycle. |
| `test-before-configure` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `test-before-setup` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `unique-config-entry` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |

##### Silver — 10 rules

| Official rule ID | Tracking | Planned evidence / note |
| --- | --- | --- |
| `action-exceptions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `config-entry-unloading` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-configuration-parameters` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-installation-parameters` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-unavailable` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `integration-owner` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `log-when-unavailable` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `parallel-updates` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `reauthentication-flow` | Not assessed | Conditional on an authentication-bearing source; assess rule exemptions. |
| `test-coverage` | Not assessed | Official checklist explicitly says **above 95%** coverage of all integration modules; define measurable CI gate. |

##### Gold — 21 rules

| Official rule ID | Tracking | Planned evidence / note |
| --- | --- | --- |
| `devices` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `diagnostics` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `discovery-update-info` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `discovery` | Not assessed | Assess feasibility of discovery for supported PlayStation source. |
| `docs-data-update` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-examples` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-known-limitations` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-supported-devices` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-supported-functions` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-troubleshooting` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `docs-use-cases` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `dynamic-devices` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-category` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-device-class` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-disabled-by-default` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `entity-translations` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `exception-translations` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `icon-translations` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `reconfiguration-flow` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `repair-issues` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |
| `stale-devices` | Not assessed | Detailed rule document pending; implementation and test evidence pending. |

##### Platinum — 3 rules

| Official rule ID | Tracking | Planned evidence / note |
| --- | --- | --- |
| `async-dependency` | Not assessed | Choose async-capable dependency; applicability depends on selected external transport. |
| `inject-websession` | Not assessed | HTTP/websession requirement may be inapplicable to MQTT-only transport; assess via detailed rule. |
| `strict-typing` | Not assessed | Adopt strict typing; confirm official rule details and tooling. |

#### Critical implementation consequences

1. **Configuration:** Plan UI config flow, duplicate-entry prevention, connection validation before saving and before setup, and full config-flow tests. Distinguish immutable config-entry data from user-changeable options.
2. **Runtime state:** Prefer `ConfigEntry.runtime_data` rather than ad-hoc global data for per-entry runtime objects; confirm implementation in the detailed official rule.
3. **Entity identity and lifecycle:** Unique IDs, `has_entity_name = True`, correct event listener lifecycle, availability and unload behavior.
4. **Quality coverage:** The Silver checklist specifies **above 95% test coverage** for integration modules. This is an internal target, not yet a passed test or an HACS admission requirement.
5. **Localization and support:** Translatable entities/exceptions/icons, diagnostics, troubleshooting, supported devices, known limitations, repair issues and reconfiguration.
6. **Efficiency:** Platinum asks for async dependencies, injectable web sessions, and strict typing. Applicability of HTTP/websession requirements to a potentially MQTT-only integration must be justified using detailed rule pages.
7. **Conditional and non-applicable rules:** Document evidence-based exemptions; do not invent polling, reauthentication or websession code just to satisfy a checklist.
8. **Publication:** None of these Core quality-scale rules substitutes for the HACS catalog requirements established in DOC-001–003.

#### Tracking convention

Each rule starts at **Not assessed**. Allowed future statuses: **Applicable / planned**, **Implemented / unverified**, **Verified** (with code and test links), or **Not applicable** (with written justification). No rules are currently claimed complete.

#### Document-specific acceptance checklist

- [x] All official rule IDs transcribed into this guide by tier.
- [x] Nested `config-flow` requirements recorded.
- [x] Above-95% test coverage threshold recorded exactly.
- [x] Custom-integration versus Core grading distinguished.
- [ ] Read detailed rules individually to establish applicability and testable criteria.
- [ ] Implement a machine-checkable quality tracker after confirming the official `quality_scale.yaml` format.
- [ ] Link every Verified rule to evidence.

**DOC-010 reviewed:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/ — index only; individual rule documents remain pending.



### DOC-010 — Home Assistant: Integration quality scale rules (index)

- **Official source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
- **Official title:** Integration quality scale rules
- **Source last updated:** 2025-05-21
- **Reviewed:** 2026-11-05
- **Scope:** The complete **rules index page only**, including each tier's one-line rule descriptions and links. **Individual rule pages have not been reviewed.**
- **Applicability:** The rules belong to Home Assistant Core's quality-scale framework; PlayStation Hub uses them as voluntary engineering standards, not an official Home Assistant quality certification.

#### Confirmed rule structure

| Tier | Rule count | Directly relevant examples |
| --- | ---: | --- |
| Bronze | 20 | \`common-modules\`, \`config-flow\`, \`runtime-data\`, \`entity-unique-id\`, \`config-flow-test-coverage\` |
| Silver | 10 | \`config-entry-unloading\`, \`entity-unavailable\`, \`reauthentication-flow\`, \`test-coverage\` |
| Gold | 21 | \`entity-translations\`, \`exception-translations\`, \`icon-translations\`, \`diagnostics\`, \`reconfiguration-flow\` |
| Platinum | 3 | \`async-dependency\`, \`inject-websession\`, \`strict-typing\` |

**Result:** The index confirms the **54 rule identifiers** already cataloged in DOC-009 and gives short explanations for each. It does **not** provide enough detail to declare any one rule implemented or verified. The individual rule pages remain a separate reading backlog.

#### Specific official localization requirements identified in this index

- \`entity-translations\` (Gold): entities have translated names.
- \`exception-translations\` (Gold): exception messages are translatable.
- \`icon-translations\` (Gold): entities implement icon translations.

**Evidence boundary:** These are only the index summaries. Exact JSON keys, file placement, language resolution, icon rules, and testing conventions must be confirmed by reviewing the individual official pages and Home Assistant translation documentation.

#### New binding project decision — multilingual from day one

**Status:** APPROVED BY PROJECT OWNER (2026-11-05). This is a PlayStation Hub policy, **not** a statement that HACS requires every custom integration to support multiple languages.

1. **English is the source language.** Code, comments, internal identifiers, documentation and translation keys use English. UI text is translated at runtime.
2. **Backend / Home Assistant (DOC-015 correction):** Use complete `translations/<language_code>.json` catalogs directly. `strings.json` is for Home Assistant Core build tooling and must not be used for custom integrations.
3. **Frontend:** Keep an independent, modular localization layer for the bundled Lovelace card/panel; use the Home Assistant selected language when supported, and fall back to English. Determine the supported locale API from official frontend documentation before implementation.
4. **No hardcoded UI strings:** Labels, buttons, errors, empty states, status messages, chart legends, units where appropriate, and accessibility text must be localizable.
5. **Locale-aware presentation:** Use the user's locale and time zone for date/time and number formatting; retain UTC for persisted event timestamps and domain calculations.
6. **Scalable locale registry:** New languages are added by supplying locale resources, not by copying UI components or changing domain algorithms.
7. **Fallback and missing keys:** English fallback for missing/unsupported translations; missing-key checks and translation completeness reporting in CI.
8. **Pluralization and interpolation:** Use locale-aware formatting and safe parameterized messages. Confirm Home Assistant's officially supported backend translation mechanisms before selecting implementations.
9. **Privacy:** Never include personal identifiers or credentials in language catalogs, translation keys, or diagnostics output.
10. **First supported locales:** English and Portuguese are the initial planned languages. Whether \`pt\` and \`pt-PT\` are distinct supported identifiers must be confirmed in the official HA translation documentation. Further languages should be easy to add.

#### Proposed localization-oriented package structure (not yet validated)

\`\`\`text
custom_components/playstation_hub/
├── translations/
│   ├── en.json
│   └── pt.json
└── frontend/
    ├── playstation-hub.js
    └── i18n/
        ├── en.json
        └── pt.json
\`\`\`

**Important:** This is a **design proposal**, not an assertion that the frontend JSON files are automatically loaded by HACS or Home Assistant. The integration must explicitly package, serve, and resolve its frontend language resources.

#### Implementation and verification checklist

- [ ] Review official \`entity-translations\` detailed rule page.
- [ ] Review official \`exception-translations\` detailed rule page.
- [ ] Review official \`icon-translations\` detailed rule page.
- [ ] Review official Home Assistant backend translation file conventions and locale identifiers.
- [ ] Review official frontend localization API / patterns.
- [ ] Define typed translation keys and test missing keys, fallback, interpolation, pluralization and locale switching.
- [ ] Test both integration configuration flows and the dashboard in at least English and Portuguese.
- [ ] Document a contributor workflow for adding translations.
- [x] Record the owner's mandatory multilingual requirement without incorrectly claiming official HACS certification.

#### Architecture impact

- This review **does not change** the decision to distribute Python and frontend in one HACS integration and one GitHub Release.
- It **does change** the minimum release acceptance criteria: multilingual-ready backend and frontend are required from the beginning.
- It does **not** resolve the SQLite-vs-Recorder decision, the exact config-flow schema, or frontend resource registration.

**DOC-011 reviewed:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-translations/ — see below.


### DOC-011 — Home Assistant: Entities have translated names

- **Official source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/entity-translations/
- **Official title:** Entities have translated names
- **Official last updated:** 2026-08-02
- **Reviewed:** 2026-11-05
- **Scope:** Entire single rule page: reasoning, example implementation, device-class exception to specifying a translation key, additional resources, explicit exceptions, related rules.
- **Quality tier:** Gold in the official Home Assistant Core quality scale. **No exceptions** to the rule. Our HACS custom integration voluntarily adopts the behavior as a mandatory project standard.

#### Source requirements and implementation contract

| ID | Source-backed rule or clarification | PlayStation Hub design and verification |
| --- | --- | --- |
| HA-ENTITY-I18N-001 | Entity names must be translated for users of different languages. | No hardcoded English entity display names for user-facing entities. |
| HA-ENTITY-I18N-002 | Example sets \`_attr_has_entity_name = True\`. | Use the modern entity naming convention, also subject to the separate \`has-entity-name\` rule review. |
| HA-ENTITY-I18N-003 | Example sets \`_attr_translation_key = "phase_voltage"\` on a \`SensorEntity\`. | Use stable English semantic keys for named entity types; never use language-dependent translation keys. |
| HA-ENTITY-I18N-004 | Core's example shows the `entity` → platform → translation key → `name` schema in `strings.json`. | For our custom integration, use the same supported key structure in `translations/en.json` and other complete locale catalogs. |
| HA-ENTITY-I18N-005 | When a \`binary_sensor\`, \`number\`, \`sensor\`, or \`update\` entity has a device class, the translation key may be omitted **if** the entity should use the device class name. | Prefer standard device-class names where they accurately express the entity; do not invent redundant translations. |
| HA-ENTITY-I18N-006 | The rule explicitly lists **no exceptions**. | No blanket exemptions for user-visible entity names; decide whether device-class naming covers an entity. |
| HA-ENTITY-I18N-007 | Entity naming is combined with the device name in the example (e.g. “My device Phase voltage”). | Avoid repeating device name in the entity's translated suffix; test rendered naming with multiple consoles. |

#### Minimal official-pattern example adapted to our domain

\`\`\`python
class ConsolePlaytimeSensor(SensorEntity):
    """Represent PlayStation console playtime."""

    _attr_has_entity_name = True
    _attr_translation_key = "console_playtime"
\`\`\`

\`\`\`json
{
  "entity": {
    "sensor": {
      "console_playtime": {
        "name": "Console playtime"
      }
    }
  }
}
\`\`\`

The JSON fragment illustrates the \`strings.json\` source structure only; it is **not** a complete integration translation catalog. The class snippet is an illustrative contract, not an implemented or tested entity.

#### Architecture decisions and multilingual consequences

1. **Backend localization (DOC-015 correction):** Custom integration entity names use standalone `translations/en.json` and other locale catalogs; `strings.json` is Core-only build input.
2. **Stable IDs:** Translation keys are stable technical identifiers, independent of locale. Do not generate unique IDs from translated names.
3. **Device naming:** Keep device identity separate from entity suffix translations. Do not embed a console's user-defined name into a translation key.
4. **Device-class reuse:** Where a standard device class describes an entity accurately, use it rather than duplicating the device-class name translation.
5. **Frontend scope:** This rule covers Home Assistant **entity names**, not arbitrary custom Lovelace labels. Our independent frontend localization layer remains a project requirement but is **not validated by this rule**.
6. **Locale targets:** English and Portuguese remain the initial languages. The precise HA locale filenames, generation and fallback semantics require the separate official translation documentation review.

#### Planned tests and acceptance checks

- [ ] Entity with \`translation_key\` renders translated name in at least two supported languages.
- [ ] Entity name composes correctly with device name without repetition.
- [ ] Entity unique ID remains stable across language changes.
- [ ] Standard device-class names are used when appropriate.
- [ ] All user-facing entity names have translations or correct device-class naming.
- [ ] No runtime I/O in entity name properties.
- [ ] Verify actual translation catalog and runtime behavior against official Home Assistant translation docs.
- [x] Record that this Gold rule has no exceptions and identify its limited scope.

#### Source boundaries

The page does **not** prescribe our SQLite architecture, frontend language loader, exact translation build pipeline, dashboard resource registration, or GitHub Release procedure. Do not infer those from this rule.

**DOC-012 reviewed:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/exception-translations/ — see the section below.


### DOC-012 — Home Assistant: Exception messages are translatable

- **Official source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/exception-translations/
- **Official title:** Exception messages are translatable
- **Last updated on official page:** 2026-08-02
- **Reviewed:** 2026-11-05
- **Scope:** Entire single page: reasoning, implementation example, \`strings.json\` example, additional resources, exceptions, and related rules.
- **Quality scale:** Gold rule for Home Assistant Core integrations. The page explicitly says there are **no exceptions** to this rule.
- **Project policy:** Adopt localized user-facing errors from day one, regardless of whether the integration has an official Core quality-scale grade.

#### Requirements grounded in DOC-012

| ID | Source-backed requirement | PlayStation Hub implementation / verification |
| --- | --- | --- |
| HA-EXC-I18N-001 | Home Assistant provides built-in translation support for errors derived from \`HomeAssistantError\`. | For user-facing service/action failures, use the Home Assistant exception hierarchy. Do not surface raw English exception text to users. |
| HA-EXC-I18N-002 | Translatable errors pass \`translation_domain\` and \`translation_key\` when raised. | Use \`translation_domain=DOMAIN\` and a stable semantic key, independent of language. |
| HA-EXC-I18N-003 | The example raises \`ServiceValidationError\` for invalid user-supplied service parameters. | Distinguish invalid user input from device/network failures; verify precise exception semantics in the dedicated raising-exceptions documentation. |
| HA-EXC-I18N-004 | The example raises \`HomeAssistantError\` for communication failures and chains the underlying exception with \`from err\`. | Keep diagnostic cause for debugging while exposing a translated user-facing message; ensure logs and diagnostics do not leak credentials. |
| HA-EXC-I18N-005 | Core's example declares exception messages under `exceptions.<translation_key>.message`. | For our custom integration, put complete messages in `translations/en.json` and other locale catalogs; never depend on Core's `strings.json` build pipeline. |
| HA-EXC-I18N-006 | The rule has no exceptions. | All applicable user-facing integration exceptions must be localizable. |
| HA-EXC-I18N-007 | Related rules include \`entity-translations\` and \`action-exceptions\`. | Review \`action-exceptions\` separately; DOC-011 already covers entity-name translations. |

#### Minimal official-pattern example adapted for PlayStation Hub

\`\`\`python
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN


async def async_set_console_mode(mode: str, client) -> None:
    """Set the requested console mode using localized errors."""
    if mode not in {"rest", "awake"}:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_console_mode",
        )

    try:
        await client.async_set_mode(mode)
    except ConnectionError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="console_unreachable",
        ) from err
\`\`\`

\`\`\`json
{
  "exceptions": {
    "invalid_console_mode": {
      "message": "The requested console mode is not supported."
    },
    "console_unreachable": {
      "message": "Cannot communicate with the PlayStation console."
    }
  }
}
\`\`\`

These snippets demonstrate the documented translation pattern. They are **illustrative only**: no such console-control transport or API has been implemented or verified.

#### Architecture decisions for multilingual errors

1. **Source language (DOC-015 correction):** English runtime messages live in `translations/en.json`; translated equivalents use other standalone locale catalogs.
2. **Stable keys:** Translation keys are immutable semantic identifiers, not localized display strings.
3. **Typed errors:** Distinguish input validation, authentication/authorization, unavailable console, timeout, unsupported command, and internal failure. Use appropriate Home Assistant exception types after reviewing their dedicated documentation.
4. **Safe chaining:** Preserve underlying causes with exception chaining where applicable; never expose tokens, passwords, device secrets, or sensitive MQTT payloads in translated messages.
5. **Parameters:** Where error messages need dynamic values, use officially supported translation placeholders after checking the dedicated translation documentation. Avoid constructing translated strings with Python f-strings.
6. **Backend/frontend separation:** Home Assistant's \`HomeAssistantError\` translation mechanism does not automatically translate arbitrary JavaScript dashboard errors. The frontend needs its own localized messages.
7. **Lifecycle:** Exceptions must not leave monitoring tasks, listeners or persistence operations partially initialized. Test cleanup separately.
8. **Consistency:** The same user-facing failure category should map to a consistent translation key and actionable explanation across integration entry points.

#### Acceptance checklist (planned; not yet implemented)

- [ ] Every user-facing service/action error is represented by a translated Home Assistant exception.
- [ ] `translations/en.json` includes each `exceptions` key used by the Python code.
- [ ] Locale catalogs cover the supported languages and fall back safely when incomplete.
- [ ] Tests verify validation failures and transport failures use the correct translation domain/key.
- [ ] Tests verify exception chaining retains diagnostic causes without exposing secrets.
- [ ] Frontend errors have separate localized labels/messages.
- [ ] Dedicated raising-exceptions documentation reviewed for the exact exception class contracts.
- [ ] Translation placeholders and runtime locale resolution validated from official docs.
- [x] Record that DOC-012 explicitly allows no exceptions to its Gold rule.

#### Source boundaries

This document does **not** specify how to implement PlayStation power control, the frontend translation loader, SQLite error recovery, or the exact Home Assistant translation build process. Those topics remain open for separate official-source reviews.

**Next official document proposed (not yet reviewed):** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/icon-translations/



## 10. Consolidated official-source review — architecture-critical batch (2026-11-05)

**Review status and limits:** The owner requested a comprehensive one-pass review. The official sites contain many hundreds of pages, changing APIs and linked rules. This batch verifies the **specific documents listed below**, records directly supported requirements and corrects prior mistakes. **It is not a claim that every page, linked child page, or all 54 individual quality rules has been exhaustively audited.** Do not label the integration fully compliant until implementation, tests, and remaining official-source reviews are completed.

### DOC-013 — Icon translations

- **Source:** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/icon-translations/
- **Reviewed:** 2026-11-05
- **Direct rule:** Icons can be specified in \`icons.json\` using translation keys; avoid overriding a semantically correct device-class icon. Icons can be state-dependent or numeric-range-dependent.
- **Example:** \`{"entity":{"sensor":{"console_status":{"default":"mdi:gamepad-variant","state":{"playing":"mdi:gamepad-variant-outline"}}}}}\`
- **Numeric range rules:** Numeric thresholds sorted ascending; highest matching lower/equal bound wins. Default applies to unavailable, nonnumeric and out-of-range low values. State-based mappings take precedence over ranges.
- **Exceptions:** The official rule says none.
- **Important distinction:** Icon “translations” map semantic keys/states to icon names; they are **not natural-language translations**.
- **Project tests:** Check device-class reuse, static/state/range icon mappings, unavailable states and no I/O in properties.

### DOC-014 — Integration file structure

- **Source:** https://developers.home-assistant.io/docs/creating_integration_file_structure/
- **Reviewed:** 2026-11-05
- **Required minimum integration files:** \`manifest.json\` and \`__init__.py\` under a directory matching the unique, effectively permanent integration domain.
- **Platforms:** e.g. \`sensor.py\`, \`switch.py\`, only when needed.
- **Actions:** Describe registered actions in \`services.yaml\` when applicable.
- **Coordinator:** \`coordinator.py\` is a recommended convention for a \`DataUpdateCoordinator\` subclass, **not a mandatory module**.
- **Custom integration location:** \`<config>/custom_components/<domain>/\`.
- **Brand:** Custom integration may include \`brand/\` inside its integration directory; image specifics require separate verification.
- **Our package:** \`custom_components/playstation_hub/\` with all runtime Python/frontend assets under it.

### DOC-015 — Custom integration localization — CRITICAL CORRECTION

- **Source:** https://developers.home-assistant.io/docs/internationalization/custom_integration/
- **Reviewed:** 2026-11-05
- **Official explicit rule:** **Do not use \`strings.json\` for custom components.**
- **Why:** \`strings.json\` and \`[%key:...]%\`-style placeholders are **build-time features for Home Assistant Core**. Custom integrations do not run through that build pipeline.
- **Runtime requirement:** Include complete, standalone \`translations/<language_code>.json\` catalogs adjacent to the integration source, including \`translations/en.json\`; use **BCP 47** language codes.
- **No unresolved references:** The full English text must appear in \`translations/en.json\`. No Core build-time references/placeholders.
- **Validation:** Use Hassfest to validate translation files.
- **Impact:** Supersedes earlier guide passages DOC-011/DOC-012 that incorrectly prescribed \`strings.json\` as the runtime translation source. Those earlier examples are **historical examples of key shape**, not valid custom-integration packaging instructions.
- **Planned files:** \`custom_components/playstation_hub/translations/en.json\`, \`pt.json\` (verify HA locale naming before first release), plus future BCP 47 catalogs.
- **Frontend:** Its JavaScript locale loader remains a separately engineered component, not automatically handled by the Python translation catalogs.

### DOC-016 — Backend localization categories (Core schema reference only)

- **Source:** https://developers.home-assistant.io/docs/internationalization/core/
- **Reviewed:** 2026-11-05
- **Categories:** \`title\`, \`common\`, \`conditions\`, \`config\`, \`device\`, \`device_automation\`, \`entity\`, \`entity_component\`, \`exceptions\`, \`issues\`, \`options\`, \`selectors\`, \`services\`, \`triggers\`, plus relevant subentry structures.
- **Project use:** Reuse the supported JSON **category/key shapes** in complete runtime translation catalogs.
- **Critical limitation:** This page explains Core's source string and reference system; **do not copy its \`strings.json\` build process or \`[%key:...]%\` references** into our custom integration. DOC-015 controls runtime packaging.

### DOC-017 — Config entries

- **Source:** https://developers.home-assistant.io/docs/config_entries_index/
- **Reviewed:** 2026-11-05
- **Persistence:** Home Assistant owns persistent Config Entries created through UI config flows.
- **Lifecycle:** \`async_setup_entry(hass, entry)\` runs per entry; forward setup to relevant entity platforms via \`await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)\`.
- **Unload:** \`async_unload_entry\` must remove listeners, unsubscribe events, close connections and unload forwarded platforms.
- **Removal:** \`async_remove_entry\` can perform cleanup when an entry is deleted. **Data deletion policy must be explicit and conservative.**
- **Migration:** Implement \`async_migrate_entry\` when entry versions change.
- **Mutation:** Never mutate \`entry.data\` or \`entry.options\` directly; use \`hass.config_entries.async_update_entry\`.
- **Subentries:** Official framework supports logical config subentries; decide whether multiple PlayStation consoles are entries or subentries only after modeling source identities and permissions.
- **Failure states:** Distinguish setup error, setup retry, migration error and failed unload; test each relevant lifecycle transition.

### DOC-018 — Data entry flow

- **Source:** https://developers.home-assistant.io/docs/data_entry_flow_index/
- **Reviewed:** 2026-11-05
- **Framework:** Asynchronous multi-step flows for configuration, options, repairs and related operations.
- **Flow results:** Show form, create entry, abort, external step, show progress and show menu.
- **Forms:** Define validation with Voluptuous and/or selectors; return structured field errors, never raw sensitive payloads.
- **Sections:** Can group inputs; only **one level** of sections is supported. Sections can have localized names/descriptions and icon configuration.
- **Version:** A flow handler defines schema version and relevant steps.
- **Project:** Implement a minimal functional UI flow with tests for duplicate entries, invalid values, cancellation, retry and translations. Do not invent options before identifying actual user-configurable behavior.
- **Correction:** The Core examples may refer to \`strings.json\`; **custom integration runtime translations still follow DOC-015**.

### DOC-019 — Integration manifest

- **Source:** https://developers.home-assistant.io/docs/creating_integration_manifest/
- **Reviewed:** 2026-11-05
- **File:** \`custom_components/playstation_hub/manifest.json\`.
- **Domain:** Must match directory, be unique and treated as immutable.
- **Custom version:** Required for custom integrations, valid AwesomeVersion-compatible SemVer/CalVer. **Project policy: SemVer + full GitHub Releases.**
- **Type:** Explicit \`integration_type\` recommended even for custom integrations. \`hub\`, \`device\`, \`service\` etc. have different semantics. **Do not finalize \`hub\` until the multi-console config-entry model is decided.**
- **Dependencies:** Use explicit \`requirements\` pins and correct \`dependencies\` / \`after_dependencies\` semantics. Verify whether MQTT is a dependency only after choosing integration transport.
- **HACS minimum:** DOC-001 additionally requires \`domain\`, \`documentation\`, \`issue_tracker\`, \`codeowners\`, \`name\`, \`version\`. Manifest validity must be checked with Hassfest.
- **Quality scale:** Do **not** declare \`quality_scale: platinum\` for a custom integration. Our Platinum target is an internal aspiration, not official certification.

### DOC-020 — HACS Plugin (Dashboard) packaging

- **Source:** https://www.hacs.xyz/docs/publish/plugin/
- **Reviewed:** 2026-11-05
- **Separate category:** HACS frontend calls it “Dashboard”; the backend calls it “plugin”.
- **Standalone plugin packaging:** Expects matching \`.js\` in \`dist/\` or repository root, with release-specific selection rules; non-JS assets belong in \`dist/\`.
- **Our chosen architecture:** **One HACS Integration**, **not** a separately registered Plugin repository. Do not impose plugin \`dist/\` layout requirements on our integration package.
- **Unresolved implementation gate:** The custom integration must serve/register its bundled frontend using **supported Home Assistant frontend APIs**, manage resource cache invalidation and remove/update resources safely. This is **not guaranteed by HACS** merely because the JS files are packaged.

### DOC-021 — HACS Integration packaging and catalog admission (revalidated)

- **Sources:** https://www.hacs.xyz/docs/publish/integration/ and https://www.hacs.xyz/docs/publish/include/
- **Rechecked:** 2026-11-05
- **One integration** in \`custom_components/\`; all runtime dependencies inside its package.
- **Valid manifest** with six HACS minimum keys, branding, and release behavior as documented.
- **Default catalog admission:** Public GitHub repo; HACS Action with zero errors/ignored checks; Hassfest; **full GitHub Release after passing actions**; correct \`hacs/default\` integration list submission.
- **Distinction:** Basic custom-repository HACS installation can work without releases, but **PlayStation Hub requires Releases** as project policy and for catalog submission.

### Corrections applied to previous design assumptions

1. **P0:** For custom integrations, use \`translations/*.json\` directly, **not** \`strings.json\`. Supersedes conflicting historical instructions in DOC-011 and DOC-012.
2. **P0:** A bundled frontend is not a HACS plugin installation; integration code must explicitly register/serve it. Test upgrade and rollback of both components.
3. **P1:** Do not set official \`quality_scale: platinum\` in the custom manifest.
4. **P1:** \`ConfigEntry.data\` and \`options\` must not be mutated directly.
5. **P1:** Preserve the unique \`playstation_hub\` domain; do not shadow Core domains.
6. **P1:** All runtime resources must remain inside the HACS-managed integration directory.
7. **P1:** The source documentation is not a substitute for real CI, HACS install testing, browser integration testing or data migration testing.

### Remaining mandatory research backlog — NOT YET EXHAUSTIVELY REVIEWED

The documentation trees at https://www.hacs.xyz/docs/use/, https://www.hacs.xyz/docs/publish/, https://www.hacs.xyz/docs/contribute/ and https://developers.home-assistant.io/ contain substantially more documents. The following areas must still receive their own verified source reviews:

| Priority | Documentation family | Reason |
| --- | --- | --- |
| P0 | Official custom integration frontend static path/resource registration, panel/custom-card APIs, frontend localization | Critical to our single-install Python + dashboard design |
| P0 | Official Home Assistant async event-loop/I/O, storage helpers, Recorder, backup coverage | Required before choosing SQLite vs native storage |
| P0 | HACS Action, Hassfest and branding details | Required for first valid catalog submission |
| P0 | Config flow specifics, config entry runtime data, setup failures, unloading | Correct first skeleton lifecycle |
| P1 | All 54 detailed IQS rule pages (only entity/exception/icon translations reviewed individually) | Evidence-based voluntary Platinum target |
| P1 | Device registry, entity platforms, service actions, permissions, diagnostics and repairs | Production features |
| P1 | Translations, pluralization, frontend language selection, language codes, accessibility | Multilingual release requirement |
| P1 | Integration test framework, pytest fixtures, coverage, Ruff, strict typing | High-quality CI |
| P2 | HACS use/contribute, AppDaemon, theme/template/plugin-only publication | Useful context; many sections do not apply to our integration category |
| P2 | Compatibility, security, licensing, privacy, telemetry and upgrade policy | Public maintenance |

**No completeness claim:** Until these are read and tests pass, do not label the guide “all official documentation reviewed”, the implementation “Platinum certified”, or the integration “Marketplace approved”.

### Next engineering decisions after documentation research

- [ ] Select and prove frontend registration mechanism and automatic resource update.
- [ ] Select source/transport and multiple-console architecture.
- [ ] Approve data storage ADR (native Store/Recorder vs application-owned SQLite).
- [ ] Create working minimal integration with direct runtime translation catalogs.
- [ ] Implement Hassfest/HACS Action and verify the actual release artifact.
- [ ] Add real tests and install as a custom repository before catalog submission.


## 11. Official frontend integration review — static resources, cards and panels (2026-11-05)

**Scope:** Verified the following **five** official Home Assistant pages. This is a focused review of frontend delivery, not an exhaustive audit of all HACS/Home Assistant documentation.

### DOC-022 — Register resources (current official frontend docs)

- Source: https://contributors.home-assistant.io/frontend/custom-ui/resources/
- **Two distinct steps:** (1) serve the JavaScript file at a URL, (2) register it as a dashboard resource.
- Standard manual route: files in \`<config>/www/\` appear under \`/local/\`, but this directory is discovered on startup; creating it may require a restart.
- Resources are normally managed at **Settings → Dashboards → Resources**; YAML \`lovelace.resource_mode: yaml\` instead manages resources through configuration, requiring \`lovelace.reload_resources\` or restart.
- Use resource type **\`module\`** for modern JavaScript. Legacy \`js\` and \`html\` resource types are deprecated.
- Resource URL version query parameters, e.g. \`?v=1.2.0\`, force browsers to fetch updated files. Reloading the browser may be needed.
- \`/local/\` files are served **without authentication**; never include credentials or sensitive data in frontend bundles.
- **Project consequence:** Shipping JavaScript inside our Python package does not by itself register the Lovelace resource. Implement both static serving and registration, or clearly document a manual registration path. Automatic registration is a **project goal** requiring tested HA API behavior for both storage and YAML resource modes.

### DOC-023 — Async static path registration

- Source: https://contributors.home-assistant.io/blog/2024/06/18/async_register_static_paths/
- **Supported async API:** \`await hass.http.async_register_static_paths([StaticPathConfig(url_path, filesystem_path, cache_headers)])\`.
- Import \`StaticPathConfig\` from \`homeassistant.components.http\`.
- The old \`hass.http.register_static_path\` blocks the event loop and was deprecated, with removal planned for Home Assistant 2025.7. **Do not use it.**
- Multiple static paths may be registered in one async call to reduce executor work.
- Proposed path: \`/playstation_hub/frontend/\` serving files under \`custom_components/playstation_hub/frontend/\`.
- Proposed module URL: \`/playstation_hub/frontend/playstation-hub.js?v=<integration-version>\`.
- **Project policy:** Register paths once per integration, not once per console/config entry. Never serve the integration's entire Python directory or persistent SQLite database. Ensure the static route exposes only intended frontend assets.
- **Unresolved:** Route removal/registration behavior across unload/reload and supported Home Assistant versions must be tested. The official article does not specify a universal unregistration API.

### DOC-024 — Custom panels

- Source: https://contributors.home-assistant.io/frontend/custom-ui/panel/
- A custom panel is a **full page** with access to the Home Assistant \`hass\` object, not simply a Lovelace card.
- Integrations register custom panels in Python with \`async_register_panel()\` from \`homeassistant.components.panel_custom\`.
- The integration API uses \`webcomponent_name\` (rather than \`name\`) and \`frontend_url_path\` (rather than \`url_path\`); consult the current signature when implementing.
- Panels receive \`hass\`, \`narrow\`, \`route\`, and \`panel\`; the integration owns layout, responsiveness and navigation.
- The sidebar entry can be controlled by panel options such as title, icon and administrator requirement.
- **Project option:** Provide a PlayStation Hub sidebar panel in addition to the Lovelace card, reusing the same UI components. **Not required for the first skeleton**; must not be confused with an automatically generated Lovelace dashboard.

### DOC-025 — Routing and panels

- Source: https://contributors.home-assistant.io/frontend/architecture/routing-and-panels/
- Built-in panels and custom panels are different: \`frontend.async_register_built_in_panel\` registers a component already present in the HA frontend; a custom integration normally uses a **custom panel** for new UI.
- Panels are associated with URL paths, and the frontend provides routing and panel metadata.
- **Project consequence:** Do not misuse built-in panel registration to pretend our custom JavaScript is part of the HA frontend bundle.
- **Unresolved:** Determine safe duplicate detection and removal behavior for panel registration from supported public APIs before implementation.

### DOC-026 — Home Assistant frontend integration

- Source: https://www.home-assistant.io/integrations/frontend/
- The frontend integration supports themes, extra JavaScript modules and localization settings.
- Users can select a preferred language in their Home Assistant profile.
- **Project consequence:** Frontend locale selection should follow the Home Assistant user's locale, not a hardcoded English or Portuguese setting; verify the \`hass\` object language contract from dedicated frontend documentation.
- **Do not require** users to edit \`configuration.yaml\` to add \`extra_module_url\` for the PlayStation Hub; our integration should manage the frontend where supported.

### Implementation blueprint — proposed, not yet tested

\`\`\`text
custom_components/playstation_hub/
├── __init__.py
├── manifest.json
├── translations/
│   ├── en.json
│   └── pt.json
└── frontend/
    ├── playstation-hub.js
    ├── components/
    ├── styles/
    └── i18n/
\`\`\`

The integration is installed/updated as **one HACS integration release**. Its Python setup serves frontend files using \`async_register_static_paths\`. The Lovelace card resource must be registered as a \`module\`; optionally a sidebar panel may be registered through \`panel_custom.async_register_panel\`. The Python package and frontend must share the same release version, with explicit browser cache-busting.

#### Safety, lifecycle and update acceptance gates

- [ ] HACS installs all required Python/JS/CSS assets from a **single** GitHub Release.
- [ ] Static URL serves **only** intended public assets, never credentials, source configuration or SQLite files.
- [ ] Registration is idempotent across multiple console config entries and HA restart/reload.
- [ ] Resource registration works in Lovelace storage mode; YAML resource mode is detected and documented without overwriting user settings.
- [ ] Frontend module is registered once; repeated updates do not create duplicate resource records.
- [ ] A release upgrade loads the matching Python and JavaScript versions; cache invalidation is tested in browser and companion app.
- [ ] Unload/removal behavior is documented and tested; no user-owned dashboard is deleted implicitly.
- [ ] Optional panel is accessible, responsive, localized and correctly removed/updated.
- [ ] Safe mode behavior is documented: Home Assistant does not load custom dashboard resources in safe mode.
- [ ] Frontend localization and accessibility verified separately.

**Important evidence boundary:** Official docs confirm static serving and manual resource registration. They do **not** by themselves establish a stable public API for automatic modification of Lovelace's storage resources from custom integrations. We must validate that API against current HA Core and integration examples before promising zero-click card registration.

**Next research:** Home Assistant frontend \`hass\` object/language contract, current Lovelace resource registration API and its storage-vs-YAML semantics; official backup/storage/Recorder guidance for the database architecture decision.



## 12. Approved frontend decision and living official-source registry (2026-11-05)

### ADR-UI-001 — One custom sidebar panel, no Lovelace card

**Status:** APPROVED by project owner, 2026-11-05. **Supersedes** earlier proposals to support both a Lovelace card and sidebar panel.

**Decision:** The only PlayStation Hub user interface will be a **full-page custom panel**, registered by the custom integration and accessible from the Home Assistant sidebar. The integration remains a single HACS Integration; its frontend is shipped with the Python code in one GitHub Release.

**Why:** One consistent user experience, one responsive UI, one navigation model, one localization implementation, and one release/update lifecycle. No separate custom Lovelace card registration, no \`window.customCards\` metadata, no Lovelace resource management for our own card, and no second dashboard distribution category.

**Direct official evidence:**
- https://contributors.home-assistant.io/frontend/custom-ui/panel/ — custom panels are full-page components with sidebar links and \`hass\`, \`narrow\`, \`route\`, \`panel\` properties; Python integrations can register them using \`panel_custom.async_register_panel\`.
- https://contributors.home-assistant.io/frontend/architecture/routing-and-panels/ — custom panels are different from built-in panels; use the custom-panel mechanism for a frontend not bundled into Home Assistant.
- https://contributors.home-assistant.io/frontend/custom-ui/ — panel and card are separate frontend extension types; a custom panel loads via its own registration rather than Lovelace resource registration.
- https://contributors.home-assistant.io/blog/2026/07/31/frontend-component-updates-2026.8/ — safe-area handling for custom panels and companion apps.
- https://contributors.home-assistant.io/blog/2026/10/28/frontend-component-updates-2026.11/ — theme backgrounds for all panels and recent component removals; avoid coupling to unstable internal \`ha-*\` UI elements.

**Proposed runtime package:**

\`\`\`text
custom_components/playstation_hub/
├── __init__.py
├── manifest.json
├── config_flow.py
├── const.py
├── translations/
│   ├── en.json
│   └── pt.json
└── frontend/
    ├── playstation-hub-panel.js
    ├── components/
    ├── views/
    ├── services/
    ├── styles/
    └── i18n/
\`\`\`

**Panel lifecycle design:**
1. Serve only packaged frontend assets via the supported async static-path API.
2. Register **one** custom panel globally, not once per PlayStation console or config entry.
3. Use the Home Assistant custom-panel registration API, checking its actual signature for the supported Core versions; do not use the built-in panel registration API.
4. Use the \`hass\` property for current Home Assistant state, \`narrow\` for responsive behavior, \`route\` for internal navigation, and \`panel.config\` for non-secret static panel configuration.
5. Support desktop, tablet and Home Assistant companion apps, including safe areas and keyboard navigation.
6. Reuse UI modules internally; a single public UI does **not** imply a monolithic JavaScript file.
7. Make registration idempotent, prevent duplicate sidebar entries, test reload/unload and cleanup, and version frontend assets with the Python release.
8. Do not delete or overwrite any existing user Lovelace dashboard during installation or removal.
9. Keep all UI strings localizable. The frontend translation mechanism must be tested independently of Home Assistant backend translation catalogs.

**Project acceptance gates:**
- [ ] One sidebar item appears after successful integration setup.
- [ ] No manual Lovelace resource registration is required.
- [ ] No PlayStation Hub custom card is distributed.
- [ ] Panel loads with multiple consoles and without duplicating the sidebar item.
- [ ] Panel displays usable empty/unavailable states.
- [ ] Unload/removal/restart/update behavior is deterministic and documented.
- [ ] Responsive layouts, safe areas, theming, accessibility and language switching are tested.
- [ ] A single GitHub Release upgrades backend and frontend together.

**Scope correction to earlier guide:** DOC-022's Lovelace resource-registration discussion remains historical reference only. The card-specific acceptance gates in DOC-022 are **superseded** by ADR-UI-001. The current frontend target is the custom-panel route in DOC-024.

### DOC-027 — Home Assistant: Custom panels (decision verification)

- **Official source:** https://contributors.home-assistant.io/frontend/custom-ui/panel/
- **Reviewed:** 2026-11-05
- **Findings:** Custom panel is a full-screen web component; Python registration through \`panel_custom.async_register_panel\`; modern \`module_url\` is supported; panel receives \`hass\`, \`narrow\`, \`route\`, \`panel\`; the panel owns its page layout and mobile sidebar access.
- **Important:** A panel does not automatically become a Lovelace dashboard and does not require maintaining a Lovelace card.
- **Unresolved:** Exact current API call arguments, idempotent removal, asset caching, supported HA version and automated UI testing remain implementation gates.

### DOC-028 — Home Assistant: Frontend custom UI extension types

- **Official source:** https://contributors.home-assistant.io/frontend/custom-ui/
- **Reviewed:** 2026-11-05
- **Findings:** Cards, strategies, views and panels are separate extension types. Panels are loaded by their own registration. Frontend internal \`ha-*\` elements are not guaranteed stable public APIs.
- **Decision:** Use the custom panel only, and prefer self-contained, documented UI dependencies rather than importing undocumented HA frontend internals.

### Official documentation registry — permanent maintenance contract

**Decision:** This guide must preserve **all consulted official documentation URLs** and provide enough metadata for future re-review. Never silently discard or replace old source links when URLs move. Record the new canonical URL and the previous URL, the date, what changed and which architecture rules are affected.

For each source entry, maintain:
- Stable ID (DOC-###), official title, canonical URL and publisher.
- Date reviewed and page last-updated date if actually visible.
- Scope: whole page, specific section, or reference only.
- Status: verified, needs re-review, superseded, moved, unavailable, or not yet read.
- Exact relevant requirement IDs, project decisions and verification/test evidence.
- Dependencies: other official pages needed to interpret the requirement.
- Next review trigger: significant HA/HACS update, deprecation notice, failed CI, API migration, or release preparation.

**Source-of-truth precedence:**
1. Current official Home Assistant/HACS docs and current supported public APIs.
2. Current official source code for API behavior when documentation is ambiguous.
3. Tests against the supported Home Assistant version.
4. Our historical notes and earlier architecture decisions, which must be updated when superseded.

**Review discipline:**
- Documentation links and project decisions are separate fields. Never label a voluntary policy as an official requirement.
- Preserve historical entries but mark outdated advice **SUPERSEDED** at its original location where practical.
- Do not claim all official documentation is read: maintain an explicit backlog.
- At every planned release, revisit all P0 sources and every document marked stale or moved.
- Keep the index within this root guide for discoverability; a future machine-readable \`docs/official-sources.json\` can be generated once its schema is agreed, but must not diverge from this guide.

**Already recorded:** DOC-001 through DOC-028, plus the grouped reading list in section 6. Their URLs and review notes remain in this document. Some DOC entries are focused re-reviews of previously consulted pages; document count is **not** a count of distinct URLs.

**Next source research:** The current \`panel_custom.async_register_panel\` signature, safe panel unregister behavior, frontend asset caching and lifecycle across config entry reload, and frontend locale selection. These are implementation questions not yet proven by this guide.



## 13. Verified Home Assistant Core custom-panel API — source inspection (2026-11-05)

**Review method:** Read the official Home Assistant Core implementation of \`panel_custom\` and relevant current Core usages. This is a source-code API review, **not** an installation or runtime test. These are moving \`dev\` branch sources; before implementing, compare against the **supported Home Assistant release tag**.

### DOC-029 — Home Assistant Core: panel_custom implementation

- **Canonical source:** https://github.com/home-assistant/core/blob/dev/homeassistant/components/panel_custom/__init__.py
- **Reviewed:** 2026-11-05
- **Official source:** Home Assistant Core (Python implementation).
- **Confirmed async API:** \`panel_custom.async_register_panel\`.

The inspected function has the following parameters:

\`\`\`python
async def async_register_panel(
    hass: HomeAssistant,
    frontend_url_path: str,
    webcomponent_name: str,
    sidebar_title: str | None = None,
    sidebar_icon: str | None = None,
    js_url: str | None = None,
    module_url: str | None = None,
    embed_iframe: bool = False,
    trust_external: bool = False,
    config: ConfigType | None = None,
    require_admin: bool = False,
    config_panel_domain: str | None = None,
) -> None:
    ...
\`\`\`

**Contract observations:**
1. At least one of \`js_url\` or \`module_url\` must be provided; the source raises \`ValueError\` otherwise. Prefer \`module_url\` for modern JavaScript.
2. \`config\` must be a dictionary when supplied; it is copied before modification.
3. The implementation adds \`_panel_custom\` metadata and delegates registration to \`frontend.async_register_built_in_panel\` with \`component_name="custom"\`. **Our code should call \`panel_custom.async_register_panel\` rather than invoking the built-in panel registration directly.**
4. The inspected signature does **not** contain \`handle_safe_area\` or \`update\`. Do not copy arguments from other integration examples without verifying their exact supported Core version.
5. \`config_panel_domain\` is described for panels used to configure an integration; our analytics panel is not necessarily such a configuration panel. Do not set it automatically.
6. A globally fixed \`frontend_url_path\` and \`webcomponent_name\` should be used across all config entries; do not create a panel for each console.

**Proposed registration sketch (NOT deployed):**

\`\`\`python
from homeassistant.components import panel_custom

await panel_custom.async_register_panel(
    hass,
    frontend_url_path="playstation-hub",
    webcomponent_name="playstation-hub-panel",
    module_url="/playstation_hub/frontend/playstation-hub-panel.js?v=0.1.0",
    sidebar_title="PlayStation Hub",
    sidebar_icon="mdi:sony-playstation",
    require_admin=False,
)
\`\`\`

The URL and version are illustrative. The icon name, static path, sidebar authorization and exact supported Core API must be verified during implementation.

### DOC-030 — Home Assistant Core: panel removal and URL collision behavior

- **Sources:**
  - https://github.com/home-assistant/core/blob/dev/homeassistant/components/hassio/addon_panel.py
  - https://github.com/home-assistant/core/blob/dev/homeassistant/components/lovelace/__init__.py
  - https://github.com/home-assistant/core/blob/dev/homeassistant/components/frontend/__init__.py
- **Reviewed:** 2026-11-05
- **Confirmed current usage:** Core integrations use \`frontend.async_remove_panel(hass, url_path, warn_if_unknown=False)\` to remove panel registrations.
- **Collision behavior:** The Lovelace implementation checks for panel URL collisions and logs failures; panel paths are shared with other Home Assistant panels. A chosen \`frontend_url_path\` must not conflict with an existing panel.
- **Idempotence:** Core's Supervisor panel management reconciles desired and registered panel sets. We should follow this lifecycle principle rather than registering blindly for each config entry.
- **Important nuance:** \`panel_custom.async_register_panel\` itself does not expose an \`update\` argument in the inspected version. Do not claim a direct idempotent update facility on this API.

### Proposed lifecycle architecture — project decision, not official implementation

1. Register the static frontend route and custom panel once per Home Assistant process, after the first successful PlayStation Hub config entry setup.
2. Keep a single integration-wide panel manager; separate per-console runtime data from the global UI registration.
3. On subsequent config entries, reuse the existing panel; do not call \`async_register_panel\` again.
4. On removal/unload of the last active config entry, determine whether panel removal is appropriate; ensure no dangling registration, and avoid breaking other entries.
5. On reload/update, reconcile registration carefully and do not overwrite unrelated panels sharing the same path.
6. Handle failure atomically: if static route registration or panel registration fails, do not report the integration as fully ready.
7. Use a deterministic, release-versioned frontend module URL. Test cache invalidation in browser and companion app.
8. Register only assets intended to be publicly served. No credentials, SQLite or runtime private state in frontend static directories.
9. Validate UI availability for non-admin users separately from backend action permissions.

### Acceptance tests required before first release

- [ ] Panel registers once with one configured console.
- [ ] Second configured console does not duplicate the sidebar entry.
- [ ] Repeated setup, reload and restart do not raise a panel URL collision.
- [ ] Last-entry unload/removal follows the documented panel lifecycle.
- [ ] Integration setup failure does not leave a broken sidebar panel.
- [ ] Existing unrelated dashboard/panel with a colliding URL is not overwritten.
- [ ] JS module is served with the expected release version and refreshed on update.
- [ ] Panel works for administrator and non-administrator users according to configured policy.
- [ ] Responsive UI respects mobile safe areas, localization and Home Assistant themes.
- [ ] Tests run against a **pinned supported HA Core version**, not only the moving \`dev\` branch.

**Remaining uncertainties:** Static-path unregistration and URL replacement semantics, compatibility with future Home Assistant versions, and browser-side module reload behavior require live tests. No API stability guarantee follows merely from inspecting the Core source.

**Next investigation:** Home Assistant \`StaticPathConfig\` registration details and release-tag compatibility, then data storage and backup APIs.


## 14. Recorder, history and long-term statistics — official documentation review (2026-11-05)

**Scope:** Three official Home Assistant documentation pages and one official architecture page reviewed for storage suitability. This section does **not** settle our database architecture or claim that the full Home Assistant storage/backup documentation has been reviewed.

### DOC-031 — Recorder integration

- **Official source:** https://www.home-assistant.io/integrations/recorder/
- **Reviewed:** 2026-11-05
- Recorder persists Home Assistant entity state changes and events; History, Activity, graphs and statistics rely on it.
- Default database is SQLite, named \`home-assistant_v2.db\` in the HA configuration directory. Recorder also supports MariaDB, MySQL and PostgreSQL.
- \`purge_keep_days\` defaults to **10**; old detailed states/events are purged automatically.
- Retention settings apply to Recorder's scope, **not to PlayStation Hub's detailed per-game ledger alone**.
- Recorder supports entity/domain include and exclude filtering; users can opt out of recording our entities.
- **Project rule:** Do not create custom tables or directly write to Home Assistant's Recorder database. It is managed by Home Assistant.
- **Consequence:** Recorder is valuable for standard Home Assistant sensors, but its ordinary detailed state history is not a reliable sole source for indefinite per-game sessions.

### DOC-032 — Long-term statistics

- **Official source:** https://www.home-assistant.io/docs/configuration/long-term-statistics/
- **Reviewed:** 2026-11-05
- Long-term statistics are computed for eligible **numeric sensors** with a \`state_class\`, provided they are recorded.
- Short-term summaries are generated every five minutes and normally purged with detailed history.
- Long-term hourly summaries are retained without automatic expiry.
- Statistics support aggregated measurements/totals, not arbitrary per-session records with player identity, title ID, artwork, session start/end and checkpoints.
- **Project rule:** Use correct sensor state classes and Recorder statistics for eligible Home Assistant-facing metrics, but do not assume long-term statistics can reconstruct the complete PlayStation session ledger.

### DOC-033 — History integration

- **Official source:** https://www.home-assistant.io/integrations/history
- **Reviewed:** 2026-11-05
- History reads from Recorder and can export selected data to CSV.
- Beyond detailed Recorder retention, eligible sensor history is displayed from long-term hourly statistics.
- Increasing \`purge_keep_days\` to preserve full-resolution history affects the Recorder database for the wider Home Assistant installation, not just our integration.
- **Project rule:** Do not require users to change global Recorder retention to preserve PlayStation Hub history.

### DOC-034 — Home Assistant architecture: History and statistics

- **Official source:** https://contributors.home-assistant.io/architecture/core/history/
- **Reviewed:** 2026-11-05
- Recorder writes in its own thread, protecting the Home Assistant event loop.
- Frequent/large entity attributes increase database storage; avoid publishing a full game library or extensive session history as sensor attributes.
- **Project rule:** Expose compact operational entities and suitable statistics; serve detailed history from our own bounded-query interface when required.

### Storage decision update — ADR-DATA-001 (provisional)

**Recommendation:** A **single application-owned SQLite database** for PlayStation Hub's durable, detailed event/session/game history, with multiple consoles and players distinguished by stable IDs in normalized tables. Use native Config Entries for setup, native Store for small configuration/checkpoint data where suitable, and Recorder for appropriate Home Assistant-facing numeric sensors. CSV/JSON remain export formats, not primary transaction stores.

**Status:** PROVISIONAL. Not yet approved for implementation. This is a project inference from the documented Recorder retention and statistics behavior, **not** an official Home Assistant mandate to use SQLite.

**Rationale:** PlayStation Hub requires arbitrary multi-year detailed queries, individual session boundaries, per-game rankings, player associations and replayable events. Recorder's default 10-day detailed retention and hourly numeric summaries do not preserve that full data model.

**Do not assume:** The current private SQLite backup or its schema is the future public schema. We will design the new schema from scratch with migrations and multi-console support.

**Before approval, investigate separately:**
1. Official \`homeassistant.helpers.storage.Store\` behavior and appropriate use for small durable state.
2. Home Assistant configuration path APIs and whether a dedicated integration data directory is covered by supported backup/restore workflows.
3. Supported async/non-blocking database access patterns, transaction serialization, SQLite WAL/locking and recovery.
4. Safe retention, export/import, migration, downgrade policy and corruption recovery.
5. Data deletion on config entry removal versus keeping shared history, with explicit user-facing policy.
6. Performance benchmarks with three years of representative sessions and multiple consoles.
7. Privacy, diagnostics redaction, encryption expectations and user backup controls.

### Acceptance criteria

- [x] Recorder's detailed retention and statistics limits recorded from official documentation.
- [x] Explicitly prohibit direct writes to Recorder's internal schema.
- [x] Distinguish native HA metrics from PlayStation Hub's own detailed session ledger.
- [ ] Verify native Store and backup coverage in dedicated official-source reviews.
- [ ] Create an architecture decision record with benchmark and migration evidence.
- [ ] Approve database path, schema, multi-console keys and backup semantics before implementation.

**Next official-source priority:** Home Assistant Store helper and integration backup/restore behavior.


## 15. Native Store and backup evidence review (2026-11-05)

**Scope and confidence:** Reviewed the official Home Assistant developer article about \`Store\` and the current Core \`homeassistant/helpers/storage.py\` source location. The previously listed \`https://developers.home-assistant.io/docs/core/backup/\` did **not** resolve during this review. Consequently **no claim is made that an arbitrary custom SQLite file is automatically included in Home Assistant backups**. Backup compatibility remains an unresolved release blocker.

### DOC-035 — Generic Store helper

- **Official article:** https://developers.home-assistant.io/blog/2022/07/08/generic-store/
- **Official implementation:** https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/storage.py
- **Reviewed:** 2026-11-05
- The article establishes \`Store(Generic[T])\` and recommends typing the stored data as JSON-serializable dictionaries/lists or a \`TypedDict\`.
- Documented pattern: \`Store[Preferences](hass, STORAGE_VERSION, STORAGE_KEY)\`, where \`Preferences\` is a suitable JSON-serializable type.
- The Store helper is a reasonable candidate for **small, versioned, JSON-serializable state**. The article does **not** establish that it is appropriate for arbitrarily large, frequently updated session ledgers.
- Implementation is part of Home Assistant Core and can evolve. Inspect the supported release tag and test async load/save, schema evolution, concurrent writes and shutdown behavior before relying on specific implementation details.
- **Project decision:** Use Config Entries for integration setup/options; consider \`Store\` only for small durable metadata/checkpoints where necessary, not automatically for multi-year detailed history.
- **Security:** No secrets in public exports or diagnostics; \`.storage\` is private Home Assistant runtime state, not a repository asset.

### DOC-036 — Backup documentation link audit (unresolved)

- **Previously proposed URL:** https://developers.home-assistant.io/docs/core/backup/
- **Status:** Unavailable / not verified during this review.
- **Reviewed:** 2026-11-05
- **Result:** Do not infer backup coverage from this broken URL. Find and validate the current official backup developer docs, supported HA backup APIs and backup inclusion behavior for custom integration data in a later source review.
- **Required tests:** Create a Home Assistant backup on a disposable instance, restore it into another disposable instance, and verify that integration configuration, panel registration, history database and schema migrations survive.
- **Explicit prohibition:** Do not state that \`hass.config.path(...)\` or placing a SQLite file in the configuration directory **guarantees** inclusion in every backup type. Coverage must be verified for the actual supported HA installation and backup mechanism.

### ADR-DATA-001 — updated decision status

**Still PROVISIONAL.** A dedicated application-owned SQLite remains the preferred candidate for durable, multi-year per-session history; it must not be implemented until the following are verified:

1. Supported configuration/data path and actual backup coverage.
2. Safe asynchronous database access and serialized writes without blocking HA's event loop.
3. Multi-console, multi-player schema and migration strategy.
4. SQLite consistency, WAL handling, corruption recovery, retention and import/export.
5. Uninstall/removal policy that does not silently delete history.
6. Reproducible backup/restore and upgrade tests.

**Next official documentation research:** Locate current Home Assistant backup developer documentation and verify custom integration storage backup semantics. Then review current Core \`Store\` APIs against a supported release tag.

## 16. Official backup scope and asynchronous persistence — verified review (2026-11-05)

**Scope:** Four official pages. This review resolves the previously missing backup documentation reference, but does not prove application-consistent backup of a live SQLite file.

### DOC-037 — Home Assistant common tasks: backup and restore
- **Source:** https://www.home-assistant.io/common-tasks/general/
- **Reviewed:** 2026-11-05.
- **Direct official finding:** Full backups include config, share, addons (locally installed apps), ssl, and media. Partial backups include selected directories and apps.
- **Implication:** A PlayStation Hub-owned SQLite file stored under the Home Assistant configuration directory is within the documented config scope of a full backup. A partial backup excluding config does not cover it.
- **Critical limitation:** File inclusion does not guarantee a transactionally consistent backup while SQLite is being written, especially when WAL is enabled. This must be tested.
- **Official guidance:** Keep backups regularly, including a copy outside the Home Assistant device and ideally off-site. Restore may overwrite selected configuration.

### DOC-038 — Backup integration
- **Source:** https://www.home-assistant.io/integrations/backup
- **Reviewed:** 2026-11-05.
- **Direct official finding:** Backup supports all Home Assistant installation types and provides backup.create and backup.create_automatic actions.
- **Project consequence:** Do not require a Supervisor-specific backup mechanism or a separate app for normal PlayStation Hub operation.
- **Limitation:** The page does not specify a hook for quiescing third-party SQLite files during backups.

### DOC-039 — Blocking operations with asyncio
- **Source:** https://developers.home-assistant.io/docs/asyncio_blocking_operations/
- **Reviewed:** 2026-11-05.
- **Direct official finding:** Blocking I/O must not execute on the Home Assistant event loop. The official integration helper is hass.async_add_executor_job.
- **Direct official warning:** Moving only the file open operation to an executor is insufficient; reads and writes must also be moved.
- **Project requirement:** All synchronous SQLite open, query, commit, backup and filesystem work must execute off-loop. Entity properties must not perform database I/O.
- **Engineering option, not official mandate:** Use a serialized database worker with bounded queries and an explicit shutdown lifecycle.
- **Test:** Enable Home Assistant asyncio debug and check for blocking-operation warnings.

### DOC-040 — Thread safety with asyncio
- **Source:** https://developers.home-assistant.io/docs/asyncio_thread_safety/
- **Reviewed:** 2026-11-05.
- **Direct official finding:** Many Home Assistant async APIs must be called on the event-loop thread; their non-async counterparts or scheduled callbacks are used from executor threads.
- **Specific example:** hass.config_entries.async_update_entry must execute on the event-loop thread.
- **Project requirement:** SQLite worker threads may not directly mutate Home Assistant entities, registries, config entries or asyncio objects. Schedule results safely back onto the event loop.
- **Test:** Concurrent source updates, unload/reload and shutdown must not produce thread-safety errors.

### ADR-DATA-001 — Updated recommendation, still provisional

**Preferred candidate:** One application-owned SQLite database under the Home Assistant configuration directory, outside the HACS-managed integration code directory, with normalized multi-console/player/session data and serialized off-loop I/O.

**Evidence:** The official backup guide includes config in full backups; Recorder detailed state retention does not provide the required arbitrary multi-year session ledger; Home Assistant async guidance forbids blocking database operations on the event loop.

**Before approval:**
1. Choose the path using supported Home Assistant configuration APIs and verify permissions on all supported installation types.
2. Inspect a real full backup and a partial backup, then restore to an isolated instance.
3. Verify SQLite consistency during backup, including WAL handling; implement a safe standalone export using SQLite backup facilities.
4. Benchmark multi-year queries, migrations and multiple-console writes.
5. Specify schema versioning, recovery, retention and non-destructive removal behavior.
6. Keep SQLite files and exports out of GitHub and the HACS integration package.

**Status:** Proposed, not implemented or recovery-tested. DOC-036's old URL remains documented as unavailable; DOC-037 provides the verified replacement for directory coverage.

**Next official review:** Supported Home Assistant configuration-path APIs and database concurrency patterns, then a storage architecture decision record.
