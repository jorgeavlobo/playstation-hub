"""
PS5 Monitoring Service - Live Publisher Reliability Tests.

Verify MQTT publication, state expiration, publication retry,
worker lifecycle, and concurrent state changes.

No production database or MQTT broker is accessed.
"""

import json
import threading
import time
import unittest

from datetime import datetime, timezone
from unittest.mock import Mock

from models import ActivityType, ConsolePower, PS5State
from ps5_live_state import PS5LiveState
from ps5_live_publisher import (
    LIVE_STATE_QOS,
    LIVE_STATE_RETAIN,
    LIVE_STATE_TOPIC,
    PS5LivePublisher,
)


class FakeClock:
    """Provide deterministic monotonic time."""

    def __init__(self):
        self.value = 1000.0
        self.lock = threading.Lock()

    def __call__(self):
        """Return the simulated monotonic time."""

        with self.lock:
            return self.value

    def advance(self, seconds):
        """Advance simulated time."""

        with self.lock:
            self.value += seconds


def make_state(
    power=ConsolePower.AWAKE,
    activity=ActivityType.PLAYING,
):
    """Create a valid simulated PS5 observation."""

    return PS5State(
        power=power,
        device_status="online",
        activity=activity,
        players=("PlayerOne",),
        title_id="PPSA17221_00",
        title_name="Minecraft",
        title_image="https://example.com/minecraft.png",
        observed_at=datetime(
            2026, 11, 4, 12, 0,
            tzinfo=timezone.utc,
        ),
    )


def wait_until(predicate, timeout=3.0):
    """Wait for a condition without unbounded blocking."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True

        time.sleep(0.01)

    return predicate()


class RecordingPublisher:
    """Capture MQTT publications in a thread-safe collection."""

    def __init__(self):
        self.lock = threading.Lock()
        self.messages = []
        self.failures_remaining = 0

    def publish(self, topic, payload, qos=0, retain=False):
        """Record a publication or simulate an MQTT failure."""

        with self.lock:
            if self.failures_remaining > 0:
                self.failures_remaining -= 1
                raise RuntimeError("Simulated MQTT failure.")

            self.messages.append({
                "topic": topic,
                "payload": json.loads(payload),
                "qos": qos,
                "retain": retain,
            })

        return Mock()

    def count(self):
        """Return the number of successful publications."""

        with self.lock:
            return len(self.messages)

    def latest(self):
        """Return the latest successfully published message."""

        with self.lock:
            return self.messages[-1] if self.messages else None


class PS5LivePublisherTests(unittest.TestCase):
    """Validate live-state publication reliability."""

    def setUp(self):
        """Create isolated live-state and MQTT components."""

        self.clock = FakeClock()

        self.live_state = PS5LiveState(
            player_name="PlayerOne",
            timeout_seconds=30.0,
            monotonic_clock=self.clock,
        )

        self.mqtt = RecordingPublisher()

        self.worker = PS5LivePublisher(
            publisher=self.mqtt,
            live_state=self.live_state,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

    def tearDown(self):
        """Stop background threads after every test."""

        self.worker.stop()

    def test_initial_unknown_publication(self):
        """Publish UNKNOWN before receiving observations."""

        self.worker.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.count() >= 1)
        )

        message = self.mqtt.latest()

        self.assertEqual(message["topic"], LIVE_STATE_TOPIC)
        self.assertEqual(message["qos"], LIVE_STATE_QOS)
        self.assertEqual(message["retain"], LIVE_STATE_RETAIN)
        self.assertFalse(message["payload"]["available"])
        self.assertEqual(message["payload"]["power"], "UNKNOWN")

    def test_confirmed_gaming_publication(self):
        """Publish confirmed Player gaming activity."""

        self.worker.start()

        self.live_state.observe(make_state())
        self.worker.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and self.mqtt.latest()["payload"]["player_gaming"]
                )
            )
        )

        message = self.mqtt.latest()

        self.assertEqual(message["payload"]["power"], "AWAKE")
        self.assertTrue(message["payload"]["console_active"])
        self.assertTrue(message["payload"]["player_gaming"])

    def test_expired_observation_published_unknown(self):
        """Publish UNKNOWN after the freshness timeout."""

        self.worker.start()

        self.live_state.observe(make_state())
        self.worker.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and self.mqtt.latest()["payload"]["available"]
                )
            )
        )

        self.clock.advance(30.0)
        self.worker.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and not self.mqtt.latest()["payload"]["available"]
                )
            )
        )

        self.assertEqual(
            self.mqtt.latest()["payload"]["power"],
            "UNKNOWN",
        )

    def test_failed_publication_retried(self):
        """Retry an unsuccessful publication."""

        self.mqtt.failures_remaining = 1

        self.worker.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.count() >= 1)
        )

        self.assertEqual(
            self.mqtt.latest()["payload"]["power"],
            "UNKNOWN",
        )

    def test_duplicate_start_rejected(self):
        """Prevent overlapping publication threads."""

        self.worker.start()

        with self.assertRaises(RuntimeError):
            self.worker.start()

    def test_restart_after_shutdown(self):
        """Allow a cleanly stopped worker to restart."""

        self.worker.start()
        self.worker.stop()

        self.assertFalse(self.worker.running)

        self.worker.start()

        self.assertTrue(self.worker.running)

    def test_no_duplicate_unchanged_publications(self):
        """Avoid repeatedly publishing identical snapshots."""

        self.worker.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.count() >= 1)
        )

        initial_count = self.mqtt.count()

        time.sleep(0.15)

        self.assertEqual(self.mqtt.count(), initial_count)

    def test_invalidation_published(self):
        """Publish UNKNOWN immediately after invalidation."""

        self.worker.start()

        self.live_state.observe(make_state())
        self.worker.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and self.mqtt.latest()["payload"]["available"]
                )
            )
        )

        self.live_state.invalidate()
        self.worker.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and not self.mqtt.latest()["payload"]["available"]
                )
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)


class BlockingPublisher:
    """Simulate an MQTT publication awaiting broker confirmation."""

    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.lock = threading.Lock()
        self.messages = []

    def publish(self, topic, payload, qos=0, retain=False):
        """Block the first publication until the test releases it."""

        with self.lock:
            first_publication = len(self.messages) == 0

        if first_publication:
            self.entered.set()

            if not self.release.wait(timeout=5):
                raise TimeoutError(
                    "Simulated MQTT publication timed out."
                )

        with self.lock:
            self.messages.append(json.loads(payload))

        return Mock()


class PS5LivePublisherConcurrencyTests(unittest.TestCase):
    """Validate publication ordering and shutdown safety."""

    def setUp(self):
        """Initialize isolated concurrency test dependencies."""

        self.clock = FakeClock()

        self.live_state = PS5LiveState(
            player_name="PlayerOne",
            monotonic_clock=self.clock,
        )

        self.mqtt = BlockingPublisher()

        self.worker = PS5LivePublisher(
            publisher=self.mqtt,
            live_state=self.live_state,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=0.1,
        )

    def tearDown(self):
        """Release blocked publications before stopping the worker."""

        self.mqtt.release.set()
        self.worker.stop()

    def test_new_state_published_after_blocked_publication(self):
        """A newer observation must eventually be published."""

        self.worker.start()

        self.assertTrue(self.mqtt.entered.wait(timeout=3))

        self.live_state.observe(make_state())
        self.worker.notify()

        self.mqtt.release.set()

        self.assertTrue(
            wait_until(lambda: len(self.mqtt.messages) >= 2)
        )

        self.assertFalse(self.mqtt.messages[0]["available"])
        self.assertTrue(self.mqtt.messages[-1]["available"])
        self.assertEqual(
            self.mqtt.messages[-1]["power"],
            "AWAKE",
        )

    def test_shutdown_timeout_prevents_unsafe_completion(self):
        """A blocked publication must prevent clean shutdown."""

        self.worker.start()

        self.assertTrue(self.mqtt.entered.wait(timeout=3))

        with self.assertRaises(TimeoutError):
            self.worker.stop()

        self.assertTrue(
            self.worker._thread is not None
            and self.worker._thread.is_alive()
        )

        self.mqtt.release.set()

        self.worker.stop()

        self.assertFalse(self.worker.running)


class PS5LivePublisherReconnectionTests(unittest.TestCase):
    """
    Verify MQTT publication epoch handling during reconnection.

    A publication acknowledged after an epoch change must
    not satisfy the publication requirement of the new epoch.
    """

    def test_reconnection_during_blocked_publication(self):
        """
        Republish the latest snapshot after a connection change.

        The first publication is deliberately blocked while
        a new MQTT publication epoch is requested.
        """

        clock = FakeClock()

        live_state = PS5LiveState(
            player_name="PlayerOne",
            monotonic_clock=clock,
        )

        mqtt = BlockingPublisher()

        worker = PS5LivePublisher(
            publisher=mqtt,
            live_state=live_state,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

        worker.start()

        try:
            self.assertTrue(
                mqtt.entered.wait(timeout=3),
                "Initial MQTT publication did not start.",
            )

            # Simulate a successful MQTT reconnection while
            # the previous QoS 1 publication is still pending.
            worker.request_republish()

            # Release the old publication acknowledgement.
            mqtt.release.set()

            self.assertTrue(
                wait_until(
                    lambda: len(mqtt.messages) >= 2,
                    timeout=3,
                ),
                "Live state was not republished after reconnection.",
            )

            # Both publications represent UNKNOWN because no
            # confirmed PS5 observation was supplied.
            self.assertEqual(
                mqtt.messages[0]["power"],
                "UNKNOWN",
            )

            self.assertEqual(
                mqtt.messages[1]["power"],
                "UNKNOWN",
            )

            # The new epoch must have completed successfully.
            self.assertEqual(
                worker._published_epoch,
                worker._publication_epoch,
            )

            self.assertEqual(
                worker.last_published_generation,
                live_state.snapshot().generation,
            )

        finally:
            mqtt.release.set()
            worker.stop()


class PS5LivePublisherBackoffTests(unittest.TestCase):
    """Verify retry throttling during persistent MQTT failures."""

    def test_notifications_do_not_bypass_retry_backoff(self):
        """
        Frequent notifications must not cause rapid retries.

        The MQTT transport is considered connected, but every
        publication fails immediately. The worker should limit
        repeated attempts despite incoming notifications.
        """

        class FailingPublisher:
            """Record every attempted publication."""

            def __init__(self):
                self.lock = threading.Lock()
                self.attempts = []

            def publish(
                self,
                topic,
                payload,
                qos=0,
                retain=False,
            ):
                """Record an attempt and simulate broker failure."""

                with self.lock:
                    self.attempts.append(time.monotonic())

                raise RuntimeError(
                    "Simulated persistent MQTT failure."
                )

            def count(self):
                """Return the number of publication attempts."""

                with self.lock:
                    return len(self.attempts)

        live_state = PS5LiveState(
            player_name="PlayerOne",
        )

        mqtt = FailingPublisher()

        worker = PS5LivePublisher(
            publisher=mqtt,
            live_state=live_state,
            transport_available=lambda: True,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

        worker.start()

        try:
            self.assertTrue(
                wait_until(lambda: mqtt.count() >= 1),
                "Initial publication attempt did not occur.",
            )

            # Generate frequent updates during the first
            # retry interval without changing the MQTT link.
            deadline = time.monotonic() + 0.4

            while time.monotonic() < deadline:
                worker.notify()
                time.sleep(0.01)

            attempts = mqtt.count()

            self.assertEqual(
                attempts,
                1,
                "Notifications bypassed the retry backoff.",
            )

        finally:
            worker.stop()


class PS5LivePublisherBackoffRecoveryTests(unittest.TestCase):
    """Verify immediate recovery after a confirmed MQTT reconnection."""

    def test_reconnection_resets_retry_backoff(self):
        """
        A confirmed reconnection must permit an immediate retry.

        Ordinary notifications remain subject to backoff,
        but request_republish() explicitly starts a new
        publication epoch and resets the retry deadline.
        """

        class RecoveringPublisher:
            """Fail the first publication and record subsequent attempts."""

            def __init__(self):
                self.lock = threading.Lock()
                self.attempts = []
                self.first_attempt = threading.Event()
                self.successful_publication = threading.Event()

            def publish(self, topic, payload, qos=0, retain=False):
                """Simulate one failure followed by successful publication."""

                with self.lock:
                    self.attempts.append(time.monotonic())
                    attempt_number = len(self.attempts)

                if attempt_number == 1:
                    self.first_attempt.set()
                    raise RuntimeError(
                        "Simulated initial MQTT failure."
                    )

                self.successful_publication.set()
                return Mock()

            def count(self):
                """Return the number of publication attempts."""

                with self.lock:
                    return len(self.attempts)

        live_state = PS5LiveState(
            player_name="PlayerOne",
        )

        mqtt = RecoveringPublisher()

        worker = PS5LivePublisher(
            publisher=mqtt,
            live_state=live_state,
            transport_available=lambda: True,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

        worker.start()

        try:
            self.assertTrue(
                mqtt.first_attempt.wait(timeout=3),
                "Initial publication failure did not occur.",
            )

            # Ensure the worker has registered the failure
            # and established a future retry deadline.
            self.assertTrue(
                wait_until(
                    lambda: worker._retry_deadline > time.monotonic()
                ),
                "Retry backoff was not established.",
            )

            self.assertEqual(mqtt.count(), 1)

            recovery_started = time.monotonic()

            # Simulate a confirmed MQTT reconnection.
            worker.request_republish()

            self.assertTrue(
                mqtt.successful_publication.wait(timeout=0.5),
                "Reconnection did not trigger immediate recovery.",
            )

            recovery_elapsed = (
                time.monotonic() - recovery_started
            )

            self.assertLess(recovery_elapsed, 0.5)
            self.assertEqual(mqtt.count(), 2)

            self.assertEqual(
                worker._published_epoch,
                worker._publication_epoch,
            )

        finally:
            worker.stop()
