from datetime import UTC, datetime


def now() -> datetime:
    """Single source of "now" so tests can freeze time (see tests/conftest.py)."""
    return datetime.now(UTC)


def aware(dt: datetime) -> datetime:
    """SQLite drops tzinfo; treat naive datetimes from the DB as UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
