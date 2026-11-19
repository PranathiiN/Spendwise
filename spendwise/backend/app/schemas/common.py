from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints

# Positive monetary amount, max 9,999,999,999.99, at most 2 decimal places.
# Pydantic serializes Decimal as a JSON string ("1234.50"), so no precision is lost.
Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]

HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
IconName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
MonthStr = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]

SUPPORTED_CURRENCIES = (
    "INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "AED", "CHF", "CNY", "NZD", "ZAR",
)
