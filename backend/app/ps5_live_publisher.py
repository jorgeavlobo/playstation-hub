"""
PS5 Monitoring Service - Live MQTT State Publisher.

Publish confirmed PlayStation live-state snapshots through
a dedicated background worker.

Responsibilities:
    - Keep MQTT publication outside network callbacks.
    - Serialize all live-state publications.
    - Coalesce rapid observation updates.
    - Publish explicit unavailable states.
    - Detect observation expiration.
    - Support graceful shutdown.
    - Prevent overlapping worker threads.

The publisher does not modify SQLite or session accounting.
"""

from __future__ import annotations

import json
import logging
import threading
import time

from typing import Any, Callable

from ps5_live_state import PS5LiveState


LOGGER = logging.getLogger(__name__)

LIVE_STATE_TOPIC = "ps5-monitor/live/state"

LIVE_STATE_QOS = 1
LIVE_STATE_RETAIN = True

DEFAULT_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_SHUTDOWN_TIMEOUT_SECONDS = 15.0


class PS5LivePublisher:
    """
    Publish live-state snapshots using one background thread.

    The worker never maintains an unbounded message queue.

    Every publication obtains a fresh snapshot from the
    live-state tracker, allowing intermediate updates
    to be coalesced safely.
    """

    def __init__(
        self,
        publisher: Any,
        live_state: PS5LiveState,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
        shutdown_timeout_seconds: float = DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
        transport_available: Callable[[], bool] | None = None,
    ) -> None:
        """Initialize the live-state publication worker."""

        if not isinstance(live_state, PS5LiveState):
            raise TypeError(
                "Expected a PS5LiveState instance."
            )

        if poll_interval_seconds <= 0:
            raise ValueError(
                "Polling interval must be positive."
            )

        if shutdown_timeout_seconds <= 0:
            raise ValueError(
                "Shutdown timeout must be positive."
            )

        self._publisher = publisher
        self._live_state = live_state

        # The transport predicate must be inexpensive and
        # must never perform blocking network operations.
        self._transport_available = (
            transport_available
            if transport_available is not None
            else lambda: True
        )

        self._retry_delay = 1.0
        self._retry_deadline = 0.0
        self._maximum_retry_delay = 30.0

        self._poll_interval = poll_interval_seconds
        self._shutdown_timeout = shutdown_timeout_seconds

        self._lock = threading.RLock()

        self._wake_event = threading.Event()
        self._stop_event = threading.Event()

        self._thread: threading.Thread | None = None

        self._last_payload: str | None = None
        self._last_published_generation: int | None = None

        # Track MQTT publication epochs independently from
        # observation generations.
        self._publication_epoch = 0
        self._published_epoch = -1

    def start(self) -> None:
        """
        Start the publication worker.

        Starting an already active worker is rejected.
        A worker that has completely stopped may restart.
        """

        with self._lock:
            if (
                self._thread is not None
                and self._thread.is_alive()
            ):
                raise RuntimeError(
                    "Live-state publisher is already running."
                )

            self._stop_event.clear()
            self._wake_event.clear()

            self._last_payload = None
            self._retry_delay = 1.0
            self._retry_deadline = 0.0
            self._last_published_generation = None

            self._thread = threading.Thread(
                target=self._run,
                name="ps5-live-state-publisher",
                daemon=False,
            )

            self._thread.start()

    def notify(self) -> None:
        """
        Signal that the live-state snapshot may have changed.

        This operation is non-blocking and safe to call from
        an MQTT callback after observation persistence.
        """

        with self._lock:
            if (
                self._thread is None
                or not self._thread.is_alive()
                or self._stop_event.is_set()
            ):
                return

            self._wake_event.set()

    def request_republish(self) -> None:
        """
        Request publication after MQTT reconnection.

        This method is safe to call from an MQTT callback
        because it performs no network operations.

        The worker remains responsible for serialized
        QoS 1 publication.
        """

        with self._lock:
            # A confirmed reconnection permits an immediate retry.
            self._retry_delay = 1.0
            self._retry_deadline = 0.0
            self._publication_epoch += 1
            self._last_payload = None

            if (
                self._thread is not None
                and self._thread.is_alive()
                and not self._stop_event.is_set()
            ):
                self._wake_event.set()

    def _publish_snapshot(self) -> bool:
        """
        Publish the latest snapshot when it has changed.

        Returns:
            True if a publication was performed successfully.
            False if the serialized payload is unchanged.

        Publication failures propagate to the worker loop.
        """

        snapshot = self._live_state.snapshot()

        payload = json.dumps(
            snapshot.to_dict(),
            separators=(",", ":"),
            ensure_ascii=False,
        )

        with self._lock:
            epoch = self._publication_epoch

            if (
                payload == self._last_payload
                and self._published_epoch == epoch
            ):
                return False

        # MQTT QoS 1 publication waits for broker acknowledgement.
        # This method executes only on the dedicated worker thread.
        self._publisher.publish(
            LIVE_STATE_TOPIC,
            payload,
            qos=LIVE_STATE_QOS,
            retain=LIVE_STATE_RETAIN,
        )

        with self._lock:
            # An acknowledgement from an older connection must
            # never mark the current epoch as published.
            if epoch == self._publication_epoch:
                self._last_payload = payload
                self._last_published_generation = (
                    snapshot.generation
                )
                self._published_epoch = epoch

        return True

    def _run(self) -> None:
        """
        Publish live snapshots with bounded retry backoff.

        Ordinary notifications may wake the worker, but
        they cannot bypass the monotonic retry deadline.
        """

        LOGGER.info("PS5 live-state publisher started.")

        while not self._stop_event.is_set():
            now = time.monotonic()

            with self._lock:
                retry_deadline = self._retry_deadline

            if now < retry_deadline:
                wait_seconds = min(
                    self._poll_interval,
                    retry_deadline - now,
                )

            else:
                wait_seconds = self._poll_interval

                try:
                    if self._transport_available():
                        self._publish_snapshot()

                        with self._lock:
                            self._retry_delay = 1.0
                            self._retry_deadline = 0.0

                except Exception:
                    LOGGER.exception(
                        "Failed to publish PS5 live state."
                    )

                    with self._lock:
                        delay = self._retry_delay

                        self._retry_deadline = (
                            time.monotonic() + delay
                        )

                        self._retry_delay = min(
                            delay * 2,
                            self._maximum_retry_delay,
                        )

                    wait_seconds = min(
                        self._poll_interval,
                        delay,
                    )

            self._wake_event.wait(
                timeout=max(0.001, wait_seconds)
            )
            self._wake_event.clear()

        LOGGER.info("PS5 live-state publisher stopped.")

    def stop(self) -> None:
        """
        Stop the worker and wait for its termination.

        A timeout prevents shutdown from proceeding while
        a publication thread may still be using MQTT.
        """

        with self._lock:
            thread = self._thread

            if thread is None:
                return

            self._stop_event.set()
            self._wake_event.set()

        if thread is threading.current_thread():
            raise RuntimeError(
                "Live-state publisher cannot join itself."
            )

        thread.join(timeout=self._shutdown_timeout)

        if thread.is_alive():
            raise TimeoutError(
                "Live-state publisher did not stop safely."
            )

        with self._lock:
            if self._thread is thread:
                self._thread = None

    @property
    def running(self) -> bool:
        """Return whether the worker thread is active."""

        with self._lock:
            return (
                self._thread is not None
                and self._thread.is_alive()
                and not self._stop_event.is_set()
            )

    @property
    def last_published_payload(self) -> dict | None:
        """
        Return a copy of the last acknowledged live-state payload.

        The result represents the latest publication accepted
        by the MQTT publishing interface.
        """

        with self._lock:
            if self._last_payload is None:
                return None

            return json.loads(self._last_payload)

    @property
    def last_published_generation(self) -> int | None:
        """Return the last successfully published generation."""

        with self._lock:
            return self._last_published_generation
