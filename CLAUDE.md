# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What this project is

A syphilis contact-tracing and case management app implementing the NCSDDC Visual Case Analysis (VCA) ghosting methodology — a 7-step pipeline that determines whether one person infected another by constructing "ghosted" lesion windows from clinical constants.

**V2 migration is underway:** the Streamlit v1 app (`app/`) is being replaced by a FastAPI backend (`fastapi_app/`) + React frontend (`frontend/`). Both backends share the same SQLAlchemy models.

---

## Commands

### Python (use the conda env for all Python work)

```bash
conda run -n ai_coding_env_311 pytest tests/ -v                   # all tests
conda run -n ai_coding_env_311 pytest tests/test_clinical.py -v   # single file
conda run -n ai_coding_env_311 pytest tests/ -v -k "test_name"    # single test
conda run -n ai_coding_env_311 python -m ruff check app/ fastapi_app/  # lint
```

Or via Make (uses system Python):

```bash
make test          # pytest tests/ -v
make test-api      # pytest tests/test_fastapi_cases.py -v
make lint          # ruff check app/ fastapi_app/
make run-api       # alembic upgrade head + uvicorn fastapi_app.main:app --reload
make db-upgrade    # alembic upgrade head (SQLite by default)
make db-revision MESSAGE="describe change"   # autogenerate new Alembic revision
make run           # docker compose up (Streamlit stack)
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

Legacy aliases (`select_p1`, `avg_inoculation_date`, `calc_d2`, `GhostingResult.p1_name`) must be kept; existing pages call them.

### FastAPI backend (`fastapi_app/`)

```
fastapi_app/
├── main.py                  # create_app() — CORS + auth middleware + router
├── app/
│   ├── auth.py              # Supabase bearer-token validation; AUTH_ENABLED env var
│   ├── db/__init__.py       # engine/session wiring using shared Base; get_db()
│   ├── routers/             # one file per domain (cases, labs, symptoms, ghosting, …)
│   └── schemas/             # Pydantic request/response models (mirror router names)
└── migrations/              # Alembic env; initial revision at versions/e3f9427…
```

Auth is opt-in: `AUTH_ENABLED=false` (default) skips bearer-token enforcement. When enabled, all `/api/*` routes except `/api/auth/status`, `/health`, and docs require a Supabase access token.

Role policy: `case_worker` / `authenticated` → read + write + analysis. `supervisor` → adds delete / MAP clear / delete cases. Permissions are returned by `GET /api/auth/me` and `GET /api/auth/permissions`.

**Testing FastAPI:** `os.environ["DATABASE_URL"] = "sqlite://"` must be set **before** importing `fastapi_app.main` so the in-memory DB is used. See `tests/test_fastapi_cases.py` for the fixture pattern.

### React frontend (`frontend/`)

```
frontend/src/
├── app/           # providers (QueryClient + AuthProvider), router, query-client
├── auth/          # AuthContext, LoginPage, RequireAuth, RequirePermission
├── lib/           # api-client (apiFetch + Bearer injection), supabase client, auth-types
└── features/
    ├── cases/     # CaseForm (symptoms + split lab editor), create/edit pages, hooks, api
    ├── labs/      # api (syncCaseLabs/syncPartnerLabs), hooks, types, constants
    ├── symptoms/  # api (syncCaseSymptoms), hooks, types, utils (normalizeSymptomDrafts)
    ├── ghosting/  # GhostingPage, VcaChartPage (pure SVG), types/api/hooks
    ├── partners/  # partner list/create/edit, relationship workflow
    ├── map/       # CaseMapPage
    └── analytics/ # CaseAnalyticsPage
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

Config at `fastapi_app/alembic.ini`. Run via `make db-upgrade` or `python3 -m alembic -c fastapi_app/alembic.ini upgrade head`. The Docker entrypoint (`docker/entrypoint.sh`) and `make run-api` both run migrations automatically before starting the server.

---

## Key constraints

- `app/utils/clinical.py` — no Streamlit, SQLAlchemy, or third-party imports, ever.
- `MAP_ITEMS` dict (1–46) in `models.py` matches the Excel workbook exactly — do not renumber.
- Lab vocabulary enums (`NonTreponemalTestType`, `TreponemalTestType`, etc.) are **UI-only** — never map them to SQLAlchemy columns.
- `SymptomEntry.classification` is always derived by `get_symptom_classification()` at save time, never set manually.
