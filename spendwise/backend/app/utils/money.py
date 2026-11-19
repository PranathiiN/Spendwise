from decimal import ROUND_HALF_UP, Decimal

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
ONE_DECIMAL = Decimal("0.1")
HUNDRED = Decimal("100")


def money(value: Decimal | int | str | None) -> Decimal:
    """Coerce to a Decimal with exactly two decimal places (banker-safe rounding)."""
    if value is None:
        return ZERO
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def percent(part: Decimal, whole: Decimal) -> Decimal:
    """part / whole * 100, rounded to one decimal place. Returns 0 when whole is 0."""
    if not whole:
        return Decimal("0.0")
    return (Decimal(part) / Decimal(whole) * HUNDRED).quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Percentage change from previous to current. None when previous is 0."""
    if not previous:
        return None
    return ((Decimal(current) - Decimal(previous)) / Decimal(previous) * HUNDRED).quantize(
        ONE_DECIMAL, rounding=ROUND_HALF_UP
    )
