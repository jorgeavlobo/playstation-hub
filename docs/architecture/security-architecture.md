# Security architecture

**Status:** Planning — 2026-11-05.

## Threat model and controls

Assets: Remote Play pairing keys, PSN access/refresh tokens, account IDs, console identity, history, and local network access.

- Explicit consent and pairing for authenticated operations.
- Do not embed credentials in frontend bundles, logs, diagnostics, fixtures or repository history.
- Keep secrets in appropriately protected Home Assistant storage, not mutable code directories.
- Distinguish LAN-only from PSN-enhanced capabilities and make unlink/revoke possible.
- Validate packet sizes, formats, destinations, network timeouts and replay/freshness.
- Use audited cryptographic primitives; do not invent cryptography.
- Require Home Assistant permissions for power-control actions.
- Review source licenses and Sony service terms before release.

**Open:** precise secret storage API, key rotation, authorization model and any private PSN endpoint restrictions.

See [protocol index](../protocols/README.md).

## PSN credential and browser-authentication research — 2026-11-05

**Classification:** Research / proposed controls, not implemented.

- NPSSO, access tokens, refresh tokens, OAuth authorization codes and relevant browser cookies are bearer-secret material. Never place them in URLs, logs, events, diagnostics, frontend local storage, example screenshots, test fixtures or shared exports.
- Sony account password, passkeys and two-factor challenges are handled exclusively by the Sony login experience. The HA integration must not impersonate a Sony login form.
- The provider-authorized OAuth registration, scopes, embedded mobile-app client ownership and redirect URI remain a release **BLOCKER** for any PSN authentication based on the community flow. A community implementation does not establish permission to reuse another client's OAuth credentials.
- Same-origin browser rules prevent Home Assistant JavaScript from reading Sony pages/cookies automatically unless Sony explicitly provides a compatible browser/redirect integration. The psn-mcp Chrome DevTools example controls its own local browser process and does not establish viability for remote HA OS panels.
- **Design direction:** PSN credential handling is backend-only and per-account. Use serialized/single-flight refresh, generation checks, bounded retries, immediate durable storage of rotated tokens, and reauthentication on confirmed invalid credentials. Avoid monkey patches affecting other HA integrations.
- Config entries / HA Store are persistence mechanisms, **not automatically an encrypted secrets vault**. Select and review secret storage, file permissions, backup inclusion, recovery, removal and key management before implementation.
- Official HA documentation says backups are encrypted by default, but their encryption/configuration can vary by location and export. Backup encryption is not the same as runtime at-rest token encryption. Restored credentials can be stale or revoked due to remote token rotation.
- A remote token rotation and a local storage transaction cannot be made atomic together. A crash after remote rotation but before local durable commit may require reauthentication; history must remain intact.
- Token-only updates should not trigger a complete integration reload. Authenticated account identity must be checked on reauth; multiple accounts must remain isolated.
- Account unlink should remove locally held secrets and stop refresh tasks; remote Sony token revocation is not established and must not be promised.

**References:** [Protocol 08](../protocols/08-psn-authentication.md); [Home Assistant backups](https://www.home-assistant.io/common-tasks/general/backups); [Emkraan refresh guard](https://github.com/Emkraan/homeassistant-playstationnetwork/blob/main/custom_components/playstation_network/compat.py); [PSNAWP authentication source](https://github.com/isFakeAccount/psnawp/blob/master/src/psnawp_api/core/authenticator.py).
