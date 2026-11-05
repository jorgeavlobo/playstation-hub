"""
PS5 Monitoring Service - Live Console State.

Maintain the latest confirmed PlayStation observation and
expose a time-bounded snapshot for dashboard publication.

This module does not communicate with MQTT or SQLite.

A confirmed observation is only accepted after the session
tracker has successfully processed and persisted it.

Monotonic time is used to determine observation freshness.
UTC timestamps are used for informational metadata only.
"""

from __future__ import annotations

import threading
import time

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from models import ConsolePower, PS5State


DEFAULT_LIVE_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class LiveStateSnapshot:
    """Represent a validated dashboard live-state snapshot."""

    power: str
    activity: str
    console_active: bool
    player_gaming: bool
    available: bool
    observed_at: str | None
    title_id: str | None
    title_name: str | None
    title_image: str | None
    generation: int

    def to_dict(self) -> dict:
        """Return a JSON-compatible snapshot."""

        return {
            "schema_version": 1,
            "power": self.power,
            "activity": self.activity,
            "console_active": self.console_active,
            "player_gaming": self.player_gaming,
            "available": self.available,
            "observed_at": self.observed_at,
            "title_id": self.title_id,
            "title_name": self.title_name,
            "title_image": self.title_image,
            "generation": self.generation,
        }


class PS5LiveState:
    """
    Track confirmed console observations independently of MQTT.

    A snapshot becomes unavailable when its observation expires
    or when the monitoring connection is explicitly invalidated.
    """

    def __init__(
        self,
        player_name: str,
        timeout_seconds: float = DEFAULT_LIVE_TIMEOUT_SECONDS,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the live-state tracker."""

        if not player_name:
            raise ValueError("Player name must not be empty.")

        if timeout_seconds <= 0:
            raise ValueError("Live-state timeout must be positive.")

        self._player_name = player_name
        self._timeout_seconds = timeout_seconds
        self._clock = monotonic_clock

        self._lock = threading.RLock()

        self._state: PS5State | None = None
        self._received_monotonic: float | None = None
        self._generation = 0

        # Shutdown freezing is irreversible for this instance.
        # A new application lifecycle creates a new tracker.
        self._frozen = False

    def observe(self, state: PS5State) -> None:
        """
        Accept a confirmed and persisted console observation.

        Call this method only after the session tracker has
        successfully accepted the observation.
        """

        if not isinstance(state, PS5State):
            raise TypeError("Expected a PS5State observation.")

        with self._lock:
            if self._frozen:
                raise RuntimeError(
                    "Live-state tracker is frozen."
                )

            self._state = state
            self._received_monotonic = self._clock()
            self._generation += 1

    def freeze(self) -> None:
        """
        Permanently invalidate live state during shutdown.

        This operation is atomic relative to observe().
        Once frozen, subsequent observations are rejected.
        """

        with self._lock:
            if self._frozen:
                return

            self._frozen = True
            self._state = None
            self._received_monotonic = None
            self._generation += 1

    @property
    def frozen(self) -> bool:
        """Return whether shutdown freezing is active."""

        with self._lock:
            return self._frozen

    def invalidate(self) -> None:
        """
        Invalidate the current observation.

        Used after MQTT disconnection, watchdog expiration,
        or failed observation persistence.
        """

        with self._lock:
            self._state = None
            self._received_monotonic = None
            self._generation += 1

    def snapshot(self) -> LiveStateSnapshot:
        """
        Return the latest valid live-state snapshot.

        Expired observations are never reported as current.
        """

        with self._lock:
            state = self._state
            received_at = self._received_monotonic

            fresh = (
                state is not None
                and received_at is not None
                and 0 <= self._clock() - received_at
                < self._timeout_seconds
            )

            if not fresh:
                return LiveStateSnapshot(
                    power=ConsolePower.UNKNOWN.value,
                    activity="unknown",
                    console_active=False,
                    player_gaming=False,
                    available=False,
                    observed_at=None,
                    title_id=None,
                    title_name=None,
                    title_image=None,
                    generation=self._generation,
                )

            return LiveStateSnapshot(
                power=state.power.value,
                activity=state.activity.value,
                console_active=state.console_active,
                player_gaming=state.player_is_gaming(
                    self._player_name
                ),
                available=True,
                observed_at=state.observed_at.astimezone(
                    timezone.utc
                ).isoformat(),
                title_id=state.title_id,
                title_name=state.title_name,
                title_image=state.title_image,
                generation=self._generation,
            )
