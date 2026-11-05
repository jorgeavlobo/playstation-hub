"""
PS5 Monitoring Service - Domain Models.

This module defines the immutable data structures used throughout
the monitoring service.

Design principles:
    - All timestamps are timezone-aware UTC datetimes.
    - Sessions use half-open intervals: [started_at, ended_at).
    - Console usage and player gaming are independent session types.
    - Unknown or missing information must never be treated as
      confirmed activity.
    - Database identifiers are independent of MQTT identifiers.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class SessionType(StrEnum):
    """Supported monitoring session categories."""

    CONSOLE = "console"
    GAMING = "gaming"


class ConsolePower(StrEnum):
    """Normalized PlayStation power states."""

    AWAKE = "AWAKE"
    STANDBY = "STANDBY"
    OFF = "OFF"
    UNKNOWN = "UNKNOWN"


class ActivityType(StrEnum):
    """Normalized PlayStation activity states."""

    PLAYING = "playing"
    IDLE = "idle"
    NONE = "none"
    UNKNOWN = "unknown"


class EventType(StrEnum):
    """Types of events recorded by the monitoring service."""

    STATE_UPDATE = "state_update"
    CONNECTION_LOST = "connection_lost"
    CONNECTION_RESTORED = "connection_restored"
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    """
    Validate and normalize a datetime to UTC.

    Naive timestamps are rejected to prevent accidental timezone
    interpretation errors.
    """

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must be timezone-aware.")

    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class PS5State:
    """
    Normalized state received from the PS5 MQTT integration.

    Attributes:
        power: Current console power state.
        device_status: Network/device availability status.
        activity: Current PSN activity.
        players: Active PSN player identifiers.
        title_id: Current game identifier, when available.
        title_name: Current game title, when available.
        title_image: Current game artwork URL, when available.
        observed_at: Time when this service received the state.
    """

    power: ConsolePower
    device_status: str
    activity: ActivityType
    players: tuple[str, ...]
    title_id: str | None
    title_name: str | None
    title_image: str | None
    observed_at: datetime

    def __post_init__(self) -> None:
        """Validate the timestamp and normalize player identifiers."""

        object.__setattr__(
            self,
            "observed_at",
            ensure_utc(self.observed_at),
        )

        object.__setattr__(
            self,
            "players",
            tuple(self.players),
        )

    @property
    def console_active(self) -> bool:
        """Return whether the console is confirmed awake and online."""

        return (
            self.power == ConsolePower.AWAKE
            and self.device_status.lower() == "online"
        )

    def player_is_gaming(self, player_name: str) -> bool:
        """
        Return whether the requested player is actively gaming.

        Player identifiers are matched exactly to avoid attributing
        another account's activity to the monitored player.
        """

        return (
            self.console_active
            and self.activity == ActivityType.PLAYING
            and player_name in self.players
        )


@dataclass(frozen=True, slots=True)
class MonitoringEvent:
    """An event stored in the monitoring event log."""

    event_type: EventType
    occurred_at: datetime
    payload: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Require a timezone-aware event timestamp."""

        object.__setattr__(
            self,
            "occurred_at",
            ensure_utc(self.occurred_at),
        )


@dataclass(frozen=True, slots=True)
class UsageSession:
    """
    A completed or ongoing monitoring session.

    An open session has ended_at=None.

    A gaming session may contain player and game information.
    Console sessions do not require these fields.
    """

    session_type: SessionType
    started_at: datetime
    ended_at: datetime | None = None
    player_name: str | None = None
    title_id: str | None = None
    title_name: str | None = None
    title_image: str | None = None
    session_id: int | None = None

    def __post_init__(self) -> None:
        """Validate session timestamps and required gaming fields."""

        start = ensure_utc(self.started_at)
        object.__setattr__(self, "started_at", start)

        if self.ended_at is not None:
            end = ensure_utc(self.ended_at)

            if end < start:
                raise ValueError(
                    "Session end cannot precede session start."
                )

            object.__setattr__(self, "ended_at", end)

        if (
            self.session_type == SessionType.GAMING
            and not self.player_name
        ):
            raise ValueError(
                "Gaming sessions require a player identifier."
            )

    @property
    def duration_seconds(self) -> float | None:
        """
        Return the completed session duration in seconds.

        Open sessions return None because their final duration
        has not yet been established.
        """

        if self.ended_at is None:
            return None

        return (
            self.ended_at - self.started_at
        ).total_seconds()
