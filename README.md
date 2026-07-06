# 🎓 NKP Academy

A modern, gamified web app that teaches **Nutanix channel partners** about the
**Nutanix Kubernetes Platform (NKP)** — interactive modules, quizzes with instant
feedback, XP, badges, and a leaderboard. It's containerized and ships with
everything needed to run it *on* NKP.

> Content is grounded in the **Nutanix Kubernetes Platform 2.17 Guide** (NKP
> components, Cluster API lifecycle, cluster types, day-2 operations, and
> licensing/positioning).

<p align="center"><em>FastAPI + React/Tailwind · SQLite→PostgreSQL · Docker · Helm · Prometheus</em></p>

---

## ✨ Features

- **Interactive learning modules** — NKP fundamentals, cluster lifecycle
  management, day-2 operations, and licensing/positioning for partners.
- **Gamification** — instant-feedback quizzes, points/XP, levels, per-module
  progress, badges for completing modules/tracks, and an XP leaderboard.
- **Three question types** — multiple choice, true/false, and scenario-based
  "what would you do" cards.
- **Per-user progress** — simple username sessions today, structured so
  **SSO/OIDC** drops in behind one dependency later.
- **Admin-editable content** — modules, questions, and badges are plain **YAML**
  under [`content/`](content/); no code or DB changes to add material.
- **Ops-ready** — `/healthz` probe endpoint and Prometheus metrics at `/metrics`.

## 🧱 Architecture

```
Browser ──HTTP──> FastAPI (async)
                   ├── /api/*        JSON API (auth, content, quiz, progress, leaderboard)
                   ├── /healthz      liveness/readiness
                   ├── /metrics      Prometheus exposition
                   └── /             built React SPA (served in production)
                          │
                          ├── content/  YAML modules + badges  (loaded at startup)
                          └── SQLAlchemy (async) ── SQLite (dev) │ PostgreSQL (prod)
```

- **Backend** — Python 3.12, FastAPI, async SQLAlchemy 2.0, Pydantic v2. Quiz
  **scoring/XP/badge logic is a pure module** ([`scoring.py`](backend/app/scoring.py)),
  so it's fully unit-tested independent of the database.
- **Frontend** — React 18 + Vite + TypeScript + Tailwind, in Nutanix brand colors
  (Iris purple `#7855FA` / charcoal `#131313`).
- **Data layer** — swap SQLite↔PostgreSQL purely via `NKP_DATABASE_URL`.

### Project layout

```
nkp-academy/
├── backend/            FastAPI app + pytest suite
│   ├── app/            main, config, database, models, content, scoring, services, routers/
│   └── tests/          scoring (pure), content validation, API integration
├── content/            YAML modules + badges (admin-editable)
├── frontend/           React + Vite + Tailwind SPA
├── deploy/
│   ├── helm/nkp-academy/  Helm chart (probes, HPA, PVC, non-root securityContext)
│   └── k8s/               raw manifests (Namespace, ConfigMap, Secret, PVC, Deploy, Svc, Ingress, HPA)
├── Dockerfile          multi-stage: node build → slim non-root python runtime
├── docker-compose.yml  local stack (SQLite default, optional PostgreSQL profile)
└── Makefile            build / test / deploy shortcuts
```

---

## 🚀 Quick start

### Option A — Docker Compose (one command)

```bash
docker compose up --build
# open http://localhost:8000  (seeded with demo learners + leaderboard)
```

With PostgreSQL instead of SQLite:

```bash
docker compose --profile postgres up --build
# app-on-postgres: http://localhost:8001
```

### Option B — Host dev (hot reload)

```bash
make venv                       # create backend venv + install dev deps
make dev-backend                # FastAPI on :8000 (terminal 1)
make dev-frontend               # Vite on :5173, proxies /api → :8000 (terminal 2)
# open http://localhost:5173
```

### Run the tests

```bash
make test        # 35 tests: pure scoring, content validation, API flow
make lint        # ruff
```

---

## 🐳 Build & push the image

The [`Dockerfile`](Dockerfile) is multi-stage — Node builds the SPA, then a slim
`python:3.12-slim` runtime serves API + static assets as a **non-root** user
(uid 10001) with a container `HEALTHCHECK`.

```bash
make build IMAGE=ghcr.io/<org>/nkp-academy TAG=1.0.0
make push  IMAGE=ghcr.io/<org>/nkp-academy TAG=1.0.0

# NKP nodes are x86/amd64 — build for that platform explicitly if on Apple Silicon:
make buildx-push IMAGE=ghcr.io/<org>/nkp-academy TAG=1.0.0 PLATFORMS=linux/amd64
```

> **Air-gapped NKP?** Push the image to your internal registry mirror (Harbor /
> JFrog / Nexus) and set `image.repository` to that mirror — the same pattern NKP
> uses to seed cluster images without external connectivity.

---

## ☸️ Deploy to Nutanix Kubernetes Platform

Target any NKP **Managed** (or single) cluster with a reachable kube-context.

### With Helm (recommended)

```bash
helm upgrade --install nkp-academy deploy/helm/nkp-academy \
  --namespace nkp-academy --create-namespace \
  --set image.repository=ghcr.io/<org>/nkp-academy \
  --set image.tag=1.0.0 \
  --set ingress.host=nkp-academy.<your-nkp-domain>
# or simply:  make deploy IMAGE=ghcr.io/<org>/nkp-academy TAG=1.0.0
```

### With raw manifests

```bash
kubectl apply -f deploy/k8s/          # or: make deploy-raw
```

Everything ships hardened and production-shaped:

| Requirement | Where |
|---|---|
| Readiness / liveness / startup probes | `/healthz` (Deployment) |
| Resource requests & limits | `resources:` (100m/128Mi → 500m/256Mi) |
| Horizontal Pod Autoscaler | `hpa.yaml` / `autoscaling.enabled` |
| Non-root securityContext | uid 10001, `readOnlyRootFilesystem`, drop `ALL` caps, `seccomp: RuntimeDefault` |
| Externalized config | ConfigMap + Secret via `envFrom` |
| Persistence | PVC mounted at `/data` (SQLite) |

### How it maps to NKP specifics

- **Ingress** — NKP ships **Traefik** as its default ingress controller, with an
  IngressClass named **`kommander-traefik`** (the chart default). Confirm yours
  with `kubectl get ingressclass` and override via `--set ingress.className=…`
  if different — a mismatched class makes Traefik silently 404.
- **StorageClass** — leave `persistence.storageClass` empty to use the NKP
  cluster default (backed by the **Nutanix CSI** driver), or pin one.
- **TLS** — NKP bundles **cert-manager**; set `ingress.tls.enabled=true` and
  reference the issued secret.
- **Metrics** — pods carry `prometheus.io/scrape` annotations, so NKP's platform
  **Prometheus** scrapes `/metrics` and you can build **Grafana** dashboards.
- **Scaling** — SQLite-on-PVC is single-writer, so keep `replicaCount: 1` there.
  To use the **HPA** / multiple replicas, point `NKP_DATABASE_URL` at PostgreSQL
  (a shared DB) and set `autoscaling.enabled=true`.

---

## ⚙️ Configuration

All config is environment-driven ([`config.py`](backend/app/config.py)); keys map
1:1 to ConfigMap/Secret entries. See [`.env.example`](.env.example).

| Env var | Default | Purpose |
|---|---|---|
| `NKP_DATABASE_URL` | `sqlite+aiosqlite:///./nkp_academy.db` | Data backend (set a `postgresql+asyncpg://…` DSN for prod) |
| `NKP_CONTENT_DIR` | `./content` | YAML content directory |
| `NKP_STATIC_DIR` | *(unset in dev)* | Built SPA dir (set to `/app/static` in the image) |
| `NKP_AUTO_SEED` | `true` | Seed demo learners on startup |
| `NKP_CORS_ORIGINS` | localhost:5173 | Allowed CORS origins (dev only) |
| `NKP_ENVIRONMENT` / `NKP_DEBUG` | `development` / `false` | Environment + SQL echo |

---

## ✍️ Editing content (no code required)

Add or edit a file in [`content/modules/`](content/modules/) — it's picked up on
restart. Minimal question shape:

```yaml
id: my-module
title: "My Module"
track: "NCP-CN Section 1"
order: 5
icon: gauge
summary: "One-line description shown on the dashboard card."
questions:
  - id: q1
    type: multiple_choice      # multiple_choice | true_false | scenario
    points: 10
    difficulty: core           # core | intermediate | advanced
    prompt: "Which CNI does NKP use on the Nutanix provider?"
    options:
      - { id: a, text: "Calico" }
      - { id: b, text: "Cilium" }
    correct: b                 # option id, or a list for multi-select
    explanation: "NKP uses Cilium on Nutanix and Calico on other providers."
```

Badges live in [`content/badges.yaml`](content/badges.yaml) and award
automatically on `module_complete`, `track_complete`, or `xp_threshold`.
Content is validated by the test suite (every `correct` must reference a real
option; ids must be unique).

---

## 🔌 API surface

| Method & path | Description |
|---|---|
| `POST /api/auth/login` | Log in / auto-register by username → session token |
| `GET  /api/auth/me` | Current user |
| `GET  /api/content/modules` · `/tracks` · `/modules/{id}` · `/badges` | Content (answers withheld) |
| `POST /api/quiz/{module}/answer` | Grade one answer → feedback, XP, level, new badges |
| `GET  /api/progress` | XP, level, per-module progress, earned badges |
| `GET  /api/leaderboard` | Top learners by XP |
| `GET  /healthz` · `GET /metrics` | Ops endpoints |

Interactive docs at `/docs` when running.

---

## 🔮 Extending

- **SSO/OIDC** — replace the token check in
  [`deps.get_current_user`](backend/app/deps.py) with JWT validation and look up
  by `User.oidc_subject` (already on the model). Nothing else changes.
- **PostgreSQL** — set `NKP_DATABASE_URL`; the `asyncpg` driver is already in the
  image. Use Alembic for real migrations (the app auto-creates tables for dev).

## 🎨 Brand

Iris Purple `#7855FA` · Charcoal `#131313` — configured in
[`tailwind.config.js`](frontend/tailwind.config.js).

## 📄 License

Apache-2.0. NKP content © Nutanix, used for partner enablement.
