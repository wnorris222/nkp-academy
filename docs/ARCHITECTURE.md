# NKP Academy — Architecture & Operations Guide

Everything you need to understand, run, modify, and deploy this application.

**Audience:** engineers, SEs, and anyone inheriting this project.
**Last verified against:** image tag `1.11.0`, 20 modules / 303 questions / 26 badges / 238 flashcards.

---

## 1. What this is

A gamified, self-contained web app that teaches Nutanix channel partners the
**Nutanix Kubernetes Platform (NKP)** and preps them for the **NCP-CN** exam.
Learners pick a module, answer questions, earn XP, unlock badges, climb a
leaderboard, and take a practice exam. Every answer cites the Nutanix doc page
it came from.

It is designed to be deployed *onto NKP itself* during partner bootcamps — the
app is both the training material and a live workload on the cluster.

### Design goals (and why)

| Goal | How it's achieved |
|---|---|
| Content editable without code changes | All questions live in version-controlled **YAML**, not the database |
| One image, one container | FastAPI serves both the JSON API *and* the built React SPA |
| Runs anywhere unchanged | 100% environment-driven config (`NKP_*` vars) |
| Safe on a shared cluster | Non-root, read-only rootfs, all caps dropped |
| Answers are trustworthy | Every question carries a source citation (label + URL + quote) |

---

## 2. The 30-second mental model

```
┌──────────────── one container (wnorris22/nkp:TAG) ────────────────┐
│                                                                    │
│   FastAPI (uvicorn, :8000)                                         │
│   ├── /api/*        → JSON API (auth, content, quiz, exam, ...)    │
│   ├── /healthz      → liveness/readiness                           │
│   ├── /metrics      → Prometheus                                   │
│   └── /*            → catch-all → serves the built React SPA       │
│                                                                    │
│   /app/content  ← YAML questions (baked into image, read at boot)  │
│   /app/static   ← compiled SPA (Vite build output)                 │
│   /data         ← SQLite file (PersistentVolume)                   │
└────────────────────────────────────────────────────────────────────┘
```

**Key split:** *content* (questions, badges) is **YAML, read-only, loaded once at
startup**. *State* (users, attempts, XP, badges earned) is **SQL**. They never mix.
That's what lets you edit a question and ship it without a migration.

---

## 3. Repository layout

```
nkp-academy/
├── Dockerfile               # 3-stage build → single runtime image
├── docker-compose.yml       # local dev/demo stack (SQLite or PostgreSQL)
├── README.md
├── docs/
│   ├── ARCHITECTURE.md      # ← this file
│   └── BOOTCAMP-LAB-GUIDE.md
│
├── content/                 # ★ THE LEARNING CONTENT (edit here)
│   ├── badges.yaml
│   └── modules/
│       ├── 05-ncpcn-s1-registry.yaml    … 24-ncpcn-s4-platform-apps.yaml
│
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py          # app factory, lifespan, middleware, SPA mount
│   │   ├── config.py        # Settings (all NKP_* env vars)
│   │   ├── content.py       # YAML → frozen dataclasses (ContentStore)
│   │   ├── models.py        # ORM: User, Attempt, ModuleProgress, UserBadge
│   │   ├── database.py      # async engine/session, init_db()
│   │   ├── deps.py          # get_store(), get_current_user()
│   │   ├── scoring.py       # ★ pure logic: grading, XP, levels, badges
│   │   ├── services.py      # orchestration: grade → persist → award
│   │   ├── exam.py          # practice-exam sampling + batch grading
│   │   ├── seed.py          # demo learners (idempotent)
│   │   ├── metrics.py       # Prometheus registry + counters
│   │   ├── schemas.py       # Pydantic request/response contracts
│   │   └── routers/         # auth, content_router, quiz, progress,
│   │                        #   leaderboard, exam
│   └── tests/               # 64 tests (scoring, content, quiz API, exam, flashcards)
│
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json
│   └── src/
│       ├── App.tsx          # routes
│       ├── main.tsx
│       ├── lib/{api.ts, auth.tsx, types.ts}
│       ├── components/{Layout.tsx, ui.tsx}
│       └── pages/{Dashboard, Quiz, Exam, Leaderboard, Login}.tsx
│
└── deploy/
    ├── helm/nkp-academy/    # ★ the supported deploy path
    │   ├── Chart.yaml, values.yaml, .helmignore
    │   └── templates/{_helpers.tpl, NOTES.txt, deployment, service,
    │                  ingress, configmap, secret, pvc, hpa, serviceaccount}
    └── k8s/                 # plain manifests (equivalent, non-templated)
```

> ⚠️ **Housekeeping:** a stray, **untracked** `nkp-academy/nkp-academy/` directory
> exists locally — a duplicate copy of the whole repo. It is *not* in git and is
> not used by anything. Safe to delete: `rm -rf nkp-academy/nkp-academy`.

---

## 4. The content model (the most important part)

### Where content lives
`content/modules/*.yaml` — one file per exam objective. Filenames are numeric-
prefixed purely for load order (`sorted(glob("*.yaml"))`).

`content/flashcards/*.yaml` — one file per study deck. Independent of the
modules: a module tests you, a deck teaches you. See §4.5.

### Shape of a module

```yaml
id: ncpcn-s1-bastion          # stable id, used in URLs and progress rows
title: 1.4 Prepare a Bastion Host
track: NCP-CN Section 1       # groups modules; drives exam sampling + badges
order: 14                     # display order on the dashboard
icon: gauge                   # emoji key (see ICONS in components/ui.tsx)
summary: 'Short blurb shown on the dashboard card.'
questions:
  - id: q73                   # globally unique across the whole app
    type: multiple_choice     # multiple_choice | true_false | scenario
    difficulty: core          # core | stretch | advanced (display only)
    points: 10                # XP awarded on a correct answer
    prompt: In an air-gapped NKP deployment, what is the primary purpose…?
    options:
      - id: a
        text: It runs the production workloads
      - id: b
        text: It hosts the Konvoy bundles, images, and local registry
    correct: b                # a single id → single-answer question
    explanation: Shown after answering, right or wrong.
    source:                   # ★ citation shown with the explanation
      label: Creating a Bastion Host
      url: https://portal.nutanix.com/page/documents/details?targetId=…
      page: p.703             # optional
      quote: "the bastion VM hosts the installation of the… Konvoy bundles"
      label2: ''              # optional SECOND citation (rare)
      url2: ''
```

### Rules that actually matter

- **`correct` drives everything.** A scalar (`correct: b`) = single-answer.
  A list (`correct: [a, b, c]`) = **multi-select**. The API derives
  `multiple = len(correct_set) > 1` and the UI switches radio → checkbox and
  shows a "Select all that apply" chip. There is **no partial credit** — the
  selected set must match exactly (`app/scoring.py:grade_answer`).
- **`id`s must be globally unique** across all modules (they key `Attempt` rows).
- **`track` must match exactly** — badges and exam sampling group on this string.
- **`source.url2`/`label2` are optional.** Set them and the citation renders two
  links. Currently exactly **1** question uses this (Obj 2.2 Q7).
- Content is **read once at startup**. Editing YAML requires a pod restart
  (or a rebuilt image) to take effect.

### Badges (`content/badges.yaml`)
Three criteria types, evaluated in `scoring.evaluate_badges`:

| `criteria_type` | `criteria_value` | Awarded when |
|---|---|---|
| `module_complete` | a module `id` | every question in that module answered correctly at least once |
| `track_complete` | a track name | every module in that track is complete |
| `xp_threshold` | an integer (as string) | cumulative XP ≥ value |

### 4.5 Flashcard decks (`content/flashcards/*.yaml`)

Decks are **purpose-written, not derived from the quiz**. This is deliberate and
was a rewrite: cards used to be a projection of the 303 questions, which read
badly because a question is built around distractors — the prompt assumes you
can see the options, and the "answer" is only meaningful next to the three wrong
ones. A card instead teaches exactly one thing and is read front-to-back.

```yaml
id: fc-capi                       # deck id, used as ?deck_id=
title: Cluster API (CAPI)
icon: refresh                     # key into ICONS in frontend/src/components/ui.tsx
order: 2                          # load/display order
summary: The CAPI objects NKP builds on — Machines, MachineDeployments, ...
cards:
  - id: capi-mhc-maxunhealthy     # must be unique across ALL decks
    kind: fact                    # term | concept | command | fact — drives the badge colour
    front: What is the default maxunhealthy value for a MachineHealthCheck?
    back: 40%. It is customizable to suit your self-healing requirements.
    detail: The cap exists so a widespread outage doesn't trigger mass remediation.
    code: |                        # optional; rendered as a mono block
      kubectl get MachineHealthCheck
    page: p.22                     # optional
    section: CAPI Concepts and Terms   # optional
```

`page`/`section` are **not** stored as-is — `content._parse_flashcard` folds them
into a display string (`ref`): `NKP 2.17 Guide · p.22 · CAPI Concepts and Terms`.
These are page references into the NKP 2.17 PDF, not portal URLs, so there are no
version-pinned slugs to rot (unlike question `source.url`).

Backticks in `front`/`back`/`detail` render as inline code (`RichText` in
`Flashcards.tsx`). Keep them balanced — a stray one just renders as text.

Flashcards are **stateless and self-graded**: no auth, no persistence, no XP. A
tick you award yourself would be trivially farmable, so it stays out of the
scoring path entirely (`app/flashcards.py` explains this).

A test (`test_cards_are_not_copies_of_quiz_questions`) fails the build if a card
front is byte-identical to a quiz prompt — the guard against regressing to the
projection model.

### Current content (verified)

| Track | Modules | Questions |
|---|---:|---:|
| NCP-CN Section 1 | 6 | 95 |
| NCP-CN Section 2 | 2 | 37 |
| NCP-CN Section 3 | 6 | 68 |
| NCP-CN Section 4 | 6 | 103 |
| **Total** | **20** | **303** |

26 badges · 17 multi-select questions · question types: `multiple_choice`,
`true_false`, `scenario`.

10 flashcard decks · 238 cards (69 term · 59 fact · 56 command · 54 concept),
sourced from the NKP 2.17 guide.

---

## 5. Backend

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 ·
uvicorn · prometheus-client.

### Request lifecycle
1. **Startup (`lifespan`)** — load YAML into an in-memory `ContentStore` on
   `app.state`; `init_db()` creates tables; optionally seed demo users.
2. **Middleware** — every request is counted/timed into Prometheus, labelled by
   *route template* (not raw path) to avoid unbounded cardinality.
3. **Routers** — `/api/*` handle the work.
4. **SPA catch-all** — anything unmatched returns `index.html` so client-side
   routes deep-link and survive refresh. (Registered *last*, so API wins.)

### Module responsibilities

| Module | Job |
|---|---|
| `content.py` | Parse YAML → frozen dataclasses (`Module`, `Question`, `Source`, `Badge`). Pure. |
| `scoring.py` | **Pure, no I/O.** Grading, XP→level curve, badge evaluation. Where the rules live. |
| `services.py` | Async orchestration: grade → write `Attempt` → recompute progress → award badges → commit. |
| `exam.py` | Stateless practice exam: proportional sampling across tracks, then batch grading. |
| `deps.py` | `get_store()` and `get_current_user()` — the single auth seam. |

### Two design decisions worth knowing

**Best-attempt semantics.** `ModuleProgress` is *recomputed from the `Attempt`
table* after every answer (`_refresh_module_progress`), using
`MAX(correct)` / `MAX(points_awarded)` per question. Once you've answered a
question correctly, a later wrong attempt can't take it away. Progress only
ever improves.

**The practice exam is stateless.** `build_exam` samples questions across tracks
using largest-remainder proportional allocation (each section is represented in
line with its size), and grading is a pure function of the content store. No
exam is ever persisted, and **exams do not affect XP or module progress**.

### XP → level curve (`scoring.level_for_xp`)
Each level costs 100 XP more than the last:
level 1 = 0–99, level 2 = 100–299, level 3 = 300–599, level 4 = 600–999 …

### API surface

| Method | Path | Auth | Purpose |
|---|---|:--:|---|
| POST | `/api/auth/login` | – | Log in or auto-register by username |
| GET | `/api/auth/me` | ✓ | Current user |
| GET | `/api/content/modules` | – | All modules (no questions) |
| GET | `/api/content/modules/{id}` | – | One module **with questions, answers withheld** |
| GET | `/api/content/tracks` | – | Track names in order |
| GET | `/api/content/badges` | – | Badge catalog |
| POST | `/api/quiz/{module_id}/answer` | ✓ | Grade one answer → XP, explanation, source, new badges |
| GET | `/api/progress` | ✓ | Per-module progress, XP, level, badges |
| GET | `/api/leaderboard` | – | Ranked learners |
| GET | `/api/flashcards/decks` | – | Deck list for the picker (+ the `all` deck) |
| GET | `/api/flashcards?deck_id=X` | – | Every card in a deck (`all` = everything) |
| GET | `/api/exam?count=N` | – | Generate a practice exam |
| POST | `/api/exam/submit` | – | Grade a whole exam → per-section report |
| GET | `/healthz` | – | Liveness/readiness (+ `modules_loaded`) |
| GET | `/metrics` | – | Prometheus |

**Answers are never leaked.** `GET /api/content/modules/{id}` returns a
`QuestionOut` that deliberately omits `correct` and `explanation`; they only
appear in the grade response *after* you submit. Same for exams.

### Authentication — read this before production

Auth is **deliberately minimal**: you log in with a username, no password, and
**the session token *is* the username**. Anyone who knows a username can act as
that user.

That is an accepted trade-off for low-stakes partner enablement on an internal
cluster — but it is **not suitable for anything sensitive**. The design isolates
this so it can be replaced: swap the body of `POST /api/auth/login` for an OIDC
code exchange and validate a JWT inside `deps.get_current_user()`. The `User`
model already carries an unused `oidc_subject` column for exactly this. No
router or frontend change would be needed.

### Metrics exposed
`nkp_academy_http_requests_total`, `..._http_request_duration_seconds`,
`..._quiz_answers_total{result}`, `..._badges_awarded_total{badge_id}`,
`..._logins_total`, `..._exams_submitted_total{result}`.

---

## 6. Frontend

**Stack:** React 18 · TypeScript · Vite · Tailwind · react-router.

| Route | Page | Notes |
|---|---|---|
| `/login` | Login | Username only; token → `localStorage` |
| `/` | Dashboard | Module cards, XP, level, badges |
| `/module/:moduleId` | Quiz | One question at a time; radio or checkbox |
| `/exam` | Exam | Generate → answer → per-section report |
| `/leaderboard` | Leaderboard | Ranked learners |

`lib/api.ts` is a thin typed client that attaches `X-Session-Token` from
`localStorage` to every request. Same-origin in production; Vite proxies `/api`
in dev. `lib/types.ts` mirrors the backend Pydantic schemas **by hand** — if you
change a schema, update both.

Branding: Nutanix Iris purple `#7855FA` on charcoal `#131313`.

---

## 7. Configuration

Every setting is an env var prefixed **`NKP_`** (`backend/app/config.py`). In
Kubernetes these come from the ConfigMap (non-secret) and Secret (secret).

| Var | Default | Notes |
|---|---|---|
| `NKP_ENVIRONMENT` | `development` | Free-form label |
| `NKP_DEBUG` | `false` | Echoes SQL when true |
| `NKP_DATABASE_URL` | `sqlite+aiosqlite:///./nkp_academy.db` | **In the image:** `sqlite+aiosqlite:////data/nkp_academy.db`. PostgreSQL: `postgresql+asyncpg://…` |
| `NKP_CONTENT_DIR` | repo `content/` | `/app/content` in the image |
| `NKP_STATIC_DIR` | unset (dev) | `/app/static` in the image — **this is what makes FastAPI serve the SPA** |
| `NKP_CORS_ORIGINS` | `http://localhost:5173,…` | Only needed for split dev |
| `NKP_AUTO_SEED` | `true` | Creates 3 demo learners on first boot |
| `NKP_EXAM_DEFAULT_COUNT` | `50` | Default exam length |
| `NKP_EXAM_PASS_THRESHOLD` | `0.75` | 75% to pass |

---

## 8. Build & image

Three-stage `Dockerfile`:
1. **`node:20-alpine`** → `npm run build` → `/frontend/dist`
2. **`python:3.12-slim`** → pip install into `/opt/venv`
3. **`python:3.12-slim` runtime** → copy venv + `app/` + `content/` + SPA → `/app/static`

The runtime is **non-root** (uid/gid `10001`), exposes `:8000`, has a container
`HEALTHCHECK`, and pre-sets `NKP_STATIC_DIR` / `NKP_CONTENT_DIR` /
`NKP_DATABASE_URL`.

> **Always build `--platform linux/amd64`.** NKP nodes are amd64; a Mac-native
> arm64 image will `CrashLoopBackOff` with an exec-format error.

```bash
docker buildx build --platform linux/amd64 \
  -t wnorris22/nkp:1.9.38 -t wnorris22/nkp:latest --push .

# verify it really landed (the push can fail silently in a pipeline)
docker buildx imagetools inspect wnorris22/nkp:1.9.38 | grep -E '^Name:|Platform:'
```

---

## 9. Running locally

```bash
# Full stack, production-like (SQLite) → http://localhost:8000
docker compose up --build

# With PostgreSQL instead → app on :8001
docker compose --profile postgres up

# Backend tests (64)
cd backend && .venv/bin/python3 -m pytest -q
```

---

## 10. Deploying to NKP

### What gets created
ConfigMap · Secret (only if `secrets`/`existingSecret` set) · ServiceAccount ·
PVC (1Gi) · Deployment · Service (ClusterIP :80) · Ingress · HPA (only if
`autoscaling.enabled`).

### Traffic path
```
Browser
 → kommander-traefik LoadBalancer (has the EXTERNAL-IP)
   → Ingress (className: kommander-traefik, host: nkp-academy.<ip>.nip.io)
     → Service nkp-academy (ClusterIP, :80)
       → Pod :8000
```
The Service is **ClusterIP** — the app is *only* reachable through Traefik.

### From scratch

```bash
# 1. Point at the cluster (kubeconfig from the NKP UI)
export KUBECONFIG=~/Downloads/<cluster>-kubeconfig.conf
kubectl get nodes

# 2. Repo
git clone https://github.com/wnorris222/nkp-academy.git
cd nkp-academy

# 3. Find Traefik's external IP → build an nip.io host (no DNS needed)
kubectl get svc -A | grep traefik      # e.g. EXTERNAL-IP 10.42.102.19
kubectl get ingressclass               # must be "kommander-traefik"

# 4. Install
helm upgrade --install nkp-academy deploy/helm/nkp-academy \
  --namespace nkp-academy --create-namespace \
  --set image.repository=wnorris22/nkp \
  --set image.tag=1.9.38 \
  --set ingress.className=kommander-traefik \
  --set ingress.host=nkp-academy.10.42.102.19.nip.io

# 5. Verify
kubectl -n nkp-academy rollout status deploy/nkp-academy
kubectl -n nkp-academy get pods,ingress
```
Open `http://nkp-academy.10.42.102.19.nip.io`. Content + DB seed themselves on
first boot.

### Delete / redeploy

```bash
helm uninstall nkp-academy -n nkp-academy
kubectl delete ns nkp-academy      # ALSO deletes the PVC → wipes all progress
```
> To keep learner data, run only `helm uninstall` and leave the namespace — the
> PVC survives and the next install reattaches to it.

Redeploy = the same `upgrade --install`, then:
```bash
kubectl -n nkp-academy rollout restart deploy/nkp-academy
```

### Key values (`deploy/helm/nkp-academy/values.yaml`)

| Value | Default | Watch out |
|---|---|---|
| `image.repository` | `wnorris22/nkp` | |
| `image.tag` | `""` → falls back to `Chart.appVersion` (**`1.0.0`**) | ⚠️ **always set explicitly** — `1.0.0` isn't published → `ImagePullBackOff` |
| `ingress.className` | `kommander-traefik` | ⚠️ NOT `traefik` → 404 |
| `ingress.host` | `nkp-academy.example.com` | must be your real nip.io host |
| `service.type` | `ClusterIP` | |
| `persistence.enabled` | `true` (1Gi) | holds the SQLite DB |
| `autoscaling.enabled` | `false` | ⚠️ **requires PostgreSQL** — see below |

### Scaling beyond one replica
The default is **SQLite on a ReadWriteOnce PVC** — it does **not** support
multiple replicas. To scale out you must move to PostgreSQL:
```bash
--set persistence.enabled=false \
--set autoscaling.enabled=true \
--set secrets.NKP_DATABASE_URL='postgresql+asyncpg://user:pass@postgres:5432/nkp_academy'
```

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| **404 from Traefik** | wrong ingress class | must be `kommander-traefik` |
| **ImagePullBackOff** | `image.tag` unset → `1.0.0` | set `--set image.tag=1.9.38` |
| **exec format error / CrashLoop** | arm64 image on amd64 nodes | rebuild `--platform linux/amd64` |
| **Old content after deploy** | pod running a cached tag | `kubectl rollout restart deploy/nkp-academy` |
| **`/healthz` = 503** | content failed to load | check `NKP_CONTENT_DIR`; `modules_loaded` in the response |
| **Pod Pending** | no default StorageClass | `kubectl get sc`; set `persistence.storageClass` |
| **Progress lost after redeploy** | namespace deleted → PVC gone | keep the ns; `helm uninstall` only |

Useful:
```bash
kubectl -n nkp-academy logs deploy/nkp-academy --tail=50
kubectl -n nkp-academy port-forward svc/nkp-academy 8080:80   # bypass ingress
curl -s localhost:8080/healthz
```

---

## 12. How to make common changes

**Edit / add a question** → edit the module YAML → `cd backend && pytest -q` →
rebuild + push a new tag → `helm upgrade` + `rollout restart`.
Content is baked into the image, so a YAML change *requires a rebuild*.

**Add a module** → new `content/modules/NN-*.yaml` with a unique `id`, an existing
`track`, unique question ids → it appears automatically (no code change).

**Add a badge** → append to `content/badges.yaml` using one of the three criteria
types.

**Change grading/XP rules** → `backend/app/scoring.py` (pure — unit-test it
directly in `backend/tests/test_scoring.py`).

**Add an API field** → `backend/app/schemas.py` **and** `frontend/src/lib/types.ts`
(they're hand-mirrored). Grade responses are built via
`SourceOut(**vars(source))`, so a matching field name threads through
automatically.

---

## 13. Known gaps / honest caveats

- **Auth is username-only, token = username.** Not for sensitive use. OIDC seam
  is ready (`deps.get_current_user`, `User.oidc_subject`).
- **No DB migrations.** `init_db()` does `create_all()`. Changing a model on an
  existing volume needs Alembic (or wipe the PVC).
- **Content requires a rebuild** to change (it's in the image). The Compose file
  bind-mounts `./content` so local edits are live; Kubernetes does not.
- **Single-replica by default** (SQLite/RWO). See §10 to scale.
- **Doc citations are a deliberate mix of pinned and version-less.** Of 304
  citation URLs: **169 version-less** (`Nutanix-Kubernetes-Platform:` → resolves
  to whatever the portal serves as "latest") and **135 version-pinned** —
  118 × `-v2_18`, 15 × `-v2_17`, 1 × `-v2_15`, 1 × `-v2_14`. Pinned links were
  verified at that specific version and **won't auto-roll forward**; that's
  intentional, because Nutanix renames doc slugs between versions and a
  version-less link to a renamed slug 404s. (This bit us: `top-nkp-preprovAG-
  configure-env-c.html` only ever existed in v2.13.) If a citation ever 404s,
  the fix is to find the current page and update `url` in the module YAML.
- **`frontend/src/lib/types.ts` is hand-maintained**, not generated from OpenAPI.
- **Stray `nkp-academy/nkp-academy/` duplicate** exists locally and is untracked.
