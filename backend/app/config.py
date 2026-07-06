"""Application configuration.

All settings are environment-driven so the same image runs unchanged across
local dev, Docker Compose, and Nutanix Kubernetes Platform (NKP). Values map
directly to keys in the Kubernetes ConfigMap/Secret (see ``deploy/``).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: .../nkp-academy — used to locate the default content directory.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration, populated from environment variables.

    Every field can be overridden with an ``NKP_``-prefixed env var, e.g.
    ``NKP_DATABASE_URL`` or ``NKP_CONTENT_DIR``.
    """

    model_config = SettingsConfigDict(
        env_prefix="NKP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "NKP Academy"
    environment: str = "development"
    debug: bool = False

    # Data layer. SQLite for dev; swap to PostgreSQL by setting NKP_DATABASE_URL
    # to e.g. postgresql+asyncpg://user:pass@postgres:5432/nkp_academy
    database_url: str = "sqlite+aiosqlite:///./nkp_academy.db"

    # Where YAML learning content lives. Mounted via ConfigMap in Kubernetes.
    content_dir: Path = Field(default=_REPO_ROOT / "content")

    # Static SPA build output served by FastAPI in production. Empty in dev
    # (the Vite dev server handles the frontend instead).
    static_dir: Path | None = Field(default=None)

    # Comma-separated list of allowed CORS origins for local frontend dev.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Seed/reset the database with content-derived rows on startup.
    auto_seed: bool = True

    # Practice-exam defaults.
    exam_default_count: int = 50
    exam_pass_threshold: float = 0.75  # 75% to pass (mirrors a typical cert cut)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (evaluated once per process)."""
    return Settings()
