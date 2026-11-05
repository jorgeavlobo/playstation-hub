"""
PS5 Monitoring Service - Live Monitoring Lifecycle.

Coordinate final live-state publication and worker shutdown.

The coordinator does not own the MQTT connection, SQLite
database, or session tracker.

The caller must prevent new console observations before
initiating shutdown.

A successful return guarantees that the final unavailable
snapshot was acknowledged by the publication worker and
that the worker thread has terminated.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable

from ps5_live_state import PS5LiveState
from ps5_live_publisher import PS5LivePublisher


@dataclass(frozen=True, slots=True)
class LiveShutdownResult:
    """
    Describe the outcome of coordinated live-state shutdown.

    confirmed indicates that the final unavailable snapshot
    was acknowledged by the publication worker.
    """

    confirmed: bool
    degraded: bool
    reason: str


class PS5LiveLifecycle:
    """
    Coordinate safe shutdown of live monitoring components.

    MQTT transport shutdown must occur only after this
    coordinator completes successfully.
    """

    def __init__(
        self,
        live_state: PS5LiveState,
        publisher: PS5LivePublisher,
        timeout_seconds: float = 15.0,
        transport_available: Callable[[], bool] | None = None,
    ) -> None:
        """Initialize the lifecycle coordinator."""

        if not isinstance(live_state, PS5LiveState):
            raise TypeError(
                "Expected a PS5LiveState instance."
            )

        if not isinstance(publisher, PS5LivePublisher):
            raise TypeError(
                "Expected a PS5LivePublisher instance."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "Shutdown timeout must be positive."
            )

        self._live_state = live_state
        self._publisher = publisher
        self._timeout_seconds = timeout_seconds

        # The transport predicate must be inexpensive and
        # must not perform network operations.
        self._transport_available = (
            transport_available
            if transport_available is not None
            else lambda: True
        )

        self._lock = threading.RLock()
        self._shutdown_started = False

    def shutdown(self) -> LiveShutdownResult:
        """
        Freeze live state, publish UNKNOWN, and stop the worker.

        The caller must first activate the MQTT observation
        shutdown barrier.

        Publication failure produces a degraded result only
        when the publication worker terminates safely.
        """

        with self._lock:
            if self._shutdown_started:
                raise RuntimeError(
                    "Live monitoring shutdown already started."
                )

            if not self._publisher.running:
                raise RuntimeError(
                    "Live publisher must be running during shutdown."
                )

            self._shutdown_started = True

        # Permanently prevent fresh observations from restoring
        # a console state after shutdown has started.
        self._live_state.freeze()

        final_generation = (
            self._live_state.snapshot().generation
        )

        self._publisher.notify()

        deadline = (
            time.monotonic() + self._timeout_seconds
        )

        confirmed = False

        while time.monotonic() < deadline:
            payload = self._publisher.last_published_payload

            if (
                payload is not None
                and payload.get("generation") == final_generation
                and payload.get("available") is False
                and payload.get("power") == "UNKNOWN"
                and self._publisher.last_published_generation
                    == final_generation
            ):
                confirmed = True
                break

            # A disconnected transport cannot acknowledge
            # another publication until connectivity returns.
            if not self._transport_available():
                break

            time.sleep(0.02)

        # Worker termination is mandatory regardless of the
        # final publication outcome. A blocked worker raises
        # TimeoutError and prevents unsafe MQTT disconnection.
        self._publisher.stop()

        if confirmed:
            return LiveShutdownResult(
                confirmed=True,
                degraded=False,
                reason="Final unavailable state acknowledged.",
            )

        return LiveShutdownResult(
            confirmed=False,
            degraded=True,
            reason="Final unavailable state not confirmed.",
        )
