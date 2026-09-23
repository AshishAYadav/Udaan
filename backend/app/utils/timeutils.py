"""Timezone-aware datetime helpers. All timestamps are stored as ISO-8601 strings."""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return utcnow().isoformat(timespec="seconds")


def parse_dt(value: str | datetime) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def in_timezone(value: datetime, tz_name: str) -> datetime:
    """Interpret naive datetimes as local time in tz_name; convert aware ones to it."""
    tz = ZoneInfo(tz_name)
    return value.replace(tzinfo=tz) if value.tzinfo is None else value.astimezone(tz)


def age_on(date_of_birth: date, on: date) -> int:
    years = on.year - date_of_birth.year
    if (on.month, on.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return years
