"""
PS5 Monitoring Service - Historical Response Builder.

Build validated, JSON-compatible historical statistics
without introducing MQTT or database connection management.

The StatisticsService remains the single source of truth
for all usage calculations.
"""

from __future__ import annotations

from typing import Any

from history_requests import HistoryRequest
from usage_statistics import StatisticsService


class HistoryResponseBuilder:
    """
    Build historical monthly statistics for the dashboard.

    The builder is deliberately independent of MQTT transport,
    allowing isolated tests and future API integrations.
    """

    def __init__(
        self,
        statistics: StatisticsService,
    ) -> None:
        """Store the existing statistics service dependency."""

        self._statistics = statistics

    def build(
        self,
        request: HistoryRequest,
    ) -> dict[str, Any]:
        """
        Build a complete response for one calendar month.

        All durations are represented in seconds to preserve
        precision. Presentation formatting belongs to the UI.
        """

        if not isinstance(request, HistoryRequest):
            raise TypeError(
                "Expected a validated HistoryRequest instance."
            )

        summary = self._statistics.month(
            request.year,
            request.month,
        )

        games = self._statistics.games(
            request.start_day,
            request.end_day,
        )

        comparison = self._statistics.month_comparison(
            request.year,
            request.month,
        )

        game_items = [
            {
                "title_id": game.title_id,
                "title_name": game.title_name,
                "title_image": game.title_image,
                "duration_seconds": round(
                    game.duration_seconds,
                    1,
                ),
                "session_count": game.session_count,
            }
            for game in games
        ]

        return {
            "schema_version": 1,
            "period": request.period,
            "summary": summary.to_dict(),
            "game_count": len(game_items),
            "games": game_items,
            "comparison": {
                "console_seconds_change": comparison[
                    "console_seconds_change"
                ],
                "gaming_seconds_change": comparison[
                    "gaming_seconds_change"
                ],
            },
        }
