"""Async SQLAlchemy data layer.

The engine is created from ``settings.database_url`` so the storage backend is
a pure configuration concern: SQLite locally, PostgreSQL in production, with no
code changes. Consumers depend on :func:`get_session` rather than the engine so
the transaction boundary is owned by the request lifecycle.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_settings = get_settings()

# SQLite needs check_same_thread disabled for the async driver; other backends
# ignore the connect_args.
_connect_args = {"check_same_thread": False} if _settings.is_sqlite else {}

engine = create_async_engine(
    _settings.database_url,
    echo=_settings.debug,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a scoped async session."""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create tables if they do not yet exist.

    Import models first so they are registered on ``Base.metadata``. For real
    schema evolution use Alembic; this keeps the app runnable out of the box.
    """
    from . import models  # noqa: F401  (register mappers)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
