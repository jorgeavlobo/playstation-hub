"""Daily PS5 history aggregation for future MQTT analytics responses.

All periods use Europe/Lisbon local calendar boundaries. The existing
StatisticsService remains the source of truth; this module does not open
or mutate the database, create MQTT subscriptions, or publish messages.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from usage_statistics import StatisticsService


MAX_DAYS = 31


def build_daily_history(
    statistics: StatisticsService,
    start_day: date,
    end_day: date,
    *,
    include_games: bool = True,
) -> dict[str, Any]:
    """Return one bounded daily series over a half-open local date range.

    The returned series includes empty days, both console and gaming
    durations, and game rankings per day. Durations of open sessions are
    limited to persisted checkpoints by StatisticsService. The caller
    must enforce MQTT transport limits separately before publishing.
    """

    if not isinstance(start_day, date) or not isinstance(end_day, date):
        raise TypeError("start_day and end_day must be dates")

    days = (end_day - start_day).days
    if not 1 <= days <= MAX_DAYS:
        raise ValueError("Daily history requires between 1 and 31 days")

    entries: list[dict[str, Any]] = []
    cursor = start_day
    while cursor < end_day:
        next_day = cursor + timedelta(days=1)
        summary = statistics.summarize(cursor, next_day)
        entry: dict[str, Any] = {
            "date": cursor.isoformat(),
            "console_seconds": round(summary.console_seconds, 3),
            "gaming_seconds": round(summary.gaming_seconds, 3),
            "non_gaming_seconds": round(summary.non_gaming_seconds, 3),
            "console_sessions": summary.console_sessions,
            "gaming_sessions": summary.gaming_sessions,
        }
        if include_games:
            entry["games"] = [
                {
                    "title_id": game.title_id,
                    "title_name": game.title_name,
                    "title_image": game.title_image,
                    "duration_seconds": round(game.duration_seconds, 3),
                    "session_count": game.session_count,
                }
                for game in statistics.games(cursor, next_day)
            ]
        entries.append(entry)
        cursor = next_day

    return {
        "schema_version": 1,
        "kind": "daily_history",
        "start_date": start_day.isoformat(),
        "end_date_exclusive": end_day.isoformat(),
        "days": entries,
    }
