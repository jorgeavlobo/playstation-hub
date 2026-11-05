"""
PS5 Monitoring Service - Home Assistant MQTT Publisher.

This module builds MQTT Discovery configurations and statistical
state payloads for Home Assistant.

Responsibilities:
    - Define stable Home Assistant entity identifiers.
    - Build MQTT Discovery configuration payloads.
    - Convert confirmed usage durations into decimal hours.
    - Publish statistics through an injected MQTT client.
    - Avoid hardcoded MQTT credentials.
    - Keep reporting independent from session accounting.

The publisher does not create its own MQTT connection.
The application must provide a connected MQTT client.

Historical monthly data is published as JSON attributes.
The dashboard integration will be implemented separately.
"""

import json
import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from ps5_history_index import PS5HistoryIndex
from usage_statistics import StatisticsService, LOCAL_TIMEZONE
from game_library_payload import build_game_library_payload


LOGGER = logging.getLogger(__name__)

DISCOVERY_PREFIX = "homeassistant"
STATE_PREFIX = "ps5-monitor"
DEVICE_IDENTIFIER = "ps5_monitoring_service"


class MQTTClientProtocol(Protocol):
    """Minimal MQTT publishing interface."""

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
    ) -> Any:
        """Publish an MQTT message."""


@dataclass(frozen=True)
class SensorDefinition:
    """Describe one Home Assistant MQTT sensor."""

    key: str
    name: str
    unit: str | None = None
    icon: str | None = None


SENSORS = (
    SensorDefinition(
        "console_today",
        "PS5 Console Today",
        "h",
        "mdi:clock-outline",
    ),
    SensorDefinition(
        "console_week",
        "PS5 Console This Week",
        "h",
        "mdi:calendar-week",
    ),
    SensorDefinition(
        "console_month",
        "PS5 Console This Month",
        "h",
        "mdi:calendar-month",
    ),
    SensorDefinition(
        "gaming_today",
        "PS5 Player Gaming Today",
        "h",
        "mdi:controller-classic",
    ),
    SensorDefinition(
        "gaming_week",
        "PS5 Player Gaming This Week",
        "h",
        "mdi:controller-classic",
    ),
    SensorDefinition(
        "gaming_month",
        "PS5 Player Gaming This Month",
        "h",
        "mdi:controller-classic",
    ),
    SensorDefinition(
        "monthly_sessions",
        "PS5 Player Monthly Sessions",
        None,
        "mdi:counter",
    ),
    SensorDefinition(
        "top_game",
        "PS5 Player Top Game",
        None,
        "mdi:trophy",
    ),
    SensorDefinition(
        "history",
        "PS5 Player Annual History",
        None,
        "mdi:chart-bar",
    ),
    SensorDefinition(
        "game_library",
        "PS5 Player Game Library",
        None,
        "mdi:gamepad-variant",
    ),
)


def seconds_to_hours(seconds: float) -> float:
    """Convert seconds into decimal hours."""

    return round(max(0.0, seconds) / 3600.0, 3)


class StatisticsPublisher:
    """
    Publish Home Assistant MQTT Discovery and statistics.

    The MQTT connection is injected to simplify testing and
    avoid duplicate network connections.
    """

    def __init__(
        self,
        client: MQTTClientProtocol,
        statistics: StatisticsService,
    ) -> None:
        """Initialize the publisher."""

        self._client = client
        self._statistics = statistics

    @staticmethod
    def discovery_topic(key: str) -> str:
        """Return the MQTT Discovery configuration topic."""

        return (
            f"{DISCOVERY_PREFIX}/sensor/"
            f"{DEVICE_IDENTIFIER}/{key}/config"
        )

    @staticmethod
    def state_topic(key: str) -> str:
        """Return the MQTT state topic."""

        return f"{STATE_PREFIX}/{key}/state"

    @staticmethod
    def attributes_topic(key: str) -> str:
        """Return the MQTT attributes topic."""

        return f"{STATE_PREFIX}/{key}/attributes"

    @staticmethod
    def discovery_payload(
        sensor: SensorDefinition,
    ) -> dict:
        """Build a Home Assistant MQTT Discovery payload."""

        payload = {
            "name": sensor.name,
            "unique_id": f"ps5_monitor_{sensor.key}",
            "state_topic": StatisticsPublisher.state_topic(
                sensor.key
            ),
            "availability_topic": (
                f"{STATE_PREFIX}/availability"
            ),
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": {
                "identifiers": [DEVICE_IDENTIFIER],
                "name": "PS5 Monitoring Service",
                "manufacturer": "Custom",
                "model": "PS5 Historical Monitor",
            },
        }

        if sensor.unit is not None:
            payload["unit_of_measurement"] = sensor.unit

        if sensor.icon is not None:
            payload["icon"] = sensor.icon

        if sensor.key in ("history", "game_library"):
            payload["json_attributes_topic"] = (
                StatisticsPublisher.attributes_topic(
                    sensor.key
                )
            )

        return payload

    def publish_discovery(self) -> None:
        """
        Register all configured sensors with Home Assistant.

        Discovery configurations are retained so Home Assistant
        can rediscover entities after an MQTT reconnect.
        """

        for sensor in SENSORS:
            payload = self.discovery_payload(sensor)

            result = self._client.publish(
                self.discovery_topic(sensor.key),
                json.dumps(payload),
                qos=1,
                retain=True,
            )

            if getattr(result, "rc", 0) != 0:
                raise RuntimeError(
                    f"Discovery publication failed: {sensor.key}"
                )

        LOGGER.info(
            "Published discovery for %d sensors.",
            len(SENSORS),
        )

    def build_statistics(
        self,
        now: datetime | None = None,
    ) -> dict:
        """
        Build the current statistical snapshot.

        Calendar calculations use Europe/Lisbon.
        Durations are based on persisted confirmed sessions.
        """

        reference = now or datetime.now(LOCAL_TIMEZONE)
        local_now = reference.astimezone(LOCAL_TIMEZONE)
        today = local_now.date()

        daily = self._statistics.today(today)
        weekly = self._statistics.current_week(today)
        monthly = self._statistics.month(
            today.year,
            today.month,
        )

        # Use the month boundaries supplied by the statistics
        # module instead of assuming a fixed number of days.
        from usage_statistics import next_month

        month_start = today.replace(day=1)

        games = self._statistics.games(
            month_start,
            next_month(month_start),
        )

        history = self._statistics.last_twelve_months(
            today
        )

        top_game = games[0].title_name if games else "None"

        return {
            "console_today": seconds_to_hours(
                daily.console_seconds
            ),
            "console_week": seconds_to_hours(
                weekly.console_seconds
            ),
            "console_month": seconds_to_hours(
                monthly.console_seconds
            ),
            "gaming_today": seconds_to_hours(
                daily.gaming_seconds
            ),
            "gaming_week": seconds_to_hours(
                weekly.gaming_seconds
            ),
            "gaming_month": seconds_to_hours(
                monthly.gaming_seconds
            ),
            "monthly_sessions": monthly.gaming_sessions,
            "top_game": top_game,
            "history": "ready",
            "game_library": "ready",
            "game_library_attributes": build_game_library_payload(
                period=month_start.strftime("%Y-%m"),
                games=games,
            ),
            "history_attributes": {
                "months": [
                    {
                        "month": item.period_start[:7],
                        "console_hours": seconds_to_hours(
                            item.console_seconds
                        ),
                        "gaming_hours": seconds_to_hours(
                            item.gaming_seconds
                        ),
                        "gaming_sessions": item.gaming_sessions,
                    }
                    for item in history
                ]
            },
        }


    def publish_history_index(
        self,
        now: datetime | None = None,
    ) -> dict:
        """
        Publish the compact 36-month historical activity index.

        The index uses the existing confirmed statistics
        service and shares the current MQTT connection.

        This method is independent of regular statistics
        publication and can be scheduled separately.

        The publication is retained so that new subscribers
        can immediately receive the latest historical index.
        """

        reference = now or datetime.now(LOCAL_TIMEZONE)
        local_now = reference.astimezone(LOCAL_TIMEZONE)

        summaries = self._statistics.last_thirty_six_months(
            reference_day=local_now.date(),
        )

        index = PS5HistoryIndex().build(summaries)

        payload = json.dumps(
            index,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

        result = self._client.publish(
            "ps5-monitor/history/index",
            payload,
            qos=1,
            retain=True,
        )

        if getattr(result, "rc", 0) != 0:
            raise RuntimeError(
                "Historical activity index publication failed."
            )

        return index

    def publish_statistics(
        self,
        now: datetime | None = None,
    ) -> dict:
        """
        Publish current statistics to Home Assistant.

        The method returns the snapshot for diagnostics.

        State messages are retained so that Home Assistant
        can restore the latest published values after restart.
        """

        snapshot = self.build_statistics(now)

        for sensor in SENSORS:
            value = snapshot[sensor.key]

            result = self._client.publish(
                self.state_topic(sensor.key),
                str(value),
                qos=1,
                retain=True,
            )

            if getattr(result, "rc", 0) != 0:
                raise RuntimeError(
                    f"State publication failed: {sensor.key}"
                )

        result = self._client.publish(
            self.attributes_topic("history"),
            json.dumps(snapshot["history_attributes"]),
            qos=1,
            retain=True,
        )

        if getattr(result, "rc", 0) != 0:
            raise RuntimeError(
                "Historical attributes publication failed."
            )

        # Game Library attributes are optional dashboard data.
        # A publication failure must not invalidate the core
        # monitoring statistics already published successfully.
        try:
            result = self._client.publish(
                self.attributes_topic("game_library"),
                json.dumps(
                    snapshot["game_library_attributes"],
                    separators=(",", ":"),
                    ensure_ascii=False,
                ),
                qos=1,
                retain=True,
            )

            if getattr(result, "rc", 0) != 0:
                raise RuntimeError(
                    "Game library attributes publication failed."
                )

        except Exception:
            LOGGER.exception(
                "Unable to publish Game Library attributes. "
                "Publication will be retried on the next update."
            )

        return snapshot
