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

## Long-Term Backlog (V2 Migration - Contingent on current sprint)

### Phase 1: Backend Foundation (FastAPI, SQLAlchemy, PostgreSQL)

- [ ] **FastAPI Project Setup:**
    - Initialize a new FastAPI project.
    - Integrate existing SQLAlchemy models (`app/db/models.py`).
    - Configure database connection for PostgreSQL (Supabase target).
- [ ] **API Layer Development:**
    - Migrate functions from `app/db/queries.py` into FastAPI endpoints for all CRUD operations.
    - Ensure `app/utils/clinical.py` is directly usable by FastAPI.
- [ ] **Authentication & Authorization:**
    - Implement initial user authentication with Supabase Auth.
    - Set up basic authorization middleware for API endpoints.
- [ ] **Database Migrations (Alembic):**
    - Integrate Alembic for managing database schema changes.
- [ ] **Testing:**
    - Establish API endpoint tests.
    - Adapt/reuse `test_db.py` tests, adding `LabResultEntry` and `SymptomEntry` CRUD tests.

### Phase 2: Frontend Foundation (React, Tailwind CSS)

- [ ] **React Project Setup:**
    - Initialize a new React project (e.g., Vite).
    - Integrate Tailwind CSS.
- [ ] **Core UI Components:**
    - Develop basic layout, navigation, and login/signup flow (Supabase Auth).
    - Create generic reusable table/form components.
- [ ] **API Integration:**
    - Develop a service layer in React to interact with the FastAPI backend.

### Phase 3: Feature Parity & Enhancements

- [ ] **Rebuild Key Pages:**
    - Prioritize rebuilding `01_dashboard.py`, `02_op_form.py`, `03_partner_form.py`, and `08_vca_chart.py` using new APIs.
    - Implement robust custom forms in React (addressing `data_editor` issues).
- [ ] **Derived Field Updates:**
    - Ensure auto-derived fields update in real-time on the frontend or upon data changes.
- [ ] **Role-Based Access Control:**
    - Fully implement supervisor vs. case worker role separation.
- [ ] **Additional Features:**
    - Implement PDF export of case summaries.
    - Migrate other Streamlit pages.
