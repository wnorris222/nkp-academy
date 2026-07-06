"""Shared pytest fixtures.

Each test run uses a throwaway in-memory SQLite database and the real YAML
content, so tests exercise the same content the app serves.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Point the app at the repo's content dir and an isolated in-memory DB BEFORE
# any app module (which reads settings at import time) is imported.
_REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("NKP_CONTENT_DIR", str(_REPO_ROOT / "content"))
os.environ.setdefault("NKP_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("NKP_AUTO_SEED", "false")

from app.config import get_settings  # noqa: E402
from app.content import load_content  # noqa: E402


@pytest.fixture(scope="session")
def content_store():
    """The real content store loaded from YAML."""
    return load_content(get_settings().content_dir)


@pytest.fixture
async def client():
    """An httpx AsyncClient wired to the FastAPI app with a fresh in-memory DB.

    A StaticPool keeps the single in-memory connection alive for the whole
    test, and the schema is created via the app's lifespan.
    """
    import httpx
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    import app.database as database

    # Rebuild the engine as a shared in-memory DB for this test.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    database.engine = engine
    database.SessionLocal = async_sessionmaker(
        bind=engine, expire_on_commit=False
    )

    from app.main import app

    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)

    # Load content onto app state without running the full seed.
    app.state.content_store = load_content(get_settings().content_dir)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await engine.dispose()
