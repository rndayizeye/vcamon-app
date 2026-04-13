# vcamon-app

Contact tracing and case management tool for syphilis disease intervention work.
Rebuilt from a legacy Excel workbook (`vcamon-launch-v1.xlsm`) and a Dash prototype
(`vca_app_v5`) as a structured, tested, containerized web application using Streamlit,
SQLAlchemy, and SQLite — designed for a planned full-stack migration to FastAPI + React.

---

## What it does

Case workers use this app to manage syphilis contact tracing cases end-to-end:

- Record original patient (OP) demographics, exam reason, lab results, and treatment
- Add and track contact partners with the same clinical data
- Complete the 46-item Major Analytical Points (MAP) assessment checklist per interview
- Run automated ghosting analysis to determine source/spread relationships between the OP and partners
- Visualize transmission networks as interactive directed graphs
- Track case activity on a date timeline with auto-seeded treatment events

---

## Project structure

```
vcamon-app/
├── app/
│   ├── main.py                    # Streamlit entry point
│   ├── pages/
│   │   ├── 01_dashboard.py        # Case list, search, navigation
│   │   ├── 02_op_form.py          # Original patient form
│   │   ├── 03_partner_form.py     # Contact partner form
│   │   ├── 04_map_sheet.py        # 46-item MAP assessment
│   │   ├── 05_network_graph.py    # Transmission network + ghosting records
│   │   ├── 06_timeline.py         # Activity timeline and calendar
│   │   └── 07_ghosting_analysis.py # VCA ghosting engine UI
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine and session
│   │   ├── models.py              # ORM models + MAP_ITEMS reference data
│   │   └── queries.py             # All database access functions
│   ├── components/
│   │   ├── dropdowns.py           # Shared enum selectboxes
│   │   └── sidebar_case_selector.py
│   └── utils/
│       ├── session_state.py       # Centralized st.session_state helpers
│       ├── validators.py          # Form validation — pure Python, no Streamlit
│       └── clinical.py            # VCA ghosting analysis engine — pure Python
├── docker/
│   ├── Dockerfile
│   └── .dockerignore
├── requirements/
│   ├── base.txt                   # Runtime dependencies
│   ├── dev.txt                    # Testing and linting tools
│   └── prod.txt                   # Production overrides
├── tests/
│   ├── test_db.py                 # Database CRUD tests (in-memory SQLite)
│   ├── test_validators.py         # Form validation unit tests
│   └── test_clinical.py          # Ghosting engine unit tests (slide 17 scenario)
├── data/                          # SQLite database volume (git-ignored)
├── .github/workflows/ci.yml       # Lint + test on push
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── .env.example
```

---

## Quickstart

### With Docker (recommended)

```bash
git clone https://github.com/rndayizeye/vcamon-app.git
cd vcamon-app

cp .env.example .env

make build
make run
```

Open [http://localhost:8501](http://localhost:8501).

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements/base.txt
pip install -e .

mkdir -p data
streamlit run app/main.py
```

---

## Environment variables

Copy `.env.example` to `.env` and set values before running:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/vcamon.db` | SQLAlchemy connection string |
| `APP_ENV` | `development` | `development` or `production` |
| `SECRET_KEY` | — | Required in production |

The SQLite database is created automatically on first run. The `data/` directory
is mounted as a Docker volume so it persists across container restarts.

---

## Development

### Running tests

```bash
make test

# With coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Single file
pytest tests/test_clinical.py -v
```

Tests use an in-memory SQLite database — no running app or Docker required.
The clinical engine tests use the exact case scenario from the NCSDDC VCA
training (slide 17) as their integration test.

### Linting

```bash
ruff check app/
ruff check app/ --fix
```

### Useful Make targets

| Command | What it does |
|---|---|
| `make run` | Start the app with Docker Compose |
| `make build` | Rebuild the Docker image |
| `make test` | Run the pytest suite |
| `make lint` | Run ruff linter |
| `make shell` | Open a shell inside the running container |

---

## Data model

Six tables derived from the original Excel workbook:

| Table | Source sheet | Description |
|---|---|---|
| `cases` | OP | Original patient — root record for each case |
| `partners` | P1, AddPartner2 | Contact partners linked to a case |
| `map_entries` | MAP, MAPOP, MAP1 | 46-item P/C assessment checklist rows |
| `arrow_links` | Arrows | Directed transmission links between parties |
| `ghostings` | GhostingSource, GhostingSpread | Calculated ghosted lesion records |
| `timeline_events` | Chart | Dated activity entries per partner |

All dropdown option lists (lab results, treatments, lesion types, etc.) are
modeled as Python enums in `app/db/models.py` and validated at the ORM level.

---

## Pages

### 01 Dashboard
Case list with search, summary metrics (total cases, treated vs pending),
and one-click navigation to any page for any case.

### 02 OP form
Creates or edits the original patient record. Fields: patient name, lot,
case manager, reason for exam, treatment date, treatment given, lesion type,
symptom, medical info, and three lab result slots (RPR/VDRL, treponemal
confirmatory, free text). Navigation buttons route directly to Partners or MAP.

### 03 Partner form
Same field structure as the OP form. Supports adding multiple partners with
"Save + add another". Shows a partner roster table below the form with
quick-select buttons. Untreated partners are highlighted in amber.

### 04 MAP sheet
The 46-item Major Analytical Points assessment. Items are grouped into six
sections: Social History, Medical History, Partners, Clusters, Risk Reduction,
and Other. Each item has P (previous interview) and C (current interview)
checkboxes, a high-priority flag, and a notes field. The same page renders
both the OP MAP sheet and partner-specific sheets via the subject selector.
All 46 items are batch-saved in a single database session on submit.

### 05 Network graph
Interactive directed graph of transmission links using `streamlit-agraph`.
OP node is coral, treated partners are teal, untreated partners are amber.
Links can be added and removed from the page. The ghosting tracker for
source, spread ghost, and spread records lives in the lower half of the page.

### 06 Timeline
Three views: scatter timeline (events on a date axis per subject), monthly
heatmap (activity density by month), and raw event table with delete.
Treatment dates from the OP and partner forms are auto-seeded on first visit.
Supports seven event types: Treatment, Lab work, Interview, Re-interview,
Field visit, Phone contact, and Other.

### 07 Ghosting analysis
Implements the full VCA ghosting methodology. The worker selects a partner,
confirms symptom data, runs the engine, reviews a step-by-step criteria log,
and saves ghosted lesion records back to the database. See the
**Epidemiological methodology** section below for a full explanation of the logic.

---

## Epidemiological methodology — VCA ghosting analysis

*Based on: Fussell, E. (2022). Visual Case Analysis. National Coalition of STD
Directors / Marion County Public Health Department.
https://www.ncsddc.org/wp-content/uploads/2022/07/VCA-Training-7.2022.pdf*

The ghosting engine answers a single question: given that two people both have
syphilis, did one infect the other — and if so, who was the source?

Since we cannot observe past infections directly, the engine uses the known
natural history of syphilis to construct "ghosted" lesion windows: calculated
date ranges representing when an unobserved primary chancre would have been
present and infectious. It then checks those windows against the clinical record.

### Syphilis natural history constants

| Phase | Min | Avg | Max |
|---|---|---|---|
| Incubation | 10 days | 21 days | 90 days |
| Primary chancre | 7 days | 21 days | 35 days |
| Latency | 0 days | 28 days | 70 days |
| Secondary symptoms | 14 days | 28 days | 42 days |

### The ghosting hierarchy

Not all symptoms are equally useful as anchors for the analysis. The hierarchy
ranks them by clinical precision, from most to least reliable:

1. Existing primary chancre — patient has an active chancre right now
2. Historical primary chancre — chancre healed but patient clearly recalls it
3. Ghosted primary chancre — calculated from a partner's symptoms in a prior analysis
4. Secondary symptoms — rash, alopecia, condylomata lata (requires working back through the full disease chain)

### The seven-step pipeline

**Step 1 — Select P1.** The person with the highest-ranking symptom in the
hierarchy becomes P1. Their symptom timeline anchors all subsequent date
calculations. The other person becomes P2. If both have symptoms of equal
rank, the OP is assigned P1.

**Step 2 — Calculate D1.** Working backwards from P1's symptom onset using
average durations, D1 is the estimated date P1 was exposed to infectious
syphilis.

- Primary chancre: `D1 = onset − 21 days`
- Secondary symptoms: `D1 = onset − 21 days incubation − 21 days primary − 28 days latency`

**Step 3 — Ghosted source lesion for P2.** If P2 was the source of P1's
infection, P2 must have had an active chancre when P1 was exposed. D1 is
placed at the midpoint of that ghosted window:

```
ghosted source onset = D1 − 10 days
ghosted source end   = D1 + 10 days
```

**Step 4 — D2 and ghosted spread lesion for P2.** D2 is the midpoint of P1's
own primary chancre — the point at which P1 was most infectious. If P1
infected P2, P2 would have developed a chancre starting one average primary
duration after that midpoint:

- Primary or historical chancre: `D2 = chancre onset + (duration ÷ 2)`
- Secondary only: `D2 = secondary onset − 28 days latency − 10.5 days`

```
ghosted spread onset = D2 + 21 days
ghosted spread end   = D2 + 42 days
```

**Step 5 — Evaluate four criteria for each scenario.**

| Criterion | What is checked | Fail condition |
|---|---|---|
| Exposure overlap | Ghosted lesion onset falls within the reported sexual exposure window | Onset outside all reported exposure dates |
| Anatomical compatibility | Symptom location is consistent with the type of sex reported | Rectal chancre with no anal sex reported, etc. |
| Latency to secondary | At least five weeks between ghosted lesion end and any secondary symptom onset | Gap less than 35 days |
| Natural order | Ghosted lesion precedes secondary symptoms and treatment date | Lesion onset on or after secondary onset or treatment |

Each criterion returns `pass`, `fail`, `warn` (missing data prevents checking),
or `n/a` (criterion not applicable for this case). A scenario passes if no
criterion is a hard fail — warnings are acceptable and flag data gaps for
the worker to review.

**Step 6 — Verdict.**

| Source passes | Spread passes | Conclusion |
|---|---|---|
| Yes | No | P2 is the source — P1 acquired infection from P2 |
| No | Yes | P1 is the source — P2 acquired infection from P1 |
| Yes | Yes | Ambiguous — both directions fit; manual review required |
| No | No | Unrelated infections — no supported transmission link |

**Step 7 — Save and iterate.** The worker confirms which ghosted lesion(s) to
save. Saved lesions are stored in the `ghostings` table and appear in the
network graph and timeline. Importantly, a saved ghosted primary chancre can
be used as P1's starting symptom in a future analysis — allowing the engine
to progressively build out a transmission chain across a full cluster.

### Interview periods

How far back to elicit partners depends on the OP's presenting symptoms:

- **Primary syphilis:** start `125 days` before chancre onset
  (max incubation 90 days + max primary 35 days)
- **Secondary syphilis:** start `237 days` before secondary symptom onset
  (90 + 35 + 70 + 42 days)

---

## Roadmap — v2 full-stack migration

This is the Streamlit v1. The planned v2 migration:

- **Backend:** FastAPI + SQLAlchemy (same models, new REST API layer)
- **Database:** PostgreSQL via Supabase
- **Frontend:** React + Tailwind CSS
- **Auth:** Supabase Auth with role-based access (case worker vs supervisor)
- **Analytics:** NetworkX cluster analysis, Plotly epidemiological dashboards
- **VCA plot:** Port the interactive Plotly timeline from `vca_app_v5` — labs,
  symptoms, exposure windows, and inoculation points on a shared date axis
- **Export:** ReportLab / WeasyPrint PDF case summaries with ghosting narrative
- **Deployment:** Docker + GitHub Actions CI/CD to Render or Railway

The `app/utils/clinical.py` ghosting engine is written as pure Python with
no Streamlit dependencies — it drops directly into a FastAPI backend without
modification.

---

## Contributing

```bash
git checkout -b feat/your-feature-name
make test
git push origin feat/your-feature-name
```

All pull requests run the CI pipeline (lint + tests) before merge.

---

## License

MIT