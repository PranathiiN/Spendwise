"""Test configuration.

Tests run against a REAL PostgreSQL database given by TEST_DATABASE_URL (from the
environment or backend/.env). Every table in that database is dropped and
recreated at the start of the run, so never point it at your real data.
"""

import os
from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
_env_file = dotenv_values(BACKEND_DIR / ".env")

_test_url = os.environ.get("TEST_DATABASE_URL") or _env_file.get("TEST_DATABASE_URL")
if not _test_url:
    pytest.exit(
        "TEST_DATABASE_URL is not set. Create a separate PostgreSQL database for tests "
        "and add TEST_DATABASE_URL to backend/.env.",
        returncode=2,
    )

_main_url = os.environ.get("DATABASE_URL") or _env_file.get("DATABASE_URL")
if _main_url and _main_url.strip() == _test_url.strip():
    pytest.exit("TEST_DATABASE_URL must be different from DATABASE_URL (tests drop all tables).", returncode=2)

# Point the application at the test database BEFORE any app module is imported.
os.environ["DATABASE_URL"] = _test_url
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-that-is-long-enough-1234567890")
if (os.environ["JWT_SECRET_KEY"]).startswith("CHANGE_ME"):
    os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-1234567890"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

import app.models  # noqa: E402,F401
from app.db.base import Base  # noqa: E402
from app.db.seed import seed_system_categories  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Budget, Category, SavingsGoal, Transaction, User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_system_categories(db)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables() -> Generator[None, None, None]:
    yield
    with SessionLocal() as db:
        db.execute(delete(Transaction))
        db.execute(delete(Budget))
        db.execute(delete(SavingsGoal))
        db.execute(delete(Category).where(Category.is_system.is_(False)))
        db.execute(delete(User))
        db.commit()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def register_user(client: TestClient) -> Callable[..., dict[str, str]]:
    """Factory: registers a user and returns Authorization headers."""

    def _register(
        email: str = "alice@example.com", password: str = "Password123", name: str = "Alice"
    ) -> dict[str, str]:
        resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
        assert resp.status_code == 201, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _register


@pytest.fixture
def auth_headers(register_user) -> dict[str, str]:
    return register_user()


@pytest.fixture
def other_headers(register_user) -> dict[str, str]:
    return register_user(email="bob@example.com", name="Bob")


@pytest.fixture
def categories(client: TestClient, auth_headers) -> dict[str, dict]:
    """System categories keyed by name."""
    resp = client.get("/api/categories", headers=auth_headers)
    assert resp.status_code == 200
    return {c["name"]: c for c in resp.json()}


@pytest.fixture
def create_tx(client: TestClient):
    def _create(headers: dict[str, str], category_id: str, **overrides) -> dict:
        body = {
            "category_id": category_id,
            "description": "Test transaction",
            "amount": "100.00",
            "transaction_type": "expense",
            "transaction_date": "2026-11-05",
        }
        body.update(overrides)
        resp = client.post("/api/transactions", json=body, headers=headers)
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create
