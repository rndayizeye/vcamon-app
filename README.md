# vcamon-app

Contact tracing and case management tool for syphilis disease intervention work.
Rebuilt from a legacy Excel workbook (`vcamon-launch-v1.xlsm`) and a Dash prototype
(`vca_app_v5`) as a structured, tested, containerized web application using Streamlit,
SQLAlchemy, and SQLite — designed for a planned full-stack migration to FastAPI + React.

---

## 🔗 Live app

**Beta:** [https://visualcaseanalysis.streamlit.app](https://visualcaseanalysis.streamlit.app)

> Beta access is password-protected. Contact the project maintainer for credentials.
> Data entered during the beta is synthetic and resets on redeploy.

Quick ghosting analysis (no login required to preview):
[https://visualcaseanalysis.streamlit.app/quick_ghost](https://visualcaseanalysis.streamlit.app/quick_ghost)

---

## What it does

Case workers use this app to manage syphilis contact tracing cases end-to-end:

- Record original patient (OP) demographics, exam reason, lab results, and treatment
- Add and track contact partners with the same clinical data
- Complete the 46-item Major Analytical Points (MAP) assessment checklist per interview
- Optionally capture clinical details (symptom onset, exposure windows, lab dates) to streamline VCA analysis
- Run automated ghosting analysis with period intersection logic to determine source/spread relationships
- Leverage previous negative lab results to intelligently constrain interview periods
- Track case activity on a date timeline with auto-seeded treatment events
- Run quick ghosting calculations without opening a case

---

## Project structure

```
vcamon-app/
├── app/
│   ├── main.py                    # Streamlit entry point + password gate
│   ├── pages/
│   │   ├── 01_dashboard.py        # Case list, search, navigation
│   │   ├── 02_op_form.py          # Original patient form
│   │   ├── 03_partner_form.py     # Contact partner form
│   │   ├── 04_map_sheet.py        # 46-item MAP assessment
│   │   ├── 05_network_graph.py    # Transmission network + ghosting records
│   │   ├── 06_timeline.py         # Activity timeline and calendar
│   │   ├── 07_ghosting_analysis.py # VCA ghosting engine UI (full workflow)
│   │   ├── 08_vca_chart.py        # VCA timeline chart
│   │   └── 09_quick_ghost.py      # Quick ghosting — no case required
│   ├── db/
│   │   ├── database.py            # SQLAlchemy engine and session
│   │   ├── models.py              # ORM models + MAP_ITEMS reference data
│   │   └── queries.py             # All database access functions
│   ├── components/
│   │   ├── dropdowns.py           # Shared enum selectboxes
│   │   └── sidebar_case_selector.py
│   └── utils/
│       ├── session_state.py       # Centralized st.session_state helpers + auth
│       ├── validators.py          # Form validation — pure Python, no Streamlit
│       ├── clinical.py            # VCA ghosting analysis engine — pure Python
│       └── ghosting_plot.py       # Plotly scenario diagram builder
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

### Local secrets (password gate)

Create `.streamlit/secrets.toml` at the project root (already git-ignored):

```toml
BETA_PASSWORD = "yourpassword"
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

> **Streamlit Cloud note:** SQLite is stored in `/tmp` on Streamlit Cloud and
> resets on container restart. A demo case is auto-seeded on each cold start.
> Production deployment should use PostgreSQL via the `DATABASE_URL` env var.

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
Creates or edits the original patient record. Fields: patient name, diagnosis / syphilis stage,
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

### 08 VCA chart
Full Plotly timeline showing exposure windows, symptom onset markers, duration
bars, lab results, treatment events, critical period, inoculation points
(min/avg/max), and ghosted lesion windows — all on a shared date axis.
Sidebar toggles control which layers are shown.

### 09 Quick ghosting
Run the VCA ghosting engine without opening a case. Enter two people's symptom
and exposure data directly and get an immediate verdict, scenario diagrams, and
criteria evaluation. Optionally save results to an active case. Useful during
interviews or for verifying scenarios before committing them to a record.

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

**Step 1 — Select Case1.** The person with the highest-ranking symptom in the
hierarchy becomes Case1. Their symptom timeline anchors all subsequent date
calculations. The other person becomes Case2. If both have symptoms of equal
rank, the person with the earlier onset date becomes Case1.

**Step 2 — Calculate Date1.** Working backwards from Case1's symptom onset using
average durations, Date1 is the estimated date Case1 was exposed to infectious
syphilis.

- Primary chancre: `Date1 = onset − 21 days`
- Secondary symptoms: `Date1 = onset − 21 days incubation − 21 days primary − 28 days latency`

**Step 3 — Ghosted source lesion for Case2.** If Case2 was the source of Case1's
infection, Case2 must have had an active chancre when Case1 was exposed. Date1 is
placed at the midpoint of that ghosted window:

ghosted source onset = Date1 − 10 days ghosted source end = Date1 + 10 days
**Step 4 — Date2 and ghosted spread lesion for Case2.** Date2 is the midpoint of Case1's
own primary chancre — the point at which Case1 was most infectious. If Case1
infected Case2, Case2 would have developed a chancre starting one average
incubation duration after that midpoint:

- Primary or historical chancre: `Date2 = chancre onset + (duration ÷ 2)`
- Secondary only: `Date2 = secondary onset − 28 days latency − 10.5 days`

ghosted spread onset = Date2 + 21 days ghosted spread end = Date2 + 42 days
**Step 5 — Evaluate four criteria for each scenario.**

| Criterion | What is checked | Pass condition |
|---|---|---|
| **Exposure overlap** | Infectious period must overlap with exposure window | Any intersection between Case2's infectious period and Case1's exposure window (SOURCE scenario), or Case1's infectious period and Case2's exposure window (SPREAD scenario) |
| **Anatomical compatibility** | Symptom location is consistent with the type of sex reported | Rectal/anal chancre matches anal sex reported, etc. |
| **Latency to secondary** | At least five weeks between ghosted lesion end and any secondary symptom onset | Gap ≥ 35 days |
| **Natural order** | Ghosted lesion precedes secondary symptoms and treatment date | Lesion onset before secondary onset and treatment |

**Exposure criterion (critical period intersection):**

The exposure check verifies that transmission was *possible* by checking if the
source's infectious period overlapped with the exposed person's contact window:

- **SOURCE scenario:** Case2's infectious period (ghosted source lesion dates) must
  intersect with Case1's exposure window. Any overlap = transmission possible.
  
- **SPREAD scenario:** Case1's infectious period (symptom onset + duration) must
  intersect with Case2's exposure window.

**Pass:** Periods overlap (any number of days)  
**Warn:** Periods miss by ≤10 days (warn margin)  
**Fail:** Periods miss by >10 days  
**N/A:** Exposure dates not recorded

Each criterion returns `pass`, `fail`, `warn` (missing data prevents checking),
or `n/a` (criterion not applicable for this case). A scenario passes if no
criterion is a hard fail — warnings are acceptable and flag data gaps for
the worker to review.

**Step 6 — Verdict.**

| Source passes | Spread passes | Conclusion |
|---|---|---|
| Yes | No | Case2 is the source — Case1 acquired infection from Case2 |
| No | Yes | Case1 is the source — Case2 acquired infection from Case1 |
| Yes | Yes | Ambiguous — both directions fit; manual review required |
| No | No | Unrelated infections — no supported transmission link |

**Step 7 — Save and iterate.** The worker confirms which ghosted lesion(s) to
save. Saved lesions are stored in the `ghostings` table and appear in the
network graph and timeline. Importantly, a saved ghosted primary chancre can
be used as Case1's starting symptom in a future analysis — allowing the engine
to progressively build out a transmission chain across a full cluster.

### Interview periods

How far back to elicit partners depends on the OP's presenting symptoms:

**Standard interview periods:**
- **Primary syphilis:** start `125 days` before chancre onset
  (max incubation 90 days + max primary 35 days)
- **Secondary syphilis:** start `237 days` before secondary symptom onset
  (90 + 35 + 70 + 42 days)

**Shortened by previous negative labs:**

If a previous negative RPR or treponemal test exists, the interview period is
constrained because the person could not have been infected before that test
(accounting for max incubation):

```python
standard_start = symptom_onset - (125 or 237 days)
floor = last_negative_date - 90 days  # Max incubation before negative test

interview_start = max(standard_start, floor)
# Cannot investigate before the floor, even if standard says to
Example:
* Primary chancre onset: May 1, 2025
* Previous negative RPR: April 1, 2025
* Standard: May 1 - 125 = Dec 27, 2024
* Floor: April 1 - 90 = Jan 1, 2025
* Interview period: Jan 1 → May 1 (120 days, shortened from 125)
The floor ensures you don't investigate before the person could have been infected, while the 90-day buffer accounts for the maximum incubation period before the negative test.

### Critical period and exposure intersection

The **critical period** represents the window during which a person was potentially
infectious — from earliest possible inoculation to treatment date. This period is
calculated for both Case1 and Case2 and used to verify transmission possibility.

**Exposure intersection logic:**

A partner qualifies for transmission analysis if their exposure period intersects
with the OP's critical period — meaning they had contact during a time when the OP
was infectious. Even a single day of overlap indicates possible transmission.

**Example:**
- OP critical period: Jan 1 → Feb 15 (infectious window)
- Partner exposure: Jan 20 → Jan 25 (contact dates)
- **Overlap: Jan 20-25 (5 days) ✓** Transmission possible

The entire critical period does not need to be contained within the exposure window —
any intersection qualifies. This ensures the ghosting analysis only evaluates
scenarios where transmission was physically possible based on timing.


---

## Roadmap — v2 full-stack migration

This is the Streamlit v1. The planned v2 migration:

- **Backend:** FastAPI + SQLAlchemy (same models, new REST API layer)
- **Database:** PostgreSQL via Supabase
- **Frontend:** React + Tailwind CSS
- **Auth:** Supabase Auth with role-based access (case worker vs supervisor)
- **Analytics:** NetworkX cluster analysis, Plotly epidemiological dashboards
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

## Acknowledgements

This project was developed with assistance from Claude (Anthropic)
for code scaffolding, architecture guidance, and documentation.

Clinical methodology is based on:

> Fussell, E. (2022). *Visual Case Analysis.*
> NCSDDC / Marion County Public Health Department.
> https://www.ncsddc.org/wp-content/uploads/2022/07/VCA-Training-7.2022.pdf

---

## License

MIT
