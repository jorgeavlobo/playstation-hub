"""
PS5 Monitoring Service - Historical Request Models.

This module provides strict validation for calendar-month
requests received through MQTT.

Responsibilities:
    - Parse requested calendar periods.
    - Reject malformed or unsupported requests.
    - Prevent requests for future periods.
    - Represent validated requests as immutable objects.

This module deliberately contains no MQTT connections,
database access, or background threads.

The request-processing worker will be implemented separately.
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo


LOCAL_TIMEZONE = ZoneInfo("Europe/Lisbon")

PERIOD_PATTERN = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>0[1-9]|1[0-2])$"
)

MINIMUM_SUPPORTED_YEAR = 2020


@dataclass(frozen=True, slots=True)
class HistoryRequest:
    """
    Represent one validated historical calendar-month request.

    Attributes:
        year:
            Requested calendar year.

        month:
            Requested calendar month, between 1 and 12.

        period:
            Canonical YYYY-MM representation.
    """

    year: int
    month: int

    def __post_init__(self) -> None:
        """Validate the immutable request fields."""

        if not isinstance(self.year, int) or isinstance(
            self.year, bool
        ):
            raise ValueError("Year must be an integer.")

        if not isinstance(self.month, int) or isinstance(
            self.month, bool
        ):
            raise ValueError("Month must be an integer.")

        if self.year < MINIMUM_SUPPORTED_YEAR:
            raise ValueError(
                "Requested year is earlier than supported."
            )

        if not 1 <= self.month <= 12:
            raise ValueError(
                "Month must be between 1 and 12."
            )

        current = datetime.now(
            LOCAL_TIMEZONE
        ).date()

        requested = date(
            self.year,
            self.month,
            1,
        )

        current_month = date(
            current.year,
            current.month,
            1,
        )

        if requested > current_month:
            raise ValueError(
                "Future calendar months are not supported."
            )

    @property
    def period(self) -> str:
        """Return the canonical calendar period."""

        return f"{self.year:04d}-{self.month:02d}"

    @property
    def start_day(self) -> date:
        """Return the first day of the requested month."""

        return date(
            self.year,
            self.month,
            1,
        )

    @property
    def end_day(self) -> date:
        """
        Return the exclusive end date of the requested month.

        The returned date is the first day of the next month.
        """

        if self.month == 12:
            return date(
                self.year + 1,
                1,
                1,
            )

        return date(
            self.year,
            self.month + 1,
            1,
        )

    @classmethod
    def parse(
        cls,
        value: str,
    ) -> HistoryRequest:
        """
        Parse and validate a YYYY-MM period.

        The input must match the canonical format exactly.
        Whitespace and alternative date formats are rejected.
        """

        if not isinstance(value, str):
            raise ValueError(
                "Requested period must be a string."
            )

        match = PERIOD_PATTERN.fullmatch(value)

        if match is None:
            raise ValueError(
                "Period must use YYYY-MM format."
            )

        return cls(
            year=int(match.group("year")),
            month=int(match.group("month")),
        )
