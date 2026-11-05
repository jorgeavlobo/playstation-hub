"""
PS5 Monitoring Service - 36-Month History Tests.

Validate calendar boundaries, chronological ordering,
backward compatibility, and invalid input handling.

No production SQLite database or MQTT broker is accessed.
"""

import unittest

from datetime import date
from unittest.mock import Mock

from usage_statistics import StatisticsService


class ThirtySixMonthHistoryTests(unittest.TestCase):
    """Verify configurable historical calendar windows."""

    def setUp(self):
        """Create an isolated statistics service without SQLite."""

        self.statistics = object.__new__(StatisticsService)
        self.statistics.summarize = Mock(
            side_effect=lambda start, end: {
                "start": start,
                "end": end,
            }
        )

    def test_thirty_six_month_window(self):
        """Return exactly 36 consecutive calendar months."""

        result = self.statistics.last_thirty_six_months(
            reference_day=date(2026, 11, 4),
        )

        self.assertEqual(len(result), 36)
        self.assertEqual(result[0]["start"], date(2023, 12, 1))
        self.assertEqual(result[-1]["start"], date(2026, 11, 1))
        self.assertEqual(result[-1]["end"], date(2026, 12, 1))

    def test_twelve_month_backward_compatibility(self):
        """Preserve the existing twelve-month calendar range."""

        result = self.statistics.last_twelve_months(
            reference_day=date(2026, 11, 4),
        )

        self.assertEqual(len(result), 12)
        self.assertEqual(result[0]["start"], date(2025, 12, 1))
        self.assertEqual(result[-1]["start"], date(2026, 11, 1))

    def test_single_month(self):
        """Support a one-month historical window."""

        result = self.statistics.last_n_months(
            count=1,
            reference_day=date(2026, 11, 4),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], date(2026, 11, 1))

    def test_calendar_year_transition(self):
        """Preserve chronological ordering across year boundaries."""

        result = self.statistics.last_n_months(
            count=4,
            reference_day=date(2026, 2, 15),
        )

        months = [
            entry["start"].strftime("%Y-%m")
            for entry in result
        ]

        self.assertEqual(
            months,
            ["2025-11", "2025-12", "2026-01", "2026-02"],
        )

    def test_invalid_month_counts(self):
        """Reject unsupported month counts and boolean values."""

        for count in (0, -1, 37, True, False, 1.5, "36", None):
            with self.subTest(count=count):
                with self.assertRaises(ValueError):
                    self.statistics.last_n_months(
                        count=count,
                        reference_day=date(2026, 11, 4),
                    )

    def test_all_months_are_aggregated(self):
        """Every month must use the existing summarize method."""

        self.statistics.last_thirty_six_months(
            reference_day=date(2026, 11, 4),
        )

        self.assertEqual(
            self.statistics.summarize.call_count,
            36,
        )

    def test_leap_year_february(self):
        """Handle February correctly during a leap year."""

        result = self.statistics.last_n_months(
            count=2,
            reference_day=date(2024, 3, 10),
        )

        self.assertEqual(
            result[0]["start"],
            date(2024, 2, 1),
        )

        self.assertEqual(
            result[0]["end"],
            date(2024, 3, 1),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
