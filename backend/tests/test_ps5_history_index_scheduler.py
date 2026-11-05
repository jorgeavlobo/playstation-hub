"""
PS5 Monitoring Service - History Index Scheduler Tests.

Verify initial publication, periodic refresh, reconnection,
and recovery from transient index publication failures.

All tests use simulated application dependencies and clocks.
No MQTT broker or production SQLite database is accessed.
"""

import unittest
from unittest.mock import Mock, patch

from main import (
    PS5MonitoringApplication,
    HISTORY_INDEX_INTERVAL_SECONDS,
)


class HistoryIndexSchedulerTests(unittest.TestCase):
    """Validate independent history index scheduling."""

    def setUp(self):
        """Create an isolated application with mocked collaborators."""

        self.application = PS5MonitoringApplication()

        self.application._mqtt = Mock()
        self.application._mqtt.connected = True
        self.application._mqtt.connection_generation = 1

        self.application._publisher = Mock()
        self.application._publish_availability = Mock()

        self.clock = 1000.0

        self.clock_patch = patch(
            "main.time.monotonic",
            side_effect=lambda: self.clock,
        )

        self.clock_patch.start()

    def tearDown(self):
        """Restore the original monotonic clock."""

        self.clock_patch.stop()

    def test_initial_publication(self):
        """Publish the index after the first MQTT connection."""

        self.application._publish_updates()

        self.application._publisher.publish_history_index.assert_called_once()

        self.assertEqual(
            self.application._last_history_index_update,
            self.clock,
        )

    def test_no_early_periodic_publication(self):
        """Avoid refreshing the index before five minutes."""

        self.application._publish_updates()

        self.clock += HISTORY_INDEX_INTERVAL_SECONDS - 1

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            1,
        )

    def test_refresh_after_five_minutes(self):
        """Refresh the index when the configured interval expires."""

        self.application._publish_updates()

        self.clock += HISTORY_INDEX_INTERVAL_SECONDS

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            2,
        )

    def test_republication_after_reconnection(self):
        """Republish the index after an MQTT connection change."""

        self.application._publish_updates()

        self.application._mqtt.connection_generation = 2

        self.clock += 10

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            2,
        )

    def test_initial_failure_is_retried(self):
        """Retry an unsuccessful initial index publication."""

        self.application._publisher.publish_history_index.side_effect = [
            RuntimeError("Simulated publication failure."),
            None,
        ]

        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.assertIsNone(
            self.application._last_history_index_update
        )

        # The failed publication must not retry immediately.
        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            1,
        )

        # Advance to the exact retry deadline.
        self.clock += 30.0

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            2,
        )

        self.assertEqual(
            self.application._last_history_index_update,
            self.clock,
        )

    def test_offline_transport_prevents_publication(self):
        """Never publish the index while MQTT is disconnected."""

        self.application._mqtt.connected = False

        self.application._publish_updates()

        self.application._publisher.publish_history_index.assert_not_called()





class HistoryIndexRetryTests(unittest.TestCase):
    """
    Verify retry scheduling using the existing test fixtures.

    Reuse setup and cleanup without inheriting test methods.
    """

    setUp = HistoryIndexSchedulerTests.setUp
    tearDown = HistoryIndexSchedulerTests.tearDown
    """Verify bounded retry scheduling after MQTT failures."""

    def test_failure_does_not_retry_early(self):
        """Repeated updates must respect the retry deadline."""

        self.application._publisher.publish_history_index.side_effect = (
            RuntimeError("Simulated index failure.")
        )

        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.assertEqual(
            self.application._next_history_index_attempt,
            self.clock + 30.0,
        )

        self.clock += 29.0

        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            1,
        )

    def test_retry_at_exact_deadline(self):
        """Retry must occur when the thirty-second deadline expires."""

        self.application._publisher.publish_history_index.side_effect = [
            RuntimeError("Simulated initial failure."),
            None,
        ]

        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.clock += 30.0

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            2,
        )

        self.assertEqual(
            self.application._last_history_index_update,
            self.clock,
        )

        self.assertEqual(
            self.application._next_history_index_attempt,
            self.clock + HISTORY_INDEX_INTERVAL_SECONDS,
        )

    def test_reconnection_resets_retry_deadline(self):
        """A new MQTT connection must permit immediate publication."""

        self.application._publisher.publish_history_index.side_effect = [
            RuntimeError("Simulated initial failure."),
            None,
        ]

        with patch("main.LOGGER.exception"):
            self.application._publish_updates()

        self.clock += 5.0
        self.application._mqtt.connection_generation = 2

        self.application._publish_updates()

        self.assertEqual(
            self.application._publisher.publish_history_index.call_count,
            2,
        )

        self.assertEqual(
            self.application._last_history_index_update,
            self.clock,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
