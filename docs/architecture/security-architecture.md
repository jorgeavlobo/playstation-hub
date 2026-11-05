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
