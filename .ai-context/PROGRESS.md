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

## Completed in last merge

- [x] **`Optional` import** added to `queries.py` — duplicate `return True` at end of file removed
- [x] **`LabResultEntry.__repr__`** stub completed
- [x] **`Case.symptoms` relationship** added to models.py — `get_symptoms_for_case()` now works
- [x] **`validate_op_form` signature** cleaned up — `lab_1`/`lab_2` args removed; `test_validators.py` updated
- [x] **Lab vocabulary enums** added to models.py: `NonTreponemalTestType`, `TreponemalTestType`, `NonTreponemalTiter`, `TreponemalTestResult` — used by split lab editor on pages 02 and 03
- [x] **Split lab editor** on pages 02 and 03 — non-treponemal (left) and treponemal (right) are now separate `st.data_editor` tables with typed selectbox columns
- [x] **`get_symptom_classification()`** helper added to `clinical.py` — auto-derives Primary/Secondary from symptom type string; called on every save so DB stays in sync without manual input
- [x] **`Symptom.location` field** added to the engine dataclass — anatomical site of a primary chancre; passed through from the symptom editor to the sex-type compatibility check
- [x] **`determine_verdict()` overlap annotation** — now accepts `source_criteria`/`spread_criteria` and appends a ⚠ warning when primary-secondary overlap is detected in either scenario
- [x] **`_natural_order()` improved** — now emits `warn` (not `fail`) for primary-secondary overlap (since latency min = 0 permits it) and hard `fail` for reversed timeline
- [x] **`_latency_to_secondary()` improved** — distinguishes true overlap (chancre active when secondary appeared) from reversed timeline (secondary before primary onset)
- [x] **`database.py` schema guard** — `init_db()` now inspects the schema and drops/recreates tables if required columns are missing (handles the old `vcamon.db` → `vcamon_v2.db` migration)
- [x] **`historical_primary_chancre` auto-derivation** — page 02 now derives this from symptom entries (lesion type + duration + treatment date) instead of a manual radio button
- [x] **Ghosting analysis pages (07, 09)** refactored — symptom input now uses multi-row `st.data_editor` with `Type`, `Onset Date`, `Duration`, `Location` columns; pre-fills from saved DB records; `_entries_to_rows()` and `_rows_to_symptoms()` helpers added

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
