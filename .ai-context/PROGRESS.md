# VCA Monitor — Progress Log
_Update this at the end of every session. Keep it short — every model reads it._
_Last updated: 2026-05-25 (session 2)_

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

## Completed in this session (2026-05-25 session 2)

- [x] **Fix `CaseForm.tsx`** — was broken/incomplete: added missing imports (`LabResultsEditor`, `REASON_FOR_EXAM_OPTIONS`, `TREATMENT_OPTIONS` from `../../labs/constants`); extended `CaseFormValues` with `reason_for_exam`, `treatment`, `nontrepLabs: LabDraft[]`, `trepLabs: LabDraft[]`; fixed `toFormValues` to accept 4 args and map existing lab records via `toLabDraft`; added `normalizeLabDrafts` helper (filters empty rows, injects `test_category`); fixed `handleFormSubmit` to submit normalized labs.
- [x] **Fix `LabResultsEditor.tsx`** — wrong import path (`../labs/constants` → `../../labs/constants`); added `keyName: "formId"` to both `useFieldArray` calls so DB `id` values survive `reset()`; changed React keys from `field.id` to `field.formId`.
- [x] **Fix `CaseCreatePage.tsx`** — was skipping lab sync on case create; added `syncCaseLabs(createdCase.id, [], [...nontrepLabs, ...trepLabs])` and corresponding cache invalidation.
- [x] **Fix `SymptomEntriesEditor.tsx`** — widened `register` prop type to `UseFormRegister<any>` to resolve TS mismatch with parent `CaseFormValues`.
- [x] **TypeScript build** — `npx tsc --noEmit` passes clean (0 errors).

## Completed in last session (2026-05-25)

- [x] **React Ghosting Analysis page** (`features/ghosting/GhostingPage.tsx`): Full VCA methodology workflow — partner selection, DB-driven analysis via `POST /cases/{id}/partners/{pid}/ghosting-analysis`, verdict banner, 4 ghosted lesion metric cards, source/spread scenario tabs with expected-range criteria table (pass/fail/warn/na), confidence level, step-by-step log (collapsible), save/delete ghosting records, existing records table.
- [x] **React VCA Timeline Chart** (`features/ghosting/VcaChartPage.tsx`): Pure SVG chart (no new dependencies) implementing all 10 visual layers from the Streamlit original — symptom duration bars, onset markers (▲), inoculation point diamonds (◆) with ported clinical constants from `clinical.py`, treatment stars (★), OP/partner exposure windows, critical period, interview period, ghosted source/spread lesions (parsed from notes). Toggle controls per layer, responsive width via ResizeObserver, legend grid, data completeness notice.
- [x] **`features/ghosting/{types,api,hooks}.ts`**: TypeScript types mirroring FastAPI ghosting schemas, `apiFetch` wrappers for all ghosting endpoints, React Query hooks for analysis, CRUD, and per-case ghosting list.
- [x] **Router + CaseLayout**: Added `/ghosting` and `/vca-chart` routes under `cases/:caseId`; added "Ghosting" and "VCA Chart" tabs to the case nav bar.
- [x] Committed as `e2004eb` — 7 files, 1811 insertions.

## Completed in session (2026-05-24)

- [x] **Implemented React Dashboard**: Created `DashboardPage` replacing `01_dashboard.py` as the primary entry point for case management.
- [x] **Dashboard Metrics**: Added global summary cards for total cases, total partners, treated, and pending treatment.
- [x] **Case Dashboard Table**: Implemented a searchable table with partner counts and conditional highlighting for untreated cases.
- [x] **Case Quick-View**: Added a detail panel with the latest lab result, medical info, and quick navigation to edit/partner views.
- [x] **Backend API Enhancements**: 
    - New `GET /cases/summary` for aggregate dashboard metrics.
    - New `GET /cases/{id}/latest-lab` for case-specific latest result.
    - Updated `GET /cases/` to return `partner_count` and treatment status in `CaseSummary`.
- [x] **Frontend Integration**: Wired the dashboard into the main router and integrated Tailwind CSS for a professional layout.

---

## Completed (stable)

---

## In progress / remaining tech debt

- [ ] **`CaseCreatePage` / `CaseEditPage` — OP form parity still incomplete**
  The React case form now has: `patient_name`, `diagnosis_code`, `case_manager`, `treatment_date`, `reason_for_exam`, `treatment`, `medical_info`, symptoms editor, split lab editor (non-trep / trep). The `CaseWriteFields` type in `cases/types.ts` still has some legacy fields (`lab_1`, `lab_2`, `lab_3`, etc.) that are no longer written by the form — clean up if the FastAPI schema no longer needs them. Partner form parity (03) is separate work.

- [ ] **`st.data_editor` inside `st.form()` — still present on pages 02 and 03**
  All three editors (symptom, non-treponemal labs, treponemal labs) are still
  inside `st.form()`. This is a known Streamlit limitation; data editors may not
  return edited rows reliably on form submit. Needs refactor to plain `st.button()` +
  session_state pattern. Trackd in ADR-008.

- [x] **Page 08 VCA chart legacy field issue** — superseded. The React `VcaChartPage` reads directly from `SymptomEntry` via the FastAPI symptoms endpoints. The Streamlit `08_vca_chart.py` remains broken for new records but is no longer the primary path.

- [ ] **`app/components/dropdowns.py` imports legacy enums**
  Still imports `LabResult`, `TreponemalResult`, `Symptom`, `LesionType` for
  the old selectbox helpers (`lab_1_select`, `lab_2_select`, etc.). These helpers
  are no longer called anywhere. File can be cleaned up or left as legacy.

- [ ] **Backend platform work remains**
  FastAPI now exposes health, cases, partners, labs, symptoms, timeline,
  relationship/report workflows, ghosting analysis/CRUD, analytics/link
  endpoints, MAP workflows, Supabase-backed auth scaffolding, and an initial
  role policy/permissions contract for the frontend. Remaining backend work is
  now mostly full client login integration, deploy wiring, and finer-grained RBAC.
