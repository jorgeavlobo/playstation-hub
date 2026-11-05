"""
PS5 Monitoring Service - Game Library Payload Builder.

Build bounded MQTT JSON attributes for the current month's
game library without modifying the underlying statistics.

The SQLite database remains the authoritative source for
the complete gaming history.
"""

from __future__ import annotations

import json

from typing import Any, Iterable


MAX_LIBRARY_PAYLOAD_BYTES = 12 * 1024


def encoded_size(payload: dict[str, Any]) -> int:
    """Return the UTF-8 size of the compact JSON payload."""

    return len(
        json.dumps(
            payload,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )


def build_game_library_payload(
    period: str,
    games: Iterable[Any],
    max_bytes: int = MAX_LIBRARY_PAYLOAD_BYTES,
) -> dict[str, Any]:
    """
    Build a bounded monthly game library payload.

    Games are ordered by confirmed gaming duration.

    Every game is retained in the source statistics.
    Only the MQTT representation may be truncated.
    """

    if max_bytes <= 0:
        raise ValueError("Payload size limit must be positive.")

    ordered_games = sorted(
        games,
        key=lambda game: game.duration_seconds,
        reverse=True,
    )

    payload: dict[str, Any] = {
        "period": period,
        "game_count": len(ordered_games),
        "published_count": 0,
        "truncated": False,
        "games": [],
    }

    if encoded_size(payload) > max_bytes:
        raise ValueError(
            "Payload size limit is too small for metadata."
        )

    for game in ordered_games:
        item = {
            "title_id": game.title_id,
            "title_name": game.title_name,
            "title_image": game.title_image,
            "duration_seconds": round(
                game.duration_seconds,
                1,
            ),
            "session_count": game.session_count,
        }

        candidate = {
            **payload,
            "games": [*payload["games"], item],
            "published_count": payload["published_count"] + 1,
            "truncated": (
                payload["published_count"] + 1
                < len(ordered_games)
            ),
        }

        if encoded_size(candidate) > max_bytes:
            payload["truncated"] = True
            break

        payload = candidate

    payload["truncated"] = (
        payload["published_count"] < payload["game_count"]
    )

    return payload
