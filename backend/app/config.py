import os
"""
PS5 Monitoring Service - Configuration Management.

This module loads, validates, and exposes the application
configuration supplied by Home Assistant Supervisor.

All configuration values are immutable after initialization.
Sensitive credentials must never be written to application logs.
"""

from dataclasses import dataclass
from pathlib import Path
import json


# The privileged entrypoint creates a protected temporary copy
# of the Supervisor configuration before dropping privileges.
#
# The original Supervisor options file remains unchanged.
# A configurable path also supports isolated integration tests.
CONFIG_PATH = Path(
    os.environ.get(
        "PS5_MONITOR_CONFIG_PATH",
        "/data/options.json",
    )
)


@dataclass(frozen=True)
class AppConfig:
    """
    Immutable application configuration.

    Attributes:
        mqtt_host: MQTT broker hostname.
        mqtt_port: MQTT broker TCP port.
        mqtt_username: MQTT authentication username.
        mqtt_password: MQTT authentication password.
        mqtt_topic: MQTT topic containing PS5 state messages.
        player_name: PSN player name to monitor.
        database_path: Persistent SQLite database location.
    """

    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_topic: str
    player_name: str
    database_path: Path


def load_config() -> AppConfig:
    """
    Load and validate configuration from Home Assistant Supervisor.

    Returns:
        A validated, immutable AppConfig instance.

    Raises:
        FileNotFoundError:
            When the Supervisor configuration file is missing.

        ValueError:
            When a required configuration value is invalid.
    """

    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        options = json.load(file)

    required_fields = (
        "mqtt_host",
        "mqtt_port",
        "mqtt_username",
        "mqtt_password",
        "mqtt_topic",
        "player_name",
        "database_path",
    )

    for field in required_fields:
        if field not in options:
            raise ValueError(
                f"Missing required configuration field: {field}"
            )

    for field in (
        "mqtt_host",
        "mqtt_username",
        "mqtt_password",
        "mqtt_topic",
        "player_name",
        "database_path",
    ):
        if not isinstance(options[field], str) or not options[field].strip():
            raise ValueError(
                f"Configuration field must be a non-empty string: {field}"
            )

    port = options["mqtt_port"]

    if isinstance(port, bool) or not isinstance(port, int):
        raise ValueError("MQTT port must be an integer.")

    if not 1 <= port <= 65535:
        raise ValueError("MQTT port must be between 1 and 65535.")

    database_path = Path(options["database_path"])

    if not database_path.is_absolute():
        raise ValueError("Database path must be absolute.")

    if not database_path.is_relative_to(Path("/data")):
        raise ValueError(
            "Database must be stored inside the persistent /data directory."
        )

    return AppConfig(
        mqtt_host=options["mqtt_host"],
        mqtt_port=port,
        mqtt_username=options["mqtt_username"],
        mqtt_password=options["mqtt_password"],
        mqtt_topic=options["mqtt_topic"],
        player_name=options["player_name"],
        database_path=database_path,
    )
