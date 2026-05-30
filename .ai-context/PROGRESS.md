# VCA Monitor — Progress Log
_Update this at the end of every session. Keep it short — every model reads it._
_Last updated: 2026-05-30 (session H)_

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

## Completed in this session (2026-05-30 session H)

- [x] **RBAC end-to-end test suite** (`tests/test_rbac.py` — commit `bc9c570`)
  - 26 new tests covering all 11 supervisor-only delete endpoints across every domain:
    cases, partners, MAP clear (case + partner), labs, symptoms, timeline events,
    ghostings, arrow links, relationships, relationship reports.
  - Permission-flag assertions for `case_worker`, `supervisor`, and bare `authenticated`
    JWT role; unauthenticated → 401 verified.
  - Fixed `test_fastapi_cases.py`: added `AUTH_ENABLED=false` at module level so the
    real `.env` (which has `AUTH_ENABLED=true`) no longer breaks 20 non-RBAC tests.
  - Fixed CORS preflight test to use an allowed origin (`localhost:5173`).
  - **141/141 tests pass.**

- [x] **PDF / Print export for VCA Chart** (commits `2d7e92c` — no new dependencies)
  - "Print / Export PDF" button added to the VCA Timeline page header. Clicking calls
    `window.print()`, which triggers the browser's native Save as PDF dialog.
  - Print-only case summary `<dl>` in the header (patient name, LOT/diagnosis, treatment
    date, partner count) — invisible on screen, rendered at the top of every printed page.
  - `@media print` CSS: hides sidebar, topbar, layer-toggle panel, legend, and data-gaps
    notice; collapses `app-body` to single column; sets landscape `@page` with 1.5 cm margins.
  - `.no-print` / `.print-only` utility classes added to `index.css`.
  - `vca-chart-panel` class on the chart container strips the negative-margin screen bleed
    for print so the SVG fills the page cleanly.
  - TypeScript compiles clean; verified live in headless Chromium (Playwright).

---

## Completed in this session (2026-05-25 session C)

- [x] **Analytics page UX** — All four analytics components (`AnalyticsSummaryCards`, `CentralityTable`,
  `ClusterPanel`, `CaseAnalyticsPage` node table) updated to use layman's terms with technical terms
  in parentheses. Each metric has a plain-language description. Centrality table has a collapsible
  "How are these calculated?" definitions panel.

- [x] **VCA chart: all symptoms + 12-month window** — `VcaChartPage` rebuilt to plot every classified
  symptom per person (not just the last one). `buildSymptomBars()` reads the `classification` field
  from `SymptomEntry` directly. Primary chancre symptoms render in red, secondary rash/lesions in
  purple. Each symptom gets its own onset marker (▲), duration bar, and inoculation diamonds (◆).
  Chart enforces a 12-month minimum window centered on the data midpoint.

- [x] **Ghosting analysis clarity** — Both `GhostingPage` and `QuickGhostPage` updated:
  - Hypothesis text panel per scenario tab (plain-language "what this tests" statement with names)
  - Inoculation date sub-row under exposure criterion: shows avg inoculation date and whether it
    falls within the ghosted lesion window
  - Latency shown across all 3 ranges (Optimistic/min, Expected/avg, Conservative/max);
    all other criteria show expected range only
  - `VerdictContext` component: per-criterion plain-language failure explanations below verdict badge
  - `QuickGhostPage` symptom editor overlap fixed: grid → flex-wrap layout

- [x] **Body parts / sex type fix** — `QuickGhostPage` was using old `LX`-vocabulary strings sent
  inside `exposure_modalities`. Fixed to use `penis/vagina/anus/mouth` vocabulary matching
  `RelationshipEditor`, sent as `op_body_parts`/`partner_body_parts` top-level API fields
  (what `_sex_type_compatible()` in the clinical engine actually reads). `GhostingAnalysisRequest`
  type updated with both fields.

- [x] **Partner create → edit redirect** — `PartnerCreatePage` now navigates to
  `/cases/${caseId}/partners/${id}/edit` after creating, so the `RelationshipEditor`
  (exposure dates + body parts grid) is immediately visible instead of going to the list.

- **TypeScript compiles clean throughout.**

---

## Completed in this session (2026-05-25 session B)

- [x] **`exposure_modalities` → `op_body_parts` / `partner_body_parts` refactor** (commit `5c57b3f`)
  - `CasePartnerRelationship` column renamed; body parts now tracked per person as canonical values
    (`"penis"`, `"vagina"`, `"anus"`, `"mouth"`) stored as JSON string.
  - `clinical.py`: `Exposure` dataclass drops `exposure_modalities`; body parts passed as
    `case1_body_parts` into `evaluate_criteria` and `run_ghosting_analysis`.
    `_exposure_modality_compatible` → `_sex_type_compatible` with cleaner site-to-part matching.
  - `ghosting.py` router: non-reactive treponemal guard added before case-partner analysis;
    reads new columns from saved relationship record.
  - `schemas/relationships.py`: `CasePartnerRelationship*` schemas expose `list[str]` with
    field validator for JSON→list coercion. `RelationshipReport` keeps its own `exposure_modalities`.
  - `queries.py`: `create/update_case_partner_relationship` use new params; `_serialize_body_parts`
    converts list → JSON for SQLite storage.
  - Alembic migration `ec2923821476` applied — DB at head.
  - React `RelationshipEditor`: textarea replaced with `BodyPartsGrid` checkbox table
    (4 body-part rows × OP/Partner columns). `partners/types.ts` updated.
  - `PartnerForm`: `historical_primary_chancre` manual select removed; now derived via
    `deriveHistoricalPrimary()` from symptom rows.
  - v1 Streamlit pages 03, 07, 08, 09 adapted — modality strings mapped to canonical body-part
    values before save; `Exposure()` constructor calls fixed.
  - **115 tests pass; TypeScript compiles clean.**

## Completed in last session (2026-05-25 session 2)

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

- [ ] **Supabase auth activation** — the true next step.
  Add `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` to `frontend/.env.local` and
  `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `AUTH_ENABLED=true` to `.env`. Then verify
  magic-link → bearer token → `/api/auth/me` returns real user + role.

- [ ] **`CaseCreatePage` / `CaseEditPage` — OP form parity still incomplete**
  `CaseWriteFields` in `cases/types.ts` still has legacy `lab_1`, `lab_2`, `lab_3` fields
  that the form no longer writes — clean up once FastAPI schema confirms they're unused.

- [ ] **`st.data_editor` inside `st.form()` — pages 02 and 03**
  Known Streamlit limitation; data editors may not return edited rows reliably on submit.
  Tracked in ADR-008. Low priority — pages 02/03 are being replaced by React.

- [ ] **Supervisor vs. case worker RBAC** — scaffold in place; final policy rules not yet
  enforced beyond the current delete/MAP-clear gates.

- [ ] **PDF export** — not started.

- [ ] **Deploy wiring** — Supabase PostgreSQL target, Docker entrypoint, CI deploy step.

- [ ] **`app/components/dropdowns.py`** — imports unused legacy enums. Low priority cleanup.
