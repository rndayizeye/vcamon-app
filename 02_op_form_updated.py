"""
app/pages/02_op_form.py  (updated)

Original Patient (OP) form — create or edit a case.
Uses session_state helpers, centralized validators, and
the shared sidebar case selector.
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
from app.utils.session_state import (
    init_session_state,
    get_active_case_id,
    set_active_case_id,
)
from app.utils.validators import validate_op_form
from app.components.dropdowns import enum_options, val_or_none

st.set_page_config(page_title="OP Form — VCA Monitor", layout="wide")
init_session_state()

# ---------------------------------------------------------------------------
# Sidebar — case selector
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Active case")

    with SessionLocal() as db:
        all_cases = get_all_cases(db)

    options = {0: "➕  New case"}
    options.update({c.id: f"#{c.id} — {c.patient_name}" for c in all_cases})

    current_id = get_active_case_id() or 0
    idx = list(options.keys()).index(current_id) if current_id in options else 0

    selected = st.selectbox(
        "Select case",
        options=list(options.keys()),
        format_func=lambda k: options[k],
        index=idx,
    )
    set_active_case_id(selected if selected != 0 else None)

    st.divider()
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")

# ---------------------------------------------------------------------------
# Load active case
# ---------------------------------------------------------------------------

def load_case():
    case_id = get_active_case_id()
    if not case_id:
        return None
    with SessionLocal() as db:
        return get_case_by_id(db, case_id)

case = load_case()

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Original Patient (OP) Form")
if case:
    st.caption(f"Editing case #{case.id} — {case.patient_name}")
else:
    st.caption("Creating a new case")

st.divider()

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

with st.form("op_form", border=True):

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
    st.subheader("Exam and treatment")
    col4, col5 = st.columns(2)

    with col4:
        reason_for_exam = st.selectbox(
            "Reason for exam",
            options=enum_options(ReasonForExam),
            index=enum_options(ReasonForExam).index(case.reason_for_exam or "") if case else 0,
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
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])

    with col_btn1:
        submitted = st.form_submit_button(
            "💾  Save" if case else "➕  Create case",
            type="primary",
            use_container_width=True,
        )
    with col_btn2:
        go_partners = st.form_submit_button(
            "Partners →",
            use_container_width=True,
        )
    with col_btn3:
        go_map = st.form_submit_button(
            "MAP sheet →",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Save logic
# ---------------------------------------------------------------------------

if submitted or go_partners or go_map:
    errors = validate_op_form(
        patient_name=patient_name,
        treatment_date=treatment_date if treatment_date else None,
        lab_1=lab_1,
        lab_2=lab_2,
    )
    if errors:
        for e in errors:
            st.error(e)
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
                saved = update_case(db, case.id, **payload)
                st.success(f"Case #{saved.id} updated — {saved.patient_name}")
            else:
                saved = create_case(db, patient_name=patient_name.strip(), **payload)
                set_active_case_id(saved.id)
                st.success(f"Case #{saved.id} created — {saved.patient_name}")

        if go_partners:
            st.switch_page("pages/03_partner_form.py")
        elif go_map:
            st.switch_page("pages/04_map_sheet.py")
        else:
            st.rerun()

# ---------------------------------------------------------------------------
# Summary metrics (shown when editing an existing case)
# ---------------------------------------------------------------------------

if case:
    st.divider()
    st.subheader("Current record")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Case ID",        f"#{case.id}")
    c2.metric("Lot",            case.lot or "—")
    c3.metric("Treatment date", str(case.treatment_date) if case.treatment_date else "—")
    c4.metric("Lab 1",          case.lab_1 or "—")

    with st.expander("Full record (debug)", expanded=False):
        st.json({
            "id":             case.id,
            "patient_name":   case.patient_name,
            "lot":            case.lot,
            "case_manager":   case.case_manager,
            "reason_for_exam": case.reason_for_exam,
            "treatment_date": str(case.treatment_date),
            "treatment":      case.treatment,
            "lesion_type":    case.lesion_type,
            "symptom":        case.symptom,
            "medical_info":   case.medical_info,
            "lab_1":          case.lab_1,
            "lab_2":          case.lab_2,
            "lab_3":          case.lab_3,
        })
