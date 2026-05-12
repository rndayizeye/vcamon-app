"""
app/pages/07_ghosting_analysis.py  (updated)

Ghosting Analysis page — VCA methodology with visual scenario diagrams.

After running the analysis the page shows:
  1. Verdict banner
  2. Side-by-side Plotly diagrams for SOURCE and SPREAD scenarios
  3. Criteria table for each scenario
  4. Step-by-step log
  5. Save controls
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
    require_password,
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
from app.utils.ghosting_plot import build_scenario_figure

st.set_page_config(page_title="Ghosting Analysis — VCA Monitor", layout="wide")
init_session_state()
require_password()


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
        case     = get_case_by_id(db, case_id)
        partners = get_partners_for_case(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")
    st.divider()

    if st.button("← MAP sheet", use_container_width=True):
        st.switch_page("pages/04_map_sheet.py")
    if st.button("VCA chart →", use_container_width=True):
        st.switch_page("pages/08_vca_chart.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ---------------------------------------------------------------------------
# Page header + reference table
# ---------------------------------------------------------------------------

st.title("Ghosting Analysis")
st.caption(
    f"Case #{case.id} — {case.patient_name}  |  "
    "NCSDDC Visual Case Analysis methodology (2022)"
)

with st.expander("Clinical reference — syphilis natural history durations", expanded=False):
    ref_data = {
        "Phase":   ["Incubation", "Primary chancre", "Latency", "Secondary"],
        "Min":     [f"{INCUBATION['min']}d", f"{PRIMARY['min']}d",
                    f"{LATENCY['min']}d",    f"{SECONDARY['min']}d"],
        "Avg":     [f"{INCUBATION['avg']}d", f"{PRIMARY['avg']}d",
                    f"{LATENCY['avg']}d",    f"{SECONDARY['avg']}d"],
        "Max":     [f"{INCUBATION['max']}d", f"{PRIMARY['max']}d",
                    f"{LATENCY['max']}d",    f"{SECONDARY['max']}d"],
    }
    st.dataframe(pd.DataFrame(ref_data), use_container_width=True, hide_index=True)
    st.caption(
        f"Interview period — Primary: {INTERVIEW_PERIOD_PRIMARY_DAYS} days before chancre onset.  "
        f"Secondary: {INTERVIEW_PERIOD_SECONDARY_DAYS} days before secondary onset."
    )

st.divider()

# ---------------------------------------------------------------------------
# Partner selection
# ---------------------------------------------------------------------------

st.subheader("Step 1 — Select partner")

if not partners:
    st.info("No partners on file. Add partners on the Partner Form first.")
    st.stop()

partner_options = {
    p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}"
    for p in partners
}

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

pname = selected_partner.name or f"Partner {selected_partner.partner_number}"

# ---------------------------------------------------------------------------
# Symptom + exposure inputs
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Step 2 — Confirm symptoms and exposure")
st.caption(
    "Adjust symptom and exposure data before running. "
    "Hierarchy: Primary Chancre > Historical Primary > Ghosted Primary > Secondary."
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
        key="op_sym_onset", format="MM/DD/YYYY",
    )
    op_sym_dur = st.number_input(
        "OP symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0, key="op_sym_dur",
    )
    st.caption("Exposure (OP's account)")
    op_exp_first = st.date_input("First exposure", value=None, key="op_exp_first", format="MM/DD/YYYY")
    op_exp_last  = st.date_input("Last exposure",  value=None, key="op_exp_last",  format="MM/DD/YYYY")
    op_sex_types = st.multiselect(
        "Sex type(s) reported by OP",
        options=["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"],
        key="op_sex",
    )
    op_treatment = st.date_input(
        "OP treatment date", value=case.treatment_date,
        key="op_treat", format="MM/DD/YYYY",
    )

with col_partner:
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
        key="p_sym_onset", format="MM/DD/YYYY",
    )
    p_sym_dur = st.number_input(
        "Partner symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0, key="p_sym_dur",
    )
    st.caption("Exposure (partner's account)")
    p_exp_first = st.date_input("First exposure", value=None, key="p_exp_first", format="MM/DD/YYYY")
    p_exp_last  = st.date_input("Last exposure",  value=None, key="p_exp_last",  format="MM/DD/YYYY")
    p_sex_types = st.multiselect(
        "Sex type(s) reported by partner",
        options=["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"],
        key="p_sex",
    )
    p_treatment = st.date_input(
        "Partner treatment date", value=selected_partner.treatment_date,
        key="p_treat", format="MM/DD/YYYY",
    )

# ---------------------------------------------------------------------------
# Run button
# ---------------------------------------------------------------------------

st.divider()
run_btn = st.button("Run ghosting analysis", type="primary")

if run_btn:
    op_symptoms = (
        [Symptom(type=op_sym_type, onset=op_sym_onset, duration_days=int(op_sym_dur))]
        if op_sym_type != "None" else []
    )
    partner_symptoms = (
        [Symptom(type=p_sym_type, onset=p_sym_onset, duration_days=int(p_sym_dur))]
        if p_sym_type != "None" else []
    )
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
        # Cache inputs alongside result for diagram building
        st.session_state["ghosting_result"]           = result
        st.session_state["ghosting_op_symptoms"]      = op_symptoms
        st.session_state["ghosting_partner_symptoms"] = partner_symptoms
        st.session_state["ghosting_op_exposure"]      = op_exposure
        st.session_state["ghosting_partner_exposure"] = partner_exposure
        st.session_state["ghosting_p_treatment"]      = p_treatment
        st.session_state["ghosting_pname"]            = pname
    except ValueError as e:
        st.error(f"Cannot run analysis: {e}")
        st.stop()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

if "ghosting_result" not in st.session_state:
    st.stop()

result      = st.session_state["ghosting_result"]
op_syms     = st.session_state.get("ghosting_op_symptoms", [])
p_syms      = st.session_state.get("ghosting_partner_symptoms", [])
op_exp      = st.session_state.get("ghosting_op_exposure")
p_exp       = st.session_state.get("ghosting_partner_exposure")
p_treat     = st.session_state.get("ghosting_p_treatment")
cached_pname = st.session_state.get("ghosting_pname", pname)

st.divider()
st.subheader("Results")

# Verdict banner
verdict = result.verdict
if "SOURCE" in verdict and "UNRELATED" not in verdict and "AMBIGUOUS" not in verdict:
    st.success(f"**Verdict:** {verdict}")
elif "SPREAD" in verdict and "UNRELATED" not in verdict:
    st.info(f"**Verdict:** {verdict}")
elif "AMBIGUOUS" in verdict:
    st.warning(f"**Verdict:** {verdict}")
else:
    st.error(f"**Verdict:** {verdict}")

# Ghosted lesion date summary
m1, m2, m3, m4 = st.columns(4)
m1.metric("Ghosted source onset",  str(result.ghosted_source.onset))
m2.metric("Ghosted source end",    str(result.ghosted_source.end))
m3.metric("Ghosted spread onset",  str(result.ghosted_spread.onset))
m4.metric("Ghosted spread end",    str(result.ghosted_spread.end))

# ---------------------------------------------------------------------------
# Visual scenario diagrams
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Scenario visualisations")
st.caption(
    "Each diagram shows P1's anchor symptom (blue), the calculated date marker "
    "(green diamond), the ghosted lesion window for P2 (amber), and P2's own "
    "symptoms (red). Shading indicates whether the exposure criterion passes "
    "(green) or fails (red) for that window."
)

# Determine which symptom list belongs to P1 vs P2
p1_is_op = result.p1_name == case.patient_name
p1_syms  = op_syms if p1_is_op else p_syms
p2_syms  = p_syms  if p1_is_op else op_syms
p1_exp   = op_exp  if p1_is_op else p_exp
p2_exp   = p_exp   if p1_is_op else op_exp

p1_symptom = p1_syms[0] if p1_syms else None

col_src, col_spr = st.columns(2)

if p1_symptom:
    with col_src:
        st.markdown("**Source scenario**")
        st.caption(
            f"If {result.p2_name} was the source, they would have had an "
            f"infectious chancre centred on D1 ({result.ghosted_source.onset} "
            f"→ {result.ghosted_source.end})."
        )
        try:
            fig_src = build_scenario_figure(
                result=result,
                scenario="source",
                p1_name=result.p1_name,
                p2_name=result.p2_name,
                p1_symptom=p1_symptom,
                p2_symptoms=p2_syms,
                p2_exposure=p2_exp,
                criteria=result.criteria["source"],
            )
            st.plotly_chart(fig_src, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render source diagram: {e}")

    with col_spr:
        st.markdown("**Spread scenario**")
        st.caption(
            f"If {result.p1_name} was the source, {result.p2_name} would have "
            f"developed a chancre in the window "
            f"{result.ghosted_spread.onset} → {result.ghosted_spread.end}."
        )
        try:
            fig_spr = build_scenario_figure(
                result=result,
                scenario="spread",
                p1_name=result.p1_name,
                p2_name=result.p2_name,
                p1_symptom=p1_symptom,
                p2_symptoms=p2_syms,
                p2_exposure=p2_exp,
                criteria=result.criteria["spread"],
            )
            st.plotly_chart(fig_spr, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render spread diagram: {e}")
else:
    st.info("No P1 symptom data available — scenario diagrams cannot be rendered.")

# ---------------------------------------------------------------------------
# Criteria tables
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Criteria evaluation")


def _render_criteria_table(criteria: dict):
    rows = []
    for k, v in criteria.items():
        icon = {"pass": "✓ Pass", "fail": "✗ Fail",
                "warn": "⚠ Warn", "na":   "— N/A"}.get(v["status"], "?")
        rows.append({
            "Criterion": k.replace("_", " ").title(),
            "Result":    icon,
            "Detail":    v["detail"],
        })
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Criterion": st.column_config.TextColumn(width="medium"),
            "Result":    st.column_config.TextColumn(width="small"),
            "Detail":    st.column_config.TextColumn(width="large"),
        },
    )


tab_src, tab_spr = st.tabs(["Source scenario", "Spread scenario"])
with tab_src:
    _render_criteria_table(result.criteria["source"])
with tab_spr:
    _render_criteria_table(result.criteria["spread"])

# Step-by-step log
with st.expander("Step-by-step analysis log", expanded=False):
    st.code("\n".join(result.log), language=None)

# ---------------------------------------------------------------------------
# Save ghosted lesions
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Save ghosted lesions")
st.caption(
    "Saved lesions appear in the network graph and VCA chart. "
    "Select which to save based on your clinical judgment."
)

save_source = st.checkbox(
    f"Save ghosted SOURCE lesion  "
    f"({result.ghosted_source.onset} → {result.ghosted_source.end})  "
    f"— assigned to {result.ghosted_source.assigned_to}",
    value=True,
)
save_spread = st.checkbox(
    f"Save ghosted SPREAD lesion  "
    f"({result.ghosted_spread.onset} → {result.ghosted_spread.end})  "
    f"— assigned to {result.ghosted_spread.assigned_to}",
    value=True,
)

if st.button("💾  Save selected lesions", type="primary"):
    saved = []
    with SessionLocal() as db:
        p1_ref = "OP" if result.p1_name == case.patient_name else str(selected_partner.partner_number)
        p2_ref = str(selected_partner.partner_number) if result.p1_name == case.patient_name else "OP"

        if save_source:
            create_ghosting(
                db, case_id=case_id,
                ghosting_type=GhostingType.SOURCE.value,
                from_ref=p1_ref, to_ref=p2_ref,
                notes=(
                    f"Ghosted source: {result.ghosted_source.onset} → "
                    f"{result.ghosted_source.end}. "
                    f"Derived from: {result.ghosted_source.derived_from_symptom}. "
                    f"Verdict: {result.verdict}"
                ),
            )
            saved.append("ghosted source")

        if save_spread:
            create_ghosting(
                db, case_id=case_id,
                ghosting_type=GhostingType.SPREAD.value,
                from_ref=p1_ref, to_ref=p2_ref,
                notes=(
                    f"Ghosted spread: {result.ghosted_spread.onset} → "
                    f"{result.ghosted_spread.end}. "
                    f"Derived from: {result.ghosted_spread.derived_from_symptom}. "
                    f"Verdict: {result.verdict}"
                ),
            )
            saved.append("ghosted spread")

    if saved:
        st.success(f"Saved: {', '.join(saved)}.")
        for key in ["ghosting_result", "ghosting_op_symptoms", "ghosting_partner_symptoms",
                    "ghosting_op_exposure", "ghosting_partner_exposure",
                    "ghosting_p_treatment", "ghosting_pname"]:
            st.session_state.pop(key, None)
        st.rerun()

# ---------------------------------------------------------------------------
# Existing ghosting records
# ---------------------------------------------------------------------------

with SessionLocal() as db:
    ghostings = get_ghostings(db, case_id)

if ghostings:
    st.divider()
    st.subheader("Saved ghosting records")

    ref_map = {str(p.partner_number): p.name or f"Partner {p.partner_number}"
               for p in partners}
    ref_map["OP"] = case.patient_name

    rows = [{
        "ID":    g.id,
        "Type":  g.ghosting_type,
        "From":  ref_map.get(g.from_ref, g.from_ref or "—"),
        "To":    ref_map.get(g.to_ref,   g.to_ref   or "—"),
        "Notes": (g.notes or "")[:90],
    } for g in ghostings]

    st.dataframe(
        pd.DataFrame(rows).drop(columns=["ID"]),
        use_container_width=True, hide_index=True,
    )

    del_options = {
        g.id: (
            f"{g.ghosting_type}  |  "
            f"{ref_map.get(g.from_ref, g.from_ref or '?')} → "
            f"{ref_map.get(g.to_ref, g.to_ref or '?')}"
        )
        for g in ghostings
    }
    dc1, dc2 = st.columns([3, 1])
    with dc1:
        del_id = st.selectbox(
            "Remove record",
            options=list(del_options.keys()),
            format_func=lambda k: del_options[k],
            label_visibility="collapsed",
        )
    with dc2:
        if st.button("✕  Remove", use_container_width=True):
            with SessionLocal() as db:
                delete_ghosting(db, del_id)
            st.success("Record removed.")
            st.rerun()
