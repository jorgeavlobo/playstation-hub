"""
PS5 Monitoring Service - Historical Request Worker.

Process historical statistics requests outside the MQTT
network callback thread.

Design principles:
    - Bounded pending-request capacity.
    - FIFO scheduling with a bounded queue.
    - Strict period validation.
    - Non-retained MQTT responses.
    - Graceful worker shutdown.
    - No direct database connection ownership.

The worker does not subscribe to MQTT topics.
Subscription and message routing belong to the MQTT client.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import deque

from dataclasses import dataclass
from typing import Protocol

from history_protocol import HistoryMQTTRequest
from history_response import HistoryResponseBuilder
from ps5_daily_protocol import DailyHistoryRequest
from ps5_daily_history import build_daily_history
from ps5_daily_pages import encode_daily_pages
from usage_statistics import StatisticsService


LOGGER = logging.getLogger("history_worker")

HISTORY_RESPONSE_TOPIC = "ps5-monitor/history/response"
DAILY_RESPONSE_TOPIC = "ps5-monitor/history/daily/response"

MAX_RESPONSE_BYTES = 16384
MAX_PENDING_REQUESTS = 32


class MQTTPublisherProtocol(Protocol):
    """Define the MQTT publishing interface required by the worker."""

    def publish(
        self,
        topic: str,
        payload: str,
        qos: int = 0,
        retain: bool = False,
    ):
        """Publish an MQTT message."""


@dataclass(frozen=True, slots=True)
class PendingHistoryRequest:
    """Represent one accepted request awaiting processing."""

    sequence: int
    request: HistoryMQTTRequest | DailyHistoryRequest


class HistoryWorker:
    """
    Process historical requests on a dedicated worker thread.

    A bounded FIFO queue preserves independent client requests.
    The capacity prevents unbounded memory growth under load.
    """

    def __init__(
        self,
        publisher: MQTTPublisherProtocol,
        response_builder: HistoryResponseBuilder,
        statistics: StatisticsService | None = None,
    ) -> None:
        """Initialize worker dependencies and synchronization."""

        self._publisher = publisher
        self._builder = response_builder
        self._statistics = statistics

        self._condition = threading.Condition()
        self._pending: deque[PendingHistoryRequest] = deque()

        self._sequence = 0
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background worker once."""

        with self._condition:
            # A previous worker may still be alive after a
            # shutdown timeout. Never start another worker until
            # the previous thread has terminated completely.
            if self._running or (
                self._thread is not None
                and self._thread.is_alive()
            ):
                raise RuntimeError(
                    "History worker is already running or stopping."
                )

            self._running = True
            self._pending.clear()

            self._thread = threading.Thread(
                target=self._run,
                name="ps5-history-worker",
                daemon=True,
            )

            self._thread.start()

    def submit(self, request: HistoryMQTTRequest) -> int:
        """
        Validate and enqueue a historical month request.

        Each accepted request retains its own response correlation.
        """

        if not isinstance(request, HistoryMQTTRequest):
            raise TypeError(
                "Expected a validated HistoryMQTTRequest."
            )

        with self._condition:
            if not self._running:
                raise RuntimeError("History worker is not running.")

            if len(self._pending) >= MAX_PENDING_REQUESTS:
                raise RuntimeError("History request queue is full.")
            self._sequence += 1
            self._pending.append(PendingHistoryRequest(
                sequence=self._sequence,
                request=request,
            ))

            self._condition.notify()

            return self._sequence

    def submit_daily(self, request: DailyHistoryRequest) -> int:
        """Queue a validated daily request using the existing worker thread."""
        if not isinstance(request, DailyHistoryRequest):
            raise TypeError("Expected a DailyHistoryRequest.")
        if self._statistics is None:
            raise RuntimeError("Daily history is not configured.")
        with self._condition:
            if not self._running:
                raise RuntimeError("History worker is not running.")
            if len(self._pending) >= MAX_PENDING_REQUESTS:
                raise RuntimeError("History request queue is full.")
            self._sequence += 1
            self._pending.append(PendingHistoryRequest(self._sequence, request))
            self._condition.notify()
            return self._sequence

    def _run(self) -> None:
        """Process requests until shutdown is requested."""

        while True:
            with self._condition:
                while self._running and not self._pending:
                    self._condition.wait()

                if not self._running:
                    return

                pending = self._pending.popleft()

            if pending is None:
                continue

            try:
                is_daily = isinstance(pending.request, DailyHistoryRequest)
                if is_daily:
                    if self._statistics is None:
                        raise RuntimeError("Daily history is not configured.")
                    response = build_daily_history(
                        self._statistics,
                        pending.request.start_day,
                        pending.request.end_day,
                        include_games=True,
                    )
                else:
                    response = self._builder.build(pending.request.history)

                # Preserve the external request identifier so
                # dashboard clients can correlate responses.
                response["request_id"] = pending.request.request_id
                response["request_sequence"] = pending.sequence

                if is_daily:
                    # Publish chronological pages rather than silently dropping
                    # a response that exceeds the broker's payload limit.
                    encoded_pages = encode_daily_pages(response)
                else:
                    encoded_pages = [json.dumps(
                        response,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )]

                encoded = encoded_pages[0]

                size = len(encoded.encode("utf-8"))

                if size > MAX_RESPONSE_BYTES:
                    raise ValueError(
                        "Historical response exceeds MQTT size limit."
                    )

                # FIFO processing preserves responses for independent clients.
                # Shutdown is checked before publishing a completed request.
                with self._condition:
                    if not self._running:
                        return

                for encoded_page in encoded_pages:
                    self._publisher.publish(
                        DAILY_RESPONSE_TOPIC if is_daily else HISTORY_RESPONSE_TOPIC,
                        encoded_page,
                        qos=1,
                        retain=False,
                    )

                LOGGER.info(
                    "Published historical statistics for %s.",
                    (pending.request.start_day.isoformat()
                     if is_daily else pending.request.period),
                )

            except Exception as error:
                LOGGER.exception(
                    "Failed to process historical request."
                )

                # Daily requests must always receive a correlated terminal
                # response. Never expose internal exception details over MQTT.
                if isinstance(pending.request, DailyHistoryRequest):
                    error_code = (
                        "response_too_large"
                        if isinstance(error, ValueError)
                        and str(error) in (
                            "Historical response exceeds MQTT size limit.",
                            "Single daily entry exceeds MQTT size limit.",
                        )
                        else "processing_failed"
                    )
                    error_response = {
                        "schema_version": 1,
                        "kind": "daily_history_error",
                        "request_id": pending.request.request_id,
                        "start_date": pending.request.start_day.isoformat(),
                        "end_date_exclusive": pending.request.end_day.isoformat(),
                        "error_code": error_code,
                    }
                    with self._condition:
                        still_running = self._running
                    if still_running:
                        try:
                            self._publisher.publish(
                                DAILY_RESPONSE_TOPIC,
                                json.dumps(error_response, separators=(",", ":")),
                                qos=1,
                                retain=False,
                            )
                        except Exception:
                            LOGGER.exception("Failed to publish daily history error.")

    def stop(self) -> None:
        """Request worker shutdown and wait for its termination."""

        with self._condition:
            # Always capture the worker thread, including when
            # a previous shutdown attempt already cleared the
            # running flag but timed out during thread joining.
            thread = self._thread

            if thread is None:
                self._running = False
                return

            self._running = False
            self._pending.clear()
            self._condition.notify_all()

        # Never wait for the worker while holding its condition lock.
        # The worker may need that lock to complete its shutdown.
        if thread is not None:
            thread.join(timeout=15.0)

            if thread.is_alive():
                raise TimeoutError(
                    "History worker did not stop within 15 seconds."
                )

        # Clear the thread reference only after termination.
        # A stopped worker must not leave an active background
        # thread that could publish obsolete MQTT responses.
        with self._condition:
            if self._thread is thread:
                self._thread = None
