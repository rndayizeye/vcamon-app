"""
app/pages/03_partner_form.py

Partner form — add and edit contact partners for the active case.
Each case can have multiple partners. Partners share the same
field structure as the OP form (reason for exam, labs, treatment).

Navigation flow:
  Dashboard → OP Form → [Partner Form] → MAP Sheet
"""

import json
from datetime import date

import pandas as pd
import streamlit as st

from app.components.dropdowns import enum_options, val_or_none
from app.db.database import SessionLocal, write_db
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
    create_case_partner_relationship,
    create_lab_result_entry,
    create_partner,
    create_relationship_report,
    create_symptom_entry,
    delete_lab_result_entry,
    delete_relationship_report,
    delete_symptom_entry,
    get_case_by_id,
    get_case_partner_relationship,
    get_lab_results_for_partner,
    get_partner_by_id,
    get_partners_for_case,
    get_reports_for_relationship,
    get_symptoms_for_partner,
    update_case_partner_relationship,
    update_lab_result_entry,
    update_partner,
    update_relationship_report,
    update_symptom_entry,
)
from app.utils.clinical import (
    derive_symptom_capture_metadata,
    get_symptom_classification,
)
from app.utils.session_state import (
    get_active_case_id,
    get_active_partner_id,
    init_session_state,
    require_password,
    set_active_partner_id,
)
from app.utils.validators import validate_partner_form

st.set_page_config(page_title="Partners — VCA Monitor", layout="wide")
init_session_state()
require_password()

# ---------------------------------------------------------------------------
# Sidebar — case context + partner switcher
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Active case")

    case_id = get_active_case_id()

    if not case_id:
        st.warning("No case selected.")
        if st.button("← Go to dashboard", use_container_width=True):
            st.switch_page("pages/01_dashboard.py")
        st.stop()

    with SessionLocal() as db:
        case = get_case_by_id(db, case_id)
        partners = get_partners_for_case(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Diagnosis: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")

    st.divider()
    st.subheader("Partners")

    # Partner switcher
    partner_options = {0: "➕  New partner"}
    partner_options.update(
        {p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}" for p in partners}
    )

    current_partner_id = get_active_partner_id() or 0
    if current_partner_id not in partner_options:
        current_partner_id = 0

    selected_partner_key = st.selectbox(
        "Select partner",
        options=list(partner_options.keys()),
        format_func=lambda k: partner_options[k],
        index=list(partner_options.keys()).index(current_partner_id),
    )
    set_active_partner_id(selected_partner_key if selected_partner_key != 0 else None)

    st.divider()

    if st.button("← OP Form", use_container_width=True):
        st.switch_page("pages/02_op_form.py")
    if st.button("MAP Sheet →", use_container_width=True):
        st.switch_page("pages/04_map_sheet.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")

# ---------------------------------------------------------------------------
# Load active partner (or None for new)
# ---------------------------------------------------------------------------

# Reload partners and active partner fresh
with SessionLocal() as db:
    partners = get_partners_for_case(db, case_id)
    active_pid = get_active_partner_id()
    partner = get_partner_by_id(db, active_pid) if active_pid else None

    # Fetch relationship data if an active partner exists
    relationship = None
    if partner:
        relationship = get_case_partner_relationship(db, case_id, partner.id)

# Next partner number for new records
next_number = max((p.partner_number for p in partners), default=0) + 1

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Partner Form")

if partner:
    st.caption(
        f"Editing Partner {partner.partner_number} for "
        f"case #{case.id} — {case.patient_name}"
    )
else:
    st.caption(f"Adding Partner {next_number} to case #{case.id} — {case.patient_name}")

# Partner count badge
if partners:
    cols_hdr = st.columns([6, 1])
    with cols_hdr[1]:
        st.info(f"{len(partners)} partner{'s' if len(partners) != 1 else ''} on file")

st.divider()

# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------

with st.form("partner_form", border=True):
    # --- Identity ---
    st.subheader("Partner information")
    col1, col2 = st.columns([3, 1])

    with col1:
        partner_name = st.text_input(
            "Partner name *",
            value=partner.name or "" if partner else "",
            placeholder="Last, First  (or alias if unknown)",
        )
    with col2:
        st.text_input(
            "Partner #",
            value=str(partner.partner_number if partner else next_number),
            disabled=True,
            help="Assigned automatically in order added.",
        )

    st.divider()

    # --- Exam & treatment (same layout as OP form) ---
    st.subheader("Exam and treatment")
    col3, col4 = st.columns(2)

    with col3:
        reason_for_exam = st.selectbox(
            "Reason for exam",
            options=enum_options(ReasonForExam),
            index=enum_options(ReasonForExam).index(
                partner.reason_for_exam or "" if partner else ""
            ),
        )
        treatment_date = st.date_input(
            "Treatment date",
            value=partner.treatment_date
            if partner and partner.treatment_date
            else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
        )
        treatment = st.selectbox(
            "Treatment given",
            options=enum_options(Treatment),
            index=enum_options(Treatment).index(
                partner.treatment or "" if partner else ""
            ),
        )

    with col4:
        st.subheader("Symptoms & Lesions")
        st.caption(
            "Add and manage all symptoms. Use onset or observation date. "
            "If onset is unknown and the symptom was observed during exam, "
            "select that date type; when duration is left blank, analysis "
            "will assume the maximum duration for that symptom class."
        )

        # Load existing symptoms for the partner
        if partner:
            with SessionLocal() as db:
                symptoms = get_symptoms_for_partner(db, partner.id)
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

        # Create DataFrame with proper schema
        symptom_df_base = pd.DataFrame(
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
            symptom_df_base,
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
            key="partner_symptom_editor",
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("History of Primary Chancre")
    historical_primary_chancre = st.radio(
        "Did the partner have a primary chancre?",
        options=[False, True],
        format_func=lambda x: "Yes" if x else "No",
        index=[False, True].index(partner.historical_primary_chancre)
        if partner and partner.historical_primary_chancre is not None
        else 0,
        help="Required for secondary syphilis diagnosis.",
    )

    historical_primary_date = None
    if historical_primary_chancre:
        historical_primary_date = st.date_input(
            "Date of primary chancre",
            value=partner.historical_primary_date if partner else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
            help="When did the primary chancre first appear?",
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=partner.medical_info or "" if partner else "",
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
    if partner:
        with SessionLocal() as db:
            labs = get_lab_results_for_partner(db, partner.id)
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
            key="partner_nontrop_lab_editor",
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
            key="partner_trep_lab_editor",
            use_container_width=True,
            hide_index=True,
        )

    st.divider()

    st.divider()
    with st.expander("📋 Exposure & Relationship Details", expanded=False):
        st.subheader("Exposure Window")
        exposure_first = st.date_input(
            "First exposure to OP",
            value=relationship.exposure_first_date if relationship else None,
            format="MM/DD/YYYY",
        )
        exposure_last = st.date_input(
            "Last exposure to OP",
            value=relationship.exposure_last_date if relationship else None,
            format="MM/DD/YYYY",
        )

        _BODY_PART_DISPLAY = ["Anal / Rectal", "Oral", "Vaginal", "Penile"]
        _BODY_PART_VALUE = ["anus", "mouth", "vagina", "penis"]

        current_sex = []
        if relationship and relationship.op_body_parts:
            try:
                stored = json.loads(relationship.op_body_parts)
                current_sex = [
                    _BODY_PART_DISPLAY[_BODY_PART_VALUE.index(s)]
                    for s in stored
                    if s in _BODY_PART_VALUE
                ]
            except (json.JSONDecodeError, ValueError):
                pass

        exposure_modalities_selected = st.multiselect(
            "Sex type(s) reported (OP's body parts)",
            options=_BODY_PART_DISPLAY,
            default=current_sex,
        )

        st.divider()
        st.subheader("Relationship Evidence")
        st.caption(
            "Multiple reports from different sources (e.g. OP, Partner) regarding their relationship."
        )

        # Load existing reports if relationship exists
        if relationship:
            with SessionLocal() as db:
                reps = get_reports_for_relationship(db, relationship.id)
                existing_reports = [
                    {
                        "id": r.id,
                        "Reporter": r.reporter,
                        "First Exposure": r.exposure_first_date,
                        "Last Exposure": r.exposure_last_date,
                        "Exposure Modalities": r.exposure_modalities,
                    }
                    for r in reps
                ]
        else:
            existing_reports = []

        report_df_base = pd.DataFrame(
            existing_reports,
            columns=[
                "id",
                "Reporter",
                "First Exposure",
                "Last Exposure",
                "Exposure Modalities",
            ],
        )

        edited_report_df = st.data_editor(
            report_df_base,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Reporter": st.column_config.SelectboxColumn(
                    "Reporter",
                    options=["OP", "Partner", "Third Party", "Other"],
                    required=True,
                ),
                "First Exposure": st.column_config.DateColumn("First Exposure"),
                "Last Exposure": st.column_config.DateColumn("Last Exposure"),
                "Exposure Modalities": st.column_config.TextColumn(
                    "Exposure Modalities (JSON array)"
                ),
            },
            key="relationship_report_editor",
            use_container_width=True,
            hide_index=True,
        )

    # --- Buttons ---
    col_b1, col_b2, col_b3, _ = st.columns([1, 1, 1, 3])

    with col_b1:
        submitted = st.form_submit_button(
            "💾  Save" if partner else "➕  Add partner",
            type="primary",
            use_container_width=True,
        )
    with col_b2:
        add_another = st.form_submit_button(
            "💾  Save + add another",
            use_container_width=True,
        )
    with col_b3:
        go_map = st.form_submit_button(
            "MAP sheet →",
            use_container_width=True,
        )

# ---------------------------------------------------------------------------
# Save logic
# ---------------------------------------------------------------------------


if submitted or add_another or go_map:
    errors = validate_partner_form(partner_name)
    if errors:
        for e in errors:
            st.error(e)
    else:
        payload = dict(
            name=partner_name.strip(),
            reason_for_exam=val_or_none(reason_for_exam),
            treatment_date=treatment_date if treatment_date else None,
            treatment=val_or_none(treatment),
            historical_primary_chancre=historical_primary_chancre,
            historical_primary_date=historical_primary_date
            if historical_primary_date
            else None,
            medical_info=val_or_none(medical_info),
        )

        with write_db() as db:
            if partner:
                saved = update_partner(db, partner.id, **payload)
                partner_id = saved.id
                st.success(f"Partner {saved.partner_number} updated — {saved.name}")
                # Update or create the relationship record
                op_parts = [
                    _BODY_PART_VALUE[_BODY_PART_DISPLAY.index(s)]
                    for s in exposure_modalities_selected
                    if s in _BODY_PART_DISPLAY
                ]
                if relationship:
                    relationship = update_case_partner_relationship(
                        db,
                        relationship.id,
                        exposure_first_date=exposure_first,
                        exposure_last_date=exposure_last,
                        op_body_parts=op_parts,
                    )
                else:
                    relationship = create_case_partner_relationship(
                        db,
                        case_id,
                        partner.id,
                        exposure_first_date=exposure_first,
                        exposure_last_date=exposure_last,
                        op_body_parts=op_parts,
                    )
            else:
                saved = create_partner(
                    db,
                    case_id=case_id,
                    partner_number=next_number,
                    **payload,
                )
                st.success(f"Partner {saved.partner_number} added — {saved.name}")
                set_active_partner_id(saved.id)
                partner_id = saved.id
                op_parts = [
                    _BODY_PART_VALUE[_BODY_PART_DISPLAY.index(s)]
                    for s in exposure_modalities_selected
                    if s in _BODY_PART_DISPLAY
                ]
                relationship = create_case_partner_relationship(
                    db,
                    case_id,
                    saved.id,
                    exposure_first_date=exposure_first,
                    exposure_last_date=exposure_last,
                    op_body_parts=op_parts,
                )

            # Sync Relationship Reports
            if relationship:
                current_report_ids = [
                    r.id for r in get_reports_for_relationship(db, relationship.id)
                ]
                editor_report_ids = [
                    int(row["id"])
                    for row in edited_report_df.to_dict("records")
                    if pd.notna(row.get("id"))
                ]

                for rid in current_report_ids:
                    if rid not in editor_report_ids:
                        delete_relationship_report(db, rid)

                for row in edited_report_df.to_dict("records"):
                    # Skip completely empty rows
                    if pd.isna(row.get("Reporter")) or not row.get("Reporter"):
                        continue

                    if pd.notna(row.get("id")):
                        update_relationship_report(
                            db,
                            int(row["id"]),
                            reporter=row["Reporter"],
                            exposure_first_date=row["First Exposure"],
                            exposure_last_date=row["Last Exposure"],
                            exposure_modalities=row["Exposure Modalities"],
                        )
                    else:
                        create_relationship_report(
                            db,
                            relationship_id=relationship.id,
                            reporter=row["Reporter"],
                            exposure_first_date=row["First Exposure"],
                            exposure_last_date=row["Last Exposure"],
                            exposure_modalities=row["Exposure Modalities"],
                        )

            # Sync Lab Results — two editors (non-treponemal + treponemal)
            current_lab_ids = [
                l.id for l in get_lab_results_for_partner(db, partner_id)
            ]
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
                        partner_id=partner_id,
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
                        partner_id=partner_id,
                        titer=None,
                        result=row.get("Result") or None,
                    )

            # Sync Symptom Entries
            current_symptom_ids = [
                s.id for s in get_symptoms_for_partner(db, partner_id)
            ]
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
                        partner_id=partner_id,
                    )

        if go_map:
            st.switch_page("pages/04_map_sheet.py")
        elif add_another:
            # Clear partner selection so form resets to new
            set_active_partner_id(None)
            st.rerun()
        else:
            st.rerun()

# ---------------------------------------------------------------------------
# Partner roster — all partners for this case shown below the form
# ---------------------------------------------------------------------------

if partners:
    st.divider()
    st.subheader("Partner roster")

    roster_rows = []
    for p in partners:
        roster_rows.append(
            {
                "#": p.partner_number,
                "Name": p.name or "—",
                "Reason": p.reason_for_exam or "—",
                "Treatment date": str(p.treatment_date) if p.treatment_date else "—",
                "Treatment": p.treatment or "—",
            }
        )

    df = pd.DataFrame(roster_rows)

    # Highlight partners with no treatment date
    def highlight_untreated(row):
        if row["Treatment date"] == "—":
            return ["background-color: #fff8e1"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(highlight_untreated, axis=1),
        use_container_width=True,
        hide_index=True,
    )
