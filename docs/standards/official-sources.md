# Official sources and external references

**Status:** Living index — 2026-11-05.

The canonical historical source register (DOC-001 through DOC-080) remains in [ARCHITECTURE_GUIDE.md](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md). Protocol-specific external source URLs appear in [docs/protocols](../protocols/README.md).

## Official documentation roots

- https://www.hacs.xyz/
- https://www.hacs.xyz/docs/use/
- https://www.hacs.xyz/docs/publish/
- https://www.hacs.xyz/docs/contribute/
- https://developers.home-assistant.io/
- https://contributors.home-assistant.io/
- https://www.home-assistant.io/

## Maintenance policy

Record title, canonical URL, publisher, reviewed date, source revision, evidence status, decisions, and change triggers. Never present third-party reverse-engineered code as official Sony documentation. Preserve moved URLs and mark superseded advice.

## Current quality, runtime and Marketplace source set — 2026-11-05

The [second official-source review](../research/official-source-reaudit-batch-02-quality-discovery-runtime-2026-11.md) inventories 29 official source entries (with one network-discovery cross-reference) and 22 prioritized findings. The [54-rule internal applicability matrix](internal-quality-scale-applicability.md) maps all 20 Bronze, 10 Silver, 21 Gold and 3 Platinum Core Quality Scale rules without claiming a formal tier for this custom Marketplace integration.

**Canonical current source categories:**
- https://contributors.home-assistant.io/core/quality-scale/rules/ — current rules
- https://contributors.home-assistant.io/core/integrations/discovery/ — DHCP/config flow ownership
- https://contributors.home-assistant.io/core/integrations/network-discovery/ — shared network services
- https://contributors.home-assistant.io/core/integrations/fetching-data/ — coordinator, cache and parallelism
- https://contributors.home-assistant.io/core/quality-scale/runtime-data/ — typed per-entry runtime
- https://contributors.home-assistant.io/core/quality-scale/action-exceptions/ — typed user/device errors
- https://contributors.home-assistant.io/core/integrations/diagnostics/ — redaction and test snapshots
- https://contributors.home-assistant.io/core/integrations/system-health/ — loaded entries only
- https://contributors.home-assistant.io/core/integrations/reauth-reconfigure/ — separate flows
- https://contributors.home-assistant.io/marketplace/reference/validation/ — install-time limits and checks

**Version boundary:** The current online docs may evolve; verify exact API behavior against pinned Core 2026.11.0 source and retest after supported release upgrades. An audited official rule is not automatically applicable to a Marketplace custom project or proof of test completion.
