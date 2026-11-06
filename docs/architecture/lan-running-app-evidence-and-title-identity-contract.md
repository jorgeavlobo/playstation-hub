# PlayStation Hub — LAN running-application evidence and title-identity contract

**Date:** 2026-11-06
**Status:** PROPOSED DOMAIN CONTRACT / NOT APPROVED AS IMPLEMENTATION / NO LIVE FIRMWARE VALIDATION
**Research:** [LAN title identity, foreground evidence and game/provider boundaries](../research/lan-running-app-identity-foreground-and-provider-boundary-2026-11-06.md)
**Inputs:** [First-party dependency sovereignty](first-party-dependency-sovereignty-policy.md), Protocols 01/02/09/10, ADR-0004/0005/0006/0020/0021, SPEC-004/021.
**Architecture:** Native Home Assistant integration; only own protocol logic; Python stdlib and supported HA APIs; no third-party PlayStation runtime packages, no on-console ELF/payload, no MQTT, and no required PSN account.

## 1. Purpose and explicit non-goals

Define the **minimal honest data contract** for what a physical PlayStation reports as its running application in a DDP discovery response.

The contract can support a first-party **LAN-only current application label** even if no Sony account is authorized, and can preserve source evidence for later uncertainty-aware history. It **does not establish** exact foreground focus, the person using a controller, game-playing time, installed library, ownership, purchase, or Sony PSN authentication.

## 2. Orthogonal source dimensions (proposed)

| Dimension | Logical field / value space | No hidden assumption |
| --- | --- | --- |
| Physical console | \`verified_console_owner_key?\` plus \`reported_host_id\` | Self-reported host-id is not proof of hardware ownership |
| Network | \`source_endpoint\`, \`source_generation\`, \`received_at_utc_us\` | UDP has no proven echoed per-request ID |
| Physical power | \`READY | STANDBY | UNKNOWN\` | READY is not active foreground game |
| App title ID field | \`ABSENT | EMPTY | VALUE | INVALID\` + raw bounded string | ABSENT is not "no app" or Home |
| App display name field | Independent \`ABSENT | EMPTY | VALUE | INVALID\` + bounded string | Name is not stable identity |
| App key | \`source=LAN_DDP\`, \`raw_id\`, \`namespace\` and source platform hint | PS4 title may run on a PS5 |
| Semantic class | \`UNKNOWN | POSSIBLE_GAME | POSSIBLE_MEDIA | POSSIBLE_SYSTEM\` | Prefix is only a heuristic; preserve OTHER |
| Freshness | \`FRESH | STALE | SOURCE_UNAVAILABLE\`, local policy | Unchanged UI does not equal a fresh sample |
| Foreground evidence | \`NOT_AVAILABLE\` for ordinary DDP | Loaded/paused game may appear behind Home |
| Player evidence | \`NOT_AVAILABLE\` for ordinary DDP | Do not attach Sony account automatically |
| Interval coverage | \`POINT_ONLY | BOUNDED_REPORTED_APP | UNKNOWN\` | Bounded reported-app is NOT human gameplay |
| PSN enrichments | \`UNLINKED | CANDIDATE | VERIFIED_CROSSWALK\` | Provider IDs and local title IDs require independent mapping |

**Strict scope:** Source-scoped title ID is the authoritative *identity of the reported ID*, not a claim that it corresponds to a particular commercial product/game edition beyond its evidence. The logical key \`(source_namespace, raw_source_id)\` should retain optional platform/source qualifiers where required to avoid collisions; names and covers never become unique keys.

## 3. Recommended immutable observation record

\`\`\`text
LocalApplicationObservation (proposed interface, NOT executable code):
  source_kind = LAN_DDP_RUNNING_APP
  console_owner_key?              # Verified owner if available; otherwise candidate only
  reported_host_id                # Untrusted DDP field; never direct credential principal
  source_run_id
  scan_window_id                  # Local metadata, no on-wire nonce
  received_at_utc_us
  temporal_quality                # WINDOW_ASSOCIATED_UNVERIFIED, etc.
  power_report                   # READY, STANDBY, UNKNOWN
  app_id_field                    # {presence, raw, namespace_hint, normalized_search?}
  app_name_field                  # {presence, raw, sanitized_label, encoding_quality}
  app_classification             # UNKNOWN/POSSIBLE_GAME/POSSIBLE_MEDIA/POSSIBLE_SYSTEM
  foreground_evidence = NOT_AVAILABLE
  player_evidence = NOT_AVAILABLE
  source_version/adapter_version
  accepted_digest/observation_id
\`\`\`

No mandatory new table, code module or field type is authorized by this sketch. ADR-0020's logical \`observations\` plus optional metadata may carry this as typed sanitized source evidence, subject to physical schema and privacy/replay review.

## 4. Conservative reducer policy for application labels

- First valid ID/name creates a **point sample** and optional display label with \`as_of\` timestamp; **zero duration**.
- Two identical, compatible, verified-owner app IDs with an independently approved max continuity budget and no source break may create **bounded reported-app coverage**, never an exact gameplay measurement. The title-specific budget is NOT implicitly equal to physical console AWAKE B.
- Distinct IDs at successive points give an **uncertain transition bracket**; no automatic assignment of entire bracket to either game.
- Same ID with changed name is a metadata revision or source conflict, not automatically a different game session. Same display name with different ID is a distinct title observation.
- App field \`ABSENT\` after a previous \`VALUE\` expires/fences **title assertion**, not proof of title closed. Chiaki's cache clears the field on absence, but that is an internal cache replacement choice.
- App field \`EMPTY\` is a literal observation only if that firmware/decoder profile considers a present-but-empty header valid. May mean no app reported, **not automatically known Home foreground**.
- If status is reported STANDBY, do not earn game time through the boundary even if stale title metadata survives. Current app becomes STALE/UNKNOWN as appropriate.
- Timeout/unknown status/old UDP datagram after a restarted listener stops earning reported-app coverage. Last known title may remain visible with timestamp and explicit stale status.
- Source entity state change notifications can be deduplicated for UI, but accepted identical point samples must still reach evidence history.
- PSN provider title (including last-used platform or lifetime hours) never overwrites LAN title or creates a physical owner/player link automatically.
- A user's explicit manual mapping is USER_DECLARED with audit, not Sony/device-confirmed crosswalk or proof of player time.
- Deleting/changing a game artwork/name does not alter historical application source identities or interval confidence.

## 5. Identifier namespaces and versioning

Preserve source IDs as opaque strings. Recognize known families for convenience only:
- PS4-format \`CUSA\` (may occur on PS5 via backward compatibility).
- PS5-format \`PPSA\`; community registry also describes some non-PPSA regional families, so a PPSA-only allowlist is invalid.
- \`NPXS\` for possible system applications, not necessarily human gameplay.
- Other \`ECAS\`, \`ELAS\`, \`ELJM\`, \`PLAS\`, \`PCAS\`, unknown future formats; never reject solely because prefix is unfamiliar.

Store original ID exactly (subject to size/character safety). Do not mutate \`PPSA-XXXXX\` into \`PPSAXXXXX\` or casefold arbitrary Unicode by default. A validated, namespace-specific ASCII normalized search form can coexist with raw source ID. Product \`conceptId\`, \`contentId\`, \`npTitleId\` and \`productId\` remain provider-scoped; no undocumented numeric or name-based crosswalk is allowed.

**Crosswalk contract:**
- \`UNRESOLVED\`: only raw LAN title key.
- \`USER_DECLARED\`: manually linked game concept; not source proof.
- \`PROVIDER_CANDIDATE\`: a source-supplied relation whose validity/permission remains to be checked.
- \`SOURCE_VERIFIED\`: only when an independently trusted mapping mechanism is demonstrated and documented.
- \`CONFLICT\`: disagreeing source mapping retained and surfaced, not last-write-wins.

A game *concept* can relate to multiple PS4/PS5 editions, regions, product IDs and DLC, but the physical observation remains attached to the actual received application identifier.

## 6. Suggested UI and report semantics

| UI display | Trigger | Label and caution |
| --- | --- | --- |
| Current reported app | Fresh accepted READY + ID/name field VALUE | "Console reports: <title>" and \`last_seen\`; not "player is playing" |
| No current app assertion | Both app fields absent/invalid | "Application unknown"; optionally last known with timestamp |
| Explicit empty app field | Accepted empty header for validated firmware | "No application reported" (not proven Home) |
| Physical standby | Fresh valid 620 | "Standby"; previous title last-known and stale |
| Provider account title | Optional authorized PSN | "PSN account reports: <title>" separately |
| Reported-app history | Only if separately approved continuity model | "Estimated console-reported application time" with coverage/unknown |
| Actual playing time | Not supported by ordinary DDP | Do not offer exact player gameplay minutes |
| Metadata enrichment | Separately verified source/title crosswalk | Cover/artwork/locale can change without rewriting source history |

Source strings must be rendered as text, not interpolated into unsanitized HTML; no title string may be assumed harmless merely because it came from LAN. Artwork is optional and subject to URL validation/SSRF/privacy/license rules, without bundling a provider SDK or a CDNs-required frontend.

## 7. What would resolve the remaining uncertainty?

**Physical retail-console fixture matrix (future, NOT_RUN):** PS5 awake with games home, foreground native PPSA game, PS4 CUSA game, Home while game remains loaded, switch between games, media app, system app, rest mode, PSN offline, no account linked; capture DDP header presence/name/ID and compare with direct visible console behavior. Record firmware model/version, exact packet grammar, local clock, source IP/host ID and observation uncertainty without publicizing household identifiers.

**Why we cannot solve foreground purely by more literature:** Sony officially states some games/apps pause under the Home screen. The [PS Game State Lib](https://github.com/StonedModder/ps-game-state-lib/tree/963a0e256ab32090143d44dc7964551aca70ed77) uses console-side process/controller-focus evidence to separate active from suspended. It requires an ELF loader/payload on the PS5, which conflicts with this project's ordinary, no-additional-console-component requirement. It is research evidence, NOT a dependency or recommended installation. Until another supported passive source is verified, active foreground and user playtime remain UNKNOWN.

## 8. Future test traces — no new SPEC numbering

Refer to [research LAT-01–LAT-24](../research/lan-running-app-identity-foreground-and-provider-boundary-2026-11-06.md#8-future-validation-matrix--all-not_run) in existing SPEC-001/004/021. Required invariants: missing!=empty, no Home inference without verified cue, app changes bracketed, ID namespace preserved, PSN separate, 0 duration at first sample, no source gap extrapolation, no cross-console first-awake assignment, no payload/third-party libraries and no alleged human gameplay minutes.

**Not implemented / no tests run:** This contract is a design artifact and an explicit statement of limits. It is not Sony protocol documentation, not a released entity, not a production database and not an authorization to write implementation code.
