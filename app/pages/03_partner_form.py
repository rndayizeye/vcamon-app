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

import streamlit as st
import pandas as pd

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
    create_case_partner_relationship,
    create_lab_result_entry,
    create_partner,
    create_relationship_report,
    delete_lab_result_entry,
    delete_relationship_report,
    get_case_by_id,
    get_case_partner_relationship,
    get_lab_results_for_partner,
    get_partner_by_id,
    get_partners_for_case,
    get_reports_for_relationship,
    update_case_partner_relationship,
    update_lab_result_entry,
    update_partner,
    update_relationship_report,
    get_symptoms_for_partner,
    delete_symptom_entry,
    update_symptom_entry,
    create_symptom_entry,
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
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")

    st.divider()
    st.subheader("Partners")

    # Partner switcher
    partner_options = {0: "➕  New partner"}
    partner_options.update({
        p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}"
        for p in partners
    })

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
next_number = (max((p.partner_number for p in partners), default=0) + 1)

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
    st.caption(
        f"Adding Partner {next_number} to "
        f"case #{case.id} — {case.patient_name}"
    )

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
            value=partner.treatment_date if partner and partner.treatment_date else None,
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
        st.caption("Add and manage all symptoms. Click a cell to edit.")
        
        # Load existing symptoms for the partner
        if partner:
            with SessionLocal() as db:
                symptoms = get_symptoms_for_partner(db, partner.id)
                existing_symptoms = [{
                    "id": s.id,
                    "Type": s.symptom_type,
                    "Classification": s.classification or "",
                    "Onset Date": s.onset_date,
                    "Duration": s.duration_days,
                    "Ongoing": s.ongoing,
                } for s in symptoms]
        else:
            existing_symptoms = []

        # Create DataFrame with proper schema
        symptom_df_base = pd.DataFrame(
            existing_symptoms,
            columns=["id", "Type", "Classification", "Onset Date", "Duration", "Ongoing"]
        )

        edited_symptom_df = st.data_editor(
            symptom_df_base,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Type": st.column_config.SelectboxColumn(
                    "Type", 
                    options=enum_options(LesionType) + enum_options(Symptom),
                    required=True
                ),
                "Onset Date": st.column_config.DateColumn("Onset Date"),
                "Duration": st.column_config.NumberColumn("Duration (Days)"),
                "Ongoing": st.column_config.CheckboxColumn("Ongoing"),
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
        index=[False, True].index(partner.historical_primary_chancre) if partner and partner.historical_primary_chancre is not None else 0,
        help="Required for secondary syphilis diagnosis."
    )

    historical_primary_date = None
    if historical_primary_chancre:
        historical_primary_date = st.date_input(
            "Date of primary chancre",
            value=partner.historical_primary_date if partner else None,
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            format="MM/DD/YYYY",
            help="When did the primary chancre first appear?"
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=partner.medical_info or "" if partner else "",
        height=100,
        placeholder="Relevant medical history, medications, conditions...",
    )

    st.divider()
    st.subheader("Lab results")
    st.caption("Manage all laboratory results. Use the table to add, edit, or remove entries.")
    
    # Load existing lab results for the partner
    if partner:
        with SessionLocal() as db:
            labs = get_lab_results_for_partner(db, partner.id)
            existing_labs = [{
                "id": l.id,
                "Category": l.test_category,
                "Test Type": l.test_type,
                "Titer": l.titer or "",
                "Result": l.result or "",
                "Date": l.collection_date,
            } for l in labs]
    else:
        existing_labs = []

    # Create DataFrame with proper schema
    lab_df_base = pd.DataFrame(
        existing_labs,
        columns=["id", "Category", "Test Type", "Titer", "Result", "Date"]
    )

    edited_lab_df = st.data_editor(
        lab_df_base,
        num_rows="dynamic",
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
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
        key="partner_lab_editor",
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.divider()
    with st.expander("🔬 Clinical Details (Optional - for VCA analysis)", expanded=False):
        st.caption("Complete these fields to streamline ghosting analysis")

        col_sym, col_exp = st.columns(2)

        with col_sym:
            st.subheader("Symptom Details")
            symptom_onset = st.date_input(
                "Symptom onset date",
                value=partner.symptom_onset_date if partner else None,
                help="When did this symptom first appear?",
                format="MM/DD/YYYY",
            )
            symptom_duration = st.number_input(
                "Symptom duration (days, 0=unknown)",
                min_value=0, max_value=90,
                value=partner.symptom_duration_days or 0 if partner else 0,
            )

        with col_exp:
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

        sex_types_display = ["Anal", "Oral", "Vaginal", "Penile", "Rectal"]
        sex_types_value = ["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"]

        current_sex = []
        if relationship and relationship.sex_types:
            try:
                stored = json.loads(relationship.sex_types)
                current_sex = [
                    sex_types_display[sex_types_value.index(s)]
                    for s in stored
                    if s in sex_types_value
                ]
            except json.JSONDecodeError:
                pass
        elif partner and hasattr(partner, 'sex_types') and partner.sex_types: 
            try:
                stored = json.loads(partner.sex_types)
                current_sex = [
                    sex_types_display[sex_types_value.index(s)]
                    for s in stored
                    if s in sex_types_value
                ]
            except json.JSONDecodeError:
                pass

        sex_types_selected = st.multiselect(
            "Sex type(s) reported",
            options=sex_types_display,
            default=current_sex,
        )

        st.divider()
        st.subheader("Relationship Evidence")
        st.caption("Multiple reports from different sources (e.g. OP, Partner) regarding their relationship.")
        
        # Load existing reports if relationship exists
        if relationship:
            with SessionLocal() as db:
                reps = get_reports_for_relationship(db, relationship.id)
                existing_reports = [{
                    "id": r.id,
                    "Reporter": r.reporter,
                    "First Exposure": r.exposure_first_date,
                    "Last Exposure": r.exposure_last_date,
                    "Sex Types": r.sex_types,
                } for r in reps]
        else:
            existing_reports = []
        
        report_df_base = pd.DataFrame(
            existing_reports,
            columns=["id", "Reporter", "First Exposure", "Last Exposure", "Sex Types"]
        )

        edited_report_df = st.data_editor(
            report_df_base,
            num_rows="dynamic",
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "Reporter": st.column_config.SelectboxColumn(
                    "Reporter",
                    options=["OP", "Partner", "Third Party", "Other"],
                    required=True
                ),
                "First Exposure": st.column_config.DateColumn("First Exposure"),
                "Last Exposure": st.column_config.DateColumn("Last Exposure"),
                "Sex Types": st.column_config.TextColumn("Sex Types (JSON array)"),
            },
            key="relationship_report_editor",
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.subheader("Lab Dates")
        st.info("Lab dates are now managed in the 'Lab results' section above.")

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
            if partner:
                saved = update_partner(db, partner.id, **payload)
                partner_id = saved.id
                st.success(
                    f"Partner {saved.partner_number} updated — {saved.name}"
                )
                # Update or create the relationship record
                sex_types_json = json.dumps([sex_types_value[sex_types_display.index(s)] 
                                             for s in sex_types_selected]) if sex_types_selected else None
                if relationship:
                    relationship = update_case_partner_relationship(
                        db, relationship.id,
                        exposure_first_date=exposure_first,
                        exposure_last_date=exposure_last,
                        sex_types=sex_types_json
                    )
                else:
                    relationship = create_case_partner_relationship(
                        db, case_id, partner.id,
                        exposure_first_date=exposure_first,
                        exposure_last_date=exposure_last,
                        sex_types=sex_types_json
                    )
            else:
                saved = create_partner(
                    db,
                    case_id=case_id,
                    partner_number=next_number,
                    **payload,
                )
                st.success(
                    f"Partner {saved.partner_number} added — {saved.name}"
                )
                set_active_partner_id(saved.id)
                partner_id = saved.id
                # Create the relationship record for the new partner
                sex_types_json = json.dumps([sex_types_value[sex_types_display.index(s)] 
                                             for s in sex_types_selected]) if sex_types_selected else None
                relationship = create_case_partner_relationship(
                    db, case_id, saved.id,
                    exposure_first_date=exposure_first,
                    exposure_last_date=exposure_last,
                    sex_types=sex_types_json
                )

            # Sync Relationship Reports
            if relationship:
                current_report_ids = [r.id for r in get_reports_for_relationship(db, relationship.id)]
                editor_report_ids = [
                    int(row["id"]) for row in edited_report_df.to_dict('records') 
                    if pd.notna(row.get("id"))
                ]
                
                for rid in current_report_ids:
                    if rid not in editor_report_ids:
                        delete_relationship_report(db, rid)
                
                for row in edited_report_df.to_dict('records'):
                    # Skip completely empty rows
                    if pd.isna(row.get("Reporter")) or not row.get("Reporter"):
                        continue

                    if pd.notna(row.get("id")):
                        update_relationship_report(
                            db, int(row["id"]),
                            reporter=row["Reporter"],
                            exposure_first_date=row["First Exposure"],
                            exposure_last_date=row["Last Exposure"],
                            sex_types=row["Sex Types"]
                        )
                    else:
                        create_relationship_report(
                            db,
                            relationship_id=relationship.id,
                            reporter=row["Reporter"],
                            exposure_first_date=row["First Exposure"],
                            exposure_last_date=row["Last Exposure"],
                            sex_types=row["Sex Types"]
                        )

            # Sync Lab Results
            current_lab_ids = [l.id for l in get_lab_results_for_partner(db, partner_id)]
            editor_lab_ids = [
                int(row["id"]) for row in edited_lab_df.to_dict('records') 
                if pd.notna(row.get("id"))
            ]
            
            for lid in current_lab_ids:
                if lid not in editor_lab_ids:
                    delete_lab_result_entry(db, lid)
            
            for row in edited_lab_df.to_dict('records'):
                # Skip completely empty rows
                if pd.isna(row.get("Category")) or not row.get("Category"):
                    continue

                if pd.notna(row.get("id")):
                    update_lab_result_entry(
                        db, int(row["id"]),
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
                        partner_id=partner_id,
                        titer=row["Titer"],
                        result=row["Result"]
                    )

            # Sync Symptom Entries
            current_symptom_ids = [s.id for s in get_symptoms_for_partner(db, partner_id)]
            editor_symptom_ids = [
                int(row["id"]) for row in edited_symptom_df.to_dict('records') 
                if pd.notna(row.get("id"))
            ]

            # Delete removed symptoms
            for sid in current_symptom_ids:
                if sid not in editor_symptom_ids:
                    delete_symptom_entry(db, sid)

            # Upsert symptoms
            for row in edited_symptom_df.to_dict('records'):
                # Skip completely empty rows
                if pd.isna(row.get("Type")) or not row.get("Type"):
                    continue
                    
                if pd.notna(row.get("id")):
                    # Update existing
                    update_symptom_entry(
                        db, int(row["id"]),
                        symptom_type=row["Type"],
                        classification=_get_symptom_classification(row["Type"]),
                        onset_date=row.get("Onset Date"),
                        duration_days=int(row["Duration"]) if pd.notna(row.get("Duration")) else None,
                        ongoing=bool(row.get("Ongoing", False))
                    )
                else:
                    # Create new
                    create_symptom_entry(
                        db,
                        symptom_type=row["Type"],
                        classification=row.get("Classification") or None,
                        onset_date=row.get("Onset Date"),
                        duration_days=int(row["Duration"]) if pd.notna(row.get("Duration")) else None,
                        ongoing=bool(row.get("Ongoing", False)),
                        partner_id=partner_id
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
        roster_rows.append({
            "#":              p.partner_number,
            "Name":           p.name or "—",
            "Reason":         p.reason_for_exam or "—",
            "Treatment date": str(p.treatment_date) if p.treatment_date else "—",
            "Lab 1":          p.lab_1 or "—",
            "Lab 2":          p.lab_2 or "—",
            "Treatment":      p.treatment or "—",
        })

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
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
        },
    )

    # Quick-select buttons to jump to a partner
    st.caption("Click a partner below to load them into the form:")
    btn_cols = st.columns(min(len(partners), 6))
    for i, p in enumerate(partners[:6]):
        with btn_cols[i]:
            label = f"P{p.partner_number} — {(p.name or 'Unnamed')[:12]}"
            if st.button(label, key=f"quick_{p.id}", use_container_width=True):
                set_active_partner_id(p.id)
                st.rerun()
s=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn("#", width="small"),
        },
    )

    # Quick-select buttons to jump to a partner
    st.caption("Click a partner below to load them into the form:")
    btn_cols = st.columns(min(len(partners), 6))
    for i, p in enumerate(partners[:6]):
        with btn_cols[i]:
            label = f"P{p.partner_number} — {(p.name or 'Unnamed')[:12]}"
            if st.button(label, key=f"quick_{p.id}", use_container_width=True):
                set_active_partner_id(p.id)
                st.rerun()
