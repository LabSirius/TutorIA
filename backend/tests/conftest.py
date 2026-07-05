"""Test fixtures.

Tests run against a dedicated PostgreSQL database (tutoria_test) created on the
same server as the dev database. SQLite is no longer viable because the schema
uses pgvector (Vector columns) and JSONB. The test database is created once per
session, its schema built with create_all after enabling the vector extension,
and tables are truncated between tests for isolation.
"""
import os

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import database
from app.db.database import Base, get_db
from app.main import app

TEST_DB_NAME = os.getenv("TEST_DB_NAME", "tutoria_test")

# Derive test URLs from the configured dev database URL.
_SQLA_BASE = settings.database_url.rsplit("/", 1)[0]          # ...@host:port
_ASYNCPG_BASE = _SQLA_BASE.replace("postgresql+asyncpg://", "postgresql://")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", f"{_SQLA_BASE}/{TEST_DB_NAME}")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False)


async def _recreate_test_database() -> None:
    """(Re)create the test database via the maintenance 'postgres' database."""
    conn = await asyncpg.connect(f"{_ASYNCPG_BASE}/postgres")
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


async def _override_get_db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _prepare_database():
    await _recreate_test_database()
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    # Point the application (routers) and services at the test database.
    database.engine = test_engine
    database.async_session = TestSession
    app.dependency_overrides[get_db] = _override_get_db

    yield

    app.dependency_overrides.clear()
    await test_engine.dispose()
    conn = await asyncpg.connect(f"{_ASYNCPG_BASE}/postgres")
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)')
    finally:
        await conn.close()


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables(_prepare_database):
    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def ollama_available():
    """Skip a test unless a real Ollama with the embedding model is reachable."""
    from app.services.rag_service import embedding_client

    try:
        await embedding_client.verify_available()
    except Exception as exc:  # noqa: BLE001 — any failure means "not available"
        import pytest

        pytest.skip(f"Ollama/embedding model unavailable: {exc}")
