"""
app/pages/09_quick_ghost.py

Quick Ghosting Analysis — run the VCA ghosting engine without
needing an active case or navigating the full workflow.

Use this when:
  - You want a fast calculation during an interview
  - You're working from paper notes and want to check dates
  - You want to verify a scenario before committing it to a case

No database reads or writes happen unless you explicitly save.
If a case is active in session state, a save option appears at the end.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from app.utils.session_state import init_session_state, get_active_case_id
from app.utils.clinical import (
    Symptom,
    Exposure,
    run_ghosting_analysis,
    INCUBATION, PRIMARY, LATENCY, SECONDARY,
    INTERVIEW_PERIOD_PRIMARY_DAYS,
    INTERVIEW_PERIOD_SECONDARY_DAYS,
)
from app.utils.ghosting_plot import build_scenario_figure

st.set_page_config(page_title="Quick Ghost — VCA Monitor", layout="wide")
init_session_state()

# ---------------------------------------------------------------------------
# Sidebar — minimal, just navigation back
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Quick ghosting")
    st.caption(
        "Run the VCA ghosting engine without opening a case. "
        "Enter dates directly and get an immediate result."
    )
    st.divider()

    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")
    if st.button("Full ghosting analysis →", use_container_width=True):
        st.switch_page("pages/07_ghosting_analysis.py")

    st.divider()
    st.caption("**Clinical reference**")

    ref_rows = [
        ("Incubation",  INCUBATION["min"],  INCUBATION["avg"],  INCUBATION["max"]),
        ("Primary",     PRIMARY["min"],      PRIMARY["avg"],      PRIMARY["max"]),
        ("Latency",     LATENCY["min"],      LATENCY["avg"],      LATENCY["max"]),
        ("Secondary",   SECONDARY["min"],    SECONDARY["avg"],    SECONDARY["max"]),
    ]
    for label, mn, avg, mx in ref_rows:
        st.markdown(
            f"<small>**{label}:** {mn}–{avg}–{mx}d</small>",
            unsafe_allow_html=True,
        )
    st.caption(
        f"Interview periods: "
        f"Primary = {INTERVIEW_PERIOD_PRIMARY_DAYS}d, "
        f"Secondary = {INTERVIEW_PERIOD_SECONDARY_DAYS}d"
    )


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("⚡ Quick Ghosting Analysis")
st.caption(
    "Enter two people's symptom and exposure data below — no case required. "
    "Results appear immediately after clicking **Run**."
)

# Interview period helper banner
with st.expander("Which dates do I need?", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
**If the presenting symptom is Primary:**
- Chancre onset date
- Exposure window (first + last contact with partner)
- Sex type(s) reported
- Treatment date

Interview period reaches back **{INTERVIEW_PERIOD_PRIMARY_DAYS} days** before chancre onset.
"""
        )
    with c2:
        st.markdown(
            f"""
**If the presenting symptom is Secondary:**
- Secondary symptom onset date
- Exposure window (first + last contact)
- Sex type(s) reported
- Treatment date

Interview period reaches back **{INTERVIEW_PERIOD_SECONDARY_DAYS} days** before secondary onset.
"""
        )

st.divider()

# ---------------------------------------------------------------------------
# Input form — two columns, Person A and Person B
# ---------------------------------------------------------------------------

SYM_TYPES = [
    "Primary Chancre",
    "Historical Primary",
    "Ghosted Primary",
    "Secondary Rash/Lesions",
    "None",
]
SEX_OPTIONS = ["Anal LX", "Oral LX", "Vaginal LX", "Penile LX", "Rectal LX"]

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Person A (OP)")
    a_name = st.text_input("Name / identifier", value="OP", key="a_name")
    a_sym_type = st.selectbox("Symptom type", SYM_TYPES, key="a_sym_type")

    a_sym_onset = st.date_input(
        "Symptom onset date",
        value=date.today() - timedelta(days=21),
        key="a_sym_onset",
        format="MM/DD/YYYY",
    )
    a_sym_dur = st.number_input(
        "Symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0, key="a_sym_dur",
    )

    st.caption("Exposure window (A's account of contact with B)")
    a_exp_first = st.date_input(
        "First exposure", value=None, key="a_exp_first", format="MM/DD/YYYY"
    )
    a_exp_last = st.date_input(
        "Last exposure", value=None, key="a_exp_last", format="MM/DD/YYYY"
    )
    a_sex = st.multiselect("Sex type(s) — A's report", SEX_OPTIONS, key="a_sex")
    a_treatment = st.date_input(
        "Treatment date", value=None, key="a_treat", format="MM/DD/YYYY"
    )

with col_b:
    st.subheader("Person B (Partner)")
    b_name = st.text_input("Name / identifier", value="Partner", key="b_name")
    b_sym_type = st.selectbox("Symptom type", SYM_TYPES, index=4, key="b_sym_type")

    b_sym_onset = st.date_input(
        "Symptom onset date",
        value=date.today() - timedelta(days=45),
        key="b_sym_onset",
        format="MM/DD/YYYY",
    )
    b_sym_dur = st.number_input(
        "Symptom duration (days, 0 = use average)",
        min_value=0, max_value=90, value=0, key="b_sym_dur",
    )

    st.caption("Exposure window (B's account of contact with A)")
    b_exp_first = st.date_input(
        "First exposure", value=None, key="b_exp_first", format="MM/DD/YYYY"
    )
    b_exp_last = st.date_input(
        "Last exposure", value=None, key="b_exp_last", format="MM/DD/YYYY"
    )
    b_sex = st.multiselect("Sex type(s) — B's report", SEX_OPTIONS, key="b_sex")
    b_treatment = st.date_input(
        "Treatment date", value=None, key="b_treat", format="MM/DD/YYYY"
    )

# ---------------------------------------------------------------------------
# Run button + validation
# ---------------------------------------------------------------------------

st.divider()

run_col, clear_col, _ = st.columns([1, 1, 5])

with run_col:
    run_btn = st.button("▶  Run analysis", type="primary", use_container_width=True)

with clear_col:
    if st.button("✕  Clear results", use_container_width=True):
        st.session_state.pop("qg_result", None)
        st.session_state.pop("qg_inputs", None)
        st.rerun()

if run_btn:
    # Build symptom lists
    a_symptoms = (
        [Symptom(type=a_sym_type, onset=a_sym_onset, duration_days=int(a_sym_dur))]
        if a_sym_type != "None" else []
    )
    b_symptoms = (
        [Symptom(type=b_sym_type, onset=b_sym_onset, duration_days=int(b_sym_dur))]
        if b_sym_type != "None" else []
    )

    if not a_symptoms and not b_symptoms:
        st.error("At least one person must have a symptom type selected.")
        st.stop()

    a_exposure = (
        Exposure(first=a_exp_first, last=a_exp_last, sex_types=a_sex)
        if a_exp_first and a_exp_last else None
    )
    b_exposure = (
        Exposure(first=b_exp_first, last=b_exp_last, sex_types=b_sex)
        if b_exp_first and b_exp_last else None
    )

    try:
        result = run_ghosting_analysis(
            op_name=a_name.strip() or "Person A",
            op_symptoms=a_symptoms,
            op_exposure=a_exposure,
            op_treatment_date=a_treatment,
            partner_name=b_name.strip() or "Person B",
            partner_symptoms=b_symptoms,
            partner_exposure=b_exposure,
            partner_treatment_date=b_treatment,
        )
        st.session_state["qg_result"] = result
        st.session_state["qg_inputs"] = {
            "a_symptoms": a_symptoms,
            "b_symptoms": b_symptoms,
            "a_exposure": a_exposure,
            "b_exposure": b_exposure,
            "a_treatment": a_treatment,
            "b_treatment": b_treatment,
            "a_name": a_name,
            "b_name": b_name,
        }
    except ValueError as e:
        st.error(f"Cannot run analysis: {e}")
        st.stop()


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

if "qg_result" not in st.session_state:
    st.stop()

result = st.session_state["qg_result"]
inp = st.session_state["qg_inputs"]

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

# Ghosted date metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Ghosted source onset", str(result.ghosted_source.onset))
m2.metric("Ghosted source end",   str(result.ghosted_source.end))
m3.metric("Ghosted spread onset", str(result.ghosted_spread.onset))
m4.metric("Ghosted spread end",   str(result.ghosted_spread.end))

# ---------------------------------------------------------------------------
# Scenario diagrams
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Scenario visualisations")

p1_is_a    = result.p1_name == (inp["a_name"].strip() or "Person A")
p1_syms    = inp["a_symptoms"] if p1_is_a else inp["b_symptoms"]
p2_syms    = inp["b_symptoms"] if p1_is_a else inp["a_symptoms"]
p2_exp     = inp["b_exposure"] if p1_is_a else inp["a_exposure"]

p1_symptom = p1_syms[0] if p1_syms else None

if p1_symptom:
    col_src, col_spr = st.columns(2)

    with col_src:
        st.markdown("**Source scenario**")
        st.caption(
            f"If {result.p2_name} infected {result.p1_name} — "
            f"ghosted chancre {result.ghosted_source.onset} → {result.ghosted_source.end}"
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
            f"If {result.p1_name} infected {result.p2_name} — "
            f"ghosted chancre {result.ghosted_spread.onset} → {result.ghosted_spread.end}"
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
    st.info("No P1 symptom data — diagrams cannot be rendered.")

# ---------------------------------------------------------------------------
# Criteria tables
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Criteria evaluation")


def _render_criteria(criteria: dict):
    rows = []
    for k, v in criteria.items():
        icon = {
            "pass": "✓ Pass", "fail": "✗ Fail",
            "warn": "⚠ Warn", "na":   "— N/A",
        }.get(v["status"], "?")
        rows.append({
            "Criterion": k.replace("_", " ").title(),
            "Result": icon,
            "Detail": v["detail"],
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
    _render_criteria(result.criteria["source"])
with tab_spr:
    _render_criteria(result.criteria["spread"])

with st.expander("Step-by-step log", expanded=False):
    st.code("\n".join(result.log), language=None)

# ---------------------------------------------------------------------------
# Calculated interview periods (bonus output)
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Interview periods")
st.caption("How far back to elicit contacts, based on the anchor symptom.")

if p1_symptom:
    if p1_symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        interview_start = p1_symptom.onset - timedelta(days=INTERVIEW_PERIOD_PRIMARY_DAYS)
        period_label = f"{INTERVIEW_PERIOD_PRIMARY_DAYS} days (primary)"
    else:
        interview_start = p1_symptom.onset - timedelta(days=INTERVIEW_PERIOD_SECONDARY_DAYS)
        period_label = f"{INTERVIEW_PERIOD_SECONDARY_DAYS} days (secondary)"

    ip1, ip2, ip3 = st.columns(3)
    ip1.metric("Anchor symptom onset",  str(p1_symptom.onset))
    ip2.metric("Interview period start", str(interview_start))
    ip3.metric("Period length",          period_label)
else:
    st.info("No P1 symptom — interview period cannot be calculated.")

# ---------------------------------------------------------------------------
# Optional save to active case
# ---------------------------------------------------------------------------

active_case_id = get_active_case_id()

if active_case_id:
    st.divider()
    st.subheader("Save to active case")
    st.caption(
        f"Case #{active_case_id} is active in your session. "
        "You can save these ghosted lesion records without leaving this page."
    )

    save_source = st.checkbox(
        f"Save ghosted SOURCE lesion "
        f"({result.ghosted_source.onset} → {result.ghosted_source.end})",
        value=True,
        key="qg_save_source",
    )
    save_spread = st.checkbox(
        f"Save ghosted SPREAD lesion "
        f"({result.ghosted_spread.onset} → {result.ghosted_spread.end})",
        value=True,
        key="qg_save_spread",
    )

    partner_ref_input = st.text_input(
        "Partner reference (number, or leave blank for OP)",
        value="",
        placeholder="e.g. 1  or  2",
        key="qg_partner_ref",
        help="Enter the partner number to attach these records to, or leave blank to attach to OP.",
    )

    if st.button("💾  Save to case", type="primary"):
        from app.db.database import SessionLocal
        from app.db.queries import create_ghosting
        from app.db.models import GhostingType

        p_ref = partner_ref_input.strip() or None
        from_ref = "OP" if result.p1_name == (inp["a_name"].strip() or "Person A") else (p_ref or "1")
        to_ref   = (p_ref or "1") if result.p1_name == (inp["a_name"].strip() or "Person A") else "OP"

        saved = []
        with SessionLocal() as db:
            if save_source:
                create_ghosting(
                    db,
                    case_id=active_case_id,
                    ghosting_type=GhostingType.SOURCE.value,
                    from_ref=from_ref,
                    to_ref=to_ref,
                    notes=(
                        f"[Quick analysis] Ghosted source: "
                        f"{result.ghosted_source.onset} → {result.ghosted_source.end}. "
                        f"Derived from: {result.ghosted_source.derived_from_symptom}. "
                        f"Verdict: {result.verdict}"
                    ),
                )
                saved.append("ghosted source")

            if save_spread:
                create_ghosting(
                    db,
                    case_id=active_case_id,
                    ghosting_type=GhostingType.SPREAD.value,
                    from_ref=from_ref,
                    to_ref=to_ref,
                    notes=(
                        f"[Quick analysis] Ghosted spread: "
                        f"{result.ghosted_spread.onset} → {result.ghosted_spread.end}. "
                        f"Derived from: {result.ghosted_spread.derived_from_symptom}. "
                        f"Verdict: {result.verdict}"
                    ),
                )
                saved.append("ghosted spread")

        if saved:
            st.success(
                f"Saved {', '.join(saved)} to case #{active_case_id}. "
                "Records will appear in the network graph and VCA chart."
            )
        else:
            st.warning("Nothing selected to save.")
else:
    st.divider()
    st.caption(
        "💡 To save these results to a case, open a case from the dashboard first — "
        "a save option will appear here automatically."
    )
