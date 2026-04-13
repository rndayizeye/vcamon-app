"""
app/pages/07_ghosting_analysis.py

Ghosting Analysis page — implements the VCA ghosting methodology
from the NCSDDC / Marion County Public Health training (2022).

Workflow:
  1. User selects a partner to analyse against the OP.
  2. Page pulls symptoms, exposure dates, and treatment data from the DB.
  3. Calls run_ghosting_analysis() from app/utils/clinical.py.
  4. Displays the step-by-step log and verdict.
  5. User confirms which ghosted lesion(s) to save back to the database.
  6. Saved lesions appear in the network graph and timeline pages.
"""

import streamlit as st
import pandas as pd
from datetime import date

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_partner_by_id,
    create_ghosting,
    get_ghostings,
    delete_ghosting,
)
from app.db.models import GhostingType
from app.utils.session_state import (
    init_session_state,
    get_active_case_id,
    set_active_partner_id,
)
from app.utils.clinical import (
    Symptom,
    Exposure,
    run_ghosting_analysis,
    INCUBATION, PRIMARY, LATENCY, SECONDARY,
    INTERVIEW_PERIOD_PRIMARY_DAYS,
    INTERVIEW_PERIOD_SECONDARY_DAYS,
    symptom_rank,
)

st.set_page_config(page_title="Ghosting Analysis — VCA Monitor", layout="wide")
init_session_state()


# ---------------------------------------------------------------------------
# Helpers — convert ORM objects to clinical dataclasses
# ---------------------------------------------------------------------------

def orm_symptoms_to_clinical(partner_or_case) -> list[Symptom]:
    """
    Convert symptom strings stored on the ORM model into Symptom dataclasses.
    The partner/case model stores symptom + lesion type info across several fields;
    we assemble what we can from the fields available.
    """
    symptoms = []

    # Primary symptom inferred from lesion_type + treatment_date
    if hasattr(partner_or_case, "lesion_type") and partner_or_case.lesion_type:
        lesion = partner_or_case.lesion_type
        onset = partner_or_case.treatment_date  # best proxy if no separate onset field
        if onset:
            s_type = _lesion_to_symptom_type(lesion)
            symptoms.append(Symptom(type=s_type, onset=onset, duration_days=0))

    # Secondary symptom inferred from symptom field
    if hasattr(partner_or_case, "symptom") and partner_or_case.symptom:
        sym = partner_or_case.symptom
        # Symptoms like "Rash", "PP Rash", "GB Rash", "C-lata", "Alopecia"
        # are all secondary manifestations
        if _is_secondary(sym):
            onset = partner_or_case.treatment_date
            if onset:
                symptoms.append(
                    Symptom(type="Secondary Rash/Lesions", onset=onset, duration_days=0)
                )

    return symptoms


def _lesion_to_symptom_type(lesion: str) -> str:
    """Map a LesionType enum value to a ghosting hierarchy symptom type."""
    # All lesion types in our model represent primary chancres
    return "Primary Chancre"


def _is_secondary(symptom_str: str) -> bool:
    secondary_indicators = ["rash", "alopecia", "c-lata", "lata"]
    return any(ind in symptom_str.lower() for ind in secondary_indicators)


def orm_to_exposure(partner) -> Exposure | None:
    """Build an Exposure from partner fields (if populated)."""
    first = getattr(partner, "first_exposure", None)
    last  = getattr(partner, "last_exposure",  None)
    sex   = getattr(partner, "sex_types",       None)

    if not first or not last:
        return None

    sex_list = []
    if sex:
        import json
        try:
            sex_list = json.loads(sex) if isinstance(sex, str) else list(sex)
        except Exception:
            sex_list = []

    return Exposure(first=first, last=last, sex_types=sex_list)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Active case")

    case_id = get_active_case_id()
    if not case_id:
        st.warning("No case selected.")
        if st.button("← Dashboard", use_container_width=True):
            st.switch_page("pages/01_dashboard.py")
        st.stop()

    with SessionLocal() as db:
        case    = get_case_by_id(db, case_id)
        partners = get_partners_for_case(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")
    st.divider()

    if st.button("← MAP sheet", use_container_width=True):
        st.switch_page("pages/04_map_sheet.py")
    if st.button("Network graph →", use_container_width=True):
        st.switch_page("pages/05_network_graph.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ---------------------------------------------------------------------------
# Page header + quick reference
# ---------------------------------------------------------------------------

st.title("Ghosting Analysis")
st.caption(
    f"Case #{case.id} — {case.patient_name}  |  "
    "Based on NCSDDC Visual Case Analysis methodology (2022)"
)

with st.expander("Clinical reference — syphilis natural history durations", expanded=False):
    ref_data = {
        "Phase": ["Incubation", "Primary chancre", "Latency", "Secondary"],
        "Min":   [f"{INCUBATION['min']}d", f"{PRIMARY['min']}d", f"{LATENCY['min']}d", f"{SECONDARY['min']}d"],
        "Avg":   [f"{INCUBATION['avg']}d", f"{PRIMARY['avg']}d", f"{LATENCY['avg']}d", f"{SECONDARY['avg']}d"],
        "Max":   [f"{INCUBATION['max']}d", f"{PRIMARY['max']}d", f"{LATENCY['max']}d", f"{SECONDARY['max']}d"],
    }
    st.dataframe(pd.DataFrame(ref_data), use_container_width=True, hide_index=True)
    st.caption(
        f"Interview period — Primary: {INTERVIEW_PERIOD_PRIMARY_DAYS} days before chancre onset.  "
        f"Secondary: {INTERVIEW_PERIOD_SECONDARY_DAYS} days before secondary onset."
    )

st.divider()

# ---------------------------------------------------------------------------
# Step 1 — Partner selection
# ---------------------------------------------------------------------------

st.subheader("Step 1 — Select partner to analyse")

if not partners:
    st.info("No partners on file. Add partners on the Partner Form first.")
    st.stop()

partner_options = {p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}" for p in partners}

selected_partner_id = st.selectbox(
    "Compare OP against:",
    options=list(partner_options.keys()),
    format_func=lambda k: partner_options[k],
)

with SessionLocal() as db:
    selected_partner = get_partner_by_id(db, selected_partner_id)

if not selected_partner:
    st.error("Partner not found.")
    st.stop()

# ---------------------------------------------------------------------------
# Symptom override inputs
# (The DB stores limited symptom data; let the user add/confirm here)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Step 2 — Confirm symptoms")
st.caption(
    "The form pre-fills from saved data. Adjust as needed before running analysis. "
    "Symptom hierarchy: Primary Chancre > Historical Primary > Ghosted Primary > Secondary."
)

col_op, col_partner = st.columns(2)

with col_op:
    st.markdown(f"**OP — {case.patient_name}**")
    op_sym_type = st.selectbox(
        "OP symptom type",
        options=["Primary Chancre", "Historical Primary", "Ghosted Primary",
                 "Secondary Rash/Lesions", "None"],
        key="op_sym_type",
        index=0 if case.lesion_type else 3,
    )
    op_sym_onset = st.date_input(
        "OP symptom onset",
        value=case.treatment_date or date.today(),
        key="op_sym_onset",
        format="MM/DD/YYYY",
    )
    op_sym_dur = st.number_input(
        "OP symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0,
        key="op_sym_dur",
    )
    st.caption("Exposure period (OP's account)")
    op_exp_first = st.date_input("OP first exposure", value=None, key="op_exp_first", format="MM/DD/YYYY")
    op_exp_last  = st.date_input("OP last exposure",  value=None, key="op_exp_last",  format="MM/DD/YYYY")
    op_sex_types = st.multiselect(
        "Sex type(s) reported by OP",
        options=["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"],
        key="op_sex",
    )
    op_treatment = st.date_input(
        "OP treatment date",
        value=case.treatment_date,
        key="op_treat",
        format="MM/DD/YYYY",
    )

with col_partner:
    pname = selected_partner.name or f"Partner {selected_partner.partner_number}"
    st.markdown(f"**Partner — {pname}**")
    p_sym_type = st.selectbox(
        "Partner symptom type",
        options=["Primary Chancre", "Historical Primary", "Ghosted Primary",
                 "Secondary Rash/Lesions", "None"],
        key="p_sym_type",
        index=0 if selected_partner.lesion_type else 4,
    )
    p_sym_onset = st.date_input(
        "Partner symptom onset",
        value=selected_partner.treatment_date or date.today(),
        key="p_sym_onset",
        format="MM/DD/YYYY",
    )
    p_sym_dur = st.number_input(
        "Partner symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0,
        key="p_sym_dur",
    )
    st.caption("Exposure period (partner's account)")
    p_exp_first = st.date_input("Partner first exposure", value=None, key="p_exp_first", format="MM/DD/YYYY")
    p_exp_last  = st.date_input("Partner last exposure",  value=None, key="p_exp_last",  format="MM/DD/YYYY")
    p_sex_types = st.multiselect(
        "Sex type(s) reported by partner",
        options=["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"],
        key="p_sex",
    )
    p_treatment = st.date_input(
        "Partner treatment date",
        value=selected_partner.treatment_date,
        key="p_treat",
        format="MM/DD/YYYY",
    )

# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------

st.divider()

run_btn = st.button("Run ghosting analysis", type="primary", use_container_width=False)

if run_btn:
    # Build clinical objects
    op_symptoms = []
    if op_sym_type != "None":
        op_symptoms = [Symptom(type=op_sym_type, onset=op_sym_onset, duration_days=int(op_sym_dur))]

    partner_symptoms = []
    if p_sym_type != "None":
        partner_symptoms = [Symptom(type=p_sym_type, onset=p_sym_onset, duration_days=int(p_sym_dur))]

    op_exposure = (
        Exposure(first=op_exp_first, last=op_exp_last, sex_types=op_sex_types)
        if op_exp_first and op_exp_last else None
    )
    partner_exposure = (
        Exposure(first=p_exp_first, last=p_exp_last, sex_types=p_sex_types)
        if p_exp_first and p_exp_last else None
    )

    try:
        result = run_ghosting_analysis(
            op_name=case.patient_name,
            op_symptoms=op_symptoms,
            op_exposure=op_exposure,
            op_treatment_date=op_treatment,
            partner_name=pname,
            partner_symptoms=partner_symptoms,
            partner_exposure=partner_exposure,
            partner_treatment_date=p_treatment,
        )
        st.session_state["ghosting_result"] = result
    except ValueError as e:
        st.error(f"Cannot run analysis: {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

if "ghosting_result" in st.session_state:
    result = st.session_state["ghosting_result"]

    st.divider()
    st.subheader("Analysis results")

    # Verdict banner
    verdict = result.verdict
    if "SOURCE" in verdict and "UNRELATED" not in verdict and "AMBIGUOUS" not in verdict:
        st.success(verdict)
    elif "SPREAD" in verdict and "UNRELATED" not in verdict:
        st.info(verdict)
    elif "AMBIGUOUS" in verdict:
        st.warning(verdict)
    else:
        st.error(verdict)

    # Ghosted lesion dates
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Ghosted source onset",  str(result.ghosted_source.onset))
        st.metric("Ghosted source end",    str(result.ghosted_source.end))
        st.caption(f"Assigned to: {result.ghosted_source.assigned_to}")
    with col2:
        st.metric("Ghosted spread onset",  str(result.ghosted_spread.onset))
        st.metric("Ghosted spread end",    str(result.ghosted_spread.end))
        st.caption(f"Assigned to: {result.ghosted_spread.assigned_to}")

    # Criteria tables
    st.subheader("Criteria evaluation")
    tab_src, tab_spr = st.tabs(["Source scenario", "Spread scenario"])

    def render_criteria_table(criteria: dict):
        rows = []
        for k, v in criteria.items():
            icon = {"pass": "✓", "fail": "✗", "warn": "⚠", "na": "—"}.get(v["status"], "?")
            color = {"pass": "green", "fail": "red", "warn": "orange", "na": "gray"}.get(v["status"], "")
            rows.append({"Criterion": k.replace("_", " ").title(), "Result": icon, "Detail": v["detail"]})
        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Criterion": st.column_config.TextColumn(width="medium"),
                "Result":    st.column_config.TextColumn(width="small"),
            },
        )

    with tab_src:
        render_criteria_table(result.criteria["source"])
    with tab_spr:
        render_criteria_table(result.criteria["spread"])

    # Step-by-step log
    with st.expander("Step-by-step analysis log", expanded=False):
        st.code("\n".join(result.log), language=None)

    # ---------------------------------------------------------------------------
    # Save ghosted lesions to DB
    # ---------------------------------------------------------------------------

    st.divider()
    st.subheader("Save ghosted lesions")
    st.caption(
        "Saved lesions will appear in the network graph and timeline. "
        "Select which lesions to save based on your clinical judgment."
    )

    save_source = st.checkbox(
        f"Save ghosted SOURCE lesion "
        f"({result.ghosted_source.onset} → {result.ghosted_source.end}) "
        f"to {result.ghosted_source.assigned_to}",
        value=True,
    )
    save_spread = st.checkbox(
        f"Save ghosted SPREAD lesion "
        f"({result.ghosted_spread.onset} → {result.ghosted_spread.end}) "
        f"to {result.ghosted_spread.assigned_to}",
        value=True,
    )

    if st.button("💾  Save selected lesions", type="primary"):
        # Determine which party (OP or partner) is P2
        p2_partner_id = selected_partner_id if result.ghosted_source.assigned_to == "partner" else None

        saved = []
        with SessionLocal() as db:
            if save_source:
                create_ghosting(
                    db,
                    case_id=case_id,
                    ghosting_type=GhostingType.SOURCE.value,
                    from_ref="OP" if result.p1_name == case.patient_name else str(selected_partner.partner_number),
                    to_ref=str(selected_partner.partner_number) if result.ghosted_source.assigned_to == "partner" else "OP",
                    notes=(
                        f"Ghosted source: {result.ghosted_source.onset} → {result.ghosted_source.end}. "
                        f"Derived from: {result.ghosted_source.derived_from_symptom}. "
                        f"Verdict: {result.verdict}"
                    ),
                )
                saved.append("ghosted source")

            if save_spread:
                create_ghosting(
                    db,
                    case_id=case_id,
                    ghosting_type=GhostingType.SPREAD.value,
                    from_ref="OP" if result.p1_name == case.patient_name else str(selected_partner.partner_number),
                    to_ref=str(selected_partner.partner_number) if result.ghosted_spread.assigned_to == "partner" else "OP",
                    notes=(
                        f"Ghosted spread: {result.ghosted_spread.onset} → {result.ghosted_spread.end}. "
                        f"Derived from: {result.ghosted_spread.derived_from_symptom}. "
                        f"Verdict: {result.verdict}"
                    ),
                )
                saved.append("ghosted spread")

        if saved:
            st.success(f"Saved: {', '.join(saved)}.")
            del st.session_state["ghosting_result"]
            st.rerun()

# ---------------------------------------------------------------------------
# Existing ghosting records for this case
# ---------------------------------------------------------------------------

with SessionLocal() as db:
    ghostings = get_ghostings(db, case_id)

if ghostings:
    st.divider()
    st.subheader("Saved ghosting records")

    partner_ref_map = {str(p.partner_number): p.name or f"Partner {p.partner_number}" for p in partners}
    partner_ref_map["OP"] = case.patient_name

    rows = []
    for g in ghostings:
        rows.append({
            "ID":    g.id,
            "Type":  g.ghosting_type,
            "From":  partner_ref_map.get(g.from_ref, g.from_ref or "—"),
            "To":    partner_ref_map.get(g.to_ref,   g.to_ref   or "—"),
            "Notes": (g.notes or "")[:80],
        })

    st.dataframe(
        pd.DataFrame(rows).drop(columns=["ID"]),
        use_container_width=True,
        hide_index=True,
    )

    # Delete a record
    del_options = {g.id: f"{g.ghosting_type} | {partner_ref_map.get(g.from_ref, g.from_ref or '?')} → {partner_ref_map.get(g.to_ref, g.to_ref or '?')}" for g in ghostings}
    col_del1, col_del2 = st.columns([3, 1])
    with col_del1:
        del_id = st.selectbox(
            "Remove record",
            options=list(del_options.keys()),
            format_func=lambda k: del_options[k],
            label_visibility="collapsed",
        )
    with col_del2:
        if st.button("✕  Remove", use_container_width=True):
            with SessionLocal() as db:
                delete_ghosting(db, del_id)
            st.success("Record removed.")
            st.rerun()
