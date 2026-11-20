from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
IST_NAME = "Asia/Kolkata"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime | None) -> datetime | None:
    """PyMongo may return naive datetimes; stored values are always UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def to_ist_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return ensure_utc(value).astimezone(IST).isoformat()


def ist_today() -> date:
    return datetime.now(IST).date()


def ist_day_bounds_utc(start: date, end: date) -> tuple[datetime, datetime]:
    """Return [start 00:00 IST, end+1 00:00 IST) as UTC datetimes for range queries."""
    start_utc = datetime.combine(start, time.min, tzinfo=IST).astimezone(timezone.utc)
    end_utc = datetime.combine(end + timedelta(days=1), time.min, tzinfo=IST).astimezone(timezone.utc)
    return start_utc, end_utc
