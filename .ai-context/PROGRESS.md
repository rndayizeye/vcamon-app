# VCA Monitor — Progress Log
_Update this at the end of every session. Keep it short — every model reads it._
_Last updated: 2026-05-19 (post-merge)_

---

## Completed (stable)

- [x] Core data model: `cases`, `partners`, `map_entries`, `arrow_links`, `ghostings`, `timeline_events`
- [x] New extended model: `lab_results`, `case_partner_relationships`, `relationship_reports`, `symptom_entries`
- [x] VCA ghosting engine (`clinical.py`) — pure Python, 7-step pipeline, period-intersection exposure check
- [x] All 9 Streamlit pages implemented (01_dashboard → 09_quick_ghost)
- [x] Test suite: `test_clinical.py`, `test_db.py`, `test_validators.py`
- [x] Docker + Docker Compose setup
- [x] GitHub Actions CI (lint + test on push)
- [x] Streamlit Cloud deployment (beta, password-protected)
- [x] Plotly VCA timeline chart (08_vca_chart.py)
- [x] Quick ghosting with no case required (09_quick_ghost.py)
- [x] `CasePartnerRelationship` association table with `RelationshipReport` evidence layer

---

## Completed in last session (2026-05-21)

- [x] **Range-Based Ghosting Engine**: Refactored `clinical.py` to execute analysis across three ranges (Aggressive, Expected, Conservative) with corresponding confidence levels (Robust, Likely, Possible, Unrelated).
- [x] **Guardrail System**: Established `PRINCIPLES.md` and `GLOSSARY.md` to enforce architectural purity and public health naming standards.
- [x] **Slack Integration**: Implemented `app/utils/notifications.py` and environment-based webhooks for task/audit alerts.
- [x] **Terminology Alignment (Full)**: Completed full sweep to rename `sex_types` to `exposure_modalities`, and `symptom.location` to `symptom.anatomical_site` across UI pages, DB queries, and unit tests to adhere strictly to `GLOSSARY.md`.
- [x] **Symmetry Verification**: Confirmed all 37 clinical unit tests pass with the new range-based logic and legacy aliases.
- [x] **Network Analysis**: Moved the network graph from a simple visualizer to an analysis tool using NetworkX. Implemented Centrality calculations, Cluster Detection, and a temporal animation slider for the network graph.

---

## Completed (stable)

---

## In progress / remaining tech debt

- [ ] **`st.data_editor` inside `st.form()` — still present on pages 02 and 03**
  All three editors (symptom, non-treponemal labs, treponemal labs) are still
  inside `st.form()`. This is a known Streamlit limitation; data editors may not
  return edited rows reliably on form submit. Needs refactor to plain `st.button()` +
  session_state pattern. Tracked in ADR-008.

- [ ] **Page 08 VCA chart reads legacy fields for symptom data**
  `08_vca_chart.py` uses `person.get("primary_sym")` and reads from
  `case.lesion_type` / `case.symptom` (legacy). The `people` list does not
  populate `primary_sym` from `SymptomEntry`. Symptom bars and inoculation points
  on the chart will be empty for all cases going forward. Needs wiring to
  `get_symptoms_for_case()` / `get_symptoms_for_partner()`.

- [ ] **`app/components/dropdowns.py` imports legacy enums**
  Still imports `LabResult`, `TreponemalResult`, `Symptom`, `LesionType` for
  the old selectbox helpers (`lab_1_select`, `lab_2_select`, etc.). These helpers
  are no longer called anywhere. File can be cleaned up or left as legacy.

- [ ] **Alembic not set up** — schema migration is handled by drop-and-recreate
  in `init_db()`. Acceptable while data is synthetic, but must be addressed
  before real patient data is stored.

- [ ] **`test_db.py` missing `LabResultEntry` and `SymptomEntry` CRUD tests**
  Coverage added for `CasePartnerRelationship` and `RelationshipReport` but not yet
  for the two new lab/symptom tables.
