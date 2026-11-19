from datetime import date, timedelta


def first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, months: int) -> date:
    """Shift a first-of-month date by N months."""
    total = d.year * 12 + (d.month - 1) + months
    return date(total // 12, total % 12 + 1, 1)


def month_range(month_start: date) -> tuple[date, date]:
    """Return (first_day, first_day_of_next_month) — the end is exclusive."""
    start = first_day_of_month(month_start)
    return start, add_months(start, 1)


def days_in_month(month_start: date) -> int:
    start, end = month_range(month_start)
    return (end - start).days


def parse_month(value: str | None) -> date:
    """Parse 'YYYY-MM' into the first day of that month. None -> current month."""
    if not value:
        return first_day_of_month(date.today())
    year_str, month_str = value.split("-")
    return date(int(year_str), int(month_str), 1)


def format_month(d: date) -> str:
    return d.strftime("%Y-%m")


def iter_days(start: date, end_exclusive: date):
    current = start
    while current < end_exclusive:
        yield current
        current += timedelta(days=1)
