# PlayStation Hub — Architecture & Standards Guide

> **Status:** Planning / living specification  
> **Document version:** 0.10.0 — 2026-11-05  
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

**Next official document proposed (not yet reviewed):** https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/ — the rules index, then each rule individually.
