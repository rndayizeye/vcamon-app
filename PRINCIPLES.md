# VCA Monitor — Development Principles & Guardrails

This document serves as the "Constitution" for the vcamon-app. It is designed to prevent the architectural decay and framework-lock experienced during the Streamlit v1 phase. All code changes must be audited against these principles.

---

## 🛡️ The Non-Negotiables (Hard Failures)

### 1. The "Clinical Wall" (Absolute Decoupling)
The core epidemiological logic in `app/utils/clinical.py` must remain **framework-agnostic**.
- **NO** imports from `streamlit`, `fastapi`, `flask`, or any UI library.
- **NO** imports from `sqlalchemy` or any database-specific library.
- **Symmetry:** The engine must only accept pure Python types (dataclasses, datetime, strings, ints) and return pure Python types.
- **Reason:** The ghosting engine is the project's primary intellectual asset. It must be a "drop-in" module for any future backend.

### 2. Pure Logic (Statelessness)
All clinical and network analysis functions must be **pure functions**.
- **No** reliance on `st.session_state`, global variables, or hidden singleton states.
- **Input $\rightarrow$ Output:** Every function must be testable by passing in data and asserting the result.
- **Reason:** Prevents the "state-sync hell" that occurs when complex UI state diverges from database state.

### 3. Schema-First Development
The database is the source of truth, not the UI.
- **Rule:** No new data-capture field may be added to a page without first defining the SQLAlchemy model and the corresponding `queries.py` helper.
- **Prohibition:** No "temporary" fields stored as JSON strings or loosely typed blobs unless explicitly approved for the "notes" fields.
- **Reason:** Ensures data integrity and makes the eventual migration to PostgreSQL seamless.

### 4. Clinical Verifiability (Test-Driven Logic)
Any change to the ghosting pipeline or period-intersection logic must be verifiable.
- **Requirement:** Every logic change must be accompanied by a test in `tests/test_clinical.py`.
- **Scenario-Based:** Tests must use real-world clinical scenarios (e.g., the NCSD training slides) to ensure epidemiological correctness.
- **Reason:** A "working" app is useless if the clinical verdict is wrong.

---

## 📈 Quality Standards (Warnings)

### 5. Network Analysis Complexity
As the app expands to handle larger clusters:
- **Complexity Audit:** Any new network analysis feature must be evaluated for time/space complexity. Avoid $O(n^2)$ or $O(n^3)$ operations on the full case set.
- **Caching:** Heavy computations (like centrality or cluster paths) should be cached at the service layer, not the UI layer.

### 6. Type Safety
- Use Python type hints (`typing`) for all function signatures.
- Use `dataclasses` for any complex data transfer object (DTO) moving between the DB and the Clinical Engine.

---

## 🤖 Guardrail Agent Protocol
When acting as the **Guardrail Agent**, the model must:
1. Review the diff for framework leakage into `app/utils/clinical.py`.
2. Verify that new logic has corresponding tests.
3. Check that no UI widgets are being used to store primary business logic.
4. **Semantic Naming Audit:** Scan the diff for new variables, functions, and files. Compare them against `GLOSSARY.md` to ensure a professional public health vocabulary is used. Flag "draft" or "naive" terms (e.g., "sex types" $\rightarrow$ "exposure modality").
5. **Session Hygiene Audit:** Before starting a task, evaluate the "contextual load." If the task requires reading/modifying many files ($\geq 5$), involves an open-ended experiment, or is a deep audit, recommend a new branched session to prevent context pollution.
6. Issue a `PASS`, `WARN`, or `FAIL` verdict based on the above.

---

## 🎯 Operational Methodology (PH Guidelines)

### 7. Primary Disease Intervention
The overarching goal of the workflow is to reach sexual partners **before** they develop symptoms of disease.

### 8. Name First Methodology
Adhere to the CDC-recommended strategy: prioritize collecting partner names first to establish the sexual network, then use re-interviews to gather detailed data (exposure, locating info, etc.).
