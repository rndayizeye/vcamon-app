"""
app/pages/02_op_form.py  (updated)

Original Patient (OP) form — create or edit a case.
Uses session_state helpers, centralized validators, and
the shared sidebar case selector.
"""

from datetime import date

import streamlit as st

from app.components.dropdowns import enum_options, val_or_none
from app.db.database import SessionLocal
from app.db.models import (
    LesionType,
    ReasonForExam,
    Symptom,
    SymptomClassification,
    TestCategory,
    Treatment,
)
from app.db.queries import (
    create_case,
    create_lab_result_entry,
    delete_lab_result_entry,
    get_all_cases,
    get_case_by_id,
    get_lab_results_for_case,
    update_case,
    update_lab_result_entry,
)
from app.utils.session_state import (
    get_active_case_id,
    init_session_state,
    require_password,
    set_active_case_id,
)
from app.utils.validators import validate_op_form

st.set_page_config(page_title="OP Form — VCA Monitor", layout="wide")
init_session_state()
require_password()

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
            "Diagnosis", #changed label from "Lot" to "Diagnosis", need to update DB field name in future
            options=["", "700", "710", "720", "730"],
            index=["", "700", "710", "720", "730"].index(case.lot or "") if case else 0,
        )
    with col3:
        case_manager = st.text_input(
            "Case manager",
            value=case.case_manager or "" if case else "",
        )
        initial_contact_date = st.date_input(
            "Date of initial contact/interview",
            value=case.initial_contact_date if case and case.initial_contact_date else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
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
        st.subheader("Symptoms & Lesions")
        st.caption("Add and manage all symptoms. Click a cell to edit.")
        
        # Load existing symptoms for the case
        existing_symptoms = []
        if case:
            with SessionLocal() as db:
                from app.db.queries import get_symptoms_for_case
                symptoms = get_symptoms_for_case(db, case.id)
                for s in symptoms:
                    existing_symptoms.append({
                        "id": s.id,
                        "Type": s.symptom_type,
                        "Classification": s.classification,
                        "Onset Date": s.onset_date,
                        "Duration": s.duration_days,
                        "Ongoing": s.ongoing,
                    })

        symptom_df = st.data_editor(
            existing_symptoms,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.Column(disabled=True),
                "Type": st.column_config.SelectboxColumn(
                    "Type", 
                    options=enum_options(LesionType) + enum_options(Symptom),
                    required=True
                ),
                "Classification": st.column_config.SelectboxColumn(
                    "Classification", 
                    options=enum_options(SymptomClassification),
                ),
                "Onset Date": st.column_config.DateColumn("Onset Date"),
                "Duration": st.column_config.NumberColumn("Duration (Days)"),
                "Ongoing": st.column_config.CheckboxColumn("Ongoing"),
            },
            key="symptom_editor",
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("History of Primary Chancre")
    historical_primary_chancre = st.radio(
        "Did the patient have a primary chancre?",
        options=[False, True], # False for No, True for Yes
        format_func=lambda x: "Yes" if x else "No",
        index=[False, True].index(case.historical_primary_chancre) if case and case.historical_primary_chancre is not None else 0,
        help="Required for secondary syphilis diagnosis."
    )

    historical_primary_date = None
    if historical_primary_chancre:
        historical_primary_date = st.date_input(
            "Date of primary chancre",
            value=case.historical_primary_date if case else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
            help="When did the primary chancre first appear?"
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=case.medical_info or "" if case else "",
        height=100,
        placeholder="Relevant medical history, medications, conditions...",
    )

    st.divider()
    st.subheader("Lab results")
    st.caption("Manage all laboratory results. Use the table to add, edit, or remove entries.")
    
    # Load existing lab results for the case
    existing_labs = []
    if case:
        with SessionLocal() as db:
            labs = get_lab_results_for_case(db, case.id)
            for l in labs:
                existing_labs.append({
                    "id": l.id,
                    "Category": l.test_category,
                    "Test Type": l.test_type,
                    "Titer": l.titer,
                    "Result": l.result,
                    "Date": l.collection_date,
                })

    # Data editor for repeatable lab history
    lab_df = st.data_editor(
        existing_labs,
        num_rows="dynamic",
        column_config={
            "id": st.column_config.Column(disabled=True),
            "Category": st.column_config.SelectboxColumn(
                "Category", 
                options=enum_options(TestCategory),
                required=True
            ),
            "Test Type": st.column_config.TextColumn("Test Type", required=True),
            "Titer": st.column_config.TextColumn("Titer (Non-treponemal)"),
            "Result": st.column_config.TextColumn("Result (Treponemal)"),
            "Date": st.column_config.DateColumn("Collection Date", required=True),
        },
        key="lab_editor",
        use_container_width=True,
    )

    st.divider()
    col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])

    st.divider()
    with st.expander("🔬 Clinical Details (Optional - for VCA analysis)", expanded=False):
        st.caption("Complete these fields to streamline ghosting analysis")
        
        st.subheader("Symptom Details")
        symptom_classification = st.selectbox(
            "Symptom classification",
            options=enum_options(SymptomClassification),
            index=enum_options(SymptomClassification).index(case.symptom_classification or "") if case else 0,
            help="Is this a primary symptom or a secondary symptom?"
        )
        symptom_onset = st.date_input(
            "Symptom onset date",
            value=case.symptom_onset_date if case else None,
            help="When did this symptom first appear?",
            format="MM/DD/YYYY",
        )
        symptom_duration = st.number_input(
            "Symptom duration (days, 0=unknown)",
            min_value=0, max_value=90,
            value=case.symptom_duration_days or 0 if case else 0,
        )
        symptom_ongoing = st.checkbox(
            "Symptom is ongoing",
            value=case.symptom_ongoing if case else False,
            help="Check if the symptom is still active."
        )
        st.info("Lab dates are now managed in the 'Lab results' section above.")

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
        lab_1=None, # Legacy validator might need update, passing None for now
        lab_2=None,
    )
    if errors:
        for e in errors:
            st.error(e)
    else:
        payload = dict(
            lot=val_or_none(lot),
            case_manager=val_or_none(case_manager),
            initial_contact_date=initial_contact_date if initial_contact_date else None,
            reason_for_exam=val_or_none(reason_for_exam),
            treatment_date=treatment_date if treatment_date else None,
            treatment=val_or_none(treatment),
            historical_primary_chancre=historical_primary_chancre,
            historical_primary_date=historical_primary_date if historical_primary_date else None,
            medical_info=val_or_none(medical_info),
            # Keep legacy fields as None
            lab_1=None,
            lab_2=None,
            lab_3=None,
            lab_1_date=None,
            lab_2_date=None,
            lab_3_date=None,
        )

        with SessionLocal() as db:
            if case:
                saved = update_case(db, case.id, **payload)
                case_id = saved.id
                st.success(f"Case #{saved.id} updated — {saved.patient_name}")
            else:
                saved = create_case(db, patient_name=patient_name.strip(), **payload)
                set_active_case_id(saved.id)
                case_id = saved.id
                st.success(f"Case #{saved.id} created — {saved.patient_name}")

            # Sync Lab Results
            # 1. Identify deletions
            current_lab_ids = [l.id for l in get_lab_results_for_case(db, case_id)]
            editor_lab_ids = [row["id"] for row in lab_df if "id" in row and row["id"] is not None]
            
            for lid in current_lab_ids:
                if lid not in editor_lab_ids:
                    delete_lab_result_entry(db, lid)
            
            # 2. Upsert entries
            for row in lab_df:
                if "id" in row and row["id"] is not None:
                    update_lab_result_entry(
                        db, row["id"],
                        test_category=row["Category"],
                        test_type=row["Test Type"],
                        titer=row["Titer"],
                        result=row["Result"],
                        collection_date=row["Date"]
                    )
                else:
                    create_lab_result_entry(
                        db,
                        test_category=row["Category"],
                        test_type=row["Test Type"],
                        collection_date=row["Date"],
                        case_id=case_id,
                        titer=row["Titer"],
                        result=row["Result"]
                    )

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
