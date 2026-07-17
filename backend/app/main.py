"""FastAPI application entrypoint.

Serves the JSON API, health/metrics endpoints, and (in production) the built
React SPA from a single process — one image, one container, NKP-friendly.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import __version__
from .config import get_settings
from .content import load_content
from .database import init_db
from .metrics import (
    http_request_duration_seconds,
    http_requests_total,
    registry,
)
from .routers import (
    auth,
    content_router,
    exam,
    flashcards,
    leaderboard,
    progress,
    quiz,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load content, initialise the database, and seed on startup."""
    app.state.content_store = load_content(settings.content_dir)
    await init_db()
    if settings.auto_seed:
        from .seed import seed_demo_data

        await seed_demo_data(app.state.content_store)
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Gamified Nutanix Kubernetes Platform (NKP) enablement for partners.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Record request count and latency, using the route template as the label
    (avoids unbounded cardinality from path parameters)."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    route = request.scope.get("route")
    path_label = getattr(route, "path", request.url.path)
    http_requests_total.labels(
        method=request.method, path=path_label, status=response.status_code
    ).inc()
    http_request_duration_seconds.labels(
        method=request.method, path=path_label
    ).observe(elapsed)
    return response


# ---- Operational endpoints ----

@app.get("/healthz", tags=["ops"], include_in_schema=False)
async def healthz() -> JSONResponse:
    """Liveness/readiness probe. Confirms content loaded successfully."""
    store = getattr(app.state, "content_store", None)
    healthy = store is not None and len(store.modules) > 0
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "version": __version__,
            "modules_loaded": len(store.modules) if store else 0,
        },
    )


@app.get("/metrics", tags=["ops"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus exposition endpoint."""
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)


# ---- API routers ----

app.include_router(auth.router)
app.include_router(content_router.router)
app.include_router(quiz.router)
app.include_router(progress.router)
app.include_router(leaderboard.router)
app.include_router(exam.router)
app.include_router(flashcards.router)


# ---- Static SPA (production only) ----

def _mount_spa() -> None:
    """Serve the built frontend if a static dir is configured and exists.

    Vite emits hashed assets under ``/assets`` plus an ``index.html`` entry.
    We mount the assets directly and add a catch-all that returns index.html for
    any non-API path, so client-side routes (e.g. /leaderboard) work on refresh
    and deep-link. API/ops routes are registered earlier and take precedence.
    """
    static_dir: Path | None = settings.static_dir
    if not (static_dir and Path(static_dir).is_dir()):
        return

    static_path = Path(static_dir)
    index_file = static_path / "index.html"
    assets_dir = static_path / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve a real static file if it exists, else the SPA entrypoint."""
        candidate = (static_path / full_path).resolve()
        # Prevent path traversal, then serve the file if present.
        if (
            full_path
            and static_path in candidate.parents
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Not found")


_mount_spa()
