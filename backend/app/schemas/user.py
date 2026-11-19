import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.schemas.common import SUPPORTED_CURRENCIES

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def validate_currency(value: str) -> str:
    value = value.strip().upper()
    if value not in SUPPORTED_CURRENCIES:
        raise ValueError(f"Unsupported currency. Choose one of: {', '.join(SUPPORTED_CURRENCIES)}")
    return value


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    preferred_currency: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: Name | None = None
    preferred_currency: str | None = None

    @field_validator("preferred_currency")
    @classmethod
    def _currency(cls, v: str | None) -> str | None:
        return validate_currency(v) if v is not None else None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return validate_password_strength(v)
