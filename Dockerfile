# syntax=docker/dockerfile:1

##############################
# Stage 1 — build the SPA
##############################
FROM node:20-alpine AS frontend
WORKDIR /frontend

# Install deps first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build   # emits /frontend/dist


##############################
# Stage 2 — python deps
##############################
FROM python:3.12-slim AS backend-deps
WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build into an isolated prefix we can copy into the slim runtime.
COPY backend/pyproject.toml ./
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Install runtime deps (declared in pyproject) into the venv.
RUN pip install \
      "fastapi>=0.115,<0.116" \
      "uvicorn[standard]>=0.32,<0.35" \
      "sqlalchemy[asyncio]>=2.0.36,<2.1" \
      "aiosqlite>=0.20,<0.22" \
      "asyncpg>=0.30,<0.31" \
      "pydantic>=2.9,<3" \
      "pydantic-settings>=2.6,<3" \
      "pyyaml>=6.0,<7" \
      "prometheus-client>=0.21,<0.24"


##############################
# Stage 3 — runtime (slim, non-root)
##############################
FROM python:3.12-slim AS runtime

# Create an unprivileged user and a writable data dir for the SQLite volume.
RUN groupadd --system --gid 10001 nkp \
 && useradd --system --uid 10001 --gid nkp --home-dir /app --no-create-home nkp \
 && mkdir -p /app /data \
 && chown -R nkp:nkp /app /data

WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NKP_STATIC_DIR=/app/static \
    NKP_CONTENT_DIR=/app/content \
    NKP_DATABASE_URL=sqlite+aiosqlite:////data/nkp_academy.db

# Python venv from the deps stage.
COPY --from=backend-deps /opt/venv /opt/venv

# Application code + content + built SPA.
COPY --chown=nkp:nkp backend/app ./app
COPY --chown=nkp:nkp content ./content
COPY --from=frontend --chown=nkp:nkp /frontend/dist ./static

USER 10001
EXPOSE 8000

# Container-level healthcheck (Kubernetes probes are defined separately).
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
