"""
PS5 Monitoring Service - Degraded Shutdown Tests.

Validate confirmed and degraded shutdown outcomes using
isolated MQTT simulations.

No production database or MQTT broker is accessed.
"""

import json
import threading
import time
import unittest

from ps5_live_state import PS5LiveState
from ps5_live_publisher import PS5LivePublisher
from ps5_live_lifecycle import PS5LiveLifecycle


class FakeMQTT:
    """Simulate an MQTT transport with controllable availability."""

    def __init__(self):
        self.connected = True
        self.messages = []
        self.lock = threading.Lock()

    def publish(self, topic, payload, qos=0, retain=False):
        """Record confirmed publications when transport is available."""

        with self.lock:
            if not self.connected:
                raise RuntimeError("MQTT transport unavailable.")

            self.messages.append(json.loads(payload))

    def latest(self):
        """Return the latest acknowledged MQTT payload."""

        with self.lock:
            return self.messages[-1] if self.messages else None


def wait_until(predicate, timeout=2.0):
    """Wait for a condition using a bounded monotonic deadline."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True

        time.sleep(0.01)

    return predicate()


class DegradedShutdownTests(unittest.TestCase):
    """Verify lifecycle outcomes with simulated MQTT availability."""

    def setUp(self):
        """Create isolated monitoring components."""

        self.mqtt = FakeMQTT()

        self.live_state = PS5LiveState(
            player_name="PlayerOne",
        )

        self.publisher = PS5LivePublisher(
            publisher=self.mqtt,
            live_state=self.live_state,
            transport_available=lambda: self.mqtt.connected,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

        self.lifecycle = PS5LiveLifecycle(
            live_state=self.live_state,
            publisher=self.publisher,
            transport_available=lambda: self.mqtt.connected,
            timeout_seconds=0.2,
        )

    def tearDown(self):
        """Ensure background workers have terminated."""

        self.publisher.stop()

    def test_confirmed_shutdown(self):
        """An acknowledged final snapshot must be confirmed."""

        self.publisher.start()

        result = self.lifecycle.shutdown()

        self.assertTrue(result.confirmed)
        self.assertFalse(result.degraded)

        message = self.mqtt.latest()

        self.assertIsNotNone(message)
        self.assertFalse(message["available"])
        self.assertEqual(message["power"], "UNKNOWN")
        self.assertFalse(self.publisher.running)

    def test_degraded_shutdown_when_mqtt_unavailable(self):
        """An unavailable transport must produce a degraded result."""

        self.publisher.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.latest() is not None)
        )

        self.mqtt.connected = False

        result = self.lifecycle.shutdown()

        self.assertFalse(result.confirmed)
        self.assertTrue(result.degraded)
        self.assertFalse(self.publisher.running)
        self.assertTrue(self.live_state.frozen)

    def test_unconfirmed_shutdown_while_connected_raises(self):
        """Publication failure must not be reported as degraded."""

        self.publisher.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.latest() is not None)
        )

        original_publish = self.mqtt.publish

        def failing_publish(*args, **kwargs):
            """Simulate publication failure with transport connected."""

            raise RuntimeError("Simulated publication failure.")

        self.mqtt.publish = failing_publish

        result = self.lifecycle.shutdown()

        self.assertFalse(result.confirmed)
        self.assertTrue(result.degraded)
        self.assertTrue(self.live_state.frozen)
        self.assertFalse(self.publisher.running)

        # Restore the simulated transport for safe test cleanup.
        self.mqtt.publish = original_publish


if __name__ == "__main__":
    unittest.main(verbosity=2)
