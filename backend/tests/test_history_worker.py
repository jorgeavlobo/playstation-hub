"""
Automated tests for the PS5 historical request worker.

Tests cover request correlation, MQTT publication, payload
limits, latest-request-wins scheduling, and safe shutdown.

No production database or MQTT broker is required.
"""

import json
import threading
import unittest
from unittest.mock import patch

from history_protocol import HistoryMQTTRequest
from history_worker import (
    HISTORY_RESPONSE_TOPIC,
    MAX_RESPONSE_BYTES,
    HistoryWorker,
)


def make_request(request_id, period):
    """Create a validated historical MQTT request."""

    payload = json.dumps({
        "request_id": request_id,
        "period": period,
    }).encode("utf-8")

    return HistoryMQTTRequest.parse(payload)


class FakePublisher:
    """Capture MQTT publications with thread-safe synchronization."""

    def __init__(self):
        self.messages = []
        self.lock = threading.Lock()
        self.published = threading.Event()

    def publish(self, topic, payload, qos=0, retain=False):
        """Record an outgoing MQTT message."""

        with self.lock:
            self.messages.append({
                "topic": topic,
                "payload": json.loads(payload),
                "qos": qos,
                "retain": retain,
            })

        self.published.set()


class FakeBuilder:
    """Generate deterministic historical responses."""

    def __init__(self, oversized=False):
        self.oversized = oversized
        self.completed = threading.Event()

    def build(self, request):
        """Build a simulated monthly response."""

        response = {
            "schema_version": 1,
            "period": request.period,
            "games": [],
        }

        if self.oversized:
            response["padding"] = "X" * (
                MAX_RESPONSE_BYTES + 100
            )

        self.completed.set()
        return response


class BlockingBuilder:
    """Control processing order using synchronization events."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.processed = []
        self.lock = threading.Lock()

    def build(self, request):
        """Block the first request until explicitly released."""

        with self.lock:
            self.processed.append(request.period)
            is_first = len(self.processed) == 1

        if is_first:
            self.entered.set()

            if not self.release.wait(timeout=10):
                raise TimeoutError(
                    "Simulated historical query timed out."
                )

        return {
            "schema_version": 1,
            "period": request.period,
            "games": [],
        }


class HistoryWorkerTests(unittest.TestCase):
    """Verify the worker's public behavior."""

    def setUp(self):
        """Create isolated test dependencies."""

        self.publisher = FakePublisher()
        self.builder = FakeBuilder()

        self.worker = HistoryWorker(
            publisher=self.publisher,
            response_builder=self.builder,
        )

        self.worker.start()

    def tearDown(self):
        """Stop the worker after each test."""

        self.worker.stop()

    def test_successful_publication(self):
        """Responses must preserve external request identifiers."""

        sequence = self.worker.submit(
            make_request("dashboard-001", "2026-11")
        )

        self.assertTrue(
            self.publisher.published.wait(timeout=5)
        )

        self.assertEqual(len(self.publisher.messages), 1)

        message = self.publisher.messages[0]
        payload = message["payload"]

        self.assertEqual(
            message["topic"],
            HISTORY_RESPONSE_TOPIC,
        )
        self.assertEqual(message["qos"], 1)
        self.assertFalse(message["retain"])

        self.assertEqual(
            payload["request_id"],
            "dashboard-001",
        )
        self.assertEqual(payload["request_sequence"], sequence)
        self.assertEqual(payload["period"], "2026-11")

    def test_invalid_request_type(self):
        """Unvalidated request objects must be rejected."""

        with self.assertRaises(TypeError):
            self.worker.submit("2026-11")

        self.assertFalse(
            self.publisher.published.wait(timeout=0.1)
        )

    def test_oversized_response_rejected(self):
        """Responses exceeding the configured limit are rejected."""

        self.worker.stop()

        self.builder = FakeBuilder(oversized=True)
        self.worker = HistoryWorker(
            self.publisher,
            self.builder,
        )
        self.worker.start()

        self.worker.submit(
            make_request("oversized-001", "2026-11")
        )

        self.assertTrue(
            self.builder.completed.wait(timeout=5)
        )

        # Wait for the worker to finish its processing cycle.
        self.worker.stop()

        self.assertEqual(self.publisher.messages, [])

    def test_submit_after_shutdown_rejected(self):
        """Stopped workers must reject incoming requests."""

        self.worker.stop()

        with self.assertRaises(RuntimeError):
            self.worker.submit(
                make_request("stopped-001", "2026-11")
            )

    def test_latest_pending_request_wins(self):
        """Only the newest pending request should be processed."""

        self.worker.stop()

        builder = BlockingBuilder()
        self.worker = HistoryWorker(
            self.publisher,
            builder,
        )
        self.worker.start()

        try:
            self.worker.submit(
                make_request("first", "2026-09")
            )

            self.assertTrue(builder.entered.wait(timeout=5))

            self.worker.submit(
                make_request("second", "2026-10")
            )

            self.worker.submit(
                make_request("third", "2026-11")
            )

            builder.release.set()

            self.assertTrue(
                self.publisher.published.wait(timeout=5)
            )

        finally:
            builder.release.set()
            self.worker.stop()

        self.assertEqual(
            builder.processed,
            ["2026-09", "2026-11"],
        )

        self.assertEqual(len(self.publisher.messages), 1)

        self.assertEqual(
            self.publisher.messages[0]["payload"]["request_id"],
            "third",
        )

    def test_duplicate_start_rejected(self):
        """An active worker must not be started twice."""

        with self.assertRaises(RuntimeError):
            self.worker.start()

    def test_restart_after_clean_shutdown(self):
        """A fully stopped worker may be restarted safely."""

        self.worker.stop()
        self.worker.start()

        self.worker.submit(
            make_request("restart-001", "2026-11")
        )

        self.assertTrue(
            self.publisher.published.wait(timeout=5)
        )

    def test_shutdown_timeout_prevents_duplicate_thread(self):
        """A blocked worker must prevent overlapping restarts."""

        self.worker.stop()

        builder = BlockingBuilder()
        self.worker = HistoryWorker(
            self.publisher,
            builder,
        )
        self.worker.start()

        try:
            self.worker.submit(
                make_request("blocking-001", "2026-11")
            )

            self.assertTrue(builder.entered.wait(timeout=5))

            with patch.object(
                threading.Thread,
                "join",
                return_value=None,
            ):
                with self.assertRaises(TimeoutError):
                    self.worker.stop()

            with self.assertRaises(RuntimeError):
                self.worker.start()

        finally:
            builder.release.set()

            # The original worker must terminate before cleanup.
            thread = self.worker._thread

            if thread is not None:
                thread.join(timeout=5)

            self.worker.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
