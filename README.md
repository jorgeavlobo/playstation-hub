# PlayStation Hub

PlayStation monitoring, analytics and control for Home Assistant.

> **Development stage.** This repository is not yet a Home Assistant Marketplace integration. The final architecture (Supervisor App/add-on or custom integration) has not been selected.

## Existing implementation

The private operational snapshot dated 5 November 2026 contains:
- Python Home Assistant App backend (v0.5.0) with MQTT discovery, sessions and SQLite historical storage.
- Custom Lovelace dashboard card (v1.1.2).
- Automated tests for both components.
- Private HA configuration, application backups and a fictitious SQLite database.

The private snapshot **must never be published**. A sanitized source-only review package has been prepared separately. No source has been deployed from this repository.

## Development plan

1. Audit and transfer the sanitized backend and frontend source code to the `develop` branch.
2. Fix the failing backend history-worker test and verify all dependencies.
3. Make hardware identity, player attribution and Home Assistant entity mapping configurable.
4. Decide the distribution architecture.
5. Create reproducible packaging and release instructions.
6. Submit a compatible integration to Marketplace only if the chosen architecture supports it.

## Testing (after source import)

```bash
python -m pip install -r backend/requirements.txt
cd backend
PYTHONPATH=app python -m unittest discover -s tests -v
```

```bash
cd frontend
node --test tests/*.test.mjs
```

The snapshot's 80 frontend tests pass locally. The Python test suite still requires verification with `paho-mqtt` installed and includes a reproducible mismatch in the history-worker test.

## Security

Never commit authentication options, SQLite databases, personal console identifiers, Home Assistant `.storage`, archived backups, or the private snapshot.
