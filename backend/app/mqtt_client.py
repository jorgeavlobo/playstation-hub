"""
PS5 Monitoring Service - MQTT Client.

This module receives PlayStation state updates from the MQTT broker
and forwards validated observations to the session tracker.

Responsibilities:
    - Authenticate with the configured MQTT broker.
    - Subscribe to the configured PlayStation topic.
    - Ignore retained MQTT messages.
    - Validate and normalize incoming JSON payloads.
    - Reconnect automatically after network interruptions.
    - Detect missing fresh updates using a monotonic clock.
    - Stop session accounting when communication becomes unreliable.

Important:
    The PS5 MQTT publisher does not provide a source timestamp.
    Therefore, timestamps represent local reception time.

    A non-retained MQTT message is treated as a fresh broker
    publication, not as absolute proof of the console's state.
"""

import json
import logging
import threading
import time

from datetime import datetime, timezone
from typing import Any

from config import AppConfig
from models import ActivityType, ConsolePower, PS5State
from session_tracker import SessionTracker
from history_protocol import HistoryMQTTRequest
from history_worker import HistoryWorker
from ps5_daily_protocol import DailyHistoryRequest


LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 30.0
WATCHDOG_INTERVAL_SECONDS = 1.0

HISTORY_REQUEST_TOPIC = "ps5-monitor/history/request"
DAILY_REQUEST_TOPIC = "ps5-monitor/history/daily/request"
DAILY_RESPONSE_TOPIC = "ps5-monitor/history/daily/response"
HISTORY_REQUEST_QOS = 1


def parse_ps5_payload(
    payload: bytes,
    observed_at: datetime | None = None,
) -> PS5State:
    """
    Parse and validate a PS5 MQTT JSON payload.

    Invalid, incomplete, or ambiguous payloads are rejected.
    Unknown power states must never be interpreted as active.

    Args:
        payload: Raw MQTT message payload.
        observed_at: Optional UTC reception timestamp.

    Returns:
        A normalized PS5State instance.

    Raises:
        ValueError: If the payload is invalid or incomplete.
    """

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid PS5 JSON payload.") from error

    if not isinstance(data, dict):
        raise ValueError("PS5 payload must be a JSON object.")

    raw_power = data.get("power")
    raw_activity = data.get("activity")
    raw_status = data.get("device_status")
    raw_players = data.get("players")

    if not isinstance(raw_power, str):
        raise ValueError("Missing or invalid power state.")

    if not isinstance(raw_activity, str):
        raise ValueError("Missing or invalid activity state.")

    if not isinstance(raw_status, str):
        raise ValueError("Missing or invalid device status.")

    if not isinstance(raw_players, list):
        raise ValueError("Players must be a JSON array.")

    if not all(isinstance(player, str) for player in raw_players):
        raise ValueError("Player identifiers must be strings.")

    try:
        power = ConsolePower(raw_power)
    except ValueError:
        power = ConsolePower.UNKNOWN

    try:
        activity = ActivityType(raw_activity)
    except ValueError:
        activity = ActivityType.UNKNOWN

    def optional_string(name: str) -> str | None:
        """Validate an optional string field."""

        value = data.get(name)

        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError(f"Invalid field: {name}")

        return value

    return PS5State(
        power=power,
        device_status=raw_status,
        activity=activity,
        players=tuple(raw_players),
        title_id=optional_string("title_id"),
        title_name=optional_string("title_name"),
        title_image=optional_string("title_image"),
        observed_at=observed_at or datetime.now(timezone.utc),
    )


class PS5MQTTClient:
    """
    Manage MQTT connectivity and PlayStation state observations.

    SessionTracker is responsible for database accounting.
    This class does not access SQLite directly.
    """

    def __init__(
        self,
        config: AppConfig,
        tracker: SessionTracker,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        history_worker: HistoryWorker | None = None,
    ) -> None:
        """Initialize the MQTT client and its watchdog."""

        if timeout_seconds <= 0:
            raise ValueError("MQTT timeout must be positive.")

        self._config = config
        self._tracker = tracker
        self._timeout_seconds = timeout_seconds

        # Historical requests are handled independently from
        # PlayStation observations and session accounting.
        self._history_worker = history_worker

        # Optional live-monitoring dependencies.
        # These are configured before MQTT startup.
        self._live_state = None
        self._live_publisher = None

        self._lock = threading.RLock()
        self._stop_event = threading.Event()

        self._connected = False
        self._last_message_monotonic: float | None = None
        self._timeout_reported = False

        # Once shutdown begins, no new console observations
        # may be accepted by the session tracker.
        self._accepting_observations = True

        self._connection_generation = 0
        self._client = None
        self._watchdog_thread = None

    def set_history_worker(
        self,
        worker: HistoryWorker,
    ) -> None:
        """
        Attach the historical request worker before MQTT startup.

        Dependency replacement is prohibited after the MQTT
        client has been initialized for network communication.
        """

        if not isinstance(worker, HistoryWorker):
            raise TypeError(
                "Expected a HistoryWorker instance."
            )

        with self._lock:
            if self._client is not None:
                raise RuntimeError(
                    "Cannot replace HistoryWorker after MQTT startup."
                )

            if self._history_worker is not None:
                raise RuntimeError(
                    "HistoryWorker dependency is already configured."
                )

            self._history_worker = worker

    def set_live_monitoring(
        self,
        live_state,
        live_publisher,
    ) -> None:
        """
        Attach live-monitoring dependencies before MQTT startup.

        Dependency replacement is prohibited after startup.
        """

        from ps5_live_state import PS5LiveState
        from ps5_live_publisher import PS5LivePublisher

        if not isinstance(live_state, PS5LiveState):
            raise TypeError("Expected a PS5LiveState instance.")

        if not isinstance(live_publisher, PS5LivePublisher):
            raise TypeError("Expected a PS5LivePublisher instance.")

        with self._lock:
            if self._client is not None:
                raise RuntimeError(
                    "Cannot configure live monitoring after MQTT startup."
                )

            if (
                self._live_state is not None
                or self._live_publisher is not None
            ):
                raise RuntimeError(
                    "Live monitoring is already configured."
                )

            self._live_state = live_state
            self._live_publisher = live_publisher

    def _invalidate_live_state(self) -> None:
        """
        Invalidate live state and notify its background worker.

        No MQTT network publication occurs in this method.
        """

        if self._live_state is None:
            return

        self._live_state.invalidate()

        if self._live_publisher is not None:
            self._live_publisher.notify()

    def begin_shutdown(self) -> None:
        """
        Prevent new PS5 observations without disconnecting MQTT.

        The existing client lock ensures that an observation
        already being processed finishes before the barrier
        becomes active.

        Historical and live-state publication workers may
        continue using the MQTT connection during shutdown.
        """

        with self._lock:
            self._accepting_observations = False

    def handle_message(
        self,
        payload: bytes,
        retained: bool = False,
        observed_at: datetime | None = None,
    ) -> bool:
        """
        Validate and process a received MQTT message.

        This method is independently testable without a broker.

        Returns:
            True if the tracker accepted the observation.
            False if the message was retained or invalid.

        Database errors are deliberately propagated rather than
        silently discarding failed persistence operations.
        """

        if retained:
            LOGGER.debug("Ignoring retained PS5 MQTT message.")
            return False

        try:
            state = parse_ps5_payload(payload, observed_at)
        except ValueError as error:
            LOGGER.warning("Rejected PS5 MQTT payload: %s", error)
            return False

        with self._lock:
            if not self._accepting_observations:
                LOGGER.debug(
                    "Ignoring PS5 observation during shutdown."
                )
                return False

            accepted = self._tracker.process_state(state)

            if accepted:
                self._last_message_monotonic = time.monotonic()
                self._timeout_reported = False

                # Only persisted and accepted observations
                # may update the dashboard live state.
                if self._live_state is not None:
                    self._live_state.observe(state)

                    if self._live_publisher is not None:
                        self._live_publisher.notify()

            return accepted

    def _on_connect(
        self,
        client: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Subscribe after a successful MQTT connection."""

        if reason_code != 0:
            LOGGER.error(
                "MQTT connection rejected: %s",
                reason_code,
            )
            return

        with self._lock:
            # A successful MQTT connection must never inherit
            # accounting sessions from a previous connection.
            #
            # This also covers reconnects where the disconnect
            # callback was not executed successfully.
            #
            # Recovery closes sessions at their latest persisted
            # checkpoints without inventing disconnected time.
            try:
                self._tracker.connection_lost()
            except Exception:
                self._connected = False
                LOGGER.exception(
                    "Unable to recover sessions after MQTT connection."
                )
                client.disconnect()
                return

            # Never reuse an observation from an older
            # MQTT connection generation.
            self._invalidate_live_state()

            self._connected = True
            self._connection_generation += 1

            if self._live_publisher is not None:
                self._live_publisher.request_republish()

            # Wait for a fresh, non-retained publication before
            # accepting the console state again.
            self._last_message_monotonic = None
            self._timeout_reported = False

        result, _ = client.subscribe(
            self._config.mqtt_topic,
            qos=0,
        )

        if result != 0:
            LOGGER.error(
                "Unable to subscribe to PS5 MQTT topic: %s",
                result,
            )
        else:
            LOGGER.info(
                "Subscribed to PS5 MQTT topic: %s",
                self._config.mqtt_topic,
            )

        # Historical requests use a separate subscription.
        # Re-subscribe after every successful MQTT connection.
        if self._history_worker is not None:
            history_result, _ = client.subscribe(
                HISTORY_REQUEST_TOPIC,
                qos=HISTORY_REQUEST_QOS,
            )

            if history_result != 0:
                LOGGER.error(
                    "Unable to subscribe to history requests: %s",
                    history_result,
                )
            else:
                LOGGER.info(
                    "Subscribed to historical request topic: %s",
                    HISTORY_REQUEST_TOPIC,
                )

        if self._history_worker is not None:
            daily_result, _ = client.subscribe(DAILY_REQUEST_TOPIC, qos=1)
            if daily_result != 0:
                LOGGER.error("Unable to subscribe to daily history requests.")
            else:
                LOGGER.info("Subscribed to daily history request topic: %s", DAILY_REQUEST_TOPIC)

    def _on_disconnect(
        self,
        client: Any,
        userdata: Any,
        disconnect_flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        """Stop accounting when the broker disconnects."""

        with self._lock:
            self._connected = False
            self._last_message_monotonic = None
            self._timeout_reported = False

            try:
                self._tracker.connection_lost()
            finally:
                self._invalidate_live_state()

        if not self._stop_event.is_set():
            LOGGER.warning(
                "MQTT disconnected: %s",
                reason_code,
            )

    def _on_message(
        self,
        client: Any,
        userdata: Any,
        message: Any,
    ) -> None:
        """Process one message received from the broker."""

        if message.topic == DAILY_REQUEST_TOPIC:
            if self._history_worker is None:
                return
            try:
                request = DailyHistoryRequest.parse(message.payload, message.retain)
                self._history_worker.submit_daily(request)
            except ValueError as error:
                LOGGER.warning("Rejected daily history MQTT request: %s", error)
            except RuntimeError as error:
                # A valid request rejected by a saturated worker must receive
                # a correlated terminal response instead of timing out.
                if str(error) == "History request queue is full.":
                    response = {
                        "schema_version": 1,
                        "kind": "daily_history_error",
                        "request_id": request.request_id,
                        "start_date": request.start_day.isoformat(),
                        "end_date_exclusive": request.end_day.isoformat(),
                        "error_code": "server_busy",
                    }
                    try:
                        client.publish(
                            DAILY_RESPONSE_TOPIC,
                            json.dumps(response, separators=(",", ":")),
                            qos=1,
                            retain=False,
                        )
                    except Exception:
                        LOGGER.exception(
                            "Unable to publish daily history overload response."
                        )
                else:
                    LOGGER.exception("Unable to enqueue daily history request.")
            except Exception:
                LOGGER.exception("Unable to enqueue daily history request.")
            return

        # Historical requests must never affect PS5 session
        # accounting, even when their payload is invalid.
        if message.topic == HISTORY_REQUEST_TOPIC:
            if self._history_worker is None:
                return

            try:
                request = HistoryMQTTRequest.parse(
                    payload=message.payload,
                    retained=message.retain,
                )

                # Enqueue only. The worker performs database
                # queries and blocking QoS 1 publications.
                self._history_worker.submit(request)

            except ValueError as error:
                LOGGER.warning(
                    "Rejected historical MQTT request: %s",
                    error,
                )

            except Exception:
                LOGGER.exception(
                    "Unable to enqueue historical MQTT request."
                )

            return

        if message.topic != self._config.mqtt_topic:
            return

        try:
            self.handle_message(
                payload=message.payload,
                retained=message.retain,
            )
        except Exception:
            LOGGER.exception(
                "Failed to persist PS5 MQTT observation."
            )

            # Stop accounting at the last confirmed checkpoint.
            # A subsequent fresh message may resume accounting.
            with self._lock:
                try:
                    self._tracker.connection_lost()
                finally:
                    self._invalidate_live_state()
                    self._last_message_monotonic = None
                    self._timeout_reported = False

    def _watchdog_loop(self) -> None:
        """
        Monitor the interval between fresh MQTT observations.

        When no valid message arrives within the configured timeout,
        the tracker closes active sessions at their last checkpoint.

        A subsequent fresh observation starts new sessions.
        """

        while not self._stop_event.wait(
            WATCHDOG_INTERVAL_SECONDS
        ):
            with self._lock:
                if not self._connected:
                    continue

                if self._last_message_monotonic is None:
                    continue

                elapsed = (
                    time.monotonic()
                    - self._last_message_monotonic
                )

                if (
                    elapsed >= self._timeout_seconds
                    and not self._timeout_reported
                ):
                    LOGGER.warning(
                        "No fresh PS5 MQTT update for %.1f seconds.",
                        elapsed,
                    )

                    try:
                        self._tracker.connection_lost()
                    finally:
                        self._invalidate_live_state()
                        self._last_message_monotonic = None
                        self._timeout_reported = True


    @property
    def connected(self) -> bool:
        """Return whether the MQTT connection is established."""

        with self._lock:
            return self._connected

    @property
    def connection_generation(self) -> int:
        """
        Return the number of successful MQTT connections.

        This counter is used to republish MQTT Discovery
        configurations after reconnection.
        """

        with self._lock:
            return self._connection_generation

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
    ):
        """
        Publish a message through the existing MQTT connection.

        QoS 1 publications wait for broker acknowledgement.

        The internal state lock is released before waiting,
        allowing MQTT callbacks to continue processing.

        This method must not be called from the Paho MQTT
        network callback thread because waiting there could
        prevent acknowledgement processing.
        """

        import paho.mqtt.client as mqtt

        if qos not in (0, 1):
            raise ValueError("Only MQTT QoS 0 and 1 are supported.")

        if threading.current_thread().name.startswith(
            "paho-mqtt-client-"
        ):
            raise RuntimeError(
                "Blocking MQTT publication from the network "
                "callback thread is not supported."
            )

        with self._lock:
            if not self._connected or self._client is None:
                raise RuntimeError("MQTT client is not connected.")

            client = self._client

        result = client.publish(
            topic,
            payload=payload,
            qos=qos,
            retain=retain,
        )

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(
                f"MQTT publication failed for {topic}: "
                f"result code {result.rc}"
            )

        if qos == 1:
            try:
                result.wait_for_publish(timeout=10.0)
            except RuntimeError as error:
                raise RuntimeError(
                    f"MQTT publication not confirmed: {topic}"
                ) from error

            if not result.is_published():
                raise TimeoutError(
                    f"MQTT publication timed out: {topic}"
                )

        return result

    def start(self) -> None:
        """Start MQTT connectivity and the watchdog thread."""

        if self._client is not None:
            raise RuntimeError("MQTT client already started.")

        # Import here so payload parsing can be tested without
        # installing MQTT dependencies on the Home Assistant host.
        import paho.mqtt.client as mqtt

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="ps5-monitoring-service",
            protocol=mqtt.MQTTv311,
        )

        client.username_pw_set(
            username=self._config.mqtt_username,
            password=self._config.mqtt_password,
        )

        # The broker publishes this retained offline message
        # if the client disconnects unexpectedly.
        #
        # Graceful shutdown publishes offline explicitly.
        client.will_set(
            topic="ps5-monitor/availability",
            payload="offline",
            qos=1,
            retain=True,
        )

        client.reconnect_delay_set(
            min_delay=1,
            max_delay=60,
        )

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        self._stop_event.clear()
        self._client = client

        client.connect_async(
            self._config.mqtt_host,
            self._config.mqtt_port,
            keepalive=30,
        )

        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="ps5-mqtt-watchdog",
            daemon=True,
        )

        self._watchdog_thread.start()
        client.loop_start()

        LOGGER.info("PS5 MQTT monitoring client started.")

    def stop(self) -> None:
        """Stop MQTT communication and the watchdog safely."""

        self._stop_event.set()

        if self._client is not None:
            self._client.disconnect()
            self._client.loop_stop()
            self._client = None

        if self._watchdog_thread is not None:
            self._watchdog_thread.join(timeout=5)
            self._watchdog_thread = None

        with self._lock:
            self._connected = False
            self._last_message_monotonic = None

        LOGGER.info("PS5 MQTT monitoring client stopped.")
