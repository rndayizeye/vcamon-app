# VCA Monitor — Active Tasks
_Current sprint. Move items to PROGRESS.md when done._

---

## Sprint: Wire SymptomEntry to VCA chart + clean up legacy

### Priority 1 — Chart broken for symptom data

- [ ] **Fix `08_vca_chart.py` — populate `primary_sym` from `SymptomEntry`**
  Problem: `people` list has no `primary_sym` key; `_sym_type()` and `_sym_onset()`
  return `None` for every person. Symptom bars, onset markers, and inoculation
  points are never drawn.

  Fix approach:
  1. After building each entry in the `people` list, query `get_symptoms_for_case()`
     or `get_symptoms_for_partner()` to get `SymptomEntry` objects.
  2. Pick the highest-ranking symptom (use `symptom_rank()` from `clinical.py`
     mapping `classification == "Primary"` → rank 1, `"Secondary"` → rank 4).
  3. Store it as `person["primary_sym"] = best_symptom_entry` so the existing
     `_sym_type()` / `_sym_onset()` helpers can read it.

  Files: `app/pages/08_vca_chart.py`, `app/db/queries.py` (add batch query helper)
  Also wire `latest_lab` from `LabResultEntry` (same issue — currently `None`).

### Priority 2 — data_editor outside st.form() on pages 02 and 03

- [ ] **Refactor pages 02 and 03 to move data editors outside `st.form()`**
  Problem: Streamlit does not reliably surface `data_editor` edits when the
  form is submitted. Users may lose lab and symptom entries silently.

  Fix approach (same pattern for both pages):
  1. Remove the outer `st.form()` wrapper.
  2. Render all fields as plain widgets; track "save clicked" with
     `st.button()` + a `st.session_state` flag.
  3. On save, read data_editor state from `st.session_state[key]` directly
     (Streamlit stores the editor state there automatically).
  4. Run validation and DB writes exactly as before.

  Reference: Streamlit docs — "Data editor outside a form"
  Files: `app/pages/02_op_form.py`, `app/pages/03_partner_form.py`

### Priority 3 — test coverage

- [ ] **Add `LabResultEntry` CRUD tests to `test_db.py`**
  Pattern: follow `TestRelationshipCRUD`. Cover create, get-for-case,
  get-for-partner, update, delete, cascade-on-case-delete.

- [ ] **Add `SymptomEntry` CRUD tests to `test_db.py`**
  Same pattern. Cover create, get-for-case, get-for-partner, update, delete.

### Priority 4 — legacy cleanup (low urgency)

- [ ] **Clean up `app/components/dropdowns.py`**
  The old selectbox helpers (`lab_1_select`, `lab_2_select`, `lesion_select`,
  `symptom_select`) are no longer called anywhere. Options:
  - Delete the unused functions, keep `enum_options()` and `val_or_none()` which
    are still widely imported.
  - Or keep as-is (no runtime cost).

- [ ] **`docker-compose.yml` DATABASE_URL env var**
  Still points to `sqlite:////project/data/vcamon.db` but `database.py` now
  defaults to `vcamon_v2.db`. Update the compose file to match, or the Docker
  volume will use the old path.
  File: `docker-compose.yml`
  Fix: `DATABASE_URL=sqlite:////project/data/vcamon_v2.db`

---

## Backlog (not this sprint)

- [ ] Wire `calc_interview_period_start()` to the ghosting UI — the function
  exists in `clinical.py` with `last_negative_date` support; just needs a display
  widget on page 07
- [ ] Alembic migration setup (required before real patient data)
- [ ] PDF export of case summary (roadmap item)
- [ ] Supervisor vs case worker role separation (v2 item)
