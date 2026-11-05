"""
PS5 Monitoring Service - Historical Activity Index Tests.

Validate chronological ordering, empty months, gaming activity,
console-only activity, and invalid historical statistics.

No production database or MQTT broker is accessed.
"""

import unittest

from dataclasses import fields, replace
from datetime import date

from ps5_history_index import PS5HistoryIndex
from usage_statistics import UsageSummary, shift_month


def make_summary(
    month_start: date,
    console_seconds: float = 0.0,
    gaming_seconds: float = 0.0,
    gaming_sessions: int = 0,
) -> UsageSummary:
    """
    Construct a complete UsageSummary for one calendar month.

    All optional statistics default to zero. The supplied
    activity values are explicitly assigned.
    """

    next_start = shift_month(month_start, 1)

    values = {
        field.name: 0
        for field in fields(UsageSummary)
    }

    values.update({
        "period_start": month_start.isoformat(),
        "period_end": next_start.isoformat(),
        "console_seconds": console_seconds,
        "gaming_seconds": gaming_seconds,
        "gaming_sessions": gaming_sessions,
    })

    return UsageSummary(**values)


def make_months():
    """Create 36 consecutive months ending in November 2026."""

    start = date(2023, 12, 1)

    return [
        make_summary(shift_month(start, offset))
        for offset in range(36)
    ]


class PS5HistoryIndexTests(unittest.TestCase):
    """Validate the compact historical activity index."""

    def setUp(self):
        """Initialize an independent 36-month index builder."""

        self.builder = PS5HistoryIndex()
        self.summaries = make_months()

    def test_thirty_six_consecutive_months(self):
        """Preserve the complete chronological calendar window."""

        result = self.builder.build(self.summaries)

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["month_count"], 36)
        self.assertEqual(len(result["months"]), 36)

        self.assertEqual(
            result["months"][0]["month"],
            "2023-12",
        )

        self.assertEqual(
            result["months"][-1]["month"],
            "2026-11",
        )

    def test_empty_months_are_preserved(self):
        """Months without confirmed usage must remain present."""

        result = self.builder.build(self.summaries)

        self.assertTrue(
            all(
                not month["has_activity"]
                and not month["has_gaming"]
                for month in result["months"]
            )
        )

    def test_console_only_activity(self):
        """Console usage without gaming must not count as gaming."""

        self.summaries[10] = make_summary(
            date(2024, 10, 1),
            console_seconds=3600,
        )

        result = self.builder.build(self.summaries)
        month = result["months"][10]

        self.assertTrue(month["has_activity"])
        self.assertFalse(month["has_gaming"])
        self.assertEqual(month["console_seconds"], 3600)

    def test_gaming_activity(self):
        """Confirmed gaming sessions must enable gaming navigation."""

        self.summaries[-1] = make_summary(
            date(2026, 11, 1),
            console_seconds=7200,
            gaming_seconds=5400,
            gaming_sessions=2,
        )

        result = self.builder.build(self.summaries)
        month = result["months"][-1]

        self.assertTrue(month["has_activity"])
        self.assertTrue(month["has_gaming"])
        self.assertEqual(month["gaming_sessions"], 2)

    def test_nonconsecutive_months_rejected(self):
        """Reject missing or duplicated calendar periods."""

        self.summaries[10] = make_summary(
            date(2024, 11, 1)
        )

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries)

    def test_gaming_exceeding_console_rejected(self):
        """Reject inconsistent confirmed durations."""

        self.summaries[-1] = make_summary(
            date(2026, 11, 1),
            console_seconds=100,
            gaming_seconds=200,
        )

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries)

    def test_invalid_month_count_rejected(self):
        """Require exactly the configured number of months."""

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries[:-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class PS5HistoryIndexCalendarBoundaryTests(unittest.TestCase):
    """Validate exact calendar boundaries in historical summaries."""

    def setUp(self):
        """Create a complete 36-month historical collection."""

        self.builder = PS5HistoryIndex()
        self.summaries = make_months()

    def test_invalid_period_end_rejected(self):
        """Reject a summary ending before the next calendar month."""

        summary = self.summaries[-1]

        self.summaries[-1] = replace(
            summary,
            period_end="2026-11-30",
        )

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries)

    def test_invalid_period_start_rejected(self):
        """Reject a summary beginning after the first day."""

        summary = self.summaries[-1]

        self.summaries[-1] = replace(
            summary,
            period_start="2026-11-02",
        )

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries)

    def test_december_to_january_boundary(self):
        """Accept the correct transition between calendar years."""

        result = self.builder.build(self.summaries)

        december = next(
            month
            for month in result["months"]
            if month["month"] == "2025-12"
        )

        self.assertEqual(december["month"], "2025-12")

        january = next(
            month
            for month in result["months"]
            if month["month"] == "2026-01"
        )

        self.assertEqual(january["month"], "2026-01")

    def test_invalid_period_end_format_rejected(self):
        """Reject an invalid exclusive end date."""

        summary = self.summaries[-1]

        self.summaries[-1] = replace(
            summary,
            period_end="invalid-date",
        )

        with self.assertRaises(ValueError):
            self.builder.build(self.summaries)
