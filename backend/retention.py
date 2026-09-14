"""Calendar-based reporting windows; never approximate months with days."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

HISTORY_START = date(2024, 1, 1)
TIMEZONE = "America/Los_Angeles"
SCHEDULE = "cron(0 6 7 * ? *)"


def shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def parse_month(value: str) -> date:
    parsed = datetime.strptime(value, "%Y-%m").date().replace(day=1)
    if parsed.strftime("%Y-%m") != value:
        raise ValueError("Month must be YYYY-MM")
    return parsed


def latest_complete_month(now: datetime | None = None) -> date:
    now = now or datetime.now(ZoneInfo(TIMEZONE))
    if now.tzinfo is None:
        raise ValueError("A timezone-aware time is required")
    return shift_month(now.astimezone(ZoneInfo(TIMEZONE)).date(), -1)


def window(end: date) -> tuple[date, date]:
    end = end.replace(day=1)
    if end < HISTORY_START:
        raise ValueError("Reporting begins January 2024")
    return max(HISTORY_START, shift_month(end, -35)), end


def months(start: date, end: date) -> list[date]:
    result = []
    while start <= end:
        result.append(start)
        start = shift_month(start, 1)
    return result
