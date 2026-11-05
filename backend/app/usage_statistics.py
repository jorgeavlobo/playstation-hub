"""
PS5 Monitoring Service - Historical Statistics.

Calculate console usage, player gaming time, game rankings,
session counts, and calendar-based reports.

All persisted timestamps are UTC. Calendar boundaries are
interpreted using Europe/Lisbon, including daylight-saving changes.

Open sessions are counted only through their latest persisted
checkpoint. Missing checkpoints contribute zero duration.

No historical statistics are cached or duplicated in SQLite.
"""

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from database import Database
from models import SessionType, UsageSession


LOCAL_TIMEZONE = ZoneInfo("Europe/Lisbon")
UTC = timezone.utc


@dataclass(frozen=True)
class UsageSummary:
    """Statistics for one calendar period."""

    period_start: str
    period_end: str
    console_seconds: float
    gaming_seconds: float
    non_gaming_seconds: float
    console_sessions: int
    gaming_sessions: int
    console_active_days: int
    gaming_active_days: int
    average_daily_console_seconds: float
    average_daily_gaming_seconds: float

    def to_dict(self) -> dict:
        """Return a JSON-compatible summary."""
        return asdict(self)


@dataclass(frozen=True)
class GameSummary:
    """Aggregated usage for a specific game."""

    title_id: str | None
    title_name: str
    duration_seconds: float
    session_count: int
    title_image: str | None = None

    def to_dict(self) -> dict:
        """Return a JSON-compatible game summary."""
        return asdict(self)


def local_midnight(day: date) -> datetime:
    """
    Return local midnight converted to UTC.

    Constructing midnight independently for each calendar date
    correctly handles 23-hour and 25-hour DST transition days.
    """

    return datetime.combine(
        day,
        time.min,
        tzinfo=LOCAL_TIMEZONE,
    ).astimezone(UTC)


def next_month(day: date) -> date:
    """Return the first day of the following calendar month."""

    if day.month == 12:
        return date(day.year + 1, 1, 1)

    return date(day.year, day.month + 1, 1)


def shift_month(day: date, offset: int) -> date:
    """Return the first day of a month at the requested offset."""

    month_index = day.year * 12 + day.month - 1 + offset

    year, month_zero_based = divmod(month_index, 12)

    return date(year, month_zero_based + 1, 1)


class StatisticsService:
    """
    Calculate historical statistics from the session database.

    This service performs read-only queries and does not change
    sessions, checkpoints, or monitoring events.
    """

    def __init__(
        self,
        database: Database,
        player_name: str,
    ) -> None:
        """Initialize the statistics service."""

        if not player_name.strip():
            raise ValueError("Player name cannot be empty.")

        self._database = database
        self._player_name = player_name

    def _effective_end(
        self,
        session: UsageSession,
    ) -> datetime:
        """
        Return the last confirmed endpoint of a session.

        Completed sessions use their stored end timestamp.
        Open sessions use their persisted checkpoint only.
        """

        if session.ended_at is not None:
            return session.ended_at

        if session.session_id is None:
            return session.started_at

        checkpoint = self._database.get_checkpoint(
            session.session_id
        )

        return checkpoint or session.started_at

    def _intervals(
        self,
        start: datetime,
        end: datetime,
    ):
        """
        Yield session intersections with a requested UTC period.

        Each yielded interval is half-open and contains only
        confirmed time within the requested period.
        """

        if end <= start:
            raise ValueError("Period end must follow its start.")

        sessions = self._database.get_sessions(start, end)

        for session in sessions:
            if (
                session.session_type == SessionType.GAMING
                and session.player_name != self._player_name
            ):
                continue

            effective_end = self._effective_end(session)

            interval_start = max(session.started_at, start)
            interval_end = min(effective_end, end)

            if interval_end > interval_start:
                yield session, interval_start, interval_end

    @staticmethod
    def _days_covered(
        start: datetime,
        end: datetime,
    ) -> set[date]:
        """
        Return local calendar dates touched by a positive interval.

        The end is exclusive. An interval ending exactly at
        midnight does not count as activity on the next day.
        """

        if end <= start:
            return set()

        first_day = start.astimezone(LOCAL_TIMEZONE).date()

        # Subtract a microsecond to preserve half-open semantics.
        last_day = (
            end - timedelta(microseconds=1)
        ).astimezone(LOCAL_TIMEZONE).date()

        days = set()
        current = first_day

        while current <= last_day:
            days.add(current)
            current += timedelta(days=1)

        return days

    def summarize(
        self,
        start_day: date,
        end_day: date,
    ) -> UsageSummary:
        """
        Summarize a half-open range of local calendar dates.

        Example:
            summarize(date(2026, 11, 1), date(2026, 12, 1))

        The daily average uses the number of calendar days in
        the requested range, including days without activity.

        For the current incomplete month, callers may instead
        request a period ending tomorrow to obtain a month-to-date
        average.
        """

        if end_day <= start_day:
            raise ValueError("End date must follow start date.")

        start = local_midnight(start_day)
        end = local_midnight(end_day)

        console_seconds = 0.0
        gaming_seconds = 0.0

        console_sessions = set()
        gaming_sessions = set()

        console_days = set()
        gaming_days = set()

        for session, interval_start, interval_end in self._intervals(
            start,
            end,
        ):
            seconds = (
                interval_end - interval_start
            ).total_seconds()

            days = self._days_covered(
                interval_start,
                interval_end,
            )

            if session.session_type == SessionType.CONSOLE:
                console_seconds += seconds
                console_sessions.add(session.session_id)
                console_days.update(days)

            elif session.session_type == SessionType.GAMING:
                gaming_seconds += seconds
                gaming_sessions.add(session.session_id)
                gaming_days.update(days)

        calendar_days = (end_day - start_day).days

        return UsageSummary(
            period_start=start_day.isoformat(),
            period_end=end_day.isoformat(),
            console_seconds=console_seconds,
            gaming_seconds=gaming_seconds,
            non_gaming_seconds=max(
                0.0,
                console_seconds - gaming_seconds,
            ),
            console_sessions=len(console_sessions),
            gaming_sessions=len(gaming_sessions),
            console_active_days=len(console_days),
            gaming_active_days=len(gaming_days),
            average_daily_console_seconds=(
                console_seconds / calendar_days
            ),
            average_daily_gaming_seconds=(
                gaming_seconds / calendar_days
            ),
        )

    def today(
        self,
        reference_day: date | None = None,
    ) -> UsageSummary:
        """Return statistics for one local calendar day."""

        day = reference_day or datetime.now(
            LOCAL_TIMEZONE
        ).date()

        return self.summarize(
            day,
            day + timedelta(days=1),
        )

    def current_week(
        self,
        reference_day: date | None = None,
    ) -> UsageSummary:
        """Return the current Monday-to-Sunday calendar week."""

        day = reference_day or datetime.now(
            LOCAL_TIMEZONE
        ).date()

        monday = day - timedelta(days=day.weekday())

        return self.summarize(
            monday,
            monday + timedelta(days=7),
        )

    def month(
        self,
        year: int,
        month: int,
    ) -> UsageSummary:
        """Return statistics for one complete calendar month."""

        start = date(year, month, 1)

        return self.summarize(
            start,
            next_month(start),
        )

    def last_n_months(
        self,
        count: int,
        reference_day: date | None = None,
    ) -> list[UsageSummary]:
        """
        Return a configurable number of calendar months.

        The result is ordered chronologically and includes
        the current, potentially incomplete calendar month.

        Months without recorded activity remain in the result
        with zero totals.

        A maximum of 36 months prevents accidental requests
        for excessively large historical collections.
        """

        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or not 1 <= count <= 36
        ):
            raise ValueError(
                "Month count must be an integer between 1 and 36."
            )

        day = reference_day or datetime.now(
            LOCAL_TIMEZONE
        ).date()

        current_month = date(day.year, day.month, 1)

        results = []

        for offset in range(1 - count, 1):
            month_start = shift_month(
                current_month,
                offset,
            )

            results.append(
                self.summarize(
                    month_start,
                    next_month(month_start),
                )
            )

        return results

    def last_twelve_months(
        self,
        reference_day: date | None = None,
    ) -> list[UsageSummary]:
        """
        Preserve the existing twelve-month history interface.

        This wrapper maintains compatibility with existing
        Home Assistant sensors and frontend consumers.
        """

        return self.last_n_months(
            count=12,
            reference_day=reference_day,
        )

    def last_thirty_six_months(
        self,
        reference_day: date | None = None,
    ) -> list[UsageSummary]:
        """
        Return the latest 36 calendar months.

        This collection is intended for the compact historical
        activity index and future multi-year dashboard views.
        """

        return self.last_n_months(
            count=36,
            reference_day=reference_day,
        )

    def games(
        self,
        start_day: date,
        end_day: date,
    ) -> list[GameSummary]:
        """
        Aggregate gaming duration by game identifier.

        The title identifier is preferred as the grouping key.
        A fallback name is used when no identifier is available.
        """

        start = local_midnight(start_day)
        end = local_midnight(end_day)

        totals = defaultdict(float)
        session_ids = defaultdict(set)
        names = {}
        identifiers = {}
        images = {}

        for session, interval_start, interval_end in self._intervals(
            start,
            end,
        ):
            if session.session_type != SessionType.GAMING:
                continue

            key = (
                ("id", session.title_id)
                if session.title_id
                else ("name", session.title_name or "Unknown game")
            )

            totals[key] += (
                interval_end - interval_start
            ).total_seconds()

            session_ids[key].add(session.session_id)

            names[key] = session.title_name or "Unknown game"
            identifiers[key] = session.title_id

            # Preserve the latest available cover artwork.
            # Do not overwrite a known image with an empty value.
            if session.title_image:
                images[key] = session.title_image

        results = [
            GameSummary(
                title_id=identifiers[key],
                title_name=names[key],
                duration_seconds=seconds,
                session_count=len(session_ids[key]),
                title_image=images.get(key),
            )
            for key, seconds in totals.items()
        ]

        return sorted(
            results,
            key=lambda item: item.duration_seconds,
            reverse=True,
        )

    def month_comparison(
        self,
        year: int,
        month: int,
    ) -> dict:
        """Compare one month with its preceding calendar month."""

        current = self.month(year, month)

        previous_start = shift_month(
            date(year, month, 1),
            -1,
        )

        previous = self.month(
            previous_start.year,
            previous_start.month,
        )

        return {
            "current": current.to_dict(),
            "previous": previous.to_dict(),
            "console_seconds_change": (
                current.console_seconds - previous.console_seconds
            ),
            "gaming_seconds_change": (
                current.gaming_seconds - previous.gaming_seconds
            ),
        }
