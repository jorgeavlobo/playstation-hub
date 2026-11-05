"""
PS5 Monitoring Service - Historical MQTT Protocol.

Validate incoming historical requests before forwarding them
to the asynchronous history worker.

This module has no MQTT connection or database dependencies.
"""

from __future__ import annotations

import json
import re

from dataclasses import dataclass
from typing import Any

from history_requests import HistoryRequest


MAX_REQUEST_BYTES = 1024

REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9_-]{1,64}$"
)


@dataclass(frozen=True, slots=True)
class HistoryMQTTRequest:
    """
    Represent a validated historical MQTT request.

    The request identifier allows dashboard clients to
    correlate responses with their original requests.
    """

    request_id: str
    history: HistoryRequest

    @property
    def period(self) -> str:
        """Return the requested calendar period."""

        return self.history.period

    @classmethod
    def parse(
        cls,
        payload: bytes,
        retained: bool = False,
    ) -> HistoryMQTTRequest:
        """
        Validate a historical request received through MQTT.

        Retained messages are rejected to prevent obsolete
        requests from being replayed after reconnection.
        """

        if retained:
            raise ValueError(
                "Retained historical requests are not accepted."
            )

        if not isinstance(payload, bytes):
            raise ValueError(
                "MQTT request payload must be bytes."
            )

        if len(payload) > MAX_REQUEST_BYTES:
            raise ValueError(
                "Historical request exceeds maximum size."
            )

        try:
            data: Any = json.loads(
                payload.decode("utf-8")
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(
                "Invalid historical request JSON."
            ) from error

        if not isinstance(data, dict):
            raise ValueError(
                "Historical request must be a JSON object."
            )

        if set(data) != {"request_id", "period"}:
            raise ValueError(
                "Historical request contains invalid fields."
            )

        request_id = data["request_id"]

        if (
            not isinstance(request_id, str)
            or REQUEST_ID_PATTERN.fullmatch(request_id) is None
        ):
            raise ValueError(
                "Invalid historical request identifier."
            )

        history = HistoryRequest.parse(
            data["period"]
        )

        return cls(
            request_id=request_id,
            history=history,
        )
