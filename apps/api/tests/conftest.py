"""Test setup.

The API depends on Postgres-only features (UUID, JSONB, extensions), so tests
run against a real Postgres database named by TEST_DATABASE_URL. The schema is
built with the Alembic migrations, which doubles as a check that they match
the models. Every table is truncated after each test.

    TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/spinninglicorice_test pytest
"""
from __future__ import annotations

import os

import pytest

_TEST_DB = os.environ.get("TEST_DATABASE_URL")
if not _TEST_DB:
    pytest.exit(
        "Set TEST_DATABASE_URL to an empty Postgres database (it will be wiped).",
        returncode=2,
    )

# Must be set before the app (and its settings) is imported.
os.environ["DATABASE_URL"] = _TEST_DB
os.environ["APP_ENV"] = "development"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["REDIS_URL"] = ""

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def _schema():
    cfg = Config(os.path.join(_API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(_API_DIR, "migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def register(client: TestClient, email: str, password: str = "password123") -> dict:
    """Register a user and return Authorization headers for them."""
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def user_id(client: TestClient, headers: dict) -> str:
    return client.get("/api/v1/auth/me", headers=headers).json()["id"]


def share_account(client: TestClient, owner: dict, member: dict, role: str) -> dict:
    """Share `owner`'s account with `member`; return member headers scoped to it."""
    invite = client.post("/api/v1/sharing/invites", json={"role": role}, headers=owner)
    assert invite.status_code == 201, invite.text
    accepted = client.post(f"/api/v1/sharing/invites/{invite.json()['token']}/accept", headers=member)
    assert accepted.status_code == 200, accepted.text
    return {**member, "X-Account-Id": user_id(client, owner)}
