# ADR-0001 — First-party PlayStation connectivity

**Status:** Accepted design direction — 2026-11-05.

## Context

The previous PS5 Monitor used PS5-MQTT and a broker to obtain already normalized PlayStation state. The new project should install as one Home Assistant custom integration.

## Decision

Implement our own Home Assistant-facing LAN and optional Remote Play/PSN adapters. Do not require PS5-MQTT, Mosquitto, Node.js or another App at runtime. Vetted Python libraries are allowed after audit.

## Consequences

More protocol maintenance, testing and credential-handling responsibility. LAN-only monitoring remains useful without PSN. Sony endpoint availability and terms remain open.

## Evidence

See [protocol index](../protocols/README.md) and the historical [architecture guide](https://github.com/jorgeavlobo/playstation-hub/blob/main/ARCHITECTURE_GUIDE.md).
