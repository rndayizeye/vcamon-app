"""
quickvca/quick_vca.py

Standalone "Quick VCA" — a single-page tool for testing the VCA ghosting
methodology with users. No database, no login, no case management.

It imports the shared clinical engine (app.utils.clinical) from the parent repo,
so any fix to the methodology propagates here automatically.

Run:
    streamlit run quickvca/quick_vca.py
"""

from __future__ import annotations

import os
import sys

# Use an in-memory DB URL *before* importing the shared modules. clinical.py
# transitively imports app.db.models -> app.db.database, which builds an engine
# at import time; the in-memory URL avoids creating any file on disk. We never
# call init_db(), so no tables are created and the DB is never touched.
os.environ.setdefault("DATABASE_URL", "sqlite://")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
# Repo root must come first so `app` resolves to the shared package; the script
# dir is appended (not prepended) for the local `presets` import.
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _HERE not in sys.path:
    sys.path.append(_HERE)

import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from app.utils.clinical import (
    INCUBATION,
    INTERVIEW_PERIOD_PRIMARY_DAYS,
    INTERVIEW_PERIOD_SECONDARY_DAYS,
    LATENCY,
    PRIMARY,
    SECONDARY,
    Exposure,
    run_ghosting_analysis,
)
from app.utils.ghosting_plot import build_scenario_figure
from app.utils.quick_inputs import (
    LOCATION_OPTIONS as _LOCATION_OPTIONS,
    SEX_DISPLAY,
    SYM_COLUMNS as _SYM_COLUMNS,
    SYMPTOM_TYPES as _SYMPTOM_TYPES,
    body_parts_from_modalities as _body_parts,
    rows_to_symptoms as _rows_to_symptoms,
    sex_display_to_values as _sex_values,
)
from presets import PRESETS

st.set_page_config(page_title="Quick VCA", page_icon="🔎", layout="wide")

# ---------------------------------------------------------------------------
# Vocabulary (input maps/helpers shared with app/pages/09_quick_ghost.py via
# app.utils.quick_inputs)
# ---------------------------------------------------------------------------

# Display labels for anatomical sites — friendlier than the raw engine tokens.
# The engine expects values like "Anal LX"; the dict maps from the display label
# back to the engine value so _translate_location_col() can restore them before
# clinical.py's _PRIMARY_LESION_VALUES frozenset comparison.
_LOCATION_DISPLAY = {
    "Anal lesion":               "Anal LX",
    "Oral lesion":               "Oral LX",
    "Vaginal lesion":            "Vaginal LX",
    "Penile lesion":             "Penile LX",
    "Rectal lesion":             "Rectal LX",
    "Non-genital lesion":        "Non-genital LX",
    "Lesion (unspecified site)": "LX",
}
_LOCATION_DISPLAY_OPTIONS = list(_LOCATION_DISPLAY.keys())


def _translate_location_col(df: pd.DataFrame) -> pd.DataFrame:
    """Map friendly display labels back to clinical engine values before analysis."""
    if "Location" not in df.columns:
        return df
    df = df.copy()
    df["Location"] = df["Location"].map(lambda v: _LOCATION_DISPLAY.get(v, v))
    return df


def _empty_sym_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_SYM_COLUMNS)


def _sym_df_from_rows(rows: list[dict] | None) -> pd.DataFrame:
    if not rows:
        return _empty_sym_df()
    return pd.DataFrame(rows, columns=_SYM_COLUMNS)


# ---------------------------------------------------------------------------
# Input state (+ preset loading via a version counter so editors re-seed)
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "qv_a_name": "Person A",
    "qv_b_name": "Person B",
    "qv_a_df": _empty_sym_df(),
    "qv_b_df": _empty_sym_df(),
    "qv_a_ef": None,
    "qv_a_el": None,
    "qv_b_ef": None,
    "qv_b_el": None,
    "qv_a_sex": [],
    "qv_b_sex": [],
    "qv_a_tx": None,
    "qv_b_tx": None,
    "qv_ver": 0,
    "qv_feedback": [],
}

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _load_preset(name: str) -> None:
    preset = PRESETS.get(name)
    if not preset:  # blank
        for side in ("a", "b"):
            st.session_state[f"qv_{side}_name"] = _DEFAULTS[f"qv_{side}_name"]
            st.session_state[f"qv_{side}_df"] = _empty_sym_df()
            st.session_state[f"qv_{side}_ef"] = None
            st.session_state[f"qv_{side}_el"] = None
            st.session_state[f"qv_{side}_sex"] = []
            st.session_state[f"qv_{side}_tx"] = None
    else:
        for side in ("a", "b"):
            person = preset[side]
            st.session_state[f"qv_{side}_name"] = person["name"]
            st.session_state[f"qv_{side}_df"] = _sym_df_from_rows(person["symptoms"])
            st.session_state[f"qv_{side}_ef"] = person["exp_first"]
            st.session_state[f"qv_{side}_el"] = person["exp_last"]
            st.session_state[f"qv_{side}_sex"] = person["sex"]
            st.session_state[f"qv_{side}_tx"] = person["treat"]
    st.session_state["qv_ver"] += 1
    st.session_state.pop("qv_result", None)
    st.session_state.pop("qv_inputs", None)


# ---------------------------------------------------------------------------
# Sidebar — reference + presets
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Quick VCA")
    st.caption(
        "Test the VCA syphilis ghosting methodology on two people. "
        "Nothing is saved; this is a sandbox for evaluating the logic."
    )
    st.divider()

    st.subheader("Load a scenario")
    preset_name = st.selectbox("Preset", list(PRESETS.keys()), key="qv_preset")
    if st.button("Load preset", use_container_width=True):
        _load_preset(preset_name)
        st.rerun()
    if PRESETS.get(preset_name):
        st.caption(f"_Expected:_ {PRESETS[preset_name]['expected']}")

    st.divider()
    st.subheader("Natural-history constants")
    for label, band in [
        ("Incubation", INCUBATION),
        ("Primary chancre", PRIMARY),
        ("Latency", LATENCY),
        ("Secondary", SECONDARY),
    ]:
        st.markdown(
            f"<small><b>{label}:</b> {band['min']}–{band['avg']}–{band['max']} d</small>",
            unsafe_allow_html=True,
        )
    st.caption(
        f"Interview periods — primary {INTERVIEW_PERIOD_PRIMARY_DAYS} d, "
        f"secondary {INTERVIEW_PERIOD_SECONDARY_DAYS} d."
    )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🔎 Quick VCA")
st.caption(
    "Enter symptom and exposure data for two people, then **Run** to see which "
    "direction the clinical timing supports. No case record or login required."
)

with st.expander("📖 Glossary — VCA terms", expanded=False):
    st.markdown("""
| Term | Meaning |
|------|---------|
| **OP** | Original Patient — the index case from which the investigation starts |
| **VCA** | Visual Case Analysis — NCSDDD methodology for establishing probable transmission links from clinical timing data |
| **Ghosting / Ghosted lesion** | A calculated lesion window inferred from clinical constants when the lesion was not directly observed |
| **MAP** | Major Analytical Points — a 46-item systematic checklist for documenting key case information |
| **LX** | Lesion — a syphilitic sore (primary chancre) or secondary rash |
| **Inoculation date** | Estimated date of infection, back-calculated from symptom onset using clinical constants |
| **Interview period** | Look-back window for eliciting contacts: 125 days before primary onset, 237 days before secondary onset |
| **Infectious window** | Period from maximum inoculation date to treatment during which the patient could have transmitted |
| **Stage code** | CDC morbidity reporting code for syphilis stage at diagnosis: 710 = Primary, 720 = Secondary, 730 = Early non-primary non-secondary, 755 = Unknown duration or late |
| **Titer** | Antibody concentration expressed as a dilution ratio (1:1, 1:2, 1:4, 1:8…) |
""")

st.info(
    "**Read the result as a plausibility check, not a probability.** The tool runs the "
    "method across minimum / average / maximum natural-history constants and reports "
    "how many of those tiers hold up. ⚠ Warnings don't fail a scenario but weaken the "
    "story — always read them. Known limitation: when **both** people have a confirmed "
    "primary chancre, the direction can be unreliable; lean on dates and exposures.",
    icon="ℹ️",
)

ver = st.session_state["qv_ver"]

# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------

_sym_col_config = {
    "Type": st.column_config.SelectboxColumn("Symptom type", options=_SYMPTOM_TYPES, required=True),
    "Onset Date": st.column_config.DateColumn("Onset date", required=True, format="MM/DD/YYYY"),
    "Duration": st.column_config.NumberColumn(
        "Duration (days, 0 = use avg)", min_value=0, max_value=90, default=0
    ),
    "Location": st.column_config.SelectboxColumn(
        "Anatomical site (primary only)", options=_LOCATION_DISPLAY_OPTIONS
    ),
}


def _person_inputs(side: str, heading: str) -> dict:
    st.subheader(heading)
    name = st.text_input(
        "Name / identifier", value=st.session_state[f"qv_{side}_name"], key=f"name_{side}_{ver}"
    )
    st.caption("Symptoms — one row per symptom; leave empty if none.")
    df = st.data_editor(
        st.session_state[f"qv_{side}_df"],
        num_rows="dynamic",
        column_config=_sym_col_config,
        key=f"df_{side}_{ver}",
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Exposure window with the other person")
    ef = st.date_input(
        "First exposure", value=st.session_state[f"qv_{side}_ef"], key=f"ef_{side}_{ver}", format="MM/DD/YYYY"
    )
    el = st.date_input(
        "Last exposure", value=st.session_state[f"qv_{side}_el"], key=f"el_{side}_{ver}", format="MM/DD/YYYY"
    )
    sex = st.multiselect(
        "Sex type(s) reported", SEX_DISPLAY, default=st.session_state[f"qv_{side}_sex"], key=f"sex_{side}_{ver}"
    )
    tx = st.date_input(
        "Treatment date", value=st.session_state[f"qv_{side}_tx"], key=f"tx_{side}_{ver}", format="MM/DD/YYYY"
    )
    return {"name": name, "df": df, "ef": ef, "el": el, "sex": sex, "tx": tx}


col_a, col_b = st.columns(2)
with col_a:
    a = _person_inputs("a", "Person A")
with col_b:
    b = _person_inputs("b", "Person B")

st.divider()
run_btn = st.button("▶  Run analysis", type="primary")

if run_btn:
    a_syms = _rows_to_symptoms(_translate_location_col(a["df"]))
    b_syms = _rows_to_symptoms(_translate_location_col(b["df"]))
    if not a_syms and not b_syms:
        st.error("At least one person needs a symptom row with a type and onset date.")
        st.stop()

    a_exp = Exposure(first=a["ef"], last=a["el"]) if a["ef"] and a["el"] else None
    b_exp = Exposure(first=b["ef"], last=b["el"]) if b["ef"] and b["el"] else None
    a_vals, b_vals = _sex_values(a["sex"]), _sex_values(b["sex"])

    try:
        result = run_ghosting_analysis(
            op_name=a["name"].strip() or "Person A",
            op_symptoms=a_syms,
            op_exposure=a_exp,
            op_treatment_date=a["tx"],
            partner_name=b["name"].strip() or "Person B",
            partner_symptoms=b_syms,
            partner_exposure=b_exp,
            partner_treatment_date=b["tx"],
            op_body_parts=_body_parts(a_vals),
            partner_body_parts=_body_parts(b_vals),
        )
    except ValueError as exc:
        st.error(f"Cannot run analysis: {exc}")
        st.stop()

    st.session_state["qv_result"] = result
    st.session_state["qv_inputs"] = {
        "a_name": a["name"].strip() or "Person A",
        "b_name": b["name"].strip() or "Person B",
        "a_syms": a_syms,
        "b_syms": b_syms,
        "a_exp": a_exp,
        "b_exp": b_exp,
        "a_tx": a["tx"],
        "b_tx": b["tx"],
    }

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

if "qv_result" not in st.session_state:
    st.stop()

result = st.session_state["qv_result"]
inp = st.session_state["qv_inputs"]

st.divider()
st.subheader("Result")

verdict = result.verdict
if "UNRELATED" in verdict:
    st.error(f"**{verdict}**")
elif "AMBIGUOUS" in verdict:
    st.warning(f"**{verdict}**")
else:
    st.success(f"**{verdict}**")


def _warn_count(scenario_result) -> int:
    return sum(
        1 for c in scenario_result.range_data["expected"].values() if c["status"] == "warn"
    )


sc, sp = result.source_scenarios, result.spread_scenarios
c1, c2 = st.columns(2)
c1.metric(
    f"Did {result.case2_name} infect {result.case1_name}?",
    f"{sc.confidence} · {sc.pass_count}/3 tiers",
    delta=f"{_warn_count(sc)} warning(s)" if _warn_count(sc) else None,
    delta_color="off",
)
c2.metric(
    f"Did {result.case1_name} infect {result.case2_name}?",
    f"{sp.confidence} · {sp.pass_count}/3 tiers",
    delta=f"{_warn_count(sp)} warning(s)" if _warn_count(sp) else None,
    delta_color="off",
)
st.caption(
    "Tiers = how many of {min, avg, max} natural-history settings keep the scenario "
    "plausible. This is a plausibility count, not a statistical confidence."
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Source lesion onset", str(result.ghosted_source.onset))
m2.metric("Source lesion end", str(result.ghosted_source.end))
m3.metric("Spread lesion onset", str(result.ghosted_spread.onset))
m4.metric("Spread lesion end", str(result.ghosted_spread.end))

# Scenario diagrams ---------------------------------------------------------
st.divider()
st.subheader("Scenario diagrams")

p1_is_a = result.case1_name == inp["a_name"]
p1_symptom = result.case1_symptom
p2_syms = inp["b_syms"] if p1_is_a else inp["a_syms"]
p2_exp = inp["b_exp"] if p1_is_a else inp["a_exp"]

_anchor = inp["a_tx"] or inp["b_tx"] or (p1_symptom.onset if p1_symptom else date.today())
_x_range = (_anchor - timedelta(days=274), _anchor + timedelta(days=91))

if p1_symptom:
    d_src, d_spr = st.columns(2)
    for column, scenario, label, lesion in [
        (d_src, "source", f"If {result.case2_name} infected {result.case1_name}", result.ghosted_source),
        (d_spr, "spread", f"If {result.case1_name} infected {result.case2_name}", result.ghosted_spread),
    ]:
        with column:
            st.markdown(f"**{label}**")
            st.caption(f"Ghosted chancre {lesion.onset} → {lesion.end}")
            try:
                fig = build_scenario_figure(
                    result=result,
                    scenario=scenario,
                    p1_name=result.case1_name,
                    p2_name=result.case2_name,
                    p1_symptom=p1_symptom,
                    p2_symptoms=p2_syms,
                    p2_exposure=p2_exp,
                    criteria=result.criteria[scenario],
                    x_range=_x_range,
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as exc:  # diagrams are best-effort
                st.warning(f"Could not render {scenario} diagram: {exc}")
else:
    st.info("No anchor symptom — diagrams cannot be rendered.")

# Criteria ------------------------------------------------------------------
st.divider()
st.subheader("Criteria (average tier)")


def _render_criteria(criteria: dict) -> None:
    icons = {"pass": "✓ Pass", "fail": "✗ Fail", "warn": "⚠ Warn", "na": "— N/A"}
    rows = [
        {
            "Criterion": k.replace("_", " ").title(),
            "Result": icons.get(v["status"], "?"),
            "Detail": v["detail"],
        }
        for k, v in criteria.items()
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


tab_src, tab_spr = st.tabs(["Source scenario", "Spread scenario"])
with tab_src:
    _render_criteria(result.criteria["source"])
with tab_spr:
    _render_criteria(result.criteria["spread"])

with st.expander("Step-by-step log"):
    st.code("\n".join(result.log), language=None)

# Interview period ----------------------------------------------------------
if p1_symptom:
    st.divider()
    st.subheader("Interview period")
    if p1_symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        days, plabel = INTERVIEW_PERIOD_PRIMARY_DAYS, "primary"
    else:
        days, plabel = INTERVIEW_PERIOD_SECONDARY_DAYS, "secondary"
    ip1, ip2, ip3 = st.columns(3)
    ip1.metric("Anchor onset", str(p1_symptom.onset))
    ip2.metric("Elicit contacts back to", str(p1_symptom.onset - timedelta(days=days)))
    ip3.metric("Window", f"{days} d ({plabel})")

# Feedback ------------------------------------------------------------------
st.divider()
st.subheader("Was this verdict reasonable?")
with st.form("qv_feedback_form", clear_on_submit=True):
    rating = st.radio(
        "Your assessment", ["Reasonable", "Unsure", "Wrong"], horizontal=True
    )
    note = st.text_input("Notes (optional)")
    if st.form_submit_button("Record feedback"):
        st.session_state["qv_feedback"].append(
            {
                "case1": result.case1_name,
                "case2": result.case2_name,
                "verdict": result.verdict,
                "rating": rating,
                "note": note,
            }
        )
        st.success("Recorded. Download all feedback below.")

if st.session_state["qv_feedback"]:
    fb_df = pd.DataFrame(st.session_state["qv_feedback"])
    buf = io.StringIO()
    fb_df.to_csv(buf, index=False)
    st.download_button(
        f"⬇ Download feedback ({len(fb_df)} row(s)) as CSV",
        buf.getvalue(),
        file_name="quickvca_feedback.csv",
        mime="text/csv",
    )
