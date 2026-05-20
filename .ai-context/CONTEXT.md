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
| UI framework | Streamlit | ≥1.35 |
| ORM | SQLAlchemy | ≥2.0 (declarative, Mapped columns) |
| Database (current) | SQLite | ./data/vcamon_v2.db (Docker volume) |
| Database (target) | PostgreSQL via Supabase | v2 migration |
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
├── tests/
│   ├── test_clinical.py           # Ghosting engine unit tests (slide 17 scenario)
│   ├── test_db.py                 # CRUD tests using in-memory SQLite
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
| `symptom_entries` | Repeatable symptom entries per case or partner |

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
- `NonTreponemalTiter` — Neg, Reactive, 1:1 … >1:1024
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

### Key functions
- `select_case1()` — rank by hierarchy; earlier onset wins ties
- `calc_date1()` — inoculation date: `onset − avg_incubation` (primary) or back through full chain (secondary)
- `calc_ghosted_source()` — `Date1 ± 10 days`
- `calc_date2()` — infectious midpoint: `onset + duration/2` (primary)
- `calc_ghosted_spread()` — `Date2 + avg_incubation`, duration = avg_primary
- `evaluate_criteria()` — exposure overlap (period intersection), anatomical compatibility, latency, natural order
- `determine_verdict()` — SOURCE / SPREAD / AMBIGUOUS / UNRELATED + overlap annotation
- `get_symptom_classification(symptom_type)` → `"Primary"` | `"Secondary"` | `None`
  Called on every form save; derives classification from the lesion/symptom type string.
  Do NOT remove — pages 02, 03, 07, 09 all depend on it.
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
- All DB access goes through functions in `queries.py` — no inline ORM queries in pages
- New query functions use `**kwargs` pattern for flexible updates
- `from_ref` / `to_ref` in ArrowLink and Ghosting: `"OP"` or partner number string (`"1"`, `"2"`)

### Streamlit pages
- Every page calls `init_session_state()` then `require_password()` at the top
- Active case ID: always use `get_active_case_id()` / `set_active_case_id()`
- Active partner ID: always use `get_active_partner_id()` / `set_active_partner_id()`
- Navigation: `st.switch_page("pages/NN_name.py")` — no relative paths
- `st.set_page_config()` must be the first Streamlit call on every page

### Lab editor pattern (pages 02 and 03)
Two separate `st.data_editor` tables: non-treponemal (left) and treponemal (right).
Both are currently inside `st.form()` — known issue, see ADR-008.
Keys: `"op_nontrop_lab_editor"`, `"op_trep_lab_editor"`, `"partner_nontrop_lab_editor"`, `"partner_trep_lab_editor"`.
Save logic: collect current IDs from DB, diff against editor IDs, delete orphans, upsert rows.

### Symptom editor pattern (pages 02, 03, 07, 09)
Single `st.data_editor` with columns: `Type` (SelectboxColumn), `Onset Date`, `Duration`, `Ongoing` (pages 02/03) or `Location` (pages 07/09).
Classification is derived via `get_symptom_classification()` at save time — never stored manually.

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
| `docker-compose.yml` DATABASE_URL still points to `vcamon.db` not `vcamon_v2.db` | docker-compose.yml | Medium |
| No Alembic — schema migration is drop-and-recreate | database.py | Must fix before real data |
| `test_db.py` missing `LabResultEntry` + `SymptomEntry` CRUD tests | tests/ | Medium |

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

Note: `docker-compose.yml` still sets `DATABASE_URL=sqlite:////project/data/vcamon.db`
(old name). This is a known mismatch — update before next Docker deploy.

Streamlit Cloud: SQLite goes to `/tmp` and resets on restart. Demo case auto-seeded on cold start.

---

## Planned v2 migration (do not start yet)

- Backend: FastAPI + SQLAlchemy (same models, REST API layer)
- Database: PostgreSQL via Supabase
- Frontend: React + Tailwind CSS
- Auth: Supabase Auth (case worker vs supervisor roles)
- `clinical.py` drops in unchanged — design decisions must preserve this
