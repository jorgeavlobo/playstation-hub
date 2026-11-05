"""
PS5 Monitoring Service - Application Entry Point.

Coordinates application initialization, MQTT communication,
persistent session tracking, statistics publishing, and shutdown.

The application uses one MQTT connection for receiving PlayStation
state updates and publishing Home Assistant discovery messages.
"""

import logging
import signal
import threading
import time

from config import load_config
from database import Database
from history_response import HistoryResponseBuilder
from history_worker import HistoryWorker
from mqtt_client import PS5MQTTClient
from ps5_live_state import PS5LiveState
from ps5_live_publisher import PS5LivePublisher
from ps5_live_lifecycle import PS5LiveLifecycle
from mqtt_publisher import StatisticsPublisher
from session_tracker import SessionTracker
from usage_statistics import StatisticsService


LOGGER = logging.getLogger("ps5_monitor")

STATISTICS_INTERVAL_SECONDS = 60.0
HISTORY_INDEX_INTERVAL_SECONDS = 300.0
HISTORY_INDEX_RETRY_SECONDS = 30.0
MAIN_LOOP_INTERVAL_SECONDS = 1.0
AVAILABILITY_TOPIC = "ps5-monitor/availability"


class PS5MonitoringApplication:
    """
    Coordinate the monitoring service lifecycle.

    Components are initialized independently to preserve
    modularity and simplify future testing and maintenance.
    """

    def __init__(self) -> None:
        """Initialize application state without starting services."""

        self._stop_event = threading.Event()

        self._database = None
        self._tracker = None
        self._mqtt = None
        self._publisher = None
        self._history_worker = None

        # Live-monitoring components are initialized
        # independently and share the existing MQTT client.
        self._live_state = None
        self._live_publisher = None
        self._live_lifecycle = None

        self._last_connection_generation = -1
        self._last_statistics_update = None
        self._last_history_index_update = None
        self._next_history_index_attempt = 0.0

    def request_shutdown(self, signum, frame) -> None:
        """Request a graceful application shutdown."""

        LOGGER.info("Shutdown requested: signal %s", signum)
        self._stop_event.set()

    def _initialize(self) -> None:
        """Initialize configuration and application components."""

        config = load_config()

        self._database = Database(config.database_path)

        self._tracker = SessionTracker(
            database=self._database,
            player_name=config.player_name,
            max_gap_seconds=30.0,
        )

        statistics = StatisticsService(
            database=self._database,
            player_name=config.player_name,
        )

        # Reuse the existing statistics service so that
        # historical queries and current statistics share
        # the same accounting rules.
        history_builder = HistoryResponseBuilder(
            statistics=statistics,
        )

        # The MQTT client is created before the worker because
        # the worker publishes through the same MQTT connection.
        self._mqtt = PS5MQTTClient(
            config=config,
            tracker=self._tracker,
            timeout_seconds=30.0,
        )

        self._history_worker = HistoryWorker(
            publisher=self._mqtt,
            response_builder=history_builder,
            statistics=statistics,
        )

        # Inject the worker before MQTT connectivity starts.
        # No callbacks can run during this initialization.
        self._mqtt.set_history_worker(
            self._history_worker
        )

        self._publisher = StatisticsPublisher(
            client=self._mqtt,
            statistics=statistics,
        )

        # Track only confirmed observations for the configured
        # player. No additional MQTT connection is created.
        self._live_state = PS5LiveState(
            player_name=config.player_name,
            timeout_seconds=30.0,
        )

        # Publications run on a dedicated worker thread.
        # The transport predicate prevents publication before
        # MQTT connectivity has been established.
        self._live_publisher = PS5LivePublisher(
            publisher=self._mqtt,
            live_state=self._live_state,
            transport_available=lambda: self._mqtt.connected,
        )

        self._live_lifecycle = PS5LiveLifecycle(
            live_state=self._live_state,
            publisher=self._live_publisher,
            transport_available=lambda: self._mqtt.connected,
        )

        # Inject dependencies before MQTT network callbacks
        # become active.
        self._mqtt.set_live_monitoring(
            self._live_state,
            self._live_publisher,
        )

    def _publish_availability(self, available: bool) -> None:
        """Publish the current monitoring service availability."""

        result = self._mqtt.publish(
            AVAILABILITY_TOPIC,
            "online" if available else "offline",
            qos=1,
            retain=True,
        )

        if result.rc != 0:
            raise RuntimeError(
                "Unable to publish MQTT availability."
            )

    def _publish_updates(self) -> None:
        """
        Publish discovery, statistics, and historical indexes.

        Regular statistics refresh every sixty seconds.
        The history index refreshes every five minutes.

        Failed history index publications retry after thirty
        seconds without interrupting core monitoring.
        """

        if not self._mqtt.connected:
            return

        generation = self._mqtt.connection_generation

        # Republish discovery and statistics after every
        # successful MQTT connection or reconnection.
        if generation != self._last_connection_generation:
            self._publisher.publish_discovery()
            self._publisher.publish_statistics()
            self._publish_availability(True)

            self._last_connection_generation = generation
            self._last_statistics_update = time.monotonic()

            # A new MQTT connection resets the historical
            # index retry deadline.
            self._last_history_index_update = None
            self._next_history_index_attempt = 0.0

            LOGGER.info(
                "Discovery and initial statistics published."
            )

            try:
                self._publisher.publish_history_index()

                published_at = time.monotonic()

                self._last_history_index_update = published_at
                self._next_history_index_attempt = (
                    published_at + HISTORY_INDEX_INTERVAL_SECONDS
                )

            except Exception:
                self._next_history_index_attempt = (
                    time.monotonic() + HISTORY_INDEX_RETRY_SECONDS
                )

                LOGGER.exception(
                    "Unable to publish historical activity index."
                )

            return

        now = time.monotonic()

        # Preserve the existing regular statistics interval.
        if (
            self._last_statistics_update is None
            or now - self._last_statistics_update
            >= STATISTICS_INTERVAL_SECONDS
        ):
            self._publisher.publish_statistics()
            self._last_statistics_update = time.monotonic()

        # The historical index uses an independent deadline.
        # A failed publication must not trigger an immediate
        # retry on every application loop iteration.
        now = time.monotonic()

        if now >= self._next_history_index_attempt:
            try:
                self._publisher.publish_history_index()

                published_at = time.monotonic()

                self._last_history_index_update = published_at
                self._next_history_index_attempt = (
                    published_at + HISTORY_INDEX_INTERVAL_SECONDS
                )

            except Exception:
                self._next_history_index_attempt = (
                    time.monotonic() + HISTORY_INDEX_RETRY_SECONDS
                )

                LOGGER.exception(
                    "Historical activity index update failed."
                )

    def run(self) -> None:
        """Run the monitoring application until shutdown."""

        signal.signal(
            signal.SIGTERM,
            self.request_shutdown,
        )

        signal.signal(
            signal.SIGINT,
            self.request_shutdown,
        )

        try:
            self._initialize()

            # Start historical processing before subscribing
            # to MQTT requests.
            self._history_worker.start()

            # Start the live worker before MQTT connectivity.
            # It remains idle until the transport is available.
            self._live_publisher.start()

            self._mqtt.start()

            LOGGER.info(
                "PS5 Monitoring Service started successfully."
            )

            while not self._stop_event.wait(
                MAIN_LOOP_INTERVAL_SECONDS
            ):
                try:
                    self._publish_updates()
                except Exception:
                    LOGGER.exception(
                        "Failed to publish monitoring statistics."
                    )

        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        """
        Stop monitoring components in dependency order.

        New observations are rejected before live-state
        freezing. MQTT remains connected until every
        publication worker has terminated.

        SQLite closes only after its dependent components
        have completed shutdown.
        """

        LOGGER.info("Stopping PS5 Monitoring Service.")

        # Prevent new console observations while preserving
        # MQTT connectivity for pending publications.
        if self._mqtt is not None:
            self._mqtt.begin_shutdown()

        # Historical processing must finish before MQTT
        # communication is terminated.
        if self._history_worker is not None:
            try:
                self._history_worker.stop()
            except Exception:
                LOGGER.exception(
                    "Historical worker shutdown failed. "
                    "MQTT and SQLite remain available."
                )
                raise

        # Complete live-state publication and terminate its
        # worker before disconnecting the MQTT transport.
        if self._live_publisher is not None:
            if self._live_publisher.running:
                try:
                    result = self._live_lifecycle.shutdown()

                    if result.degraded:
                        LOGGER.warning(
                            "Live monitoring degraded shutdown: %s",
                            result.reason,
                        )
                    else:
                        LOGGER.info(
                            "Live monitoring final state confirmed."
                        )

                except Exception:
                    LOGGER.exception(
                        "Live monitoring shutdown failed. "
                        "MQTT remains available."
                    )
                    raise

            else:
                # Handle partial application startup safely.
                # stop() also joins a thread that may be
                # stopping but has not terminated yet.
                self._live_publisher.stop()

        # Publish service availability only after dependent
        # publication workers have completed.
        if self._mqtt is not None:
            if self._mqtt.connected:
                try:
                    self._publish_availability(False)
                except Exception:
                    LOGGER.exception(
                        "Failed to publish offline availability."
                    )

            try:
                self._mqtt.stop()
            except Exception:
                LOGGER.exception(
                    "MQTT shutdown failed. "
                    "SQLite will remain open."
                )
                raise

        # Finalize monitoring sessions after MQTT stops.
        if self._tracker is not None:
            self._tracker.shutdown()

        # Close persistent storage last.
        if self._database is not None:
            self._database.close()

        LOGGER.info("PS5 Monitoring Service stopped.")


def configure_logging() -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(levelname)s "
            "[%(name)s] %(message)s"
        ),
    )


def main() -> None:
    """Configure logging and start the application."""

    configure_logging()

    application = PS5MonitoringApplication()
    application.run()


if __name__ == "__main__":
    main()
