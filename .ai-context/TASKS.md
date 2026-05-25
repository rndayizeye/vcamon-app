# VCA Monitor — Active Tasks
_Current sprint. Move items to PROGRESS.md when done._

---

## Sprint: Network Analysis & Terminology Alignment

### Priority 1: Network Analysis

### Priority 2: Terminology Alignment

- [x] **Terminology Alignment (Task #1):** Iteratively renamed remaining "draft" variables and columns across the project to match `GLOSSARY.md`.
    - Identified all instances of "draft" terms (e.g. sex_types, symptom.location, etc).
    - Refactored code to use aligned terminology (e.g. exposure_modalities, symptom.anatomical_site, etc).

---

## Long-Term Backlog (V2 Migration - now underway)

### Phase 1: Backend Foundation (FastAPI, SQLAlchemy, PostgreSQL)

- [x] **FastAPI Project Setup:**
    - FastAPI app scaffold is live in `fastapi_app/`.
    - Existing shared SQLAlchemy models are wired into FastAPI via shared `Base.metadata`.
    - FastAPI DB config now accepts SQLite locally and PostgreSQL URLs for the Supabase target.
- [x] **API Layer Development:**
    - [x] Initial REST slice implemented for health, cases, and partners.
    - [x] Labs and symptoms endpoints implemented with case-level and partner-level CRUD routes.
    - [x] Timeline and relationship/report endpoints implemented.
    - [x] Migrate remaining `app/db/queries.py` functions into FastAPI endpoints.
    - [x] Expose MAP workflows.
    - [x] Expose network-analysis workflows.
    - [x] Ensure `app/utils/clinical.py` is directly callable from dedicated ghosting endpoints.
- [x] **Authentication & Authorization:**
    - [x] Implemented initial Supabase-backed auth scaffolding for FastAPI.
    - [x] Added basic authorization middleware for API endpoints.
- [x] **Database Migrations (Alembic):**
    - [x] Alembic config and shared metadata wiring added under `fastapi_app/migrations/`.
    - [x] Generate the first real revision and remove `create_all()` bootstrap from FastAPI startup.
    - [x] Wire `alembic upgrade head` into local/dev/deploy bootstrap flows (`docker/entrypoint.sh` + `make run-api`).
- [ ] **Testing:**
    - [x] Initial API endpoint tests added in `tests/test_fastapi_cases.py`.
    - [x] Expanded API coverage to labs, symptoms, timeline, and relationship/report endpoints.
    - [x] Adapted `test_db.py` with `LabResultEntry`, `SymptomEntry`, and `TimelineEvent` CRUD tests.
    - [x] Expanded API coverage to MAP endpoints.
    - [x] Expanded API coverage to ghosting and analytics endpoints.

### Phase 2: Frontend Foundation (React, Tailwind CSS)

- [x] **React Project Setup:**
    - [x] Initialize a new React project (Vite-based frontend scaffold now lives in `frontend/`).
    - [x] Integrate Tailwind CSS.
- [x] **Core UI Components:**
    - [x] Develop basic layout and authenticated app shell.
    - [x] Build partner/relationship forms on top of the new case + symptom scaffolding.
    - [x] Create reusable case and symptom form components.
- [x] **API Integration:**
    - [x] Develop a service layer in React to interact with the FastAPI backend.
    - [x] Add React integration for OP↔partner relationship/exposure endpoints.

### Phase 3: Feature Parity & Enhancements

- [ ] **Rebuild Key Pages:**
    - [x] Implement the React Dashboard (replacing `01_dashboard.py`).
    - [x] Implement React Ghosting Analysis page (replacing `07_ghosting_analysis.py`) — `features/ghosting/GhostingPage.tsx`.
    - [x] Implement React VCA Timeline Chart (replacing `08_vca_chart.py`) — `features/ghosting/VcaChartPage.tsx`, pure SVG.
    - [ ] Rebuild `02_op_form.py` and `03_partner_form.py` as dedicated React pages (case/partner create+edit forms exist but are not feature-parity with full Streamlit forms).
    - [x] Implement a React case create/edit form with normalized symptom row editing.
    - [x] Implement the React partner/relationship workflow, including pair-specific exposure dates on the OP↔partner relationship record.
    - [x] Fix `CaseForm.tsx` — added missing imports (`LabResultsEditor`, `REASON_FOR_EXAM_OPTIONS`, `TREATMENT_OPTIONS`), extended `CaseFormValues` with `reason_for_exam`, `treatment`, `nontrepLabs`, `trepLabs` fields, fixed `toFormValues` 4-arg signature, added `normalizeLabDrafts` helper.
    - [x] Fix `LabResultsEditor.tsx` — corrected import path (`../../labs/constants`), added `keyName:"formId"` to both `useFieldArray` calls so DB ids survive reset/re-render.
    - [x] Fix `CaseCreatePage.tsx` — added `syncCaseLabs` call and lab cache invalidation on case create.
    - [ ] Implement robust custom forms in React (addressing `data_editor` issues).
- [ ] **Derived Field Updates:**
    - [x] Symptom timing provenance is now derived consistently in backend + React case form.
    - [ ] Add frontend relationship/exposure derivations and summaries once the partner relationship editor exists.
- [ ] **Role-Based Access Control:**
    - [x] Added an initial supervisor vs. case worker/operator policy scaffold in FastAPI.
    - [ ] Fully implement the final supervisor vs. case worker role separation.
- [ ] **Additional Features:**
    - Implement PDF export of case summaries.
    - Migrate remaining Streamlit pages (02, 03 form parity; 05 network graph; 06 timeline; 09 quick ghost).
