"""
app/pages/02_op_form.py  (updated)

Original Patient (OP) form — create or edit a case.
Uses session_state helpers, centralized validators, and
the shared sidebar case selector.
"""

from datetime import date

import pandas as pd
import streamlit as st

from app.components.dropdowns import enum_options, val_or_none
from app.db.database import SessionLocal
from app.db.models import (
    LesionType,
    NonTreponemalTestType,
    NonTreponemalTiter,
    ReasonForExam,
    Symptom,
    SymptomDateKind,
    TestCategory,
    Treatment,
    TreponemalTestResult,
    TreponemalTestType,
)
from app.db.queries import (
    create_case,
    create_lab_result_entry,
    create_symptom_entry,
    delete_lab_result_entry,
    delete_symptom_entry,
    get_all_cases,
    get_case_by_id,
    get_lab_results_for_case,
    get_symptoms_for_case,
    update_case,
    update_lab_result_entry,
    update_symptom_entry,
)
from app.utils.clinical import (
    derive_symptom_capture_metadata,
    derive_symptom_end_date,
    get_symptom_classification,
    resolve_symptom_timing_for_analysis,
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
        diagnosis_options = ["", "700", "710", "720", "730", "755"]
        lot = st.selectbox(
            "Diagnosis / syphilis stage",
            options=diagnosis_options,
            index=diagnosis_options.index(case.lot or "")
            if case and case.lot in diagnosis_options
            else 0,
        )
    with col3:
        case_manager = st.text_input(
            "Case manager",
            value=case.case_manager or "" if case else "",
        )
        initial_contact_date = st.date_input(
            "Date of initial contact/interview",
            value=case.initial_contact_date
            if case and case.initial_contact_date
            else None,
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
            index=enum_options(ReasonForExam).index(case.reason_for_exam or "")
            if case
            else 0,
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
        st.subheader("Symptoms")
        st.caption(
            "Add and manage all symptoms. Use onset or observation date. "
            "If onset is unknown and the symptom was observed during exam, "
            "select that date type; when duration is left blank, analysis "
            "will assume the maximum duration for that symptom class."
        )

        # Load existing symptoms for the case

        if case:
            with SessionLocal() as db:
                symptoms = get_symptoms_for_case(db, case.id)
                existing_symptoms = [
                    {
                        "id": s.id,
                        "Type": s.symptom_type,
                        "Onset or Observation Date": s.onset_date,
                        "Date Type": (
                            s.date_kind.value
                            if isinstance(s.date_kind, SymptomDateKind)
                            else s.date_kind or SymptomDateKind.ONSET_REPORTED.value
                        ),
                        "Duration": s.duration_days,
                    }
                    for s in symptoms
                ]
        else:
            existing_symptoms = []

        # Create DataFrame with proper schema (shows editable table even when empty)
        symptom_df = pd.DataFrame(
            existing_symptoms,
            columns=[
                "id",
                "Type",
                "Onset or Observation Date",
                "Date Type",
                "Duration",
            ],
        )

        edited_symptom_df = st.data_editor(
            symptom_df,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=enum_options(LesionType) + enum_options(Symptom),
                    required=True,
                ),
                "Onset or Observation Date": st.column_config.DateColumn(
                    "Onset or observation date"
                ),
                "Date Type": st.column_config.SelectboxColumn(
                    "Date type",
                    options=[option.value for option in SymptomDateKind],
                    required=True,
                ),
                "Duration": st.column_config.NumberColumn("Duration (Days, if known)"),
            },
            key="symptom_editor",
            use_container_width=True,
            hide_index=True,
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=case.medical_info or "" if case else "",
        height=100,
        placeholder="Relevant medical history, medications, conditions...",
    )

    st.divider()
    st.subheader("Lab results")
    st.caption(
        "Add, edit, or remove entries. "
        "Non-treponemal (RPR / VDRL) on the left; treponemal confirmatory on the right."
    )

    # Load existing lab results — split by category
    if case:
        with SessionLocal() as db:
            labs = get_lab_results_for_case(db, case.id)
            existing_nontrop = [
                {
                    "id": l.id,
                    "Test Type": l.test_type,
                    "Titer": l.titer or "",
                    "Date": l.collection_date,
                }
                for l in labs
                if l.test_category == TestCategory.NON_TREPONEMAL.value
            ]
            existing_trep = [
                {
                    "id": l.id,
                    "Test Type": l.test_type,
                    "Result": l.result or "",
                    "Date": l.collection_date,
                }
                for l in labs
                if l.test_category == TestCategory.TREPONEMAL.value
            ]
    else:
        existing_nontrop = []
        existing_trep = []

    nontrop_df = pd.DataFrame(
        existing_nontrop, columns=["id", "Test Type", "Titer", "Date"]
    )
    trep_df = pd.DataFrame(existing_trep, columns=["id", "Test Type", "Result", "Date"])

    col_lab1, col_lab2 = st.columns(2)

    with col_lab1:
        st.caption("🔵 Non-treponemal (RPR / VDRL)")
        edited_nontrop_df = st.data_editor(
            nontrop_df,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Test Type": st.column_config.SelectboxColumn(
                    "Test",
                    options=enum_options(NonTreponemalTestType),
                    required=True,
                ),
                "Titer": st.column_config.SelectboxColumn(
                    "Titer",
                    options=enum_options(NonTreponemalTiter),
                ),
                "Date": st.column_config.DateColumn("Collection Date", required=True),
            },
            key="op_nontrop_lab_editor",
            use_container_width=True,
            hide_index=True,
        )

    with col_lab2:
        st.caption("🟢 Treponemal confirmatory")
        edited_trep_df = st.data_editor(
            trep_df,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Test Type": st.column_config.SelectboxColumn(
                    "Test",
                    options=enum_options(TreponemalTestType),
                    required=True,
                ),
                "Result": st.column_config.SelectboxColumn(
                    "Result",
                    options=enum_options(TreponemalTestResult),
                ),
                "Date": st.column_config.DateColumn("Collection Date", required=True),
            },
            key="op_trep_lab_editor",
            use_container_width=True,
            hide_index=True,
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
    )
    if errors:
        for e in errors:
            st.error(e)
    else:
        # Deduce historical_primary_chancre and date
        derived_historical_primary_chancre = False
        derived_historical_primary_date = None

        for row in edited_symptom_df.to_dict("records"):
            symptom_type = row.get("Type")
            anchor_date = row.get("Onset or Observation Date")
            date_kind = row.get("Date Type")
            duration_days = (
                int(row["Duration"]) if pd.notna(row.get("Duration")) else None
            )

            is_primary_chancre = symptom_type in [
                LesionType.ANAL.value,
                LesionType.LAB.value,
                LesionType.LX.value,
                LesionType.ORAL.value,
                LesionType.PENILE.value,
                LesionType.RECTAL.value,
                LesionType.VAGINAL.value,
            ]

            if is_primary_chancre and pd.notna(anchor_date) and treatment_date:
                try:
                    analysis_onset, _ = resolve_symptom_timing_for_analysis(
                        symptom_type=symptom_type,
                        anchor_date=pd.to_datetime(anchor_date).date(),
                        duration_days=duration_days,
                        date_kind=date_kind,
                        classification=get_symptom_classification(symptom_type),
                    )
                    symptom_end_date = derive_symptom_end_date(
                        anchor_date=pd.to_datetime(anchor_date).date(),
                        duration_days=duration_days,
                        date_kind=date_kind,
                    )
                    if (
                        analysis_onset
                        and symptom_end_date
                        and symptom_end_date < treatment_date
                    ):
                        derived_historical_primary_chancre = True
                        derived_historical_primary_date = analysis_onset
                        break  # Found one, no need to check further
                except ValueError:
                    pass  # Handle cases where date conversion might fail

        payload = dict(
            lot=val_or_none(lot),
            case_manager=val_or_none(case_manager),
            initial_contact_date=initial_contact_date if initial_contact_date else None,
            reason_for_exam=val_or_none(reason_for_exam),
            treatment_date=treatment_date if treatment_date else None,
            treatment=val_or_none(treatment),
            historical_primary_chancre=derived_historical_primary_chancre,
            historical_primary_date=derived_historical_primary_date,
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

            # Sync Lab Results — two editors (non-treponemal + treponemal)
            current_lab_ids = [l.id for l in get_lab_results_for_case(db, case_id)]
            editor_lab_ids = {
                int(row["id"])
                for df in (edited_nontrop_df, edited_trep_df)
                for row in df.to_dict("records")
                if pd.notna(row.get("id"))
            }

            for lid in current_lab_ids:
                if lid not in editor_lab_ids:
                    delete_lab_result_entry(db, lid)

            for row in edited_nontrop_df.to_dict("records"):
                if pd.isna(row.get("Test Type")) or not row.get("Test Type"):
                    continue
                if pd.notna(row.get("id")):
                    update_lab_result_entry(
                        db,
                        int(row["id"]),
                        test_category=TestCategory.NON_TREPONEMAL.value,
                        test_type=row["Test Type"],
                        titer=row.get("Titer") or None,
                        result=None,
                        collection_date=row["Date"],
                    )
                else:
                    create_lab_result_entry(
                        db,
                        test_category=TestCategory.NON_TREPONEMAL.value,
                        test_type=row["Test Type"],
                        collection_date=row["Date"],
                        case_id=case_id,
                        titer=row.get("Titer") or None,
                        result=None,
                    )

            for row in edited_trep_df.to_dict("records"):
                if pd.isna(row.get("Test Type")) or not row.get("Test Type"):
                    continue
                if pd.notna(row.get("id")):
                    update_lab_result_entry(
                        db,
                        int(row["id"]),
                        test_category=TestCategory.TREPONEMAL.value,
                        test_type=row["Test Type"],
                        titer=None,
                        result=row.get("Result") or None,
                        collection_date=row["Date"],
                    )
                else:
                    create_lab_result_entry(
                        db,
                        test_category=TestCategory.TREPONEMAL.value,
                        test_type=row["Test Type"],
                        collection_date=row["Date"],
                        case_id=case_id,
                        titer=None,
                        result=row.get("Result") or None,
                    )

            # Sync Symptom Entries
            current_symptom_ids = [s.id for s in get_symptoms_for_case(db, case_id)]
            editor_symptom_ids = {
                int(row["id"])
                for row in edited_symptom_df.to_dict("records")
                if pd.notna(row.get("id"))
            }

            for sid in current_symptom_ids:
                if sid not in editor_symptom_ids:
                    delete_symptom_entry(db, sid)

            for row in edited_symptom_df.to_dict("records"):
                if pd.isna(row.get("Type")) or not row.get("Type"):
                    continue
                derived_class = get_symptom_classification(row["Type"])
                anchor_date = row.get("Onset or Observation Date")
                duration_days = (
                    int(row["Duration"]) if pd.notna(row.get("Duration")) else None
                )
                date_kind, duration_source, derived_ongoing = (
                    derive_symptom_capture_metadata(
                        symptom_type=row["Type"],
                        anchor_date=anchor_date,
                        duration_days=duration_days,
                        date_kind=row.get("Date Type"),
                        classification=derived_class,
                    )
                )
                if pd.notna(row.get("id")):
                    update_symptom_entry(
                        db,
                        int(row["id"]),
                        symptom_type=row["Type"],
                        classification=derived_class,
                        onset_date=anchor_date,
                        date_kind=date_kind,
                        duration_days=duration_days,
                        duration_source=duration_source,
                        ongoing=derived_ongoing,
                    )
                else:
                    create_symptom_entry(
                        db,
                        symptom_type=row["Type"],
                        classification=derived_class,
                        onset_date=anchor_date,
                        date_kind=date_kind,
                        duration_days=duration_days,
                        duration_source=duration_source,
                        ongoing=derived_ongoing,
                        case_id=case_id,
                    )

        # Navigation — outside DB session and symptom loop
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
    c1.metric("Case ID", f"#{case.id}")
    c2.metric("Diagnosis", case.lot or "—")
    c3.metric(
        "Treatment date", str(case.treatment_date) if case.treatment_date else "—"
    )
    c4.metric("Lab 1", case.lab_1 or "—")

    with st.expander("Full record (debug)", expanded=False):
        st.json(
            {
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
            }
        )
