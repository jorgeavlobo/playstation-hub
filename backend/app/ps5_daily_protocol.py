"""Strict bounded MQTT request validation for daily PS5 analytics."""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

REQUEST_ID = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')

@dataclass(frozen=True, slots=True)
class DailyHistoryRequest:
    """A bounded, non-retained request for up to 31 local calendar days."""
    request_id: str
    start_day: date
    end_day: date

    @classmethod
    def parse(cls, payload: bytes, retained: bool = False) -> 'DailyHistoryRequest':
        """Reject malformed, future, oversized, or retained MQTT requests."""
        if retained or not isinstance(payload, bytes) or len(payload) > 1024:
            raise ValueError('Invalid daily request transport.')
        try:
            data = json.loads(payload.decode('utf-8'))
        except (UnicodeError, ValueError) as error:
            raise ValueError('Invalid daily request JSON.') from error
        if not isinstance(data, dict) or set(data) != {'request_id', 'start_date', 'end_date_exclusive'}:
            raise ValueError('Invalid daily request fields.')
        identifier = data['request_id']
        if not isinstance(identifier, str) or not REQUEST_ID.fullmatch(identifier):
            raise ValueError('Invalid daily request identifier.')
        values = (data['start_date'], data['end_date_exclusive'])
        if any(not isinstance(value, str) or not DAY.fullmatch(value) for value in values):
            raise ValueError('Invalid daily date format.')
        try:
            start, end = (date.fromisoformat(value) for value in values)
        except ValueError as error:
            raise ValueError('Invalid daily date.') from error
        if not 1 <= (end - start).days <= 31 or start.year < 2020:
            raise ValueError('Daily range must span 1 to 31 days.')
        today = datetime.now(ZoneInfo('Europe/Lisbon')).date()
        if start > today or end > today + timedelta(days=1):
            raise ValueError('Future daily ranges are unsupported.')
        return cls(identifier, start, end)
