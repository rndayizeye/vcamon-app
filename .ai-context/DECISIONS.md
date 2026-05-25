# VCA Monitor — Architecture Decision Records (ADRs)
_Why things are the way they are. Read before proposing refactors._

---

## ADR-001: clinical.py must stay framework-free

**Status:** Active
**Decision:** `app/utils/clinical.py` imports only Python stdlib (`datetime`, `dataclasses`).
No Streamlit, no SQLAlchemy, no third-party libraries.
**Reason:** The ghosting engine is the core intellectual asset. It must drop directly
into the planned FastAPI v2 backend without modification.
**Note:** `get_symptom_classification()` was added to `clinical.py` in the last merge.
This is acceptable — it is pure Python with no framework imports and is legitimately
part of the clinical vocabulary (Primary vs Secondary classification).

---

## ADR-002: SQLite for v1, PostgreSQL for v2

**Status:** Active
**Decision:** SQLite for local dev and Streamlit Cloud beta. PostgreSQL via Supabase for v2.
**Database filename:** `vcamon_v2.db` (changed from `vcamon.db` after the schema standardisation merge).
**Migration policy:** `init_db()` inspects the schema on startup and drops/recreates tables
if required columns are missing. Acceptable while all data is synthetic.
**Critical:** `docker-compose.yml` still references the old `vcamon.db` filename — must
be updated before the next Docker deploy.
**Implication:** Do not use SQLite-specific syntax. Keep queries PostgreSQL-compatible.

---

## ADR-003: All DB access through queries.py

**Status:** Active
**Decision:** No inline ORM queries in page files. All reads and writes go through
named functions in `app/db/queries.py`.
**Reason:** Pages are already complex. Query functions can be tested in isolation with
in-memory SQLite. The ghosting analysis pages (07, 09) import `get_symptoms_for_case`
and `get_symptoms_for_partner` from queries — this is the correct pattern.

---

## ADR-004: from_ref / to_ref use string refs, not foreign keys

**Status:** Active
**Decision:** `ArrowLink.from_ref` and `Ghosting.from_ref/to_ref` store `"OP"` or
a partner number string (`"1"`, `"2"`), not integer foreign keys.
**Reason:** The "OP" party is not a `Partner` row. String refs mirror the Excel convention
and avoid a polymorphic relationship.
**Implication:** Refs must be resolved to display labels at the page layer using
the `ref_to_label` dict pattern in `05_network_graph.py`.

---

## ADR-005: Exposure check uses period intersection, not point-in-time

**Status:** Active
**Decision:** The exposure criterion checks whether the infectious period _overlaps_
with the exposure window (any intersection), not whether a single date falls inside.
**Warn margin:** Periods that miss by ≤10 days → WARN not FAIL.
**Implementation:** `_check_exposure()` in `clinical.py`.

---

## ADR-006: Legacy fields kept, new tables added

**Status:** Active
**Decision:** `lab_1`, `lab_2`, `lab_3`, `lesion_type`, `symptom` on `cases` and
`partners` are kept but deprecated. All new writes go to `lab_results` and
`symptom_entries`. Legacy fields are set to `None` on new saves.
**Reason:** Avoiding a breaking migration on a live deployment.
**Current state:** Pages 02 and 03 fully write to the new tables. Page 08 (VCA chart)
still reads legacy fields for symptom data — this is known tech debt (see TASKS).

---

## ADR-007: GhostingResult uses case1/case2 naming, not p1/p2

**Status:** Active
**Decision:** `GhostingResult` fields are `case1_name`, `case2_name`, `case1_symptom`.
Legacy `p1_name`, `p2_name`, `p1_symptom` are property aliases that must be kept.
**Reason:** The VCA methodology uses "Case1/Case2" terminology. The old p1/p2 naming
was ambiguous ("P1" also means "Partner 1" in the app).

---

## ADR-008: Streamlit data_editor not used inside st.form()

**Status:** Pending (not yet fixed)
**Decision:** `st.data_editor(num_rows="dynamic")` must not be placed inside a
`st.form()` block — Streamlit does not reliably surface edits on submit.
**Current state:** Pages 02 and 03 still have all three editors inside `st.form()`.
This is a known bug. The fix (plain `st.button()` + session_state) is tracked in TASKS.

---

## ADR-009: Lab vocabulary enums are UI-only, not DB-mapped

**Status:** Active (decided in last merge)
**Decision:** `NonTreponemalTestType`, `TreponemalTestType`, `NonTreponemalTiter`,
and `TreponemalTestResult` are Python enums used only for `st.data_editor`
`SelectboxColumn` options. They are NOT declared as SQLAlchemy `Enum` columns.
**Reason:** Lab data is stored as free text strings in `LabResultEntry.test_type`,
`.titer`, and `.result`. Using DB-level enums would require a migration every time a
new test type is added. The UI enums provide validation at input time without
constraining the schema.
**Implication:** Never pass these enums as `Enum(NonTreponemalTestType, ...)` to
a SQLAlchemy `mapped_column()`.

---

## ADR-010: Symptom classification is derived, never manually set

**Status:** Active (decided in last merge)
**Decision:** `SymptomEntry.classification` is set by calling
`get_symptom_classification(symptom_type)` at save time, not by user input.
**Reason:** The classification (Primary/Secondary) is deterministic from the lesion
or symptom type string. Asking users to set it manually is redundant and error-prone.
**Implication:** Any code path that saves `SymptomEntry` rows must call
`get_symptom_classification()` before writing to DB. Pages 02, 03 and the FastAPI
symptom routes already do this.

---

## ADR-011: UI logic decoupled from core engine tasks
**Status:** Active
**Decision:** All heavy lifting for data transformations, graphing engines, or network analytics must be isolated in Python utility scripts (`app/utils/network_analysis.py`, etc.) and completely decoupled from Streamlit rendering (`app/pages/*`).
**Reason:** Prepares the codebase for a React migration without rewriting complex logic.
**Implication:** Do not import `networkx` or do large data transformations directly in `st` pages.

## ADR-012: Notifications are for Agent-to-Dev communication
**Status:** Active
**Decision:** `app/utils/notifications.py` (Slack integration) is explicitly meant as a developer convenience (agent status reporting) and is not wired into the application's business logic.
**Reason:** The app is a clinical tool, not an event-streaming system. Pinging Slack on every DB change is noisy and out of scope.

---

## ADR-013: FastAPI reuses the shared ORM and query layer
**Status:** Active
**Decision:** `fastapi_app/` must reuse the shared SQLAlchemy models from `app/db/models.py` and should prefer calling functions from `app/db/queries.py` rather than duplicating CRUD logic in a parallel backend-specific data layer.
**Reason:** The v1 Streamlit app already contains the stable domain model and most of the tested CRUD surface. Reusing that layer keeps FastAPI migration incremental, avoids schema drift, and preserves the option to run Streamlit and FastAPI in parallel during the transition.
**Implication:** Do not introduce a second declarative `Base` with duplicated models for FastAPI. New backend routes should stay thin and delegate data access to shared query functions unless there is a strong API-specific reason not to.

---

## ADR-014: Exposure dates are pair-specific, not case-level
**Status:** Active
**Decision:** Exposure timing (`exposure_first_date`, `exposure_last_date`, `exposure_modalities`) belongs on `CasePartnerRelationship` and `RelationshipReport`, not on `Case` or the React case form.
**Reason:** Exposure is defined per OP↔partner pair. Storing or presenting it at the case level becomes ambiguous as soon as one OP has multiple partners.
**Implication:** Do not add pairwise exposure fields to React case create/edit forms. Future frontend exposure capture must be implemented on partner/relationship screens using the existing FastAPI relationship endpoints.

---

## ADR-015: Symptom timing must preserve provenance
**Status:** Active
**Decision:** Symptom rows must capture whether the stored date is a reported onset date or an observation date from exam (`SymptomDateKind`), and whether duration is reported, assumed max, or unknown (`SymptomDurationSource`).
**Reason:** The field labeled only as “Onset Date” was not expressive enough for real workflows. Users sometimes know only the observation date from exam, and analysis must distinguish reported timing from inferred timing.
**Implication:** New symptom collection flows use “Onset or observation date” and explicit “Date type”. When a symptom is observed during exam and duration is blank, analysis treats the observation date as the last day of the maximum duration for that symptom class. `ongoing` is derived in these flows instead of being manually entered.
