"""Encode daily analytics as size-bounded, correlated MQTT pages.

The page builder preserves chronological order, never splits one day's
statistics, and rejects any individual day that exceeds the transport limit.
"""
from __future__ import annotations

import json
from typing import Any

MAX_RESPONSE_BYTES = 16384


def encode_daily_pages(response: dict[str, Any], *, limit: int = MAX_RESPONSE_BYTES) -> list[str]:
    """Return ordered MQTT page payloads within a strict UTF-8 byte limit.

    Each page includes request_id, start/end dates, page_index, page_count,
    and a consecutive subset of the requested daily entries.
    """
    if not isinstance(response, dict) or response.get('kind') != 'daily_history':
        raise ValueError('Expected a daily history response.')
    if not isinstance(response.get('days'), list) or not response['days']:
        raise ValueError('Daily history must contain at least one day.')
    if not isinstance(limit, int) or limit < 512:
        raise ValueError('Invalid MQTT payload limit.')

    envelope = {key: response[key] for key in (
        'schema_version', 'kind', 'request_id',
        'start_date', 'end_date_exclusive',
    )}
    # Page count cannot exceed the number of days. Reserve the largest
    # possible count before packing so the final encoding cannot grow.
    maximum_count = len(response['days'])
    pages: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []

    def encoded(items: list[dict[str, Any]], index: int) -> str:
        return json.dumps({
            **envelope,
            'page_index': index,
            'page_count': maximum_count,
            'days': items,
        }, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

    for day in response['days']:
        candidate = current + [day]
        if len(encoded(candidate, len(pages)).encode('utf-8')) <= limit:
            current = candidate
            continue
        if not current:
            raise ValueError('Single daily entry exceeds MQTT size limit.')
        pages.append(current)
        current = [day]
        if len(encoded(current, len(pages)).encode('utf-8')) > limit:
            raise ValueError('Single daily entry exceeds MQTT size limit.')
    if current:
        pages.append(current)

    result = [json.dumps({
        **envelope,
        'page_index': index,
        'page_count': len(pages),
        'days': items,
    }, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
        for index, items in enumerate(pages)]
    if any(len(item.encode('utf-8')) > limit for item in result):
        raise AssertionError('Daily page exceeds transport limit.')
    return result
