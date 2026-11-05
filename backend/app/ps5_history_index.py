"""
PS5 Monitoring Service - Historical Activity Index.

Build a compact, validated index of confirmed monthly usage.

The index is independent of MQTT, SQLite, and Home Assistant.
It preserves empty calendar months and provides a reliable
foundation for intelligent dashboard navigation.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from typing import Any

from usage_statistics import UsageSummary


HISTORY_INDEX_SCHEMA_VERSION = 1
HISTORY_INDEX_MONTH_COUNT = 36


class PS5HistoryIndex:
    """
    Build and validate a chronological monthly activity index.

    All durations remain in seconds to avoid rounding errors.
    The frontend is responsible for presentation formatting.
    """

    def __init__(
        self,
        month_count: int = HISTORY_INDEX_MONTH_COUNT,
    ) -> None:
        """Initialize the historical index builder."""

        if (
            isinstance(month_count, bool)
            or not isinstance(month_count, int)
            or not 1 <= month_count <= HISTORY_INDEX_MONTH_COUNT
        ):
            raise ValueError(
                "Month count must be an integer between 1 and 36."
            )

        self._month_count = month_count

    @staticmethod
    def _validate_duration(value: Any, field: str) -> float:
        """Validate a finite, non-negative duration."""

        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise ValueError(f"Invalid duration: {field}")

        result = float(value)

        if not math.isfinite(result) or result < 0:
            raise ValueError(f"Invalid duration: {field}")

        return result

    @staticmethod
    def _validate_sessions(value: Any) -> int:
        """Validate a non-negative integer session count."""

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError("Invalid gaming session count.")

        return value

    @staticmethod
    def _month_from_summary(summary: UsageSummary) -> str:
        """Extract the calendar month from a usage summary."""

        try:
            start = date.fromisoformat(summary.period_start)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Invalid summary period start."
            ) from error

        if start.day != 1:
            raise ValueError(
                "Summary must start on the first day of a month."
            )

        # The exclusive end date must be the first day
        # of the immediately following calendar month.
        try:
            end = date.fromisoformat(summary.period_end)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Invalid summary period end."
            ) from error

        if start.month == 12:
            expected_end = date(start.year + 1, 1, 1)
        else:
            expected_end = date(
                start.year,
                start.month + 1,
                1,
            )

        if end != expected_end:
            raise ValueError(
                "Summary must cover exactly one calendar month."
            )

        return start.strftime("%Y-%m")

    def build(
        self,
        summaries: list[UsageSummary],
    ) -> dict:
        """
        Build a compact chronological historical index.

        A month with console activity but no gaming remains
        visible in the index.

        Empty months are preserved with zero totals.

        The caller supplies the complete calendar window.
        """

        if not isinstance(summaries, list):
            raise TypeError(
                "Historical summaries must be a list."
            )

        if len(summaries) != self._month_count:
            raise ValueError(
                f"Expected exactly {self._month_count} months."
            )

        months = []
        previous_month_index = None

        for summary in summaries:
            if not isinstance(summary, UsageSummary):
                raise TypeError(
                    "Expected UsageSummary instances."
                )

            month = self._month_from_summary(summary)

            year, month_number = map(
                int,
                month.split("-"),
            )

            month_index = year * 12 + month_number - 1

            if previous_month_index is not None:
                if month_index != previous_month_index + 1:
                    raise ValueError(
                        "Historical months must be consecutive."
                    )

            previous_month_index = month_index

            console_seconds = self._validate_duration(
                summary.console_seconds,
                "console_seconds",
            )

            gaming_seconds = self._validate_duration(
                summary.gaming_seconds,
                "gaming_seconds",
            )

            gaming_sessions = self._validate_sessions(
                summary.gaming_sessions
            )

            if gaming_seconds > console_seconds:
                raise ValueError(
                    "Gaming duration exceeds console duration."
                )

            has_gaming = (
                gaming_seconds > 0
                or gaming_sessions > 0
            )

            has_activity = (
                console_seconds > 0
                or has_gaming
            )

            months.append({
                "month": month,
                "console_seconds": console_seconds,
                "gaming_seconds": gaming_seconds,
                "gaming_sessions": gaming_sessions,
                "has_activity": has_activity,
                "has_gaming": has_gaming,
            })

        return {
            "schema_version": HISTORY_INDEX_SCHEMA_VERSION,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "month_count": self._month_count,
            "months": months,
        }
