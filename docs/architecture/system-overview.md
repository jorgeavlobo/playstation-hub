# System overview

**Status:** Architecture planning — 2026-11-05.

PlayStation Hub is one HACS custom integration and one GitHub Release containing native Home Assistant Python code and a single multilingual custom sidebar panel.

## Logical components

1. LAN discovery/status transport.
2. Optional Remote Play pairing, wake and standby transport.
3. Optional PSN authentication and presence adapter.
4. State fusion with freshness and explicit uncertainty.
5. Multi-console/player domain and session tracking.
6. Dedicated persistence and native HA entities/actions.
7. One responsive sidebar frontend.

No PS5-MQTT, Mosquitto, Node.js or separate App is required by design. External protocol libraries remain subject to licensing and security review.

## Open architectural decisions

- Final storage path, SQLite consistency and backup/restore behavior.
- Multi-console config-entry boundaries and PSN account association.
- Exact Python transport contracts and supported console generations.
- Supported minimum Home Assistant release and frontend registration lifecycle.

See [protocol index](../protocols/README.md) and [architecture guide](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md).
