from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Make a plain PostgreSQL / Neon URL usable by SQLAlchemy with the psycopg 3 driver.

    Neon hands out URLs like ``postgresql://user:pw@host/db?sslmode=require``.
    SQLAlchemy would pick psycopg2 for ``postgresql://``, so we switch the scheme
    to ``postgresql+psycopg://``. Query parameters such as ``sslmode`` and
    ``channel_binding`` are passed through to libpq unchanged.
    """
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("sqlite"):
        raise ValueError("SQLite is not supported. Use a PostgreSQL DATABASE_URL.")
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SpendWise API"
    environment: str = "development"

    database_url: str = Field(..., alias="DATABASE_URL")
    test_database_url: str | None = Field(default=None, alias="TEST_DATABASE_URL")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("jwt_secret_key")
    @classmethod
    def _check_secret(cls, value: str) -> str:
        if len(value) < 32 or value.startswith("CHANGE_ME"):
            raise ValueError(
                "JWT_SECRET_KEY must be a random string of at least 32 characters "
                "(not the placeholder from .env.example)."
            )
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
