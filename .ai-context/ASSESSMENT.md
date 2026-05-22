Honest take: it's both, and they're compounding each other. Let me be specific.

**Where you've genuinely hit Streamlit's ceiling**

Streamlit was designed for data science dashboards — one script, simple widgets, rerun on every interaction. The VCA Monitor has grown into a multi-table relational CRUD application with complex inter-page state, and Streamlit's execution model fights you at every step.

The `st.data_editor` inside `st.form()` issue isn't a bug you can fix with a refactor — it's a fundamental mismatch. Streamlit's form abstraction batches widget state and submits it atomically, but `data_editor` manages its own internal state separately. They were never designed to compose cleanly. You can work around it with the session_state pattern but you're essentially rebuilding the form abstraction yourself.

The rerun model is the deeper issue. Every interaction reruns the entire page. With 3 data editors, a sidebar case selector, and multiple DB queries per render, you're doing a lot of work just to display the page, and any state that lives between reruns has to be manually threaded through `st.session_state`. The more complex the page, the more fragile that threading becomes.

**Where the design has real fixable problems**

The symptom → ghosting engine conversion chain is genuinely risky. `SymptomEntry` rows go through `_entries_to_rows()` → data editor → `_rows_to_symptoms()` → engine `Symptom` dataclass. Each step can silently drop data. A row with no `onset_date` is silently skipped, a row with an unrecognised classification returns no VCA type, the editor can drop edits if inside a form. You don't know which step failed.

Page 08 (the centrepiece chart) is completely broken for the new data model — `primary_sym` is never populated, so symptom bars, onset markers, and inoculation points are blank for every case. That's not a Streamlit ceiling issue, it's an unfinished migration.

The `historical_primary_chancre` auto-derivation runs only at save time and doesn't update when you reload the form. If someone edits a symptom, the derived field is stale until the next save.

**The honest verdict**

The v1 Streamlit app has done its job — it proved the data model, the clinical engine works, and the workflow is right. The final feature work (Network Analysis and public health Terminology Alignment) for this iteration is complete. But you're spending more time fighting Streamlit's rendering model than building features, and that ratio is going to get worse as the app grows.

The question isn't whether to do the v2 migration but when. A few specific signals that you've reached that point: if fixing the data_editor/form issue requires building a custom form abstraction, if page 08 needs a full rewrite to wire the new data model, and if adding a new field now requires touching 4–5 files. All three are true right now.

**Pragmatic path forward**

If you need to keep iterating on v1, the highest-ROI fix is moving pages 02 and 03 off `st.form()` entirely. That unblocks the data editor reliability issue and is a contained change. Everything else — page 08, the conversion chain, the derived fields — flows from having reliable data capture first.

However, the real goal is a usable clinical tool. Starting the FastAPI + React skeleton now and running both in parallel is definitely the right move. The clinical engine (`clinical.py`) drops in unchanged, the data model is solid, and the queries layer + new analytical tools (`network_analysis.py`) are completely decoupled from the UI. The hardest part of v2 is already done. We are ready to tackle Phase 1: Backend Foundation.
