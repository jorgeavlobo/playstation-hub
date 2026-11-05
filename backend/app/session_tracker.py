"""
PS5 Monitoring Service - Transactional Session Tracker.

This module coordinates PS5 observations and database persistence.

Responsibilities:
    - Accept validated, fresh PS5 observations.
    - Reject observations older than the last accepted timestamp.
    - Delegate session accounting to one atomic database operation.
    - Recover interrupted sessions using persistent checkpoints.
    - Handle communication failures conservatively.
    - Expose diagnostic information without modifying stored data.

Important limitations:
    - MQTT retained messages must be filtered by the MQTT client.
    - Incoming timestamps represent observation time, not the exact
      moment when the PlayStation changed state.
    - A missing observation cannot prove continued console activity.
    - Session durations are conservative estimates.
"""

import logging
import threading

from datetime import datetime

from database import Database
from models import (
    EventType,
    MonitoringEvent,
    PS5State,
    SessionType,
    ensure_utc,
    utc_now,
)


LOGGER = logging.getLogger(__name__)


class SessionTracker:
    """
    Coordinate atomic PlayStation session accounting.

    The database remains the authoritative source of session state.
    In-memory values are used only for diagnostics and ordering.
    """

    def __init__(
        self,
        database: Database,
        player_name: str,
        max_gap_seconds: float = 90.0,
    ) -> None:
        """
        Initialize the tracker and recover unfinished sessions.

        Args:
            database: Persistent SQLite database instance.
            player_name: Exact PSN player identifier.
            max_gap_seconds: Maximum accepted observation gap.
        """

        if not player_name.strip():
            raise ValueError("Player name cannot be empty.")

        if max_gap_seconds <= 0:
            raise ValueError("Maximum gap must be positive.")

        self._database = database
        self._player_name = player_name
        self._max_gap_seconds = max_gap_seconds

        self._lock = threading.RLock()
        self._last_observation: datetime | None = None

        # Recover sessions before accepting new observations.
        # The recovery operation is atomic and idempotent.
        recovered = self._database.recover_open_sessions()

        if recovered:
            LOGGER.warning(
                "Recovered %d interrupted PS5 sessions.",
                recovered,
            )

        self._database.insert_event(
            MonitoringEvent(
                event_type=EventType.SERVICE_STARTED,
                occurred_at=utc_now(),
            )
        )

    def process_state(self, state: PS5State) -> bool:
        """
        Process one validated PS5 observation.

        The database applies all session transitions, checkpoints,
        and the observation event in a single transaction.

        Returns:
            True when the observation was accepted.
            False when it was rejected as out of order.

        Raises:
            Any database exception without hiding the failure.
        """

        with self._lock:
            timestamp = ensure_utc(state.observed_at)

            if (
                self._last_observation is not None
                and timestamp <= self._last_observation
            ):
                LOGGER.warning(
                    "Rejected an out-of-order PS5 observation."
                )
                return False

            # Database writes are atomic. If this call fails,
            # the in-memory timestamp remains unchanged.
            accepted = self._database.apply_observation(
                state=state,
                player_name=self._player_name,
                max_gap_seconds=self._max_gap_seconds,
            )

            if accepted:
                self._last_observation = timestamp

            return accepted

    def connection_lost(self) -> None:
        """
        Stop accounting when communication becomes unavailable.

        The database recovery method closes sessions at their
        latest persisted checkpoints.

        No additional time is attributed to the disconnected period.
        """

        with self._lock:
            recovered = self._database.recover_open_sessions()

            if recovered:
                LOGGER.warning(
                    "Communication lost; closed %d sessions "
                    "at their latest confirmed checkpoints.",
                    recovered,
                )

            self._database.insert_event(
                MonitoringEvent(
                    event_type=EventType.CONNECTION_LOST,
                    occurred_at=utc_now(),
                )
            )

            self._last_observation = None

    def shutdown(self) -> None:
        """
        Close active sessions during an orderly shutdown.

        Confirmed accounting ends at the latest checkpoint.
        """

        with self._lock:
            self._database.recover_open_sessions()

            self._database.insert_event(
                MonitoringEvent(
                    event_type=EventType.SERVICE_STOPPED,
                    occurred_at=utc_now(),
                )
            )

            self._last_observation = None

    def get_status(self) -> dict:
        """
        Return a diagnostic snapshot of the monitoring service.

        No database changes are performed.
        """

        with self._lock:
            sessions = self._database.get_open_sessions()

            console = next(
                (
                    session
                    for session in sessions
                    if session.session_type == SessionType.CONSOLE
                ),
                None,
            )

            gaming = next(
                (
                    session
                    for session in sessions
                    if (
                        session.session_type == SessionType.GAMING
                        and session.player_name == self._player_name
                    )
                ),
                None,
            )

            return {
                "player_name": self._player_name,
                "console_active": console is not None,
                "gaming_active": gaming is not None,
                "current_game": (
                    gaming.title_name if gaming else None
                ),
                "last_observation": (
                    self._last_observation.isoformat()
                    if self._last_observation
                    else None
                ),
                "max_gap_seconds": self._max_gap_seconds,
            }
