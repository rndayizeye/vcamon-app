# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this project is

A syphilis contact-tracing and case management app implementing the NCSDDC Visual Case Analysis (VCA) ghosting methodology — a 7-step pipeline that determines whether one person infected another by constructing "ghosted" lesion windows from clinical constants.

**V2 migration is underway:** the Streamlit v1 app (`app/`) is being replaced by a FastAPI backend (`fastapi_app/`) + React frontend (`frontend/`). Both backends share the same SQLAlchemy models sourced from `app/db/models.py`.

---

## Commands

### Python (use the conda env for all Python work)

```bash
conda run -n ai_coding_env_311 pytest tests/ -v                        # all tests
conda run -n ai_coding_env_311 pytest tests/test_clinical.py -v        # single file
conda run -n ai_coding_env_311 pytest tests/ -v -k "test_name"         # single test
conda run -n ai_coding_env_311 python -m ruff check app/ fastapi_app/  # lint
```

Or via Make (uses system Python):

```bash
make test              # pytest tests/ -v
make test-api          # pytest tests/test_fastapi_cases.py -v
make lint              # ruff check app/ fastapi_app/
make run-api           # alembic upgrade head + uvicorn fastapi_app.main:app --reload
make db-upgrade        # alembic upgrade head (SQLite by default)
make db-revision MESSAGE="describe change"   # autogenerate new Alembic revision
make run               # docker compose up (Streamlit stack)
```

### Frontend

```bash
cd frontend
npm run dev        # Vite dev server (http://localhost:5173)
npx tsc --noEmit   # type check
npm run lint       # ESLint
npm run build      # tsc + vite build
npm test           # vitest
```

Frontend talks to the FastAPI backend at `VITE_API_BASE_URL` (default `http://localhost:8000`). Copy `frontend/.env.example` → `frontend/.env.local` and set `VITE_SUPABASE_URL` / `VITE_SUPABASE_PUBLISHABLE_KEY` if auth is needed.

---

## Architecture

### Shared SQLAlchemy layer (the source of truth)

`app/db/models.py` — all ORM models and enums. Both the Streamlit app and FastAPI import from here. **Never create a second declarative `Base`.**

`app/db/queries.py` — all DB access functions. FastAPI routers call these; they do not write inline ORM queries. New query functions use `**kwargs` for flexible updates.

`app/db/database.py` — engine, `SessionLocal`, `init_db()`. Always use `with SessionLocal() as db:`, never bare `db = SessionLocal()`.

### Clinical engine

`app/utils/clinical.py` — **pure Python, zero framework imports**. Implements the 7-step VCA pipeline. Must stay framework-free so it drops into FastAPI without modification. Key entry points: `select_case1`, `calc_date1`, `calc_ghosted_source`, `calc_date2`, `calc_ghosted_spread`, `evaluate_criteria`, `determine_verdict`, `get_symptom_classification`.

`get_symptom_classification(symptom_type)` is called on every symptom save to derive `Primary`/`Secondary` — do not remove.

Legacy aliases (`select_p1`, `avg_inoculation_date`, `calc_d2`, `GhostingResult.p1_name`) must be kept; existing Streamlit pages call them.

### Streamlit app (`app/`)

The v1 implementation. Being superseded by v2 but must remain functional.

```
app/
├── main.py                      # Entry point + password gate
├── pages/                       # 9 multi-page app modules
│   ├── 01_dashboard.py          # Case list, search, KPI widgets
│   ├── 02_op_form.py            # Original patient clinical form
│   ├── 03_partner_form.py       # Contact partner form
│   ├── 04_map_sheet.py          # 46-item MAP assessment checklist
│   ├── 05_network_graph.py      # Transmission network + ghosting records
│   ├── 06_timeline.py           # Activity timeline with auto-seeded events
│   ├── 07_ghosting_analysis.py  # VCA ghosting engine UI (full workflow)
│   ├── 08_vca_chart.py          # Timeline visualization (Plotly)
│   └── 09_quick_ghost.py        # Quick-ghosting calculator (no case required)
├── components/                  # Reusable Streamlit widgets
│   ├── dropdowns.py             # Enum-based selectboxes
│   ├── map_grid.py              # MAP checklist grid renderer
│   ├── patient_card.py          # Case/Partner card display
│   └── sidebar_case_selector.py # Case navigation
├── db/                          # Shared data layer
│   ├── database.py              # Engine, session factory, init_db()
│   ├── models.py                # 10 ORM tables + 30+ enums (source of truth)
│   └── queries.py               # All DB access functions
└── utils/
    ├── clinical.py              # VCA engine — pure Python, no framework imports
    ├── ghosting_plot.py         # Plotly scenario diagram builder
    ├── validators.py            # Form validation rules
    ├── session_state.py         # Streamlit session state helpers + auth
    ├── network_analysis.py      # Graph construction utilities
    ├── quick_inputs.py          # Form input generators
    └── notifications.py         # User feedback widgets
```

### FastAPI backend (`fastapi_app/`)

```
fastapi_app/
├── main.py                  # create_app() — CORS + auth middleware + router
├── alembic.ini              # Alembic config
├── app/
│   ├── auth.py              # Supabase JWT verification (HS256/ES256/RS256); AUTH_ENABLED
│   ├── db/__init__.py       # engine/session wiring using shared Base; get_db()
│   ├── routers/             # 10 domain routers (one file per domain)
│   │   ├── __init__.py      # APIRouter aggregator
│   │   ├── auth.py          # GET /auth/me, /auth/status, /auth/permissions
│   │   ├── cases.py         # CRUD + analytics
│   │   ├── labs.py          # Lab result endpoints
│   │   ├── symptoms.py      # Symptom capture & classification
│   │   ├── ghosting.py      # VCA analysis (calls app.utils.clinical)
│   │   ├── map.py           # MAP entry CRUD + section totals
│   │   ├── relationships.py # Partner exposure windows & transmission links
│   │   ├── timeline.py      # Timeline events
│   │   └── analytics.py     # Case summary & statistics
│   └── schemas/             # Pydantic request/response models (mirror router names)
│       ├── auth.py, cases.py, labs.py, symptoms.py, ghosting.py
│       ├── map.py, relationships.py, timeline.py, analytics.py
└── migrations/
    ├── env.py               # Alembic environment setup
    └── versions/            # 6 migration files (chronological)
        ├── e3f9427a3fbf_initial_schema.py
        ├── b1c2d3e4f5a6_extract_subject_clinical_profile.py
        ├── 6b2a2836b7f8_add_symptom_capture_metadata.py
        ├── a1b2c3d4e5f6_add_linked_case_id_to_partners.py
        ├── d4e5f6a7b8c9_drop_deprecated_subject_fields.py
        └── ec2923821476_replace_exposure_modalities_with_body_.py
```

Auth is opt-in: `AUTH_ENABLED=false` (default) skips bearer-token enforcement. When enabled, all `/api/*` routes except `/api/auth/status`, `/health`, and docs require a Supabase access token.

Role policy: `case_worker` / `authenticated` → read + write + analysis. `supervisor` → adds delete / MAP clear / delete cases. Permissions are returned by `GET /api/auth/me` and `GET /api/auth/permissions`.

**Testing FastAPI:** `os.environ["DATABASE_URL"] = "sqlite://"` must be set **before** importing `fastapi_app.main` so the in-memory DB is used. See `tests/test_fastapi_cases.py` for the fixture pattern.

### React frontend (`frontend/`)

Stack: React 19.2, React Router 7, TanStack React Query, Supabase auth, TypeScript strict mode, Vite.

```
frontend/src/
├── main.tsx
├── app/
│   ├── providers.tsx        # QueryClientProvider + AuthProvider root
│   ├── query-client.ts      # TanStack React Query client config
│   └── router.tsx           # Browser router + RequireAuth guard
├── auth/
│   ├── auth-context.tsx     # AuthProvider, AuthContext
│   ├── auth-context-store.ts # Zustand store for auth state
│   ├── use-auth.ts          # useAuth() hook
│   ├── LoginPage.tsx
│   ├── RequireAuth.tsx      # Route-level auth guard
│   ├── RequirePermission.tsx # Role-based access guard
│   └── AuthStatusBanner.tsx
├── lib/
│   ├── api-client.ts        # apiFetch() + automatic Bearer injection
│   ├── supabase.ts          # Supabase client initialization
│   ├── auth-types.ts        # TypeScript auth interfaces
│   └── utils.ts
├── components/
│   ├── feedback/            # EmptyState, ErrorState, LoadingState, PageErrorBoundary
│   └── layout/              # AppShell, TopBar, Sidebar, CaseLayout
├── pages/
│   └── DashboardPage.tsx
└── features/                # Domain-organized feature modules
    ├── cases/               # CaseForm (symptoms + split lab editor), CRUD pages, hooks, api
    ├── partners/            # Partner list/create/edit, relationship workflow
    ├── labs/                # api (syncCaseLabs/syncPartnerLabs), hooks, types, constants
    ├── symptoms/            # api (syncCaseSymptoms), hooks, types, utils
    ├── ghosting/            # GhostingPage, VcaChartPage (pure SVG), QuickGhostPage
    ├── map/                 # CaseMapPage + components
    ├── timeline/            # TimelinePage, api, hooks, types
    ├── analytics/           # CaseAnalyticsPage + components
    └── network/             # NetworkGraphPage
```

All API calls go through `lib/api-client.ts` → `apiFetch`, which automatically reads the Supabase session token and injects `Authorization: Bearer <token>`.

**Lab field arrays** in `CaseForm` use `keyName: "formId"` on `useFieldArray` to prevent react-hook-form from overwriting the database `id` field. Never remove `keyName`.

**Symptom classification** is never stored manually; `get_symptom_classification()` on the backend derives it from the symptom type string at save time.

**Exposure dates** belong on `CasePartnerRelationship`, not on `Case`. Do not add pairwise exposure fields to the case create/edit form.

### Data model (10 tables)

`cases`, `partners`, `map_entries`, `arrow_links`, `ghostings`, `timeline_events`, `lab_results`, `case_partner_relationships`, `relationship_reports`, `symptom_entries`

`from_ref` / `to_ref` in `ArrowLink` and `Ghosting` store `"OP"` or a partner number string (`"1"`, `"2"`), not FK integers. Do not change this convention.

Legacy fields `lab_1/2/3`, `lesion_type`, `symptom` on `cases`/`partners` are deprecated — new writes set them to `None`.

### Alembic

Config at `fastapi_app/alembic.ini`. Run via `make db-upgrade` or `python3 -m alembic -c fastapi_app/alembic.ini upgrade head`. The Docker entrypoint (`docker/entrypoint.sh`) and `make run-api` both run migrations automatically before starting the server. To generate a new migration: `make db-revision MESSAGE="describe change"`.

---

## Tests

```
tests/
├── test_db.py              # Database CRUD (in-memory SQLite)
├── test_validators.py      # Form validation unit tests
├── test_clinical.py        # VCA engine (slide 17 scenario)
├── test_auth_jwt.py        # JWT verification
├── test_rbac.py            # Role-based access control
├── test_fastapi_cases.py   # FastAPI cases router (in-memory SQLite fixture)
├── test_alembic.py         # Migration validation
└── test_formatters.py      # Data formatting utilities
```

**FastAPI test fixture pattern** (`tests/test_fastapi_cases.py`):
```python
import os
os.environ["DATABASE_URL"] = "sqlite://"   # must come before the import below
from fastapi_app.main import create_app
```

CI runs on GitHub Actions (`.github/workflows/ci.yml`) against Python 3.11 on push to `main`/`develop` and PRs to `main`.

---

## Deployment

```
docker-compose.yml
├── app     (Streamlit, port 8501)
└── fastapi (FastAPI, port 8000)
```

Both services use the same project root as build context. `docker/entrypoint.sh` runs `alembic upgrade head` before starting uvicorn.

**Key environment variables** (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/vcamon_v2.db` | Switch to Supabase PostgreSQL URL for prod |
| `AUTH_ENABLED` | `false` | Set `true` to enforce Supabase JWT on all `/api/*` routes |
| `SUPABASE_URL` | — | Required when `AUTH_ENABLED=true` |
| `SUPABASE_ANON_KEY` | — | Required when `AUTH_ENABLED=true` |
| `SUPABASE_JWT_SECRET` | — | Required when `AUTH_ENABLED=true` |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |

Frontend env (copy `frontend/.env.example` → `frontend/.env.local`):

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | FastAPI base URL (default `http://localhost:8000`) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase anon key |

---

## Key constraints

- `app/utils/clinical.py` — no Streamlit, SQLAlchemy, or third-party imports, ever.
- `MAP_ITEMS` dict (1–46) in `models.py` matches the Excel workbook exactly — do not renumber.
- Lab vocabulary enums (`NonTreponemalTestType`, `TreponemalTestType`, etc.) are **UI-only** — never map them to SQLAlchemy columns.
- `SymptomEntry.classification` is always derived by `get_symptom_classification()` at save time, never set manually.
- Never create a second SQLAlchemy `Base`; always import from `app/db/models.py`.
- FastAPI routers never write inline ORM queries — all DB access goes through `app/db/queries.py`.
- `from_ref` / `to_ref` use string identifiers (`"OP"`, `"1"`, `"2"`), not integer foreign keys.
- Legacy Streamlit aliases in `clinical.py` must be preserved.

---

## Common tasks

**Add a new FastAPI endpoint:**
1. Add query function(s) to `app/db/queries.py`.
2. Add Pydantic schema(s) to `fastapi_app/app/schemas/<domain>.py`.
3. Add route handler to `fastapi_app/app/routers/<domain>.py` using `Depends(get_db)`.
4. The router is auto-registered via `fastapi_app/app/routers/__init__.py`.

**Add a new database column:**
1. Add the column to the ORM model in `app/db/models.py`.
2. Run `make db-revision MESSAGE="add <column> to <table>"` to autogenerate the migration.
3. Run `make db-upgrade` to apply.

**Add a new frontend feature page:**
1. Create `frontend/src/features/<domain>/` with `api.ts`, `hooks.ts`, `types.ts`, and page component(s).
2. Add the route to `frontend/src/app/router.tsx`.
3. Use `apiFetch` from `lib/api-client.ts` for all HTTP calls — never use `fetch` directly.
