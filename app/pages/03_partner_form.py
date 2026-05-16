"""
app/pages/03_partner_form.py

Partner form — add and edit contact partners for the active case.
Each case can have multiple partners. Partners share the same
field structure as the OP form (reason for exam, labs, treatment).

Navigation flow:
  Dashboard → OP Form → [Partner Form] → MAP Sheet
"""

import streamlit as st
import json
from datetime import date

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_partner_by_id,
    create_partner,
    update_partner,
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
    get_active_partner_id,
    set_active_partner_id,
    require_password,
)
from app.utils.validators import validate_partner_form
from app.components.dropdowns import enum_options, val_or_none

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
        lesion_type = st.selectbox(
            "Lesion type",
            options=enum_options(LesionType),
            index=enum_options(LesionType).index(
                partner.lesion_type or "" if partner else ""
            ),
        )
        symptom = st.selectbox(
            "Symptom",
            options=enum_options(Symptom),
            index=enum_options(Symptom).index(
                partner.symptom or "" if partner else ""
            ),
        )

    medical_info = st.text_area(
        "Medical info on date treated",
        value=partner.medical_info or "" if partner else "",
        height=100,
        placeholder="Relevant medical history, medications, conditions...",
    )

    st.divider()

    # --- Lab results ---
    st.subheader("Lab results")
    st.caption("Lab 1 = RPR/VDRL titer · Lab 2 = Treponemal confirmatory · Lab 3 = free text")
    col5, col6, col7 = st.columns(3)

    with col5:
        lab_1 = st.selectbox(
            "Lab 1 — RPR / VDRL",
            options=enum_options(LabResult),
            index=enum_options(LabResult).index(
                partner.lab_1 or "" if partner else ""
            ),
        )
    with col6:
        lab_2 = st.selectbox(
            "Lab 2 — Treponemal",
            options=enum_options(TreponemalResult),
            index=enum_options(TreponemalResult).index(
                partner.lab_2 or "" if partner else ""
            ),
        )
    with col7:
        lab_3 = st.text_input(
            "Lab 3 — other",
            value=partner.lab_3 or "" if partner else "",
            placeholder="Drfd N/A, or free text",
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
                value=relationship.exposure_first_date if relationship else partner.exposure_first_date if partner else None,
                format="MM/DD/YYYY",
            )
            exposure_last = st.date_input(
                "Last exposure to OP",
                value=relationship.exposure_last_date if relationship else partner.exposure_last_date if partner else None,
                format="MM/DD/YYYY",
            )

            sex_types_display = ["Anal", "Oral", "Vaginal", "Penile", "Rectal"]
            sex_types_value = ["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"]

            import json
            current_sex = []
            if relationship and relationship.sex_types:
            try:
                stored = json.loads(relationship.sex_types)
                current_sex = [sex_types_display[sex_types_value.index(s)] 
                              for s in stored if s in sex_types_value]
            except:
                pass
            elif partner and partner.sex_types: # Fallback to partner's old data if no relationship yet
            try:
                stored = json.loads(partner.sex_types)
                current_sex = [sex_types_display[sex_types_value.index(s)] 
                              for s in stored if s in sex_types_value]
            except:
                pass

            sex_types_selected = st.multiselect(
            "Sex type(s) reported",
            options=sex_types_display,
            default=current_sex,
            )
        st.divider()
        st.subheader("Lab Dates")
        col_l1, col_l2, col_l3 = st.columns(3)

        with col_l1:
            lab_1_date = st.date_input(
                "Lab 1 date",
                value=partner.lab_1_date if partner else None,
                format="MM/DD/YYYY",
            )
        with col_l2:
            lab_2_date = st.date_input(
                "Lab 2 date",
                value=partner.lab_2_date if partner else None,
                format="MM/DD/YYYY",
            )
        with col_l3:
            lab_3_date = st.date_input(
                "Lab 3 date",
                value=partner.lab_3_date if partner else None,
                format="MM/DD/YYYY",
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
            lesion_type=val_or_none(lesion_type),
            symptom=val_or_none(symptom),
            medical_info=val_or_none(medical_info),
            lab_1=val_or_none(lab_1),
            lab_2=val_or_none(lab_2),
            lab_3=val_or_none(lab_3),
            symptom_onset_date=symptom_onset if symptom_onset else None,
            symptom_duration_days=symptom_duration if symptom_duration > 0 else None,
            lab_1_date=lab_1_date if lab_1_date else None,
            lab_2_date=lab_2_date if lab_2_date else None,
            lab_3_date=lab_3_date if lab_3_date else None,
        )

        with SessionLocal() as db:
            if partner:
                saved = update_partner(db, partner.id, **payload)
                st.success(
                    f"Partner {saved.partner_number} updated — {saved.name}"
                )
                # Update or create the relationship record
                sex_types_json = json.dumps([sex_types_value[sex_types_display.index(s)] 
                                             for s in sex_types_selected]) if sex_types_selected else None
                if relationship:
                    update_case_partner_relationship(
                        db, relationship.id,
                        exposure_first_date=exposure_first,
                        exposure_last_date=exposure_last,
                        sex_types=sex_types_json
                    )
                else:
                    create_case_partner_relationship(
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
                # Create the relationship record for the new partner
                sex_types_json = json.dumps([sex_types_value[sex_types_display.index(s)] 
                                             for s in sex_types_selected]) if sex_types_selected else None
                create_case_partner_relationship(
                    db, case_id, saved.id,
                    exposure_first_date=exposure_first,
                    exposure_last_date=exposure_last,
                    sex_types=sex_types_json
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

    import pandas as pd

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
