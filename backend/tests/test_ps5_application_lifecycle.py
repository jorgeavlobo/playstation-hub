"""
PS5 Monitoring Service - Application Lifecycle Tests.

Validate shutdown dependency ordering, partial startup
recovery, and publication worker safety.

All external components are simulated.
No production SQLite database or MQTT broker is accessed.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from main import PS5MonitoringApplication


class ApplicationLifecycleTests(unittest.TestCase):
    """Verify coordinated application shutdown."""

    def setUp(self):
        """Create an application with simulated dependencies."""

        self.events = []
        self.application = PS5MonitoringApplication()

        self.application._database = Mock()
        self.application._tracker = Mock()
        self.application._history_worker = Mock()
        self.application._live_publisher = Mock()
        self.application._live_lifecycle = Mock()
        self.application._mqtt = Mock()

        self.application._mqtt.connected = True
        self.application._live_publisher.running = True

        self.application._live_lifecycle.shutdown.return_value = (
            SimpleNamespace(
                confirmed=True,
                degraded=False,
                reason="Final state acknowledged.",
            )
        )

        def record(name):
            """Record a lifecycle operation."""

            return lambda *args, **kwargs: self.events.append(name)

        self.application._mqtt.begin_shutdown.side_effect = record(
            "mqtt_barrier"
        )

        self.application._history_worker.stop.side_effect = record(
            "history_stop"
        )

        self.application._live_lifecycle.shutdown.side_effect = (
            lambda: (
                self.events.append("live_shutdown")
                or SimpleNamespace(
                    confirmed=True,
                    degraded=False,
                    reason="Acknowledged.",
                )
            )
        )

        self.application._mqtt.stop.side_effect = record(
            "mqtt_stop"
        )

        self.application._tracker.shutdown.side_effect = record(
            "tracker_shutdown"
        )

        self.application._database.close.side_effect = record(
            "database_close"
        )

        self.application._publish_availability = Mock(
            side_effect=record("availability_offline")
        )

    def test_shutdown_dependency_order(self):
        """Workers must stop before MQTT and SQLite."""

        self.application._shutdown()

        self.assertEqual(
            self.events,
            [
                "mqtt_barrier",
                "history_stop",
                "live_shutdown",
                "availability_offline",
                "mqtt_stop",
                "tracker_shutdown",
                "database_close",
            ],
        )

    def test_partial_startup_without_live_worker(self):
        """An unstarted live worker must not invoke lifecycle shutdown."""

        self.application._live_publisher.running = False

        self.application._shutdown()

        self.application._live_lifecycle.shutdown.assert_not_called()
        self.application._live_publisher.stop.assert_called_once()

    def test_history_shutdown_failure_preserves_dependencies(self):
        """A failed history worker must prevent unsafe resource cleanup."""

        self.application._history_worker.stop.side_effect = RuntimeError(
            "Simulated history shutdown failure."
        )

        with self.assertRaises(RuntimeError):
            self.application._shutdown()

        self.application._mqtt.stop.assert_not_called()
        self.application._database.close.assert_not_called()

    def test_live_shutdown_failure_preserves_mqtt(self):
        """A failed live shutdown must not disconnect MQTT."""

        self.application._live_lifecycle.shutdown.side_effect = RuntimeError(
            "Simulated live shutdown failure."
        )

        with self.assertRaises(RuntimeError):
            self.application._shutdown()

        self.application._mqtt.stop.assert_not_called()
        self.application._database.close.assert_not_called()

    def test_empty_application_shutdown(self):
        """Shutdown must tolerate initialization failure."""

        application = PS5MonitoringApplication()

        application._shutdown()

        self.assertIsNone(application._database)
        self.assertIsNone(application._mqtt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
