# VCA Monitor — Project Context
_Read this before touching any code. Updated rarely — edit only when stack or conventions change._

---

## What this project is

A Streamlit contact tracing and case management web app for syphilis disease
intervention work. It implements the NCSDDC Visual Case Analysis (VCA) ghosting
methodology — a 7-step pipeline that calculates whether one person infected another
by constructing "ghosted" lesion windows from syphilis natural history constants.

Rebuilt from two sources:
- `vcamon-launch-v1.xlsm` — legacy Excel workbook (field names, workflow structure)
- Fussell (2022) NCSDDC VCA Training — clinical methodology

Live beta: https://visualcaseanalysis.streamlit.app
Repo: rndayizeye/vcamon-app

---

## Stack

| Layer | Technology | Version |
|---|---|---|
| UI framework | Streamlit $\rightarrow$ React (V2 Migration) | ≥1.35 (Streamlit), Vite (React) |
| API framework | FastAPI | ≥0.104 |
| ORM | SQLAlchemy | ≥2.0 (declarative, Mapped columns) |
| Migrations | Alembic | ≥1.10 |
| Database (current) | SQLite | ./data/vcamon_v2.db (Docker volume) |
| Database (target) | PostgreSQL via Supabase | v2 migration underway |
| Python | 3.11 | |
| Linter | Ruff | |
| Tests | Pytest | ≥8.0 |
| Graphs | streamlit-agraph | ≥0.0.45 |
| Charts | Plotly | ≥5.0 |
| Containerisation | Docker + Docker Compose | |
| CI | GitHub Actions | .github/workflows/ci.yml |

---

## Project structure

```
vcamon-app/
├── app/
│   ├── main.py                    # Entry point + password gate + demo seed
│   ├── pages/
│   │   ├── 01_dashboard.py        # Case list, search, metrics
│   │   ├── 02_op_form.py          # Original patient form (split lab editors)
│   │   ├── 03_partner_form.py     # Contact partner form (split lab editors)
│   │   ├── 04_map_sheet.py        # 46-item MAP assessment checklist
│   │   ├── 05_network_graph.py    # Transmission network (streamlit-agraph)
│   │   ├── 06_timeline.py         # Activity timeline + heatmap
│   │   ├── 07_ghosting_analysis.py # Full VCA ghosting workflow (multi-row symptom editor)
│   │   ├── 08_vca_chart.py        # Plotly VCA timeline chart ⚠ symptom data not wired yet
│   │   └── 09_quick_ghost.py      # Quick ghosting (multi-row symptom editor, no case needed)
│   ├── db/
│   │   ├── database.py            # Engine, SessionLocal, init_db (with schema guard)
│   │   ├── models.py              # ORM models + MAP_ITEMS + all Enums
│   │   └── queries.py             # All DB access functions (no raw SQL)
│   ├── components/
│   │   ├── dropdowns.py           # enum_options(), val_or_none() — legacy selectbox helpers
│   │   └── sidebar_case_selector.py
│   └── utils/
│       ├── session_state.py       # Centralized st.session_state keys + require_password()
│       ├── validators.py          # Pure Python form validation (no Streamlit imports)
│       ├── clinical.py            # VCA ghosting engine — pure Python, no Streamlit/SQLAlchemy
│       └── ghosting_plot.py       # Plotly scenario diagram builder
├── fastapi_app/
│   ├── main.py                    # FastAPI entry point / app factory
│   ├── app/
│   │   ├── db/__init__.py         # FastAPI engine/session wiring using shared Base
│   │   ├── routers/cases.py       # Initial REST endpoints for cases + partners
│   │   └── schemas/cases.py       # Pydantic request/response models
│   └── migrations/                # Alembic env + future revisions
├── tests/
│   ├── test_clinical.py           # Ghosting engine unit tests (slide 17 scenario)
│   ├── test_db.py                 # CRUD tests using in-memory SQLite
│   ├── test_fastapi_cases.py      # FastAPI health + case/partner API tests
│   └── test_validators.py         # Form validation unit tests
├── docker/ requirements/ data/
└── .ai-context/                   # ← YOU ARE HERE
```

---

## Data model (10 tables)

| Table | Description |
|---|---|
| `cases` | Root record — one per original patient (OP) |
| `partners` | Contact partners linked to a case |
| `map_entries` | 46-item MAP checklist rows (item_number, p_value, c_value) |
| `arrow_links` | Directed transmission links (from_ref / to_ref = "OP" or "1".."N") |
| `ghostings` | Saved ghosted lesion records (SOURCE / SPREAD_GHOST / SPREAD) |
| `timeline_events` | Dated activity entries per partner |
| `lab_results` | Repeatable lab history per case or partner (split by TestCategory) |
| `case_partner_relationships` | Exposure window + sex types per OP↔partner pair |
| `relationship_reports` | Per-reporter evidence for the consensus narrative |
| `symptom_entries` | Repeatable symptom entries per case or partner, with date provenance (`date_kind`) and duration provenance (`duration_source`) |

Legacy fields (`lab_1`, `lab_2`, `lab_3`, `lesion_type`, `symptom`) are kept on
`cases` and `partners` but deprecated — all new writes set them to `None`.

---

## Enums — complete list (models.py)

**Clinical / workflow (mapped to DB columns):**
`ReasonForExam`, `LabResult` (legacy), `TreponemalResult` (legacy), `Treatment`,
`LesionType`, `Symptom` (secondary symptoms), `SymptomClassification`, `TestCategory`,
`GhostingType`

**Lab vocabulary (UI-only — NOT mapped to DB columns, used in data_editor column_config):**
- `NonTreponemalTestType` — RPR, VDRL
- `TreponemalTestType` — TPPA, TP-AB, FTA, FTA-ABS, DFKD, MHA-TP, Other
- `NonTreponemalTiter` — Non-Reactive, 1:1 … >1:1024
- `TreponemalTestResult` — Reactive, Non-reactive

The UI-only enums are used via `enum_options(EnumClass)` in the split lab editor
column configs on pages 02 and 03. They are not stored directly; the text value
is written to `LabResultEntry.test_type`, `titer`, and `result` as strings.

---

## Clinical engine (app/utils/clinical.py)

**The most important file.** Pure Python, zero dependencies on Streamlit or SQLAlchemy.
Implements the 7-step VCA ghosting pipeline.

### Key constants
`INCUBATION {10/21/90}`, `PRIMARY {7/21/35}`, `LATENCY {0/28/70}`, `SECONDARY {14/28/42}`
Warn margin: `EXPOSURE_WARN_MARGIN_DAYS = 10`
Min latency to secondary: `MIN_LATENCY_TO_SECONDARY_DAYS = 35`

**Interview Periods (Sum of maximums):**
- Primary: 4 months, 1 week (Max Incubation + Max Primary)
- Secondary: 8 months, 1 week (Max Incubation + Max Primary + Max Latency + Max Secondary)

**Clinical Notes:**
- Generalized body rash typically does not last > ~6 weeks.
- **Partner Services** (broad social action/prevention) $\neq$ **Contact Tracing** (locating partners for care).

### Key functions
- `select_case1()` — rank by hierarchy; earlier onset wins ties
- `calc_date1()` — inoculation date: `onset − avg_incubation` (primary) or back through full chain (secondary)
- `calc_ghosted_source()` — `Date1 ± 10 days`
- `calc_date2()` — infectious midpoint: `onset + duration/2` (primary)
- `calc_ghosted_spread()` — `Date2 + avg_incubation`, duration = avg_primary
- `evaluate_criteria()` — exposure overlap (period intersection), anatomical compatibility, latency, natural order
- `determine_verdict()` — SOURCE / SPREAD / AMBIGUOUS / UNRELATED + overlap annotation
- `get_symptom_classification(symptom_type)` → `"Primary"` | `"Secondary"` | `None`
  Called on every form/API save; derives classification from the lesion/symptom type string.
  Do NOT remove — pages 02, 03, 07, 09 and FastAPI symptom routes all depend on it.
- `calc_interview_period_start(onset, type, last_negative_date)` — exists but not yet wired to UI

### `Symptom` dataclass fields
`type: str`, `onset: date`, `duration_days: int`, `location: str | None`
The `location` field stores the anatomical site (e.g. `"Penile LX"`) for the
sex-type compatibility criterion. Set from the `Location` column of the symptom editor.

### `_natural_order()` behaviour (important — changed in last merge)
- Returns `warn` (not `fail`) when primary overlaps secondary onset
  (chancre active when secondary appeared — biologically possible, latency min = 0)
- Returns `fail` for reversed timeline (secondary appeared before primary started)
- `determine_verdict()` appends a ⚠ annotation when either scenario has an overlap warn

### Legacy aliases (keep, don't remove)
`select_p1 = select_case1`, `avg_inoculation_date = calc_date1`, `calc_d2 = calc_date2`
`GhostingResult.p1_name`, `.p2_name`, `.p1_symptom` — property aliases for `case1_*`

---

## Conventions

### Database
- Always use `with SessionLocal() as db:` context manager — never bare `db = SessionLocal()`
- All DB access goes through functions in `queries.py` — no inline ORM queries in pages or FastAPI routers
- New query functions use `**kwargs` pattern for flexible updates
- `from_ref` / `to_ref` in ArrowLink and Ghosting: `"OP"` or partner number string (`"1"`, `"2"`)

### FastAPI backend (`fastapi_app/`)
- Reuse shared ORM models from `app/db/models.py` via the shared `Base`; do not create a second declarative model tree.
- Reuse business/data-access logic from `app/db/queries.py` where practical; FastAPI should be a thin API layer, not a parallel rewrite.
- Routers live in `fastapi_app/app/routers/`; Pydantic schemas live in `fastapi_app/app/schemas/`.
- Endpoint tests should override `get_db` and pin `DATABASE_URL` to SQLite before importing the FastAPI app.
- Symptom APIs now expose `date_kind` and `duration_source` and derive `ongoing` server-side from symptom provenance.

### Streamlit pages
- Every page calls `init_session_state()` then `require_password()` at the top
- Active case ID: always use `get_active_case_id()` / `set_active_case_id()`
- Active partner ID: always use `get_active_partner_id()` / `set_active_partner_id()`
- Navigation: `st.switch_page("pages/NN_name.py")` — no relative paths
- `st.set_page_config()` must be the first Streamlit call on every page
- Exposure window fields belong on the OP↔partner relationship workflow (`CasePartnerRelationship`), not on the case record itself.

### Lab editor pattern (pages 02 and 03)
Two separate `st.data_editor` tables: non-treponemal (left) and treponemal (right).
Both are currently inside `st.form()` — known issue, see ADR-008.
Keys: `"op_nontrop_lab_editor"`, `"op_trep_lab_editor"`, `"partner_nontrop_lab_editor"`, `"partner_trep_lab_editor"`.
Save logic: collect current IDs from DB, diff against editor IDs, delete orphans, upsert rows.

### Symptom editor pattern (pages 02, 03, 07, 09)
Streamlit pages 02 and 03 now collect symptom rows with `Type`, `Onset or Observation Date`, `Date Type`, and `Duration`.
`ongoing` is derived in the new symptom provenance flow instead of being manually entered.
Classification is derived via `get_symptom_classification()` at save time — never stored manually.

Pages 07 and 08 must interpret saved symptom rows through the derived timing helpers rather than assuming the stored date is always a true onset date.

### Models
- All enums inherit from `(str, enum.Enum)` for SQLAlchemy compatibility
- UI-only lab vocabulary enums (`NonTreponemalTestType` etc.) are NOT mapped to columns
- `MAP_ITEMS` dict (1–46) lives in models.py — reference it in UI, never store labels in DB

---

## Known tech debt

| Issue | File(s) | Priority |
|---|---|---|
| `st.data_editor` inside `st.form()` — may lose edits on submit | 02, 03 | High |
| VCA chart (08) not reading `SymptomEntry` — symptom bars blank | 08 | High |
| VCA chart (08) not reading `LabResultEntry` — lab markers blank | 08 | Medium |
| `dropdowns.py` has unused legacy helpers | components/dropdowns.py | Low |

---

## Do not touch

- `app/utils/clinical.py` — must stay framework-free (pure Python) for v2 FastAPI drop-in
- The `MAP_ITEMS` dict numbering (1–46) — matches the Excel workbook exactly
- `from_ref` / `to_ref` string convention — changing breaks existing ghosting records
- Legacy alias properties on `GhostingResult` and functions — still called by existing pages

---

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/vcamon_v2.db` | PostgreSQL in production |
| `APP_ENV` | `development` | |
| `SECRET_KEY` | — | Required in production |
| `BETA_PASSWORD` | — | In `.streamlit/secrets.toml` (never commit) |

Local agent validation should use the dedicated conda env `ai_coding_env_311` via
`conda run -n ai_coding_env_311 ...` to avoid installing into base Anaconda.

`docker-compose.yml` now points at `sqlite:////project/data/vcamon_v2.db`.

Streamlit Cloud: SQLite goes to `/tmp` and resets on restart. Demo case auto-seeded on cold start.

---

## V2 migration status

**Started. Current backend baseline:**
- FastAPI app scaffold is active under `fastapi_app/`
- Shared SQLAlchemy metadata from `app/db/models.py` is reused by FastAPI and Alembic
- Implemented endpoints: `/health`, `/api/cases`, `/api/cases/{id}`, `/api/cases/{id}/partners`, `/api/cases/partners/{partner_id}`
- Implemented labs endpoints: `/api/cases/{id}/labs`, `/api/cases/partners/{partner_id}/labs`, `/api/cases/labs/{entry_id}`
- Implemented symptoms endpoints: `/api/cases/{id}/symptoms`, `/api/cases/partners/{partner_id}/symptoms`, `/api/cases/symptoms/{entry_id}`
- Implemented timeline endpoints: `/api/cases/{id}/timeline`, `/api/cases/timeline/{event_id}`
- Implemented relationship endpoints: `/api/cases/{case_id}/partners/{partner_id}/relationship`, `/api/cases/relationships/{relationship_id}/reports`, `/api/cases/relationships/reports/{report_id}`
- Implemented ghosting endpoints: `/api/ghosting/analyze`, `/api/cases/{case_id}/partners/{partner_id}/ghosting-analysis`, `/api/cases/{case_id}/ghostings`, `/api/cases/ghostings/{ghosting_id}`
- Implemented analytics endpoints: `/api/cases/{id}/links`, `/api/cases/links/{link_id}`, `/api/cases/{id}/analytics`
- Implemented MAP endpoints: `/api/map/items`, `/api/cases/{case_id}/map`, `/api/cases/{case_id}/partners/{partner_id}/map`
- Implemented auth scaffolding: optional Supabase-backed auth middleware plus `/api/auth/status`, `/api/auth/me`, and `/api/auth/permissions`
- Added initial role policy scaffold: operator access for create/update flows; supervisor-only access for destructive deletes/MAP clears
- Initial Alembic revision exists at `fastapi_app/migrations/versions/e3f9427a3fbf_initial_schema.py`
- API tests live in `tests/test_fastapi_cases.py`; migration coverage lives in `tests/test_alembic.py`

**Completed this session:**
- Alembic migrations applied (`make db-upgrade`) — `vcamon_v2.db` is current
- Frontend login flow complete and tested end-to-end in open access mode (`AUTH_ENABLED=false`)
  - `useAuthBootstrap` sequence: `GET /api/auth/status` → `GET /api/auth/me` → resolve `OPEN_ACCESS_PERMISSIONS`
  - `RequireAuth` route guard, `RequirePermission` permission gates wired on all destructive actions
  - `LoginPage` handles both auth-enabled (magic link) and auth-disabled (bypass) modes
  - `TopBar` shows user email + sign-out when auth is enabled
  - TypeScript compiles clean; full stack verified: FastAPI on `localhost:8000`, Vite on `localhost:5173`
- React partner form complete (`frontend/src/features/partners/components/PartnerForm.tsx`)
  - Fixed `historical_primary_chancre`: select string → `bool | null` conversion in `toPartnerPayload`
  - Fixed `any[]` types → `SymptomEntryRead[]` / `LabResultEntryRead[]`
  - Added `toLabDraft()` so DB `id` is preserved on edit (prevents duplicate rows)
  - Added `normalizeLabDrafts()` before submit — blank rows are stripped
  - Removed dead exposure fields (belong on `CasePartnerRelationship`, not `Partner`)
  - Fixed `PartnerCreatePage` to sync labs on create (`syncPartnerLabs` alongside `syncPartnerSymptoms`)

**Next steps:**
- Set up Supabase project and add credentials to activate real auth (`AUTH_ENABLED=true`)
  - `frontend/.env.local`: add `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`
  - `.env`: add `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `AUTH_ENABLED=true`
- Test authenticated flow end-to-end (magic link → token injection → `/api/auth/me` returns real user)
- Remaining React page migrations: MAP sheet (page 04), network graph (page 05), timeline (page 06), quick ghost (page 09)
- Refine RBAC beyond the current rollout-safe operator/supervisor scaffold if product rules become more specific
