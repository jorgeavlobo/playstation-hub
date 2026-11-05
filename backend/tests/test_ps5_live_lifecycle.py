"""
PS5 Monitoring Service - Live Lifecycle Tests.

Verify graceful shutdown, final unavailable publication,
publication failures, and repeated shutdown protection.

No production database or MQTT broker is accessed.
"""

import json
import threading
import time
import unittest

from datetime import datetime, timezone

from models import ActivityType, ConsolePower, PS5State
from ps5_live_state import PS5LiveState
from ps5_live_publisher import PS5LivePublisher
from ps5_live_lifecycle import PS5LiveLifecycle


PLAYER_NAME = "PlayerOne"


def make_state():
    """Create a confirmed simulated gaming observation."""

    return PS5State(
        power=ConsolePower.AWAKE,
        device_status="online",
        activity=ActivityType.PLAYING,
        players=(PLAYER_NAME,),
        title_id="PPSA17221_00",
        title_name="Minecraft",
        title_image=None,
        observed_at=datetime.now(timezone.utc),
    )


class RecordingMQTT:
    """Record acknowledged MQTT publications."""

    def __init__(self):
        self.lock = threading.Lock()
        self.messages = []
        self.fail = False

    def publish(self, topic, payload, qos=0, retain=False):
        """Record a publication or simulate failure."""

        if self.fail:
            raise RuntimeError(
                "Simulated MQTT publication failure."
            )

        with self.lock:
            self.messages.append({
                "topic": topic,
                "payload": json.loads(payload),
                "qos": qos,
                "retain": retain,
            })

    def latest(self):
        """Return the latest acknowledged publication."""

        with self.lock:
            return self.messages[-1] if self.messages else None


def wait_until(predicate, timeout=2.0):
    """Wait for a condition with a bounded deadline."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        if predicate():
            return True

        time.sleep(0.01)

    return predicate()


class PS5LiveLifecycleTests(unittest.TestCase):
    """Validate the live-monitoring shutdown coordinator."""

    def setUp(self):
        """Create isolated lifecycle dependencies."""

        self.live_state = PS5LiveState(
            player_name=PLAYER_NAME,
        )

        self.mqtt = RecordingMQTT()

        self.publisher = PS5LivePublisher(
            publisher=self.mqtt,
            live_state=self.live_state,
            poll_interval_seconds=0.02,
            shutdown_timeout_seconds=2.0,
        )

        self.lifecycle = PS5LiveLifecycle(
            live_state=self.live_state,
            publisher=self.publisher,
            timeout_seconds=0.5,
        )

    def tearDown(self):
        """Ensure no publication worker remains active."""

        self.publisher.stop()

    def test_graceful_shutdown_publishes_unknown(self):
        """Shutdown must acknowledge an unavailable snapshot."""

        self.publisher.start()

        self.live_state.observe(make_state())
        self.publisher.notify()

        self.assertTrue(
            wait_until(
                lambda: (
                    self.mqtt.latest() is not None
                    and self.mqtt.latest()["payload"]["available"]
                )
            )
        )

        self.lifecycle.shutdown()

        message = self.mqtt.latest()

        self.assertFalse(message["payload"]["available"])
        self.assertEqual(message["payload"]["power"], "UNKNOWN")
        self.assertEqual(message["qos"], 1)
        self.assertTrue(message["retain"])
        self.assertFalse(self.publisher.running)

    def test_publication_failure_prevents_successful_shutdown(self):
        """Unconfirmed final publication must raise a timeout."""

        self.publisher.start()

        self.assertTrue(
            wait_until(lambda: self.mqtt.latest() is not None)
        )

        self.mqtt.fail = True

        result = self.lifecycle.shutdown()

        self.assertFalse(result.confirmed)
        self.assertTrue(result.degraded)
        self.assertFalse(self.publisher.running)

    def test_repeated_shutdown_rejected(self):
        """A second shutdown attempt must be rejected."""

        self.publisher.start()

        self.lifecycle.shutdown()

        with self.assertRaises(RuntimeError):
            self.lifecycle.shutdown()

    def test_shutdown_requires_running_publisher(self):
        """Shutdown must reject an inactive publisher."""

        with self.assertRaises(RuntimeError):
            self.lifecycle.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
