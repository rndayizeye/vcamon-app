"""
app/pages/02_op_form.py

Original Patient (OP) form page.
Handles both creating a new case and editing an existing one.
Case is selected via st.session_state["active_case_id"] set by the dashboard,
or the user can start a new case directly from this page.
"""

import streamlit as st
from datetime import date
from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    create_case,
    update_case,
    get_all_cases,
)
from app.db.models import (
    ReasonForExam,
    LabResult,
    TreponemalResult,
    Treatment,
    LesionType,
    Symptom,
)

st.set_page_config(page_title="OP Form — VCA Monitor", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def enum_options(enum_cls, include_blank: bool = True) -> list[str]:
    """Return enum values as a list, with an optional leading blank."""
    vals = [e.value for e in enum_cls]
    return [""] + vals if include_blank else vals


def val_or_none(v: str):
    """Convert empty string back to None before saving."""
    return v if v else None


def load_case(case_id: int | None):
    """Return a Case object or None for a new record."""
    if not case_id:
        return None
    with SessionLocal() as db:
        return get_case_by_id(db, case_id)


# ---------------------------------------------------------------------------
# Page header + case selector
# ---------------------------------------------------------------------------

st.title("Original Patient (OP) Form")
st.caption("Complete all fields known at time of interview. Use the sidebar to switch cases.")

# Sidebar — pick existing case or start new
with st.sidebar:
    st.header("Case selection")
    with SessionLocal() as db:
        all_cases = get_all_cases(db)

    case_names = {c.id: f"#{c.id} — {c.patient_name}" for c in all_cases}
    case_names[0] = "➕  New case"

    # Default to whatever the dashboard set, or "new"
    default_id = st.session_state.get("active_case_id", 0)
    default_idx = list(case_names.keys()).index(default_id) if default_id in case_names else 0

    selected_key = st.selectbox(
        "Select case",
        options=list(case_names.keys()),
        format_func=lambda k: case_names[k],
        index=default_idx,
    )
    st.session_state["active_case_id"] = selected_key if selected_key != 0 else None

# Load the chosen case (or None for new)
case = load_case(st.session_state.get("active_case_id"))

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

with st.form("op_form", border=True):

    # --- Patient identifiers ---
    st.subheader("Patient information")
    col1, col2, col3 = st.columns([3, 1, 2])

    with col1:
        patient_name = st.text_input(
            "Patient name *",
            value=case.patient_name if case else "",
            placeholder="Last, First",
        )
    with col2:
        lot = st.selectbox(
            "Lot",
            options=["", "700", "710", "720", "730"],
            index=["", "700", "710", "720", "730"].index(case.lot or "") if case else 0,
        )
    with col3:
        case_manager = st.text_input(
            "Case manager",
            value=case.case_manager or "" if case else "",
        )

    st.divider()

    # --- Exam & treatment ---
    st.subheader("Exam and treatment")
    col4, col5 = st.columns(2)

    with col4:
        reason_for_exam = st.selectbox(
            "Reason for exam",
            options=enum_options(ReasonForExam),
            index=enum_options(ReasonForExam).index(case.reason_for_exam or "")
            if case else 0,
        )
        treatment_date = st.date_input(
            "Treatment date",
            value=case.treatment_date if case and case.treatment_date else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
        )
        treatment = st.selectbox(
            "Treatment given",
            options=enum_options(Treatment),
            index=enum_options(Treatment).index(case.treatment or "") if case else 0,
        )

    with col5:
        lesion_type = st.selectbox(
            "Lesion type",
            options=enum_options(LesionType),
            index=enum_options(LesionType).index(case.lesion_type or "") if case else 0,
        )
        symptom = st.selectbox(
            "Symptom",
            options=enum_options(Symptom),
            index=enum_options(Symptom).index(case.symptom or "") if case else 0,
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=case.medical_info or "" if case else "",
        height=100,
        placeholder="Relevant medical history, medications, conditions...",
    )

    st.divider()

    # --- Lab results ---
    st.subheader("Lab results")
    st.caption("Lab 1 = RPR/VDRL titer · Lab 2 = Treponemal confirmatory · Lab 3 = free text")
    col6, col7, col8 = st.columns(3)

    with col6:
        lab_1 = st.selectbox(
            "Lab 1 — RPR / VDRL",
            options=enum_options(LabResult),
            index=enum_options(LabResult).index(case.lab_1 or "") if case else 0,
        )
    with col7:
        lab_2 = st.selectbox(
            "Lab 2 — Treponemal",
            options=enum_options(TreponemalResult),
            index=enum_options(TreponemalResult).index(case.lab_2 or "") if case else 0,
        )
    with col8:
        lab_3 = st.text_input(
            "Lab 3 — other",
            value=case.lab_3 or "" if case else "",
            placeholder="Drfd N/A, or free text",
        )

    st.divider()

    # --- Submit ---
    col_btn1, col_btn2, _ = st.columns([1, 1, 4])
    with col_btn1:
        submitted = st.form_submit_button(
            "💾  Save" if case else "➕  Create case",
            type="primary",
            use_container_width=True,
        )
    with col_btn2:
        if case:
            clear = st.form_submit_button(
                "✕  Clear",
                use_container_width=True,
            )

# ---------------------------------------------------------------------------
# Save logic
# ---------------------------------------------------------------------------

if submitted:
    if not patient_name.strip():
        st.error("Patient name is required.")
    else:
        payload = dict(
            lot=val_or_none(lot),
            case_manager=val_or_none(case_manager),
            reason_for_exam=val_or_none(reason_for_exam),
            treatment_date=treatment_date if treatment_date else None,
            treatment=val_or_none(treatment),
            lesion_type=val_or_none(lesion_type),
            symptom=val_or_none(symptom),
            medical_info=val_or_none(medical_info),
            lab_1=val_or_none(lab_1),
            lab_2=val_or_none(lab_2),
            lab_3=val_or_none(lab_3),
        )

        with SessionLocal() as db:
            if case:
                updated = update_case(db, case.id, **payload)
                st.success(f"Case #{updated.id} updated — {updated.patient_name}")
            else:
                new_case = create_case(db, patient_name=patient_name.strip(), **payload)
                st.session_state["active_case_id"] = new_case.id
                st.success(f"Case #{new_case.id} created — {new_case.patient_name}")
                st.rerun()

# ---------------------------------------------------------------------------
# Read-only summary card (shown when a case is loaded)
# ---------------------------------------------------------------------------

if case:
    st.divider()
    st.subheader("Current record")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Case ID", f"#{case.id}")
    c2.metric("Lot", case.lot or "—")
    c3.metric("Treatment date", str(case.treatment_date) if case.treatment_date else "—")
    c4.metric("Lab 1", case.lab_1 or "—")

    with st.expander("Full record JSON (for debugging)", expanded=False):
        import json
        st.json({
            "id": case.id,
            "patient_name": case.patient_name,
            "lot": case.lot,
            "case_manager": case.case_manager,
            "reason_for_exam": case.reason_for_exam,
            "treatment_date": str(case.treatment_date),
            "treatment": case.treatment,
            "lesion_type": case.lesion_type,
            "symptom": case.symptom,
            "medical_info": case.medical_info,
            "lab_1": case.lab_1,
            "lab_2": case.lab_2,
            "lab_3": case.lab_3,
        })