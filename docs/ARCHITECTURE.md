# Architecture — current installed project

This document describes the current working **Home Assistant App + Lovelace** implementation. It does not pre-decide migration to `custom_components`.

```text
PS5 -> PS5-MQTT -> Mosquitto -> Python monitoring app -> SQLite
                                 |                        |
                                 +-> MQTT discovery       +-> live/history MQTT
                                         |                       |
                                         +------> Home Assistant +
                                                    |
                                              Lovelace card
```

- Backend at `/addons/ps5_monitor/`
- Frontend at `/config/www/ps5-dashboard/`
- Dashboard configuration at `/config/.storage/lovelace.dashboard_ps5`
- App database at `/data/ps5_monitor.db` inside the container
- Current backend version: `0.5.0`
- Current frontend version: `1.1.2`

The existing application uses installation-specific player names, PS5-MQTT device topics, and historic entity IDs. These must be made configurable before a general-purpose release.

The original ZIP remains private, including the fictitious database and deployment settings.
