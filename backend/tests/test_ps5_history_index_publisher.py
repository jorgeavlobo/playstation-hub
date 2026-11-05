"""
PS5 Monitoring Service - History Index MQTT Publisher Tests.

Verify the 36-month history index publication contract.

All tests use simulated statistics and MQTT clients.
No production SQLite database or MQTT broker is accessed.
"""

import json
import unittest

from dataclasses import fields
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from mqtt_publisher import StatisticsPublisher
from usage_statistics import UsageSummary, shift_month


HISTORY_INDEX_TOPIC = "ps5-monitor/history/index"


def make_summary(month_start, console_seconds=0, gaming_seconds=0,
                 gaming_sessions=0):
    """Construct a complete immutable monthly usage summary."""

    values = {
        field.name: 0
        for field in fields(UsageSummary)
    }

    values.update({
        "period_start": month_start.isoformat(),
        "period_end": shift_month(month_start, 1).isoformat(),
        "console_seconds": console_seconds,
        "gaming_seconds": gaming_seconds,
        "gaming_sessions": gaming_sessions,
    })

    return UsageSummary(**values)


def make_summaries():
    """Create 36 consecutive months ending in November 2026."""

    start = date(2023, 12, 1)

    summaries = [
        make_summary(shift_month(start, offset))
        for offset in range(36)
    ]

    # Include a historical gaming month and a current gaming month.
    summaries[1] = make_summary(
        date(2024, 1, 1),
        console_seconds=7200,
        gaming_seconds=5400,
        gaming_sessions=2,
    )

    summaries[-1] = make_summary(
        date(2026, 11, 1),
        console_seconds=3600,
        gaming_seconds=1800,
        gaming_sessions=1,
    )

    return summaries


class HistoryIndexPublisherTests(unittest.TestCase):
    """Validate independent historical index MQTT publication."""

    def setUp(self):
        """Create isolated publisher dependencies."""

        self.client = Mock()
        self.client.publish.return_value = SimpleNamespace(rc=0)

        self.statistics = Mock()
        self.statistics.last_thirty_six_months.return_value = (
            make_summaries()
        )

        # Avoid initializing unrelated publisher dependencies.
        # The tested method only needs these two collaborators.
        self.publisher = object.__new__(StatisticsPublisher)
        self.publisher._client = self.client
        self.publisher._statistics = self.statistics

        self.reference = datetime(
            2026, 11, 4, 12, 0, tzinfo=timezone.utc
        )

    def test_publishes_valid_36_month_payload(self):
        """Publish a complete chronological history index."""

        result = self.publisher.publish_history_index(
            now=self.reference
        )

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["month_count"], 36)
        self.assertEqual(len(result["months"]), 36)

        self.assertEqual(
            result["months"][0]["month"], "2023-12"
        )
        self.assertEqual(
            result["months"][-1]["month"], "2026-11"
        )

        self.assertTrue(result["months"][1]["has_gaming"])
        self.assertFalse(result["months"][2]["has_gaming"])

    def test_uses_correct_mqtt_delivery_settings(self):
        """Require the dedicated topic, QoS 1, and retention."""

        self.publisher.publish_history_index(
            now=self.reference
        )

        self.client.publish.assert_called_once()

        args = self.client.publish.call_args

        self.assertEqual(args.args[0], HISTORY_INDEX_TOPIC)
        self.assertEqual(args.kwargs["qos"], 1)
        self.assertIs(args.kwargs["retain"], True)

        payload = json.loads(args.args[1])

        self.assertEqual(payload["month_count"], 36)
        self.assertEqual(len(payload["months"]), 36)

    def test_uses_existing_statistics_service(self):
        """Reuse confirmed statistics with the correct local date."""

        self.publisher.publish_history_index(
            now=self.reference
        )

        self.statistics.last_thirty_six_months.assert_called_once_with(
            reference_day=date(2026, 11, 4)
        )

    def test_rejects_mqtt_publication_failure(self):
        """Report unsuccessful MQTT publication results."""

        self.client.publish.return_value = SimpleNamespace(rc=1)

        with self.assertRaises(RuntimeError):
            self.publisher.publish_history_index(
                now=self.reference
            )

    def test_rejects_invalid_historical_collection(self):
        """Never publish an incomplete historical index."""

        self.statistics.last_thirty_six_months.return_value = (
            make_summaries()[:-1]
        )

        with self.assertRaises(ValueError):
            self.publisher.publish_history_index(
                now=self.reference
            )

        self.client.publish.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
