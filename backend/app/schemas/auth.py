from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.user import Name, UserRead, validate_currency, validate_password_strength


def normalize_email(value: str) -> str:
    return value.strip().lower()


class RegisterRequest(BaseModel):
    name: Name
    email: EmailStr
    password: str
    preferred_currency: str = "INR"

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v) if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email_lower(cls, v: str) -> str:
        # EmailStr may re-case the domain part; force full lower-case storage.
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("preferred_currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        return validate_currency(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalize_email(v) if isinstance(v, str) else v

    @field_validator("email")
    @classmethod
    def _email_lower(cls, v: str) -> str:
        return v.lower()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
