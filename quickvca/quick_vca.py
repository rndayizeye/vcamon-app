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
from datetime import date, datetime, timedelta

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
    "qv_mode": "Traditional VCA",
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
| **Stage code** | CDC morbidity reporting code for syphilis stage at diagnosis: 700 = Unknown, 710 = Primary, 720 = Secondary, 730 = Early non-primary non-secondary, 755 = Unknown duration or late |
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
st.radio(
    "Analysis mode",
    ["Traditional VCA", "Comprehensive"],
    index=0,
    horizontal=True,
    key="qv_mode",
    help=(
        "**Traditional VCA** follows the NCSDDC methodology: the 4 criteria are "
        "evaluated once using average natural-history constants only.\n\n"
        "**Comprehensive** re-runs all 4 criteria under three constant sets "
        "(optimistic / expected / conservative) and scores how many tiers pass."
    ),
)
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


def _pdf_safe(text: str) -> str:
    """Replace common Unicode chars with Latin-1 equivalents for fpdf2 built-in fonts."""
    return (
        text
        .replace("→", "->")   # →
        .replace("←", "<-")   # ←
        .replace("—", "-")    # — em dash
        .replace("–", "-")    # – en dash
        .replace("•", "*")    # •
        .replace("·", "*")    # ·
        .encode("latin-1", errors="replace").decode("latin-1")
    )


def _build_pdf(result, inp: dict, mode: str) -> bytes:
    from fpdf import FPDF

    p1_is_a = result.case1_name == inp["a_name"]
    p1_symptom = result.case1_symptom
    p2_syms = inp["b_syms"] if p1_is_a else inp["a_syms"]
    p2_exp = inp["b_exp"] if p1_is_a else inp["a_exp"]
    anchor = inp["a_tx"] or inp["b_tx"] or (p1_symptom.onset if p1_symptom else date.today())
    x_range = (anchor - timedelta(days=274), anchor + timedelta(days=91))

    sc, sp = result.source_scenarios, result.spread_scenarios

    _labels = {
        "exposure": "Exposure overlap",
        "exposure_modality": "Anatomical compatibility",
        "latency": "Latency to secondary",
        "natural_order": "Natural progression order",
    }
    _status_text = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "na": "N/A"}

    if mode == "Traditional VCA":
        mode_detail = "Average natural-history constants only (NCSDDC methodology)"
        src_ok = all(v["status"] != "fail" for v in sc.range_data["expected"].values())
        spr_ok = all(v["status"] != "fail" for v in sp.range_data["expected"].values())
        if src_ok and not spr_ok:
            verdict_text = f"SOURCE — {result.case2_name} infected {result.case1_name}"
        elif spr_ok and not src_ok:
            verdict_text = f"SPREAD — {result.case1_name} infected {result.case2_name}"
        elif src_ok and spr_ok:
            verdict_text = "AMBIGUOUS — both directions pass. Manual review required."
        else:
            verdict_text = "UNRELATED INFECTIONS — neither direction supported."
        direction_summary = (
            f"Source: {'Pass' if src_ok else 'Fail'}  |  "
            f"Spread: {'Pass' if spr_ok else 'Fail'}"
        )
    else:
        mode_detail = "3 tiers: optimistic (min) / expected (avg) / conservative (max) constants"
        verdict_text = result.verdict
        direction_summary = (
            f"Source: {sc.confidence} ({sc.pass_count}/3 tiers)  |  "
            f"Spread: {sp.confidence} ({sp.pass_count}/3 tiers)"
        )

    pdf = FPDF(orientation="L")  # A4 landscape — ~267 mm effective width
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Header ---
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Quick VCA Analysis Report", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- Analysis mode (prominent) ---
    pdf.set_fill_color(220, 235, 255)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Analysis Mode: {mode}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, mode_detail, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Persons ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Persons", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6,
        _pdf_safe(f"Person A: {result.case1_name}     Person B: {result.case2_name}"),
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(3)

    # --- Verdict ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Verdict", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, _pdf_safe(verdict_text), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, _pdf_safe(direction_summary), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- Ghosted lesion windows ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Ghosted Lesion Windows", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6,
        f"Source:  {result.ghosted_source.onset}  to  {result.ghosted_source.end}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.cell(
        0, 6,
        f"Spread:  {result.ghosted_spread.onset}  to  {result.ghosted_spread.end}",
        new_x="LMARGIN", new_y="NEXT",
    )
    pdf.ln(4)

    # --- Scenario diagrams ---
    if p1_symptom:
        for scenario, diagram_label in [
            ("source", f"Source: If {result.case2_name} infected {result.case1_name}"),
            ("spread", f"Spread: If {result.case1_name} infected {result.case2_name}"),
        ]:
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 7, _pdf_safe(f"Scenario Diagram - {diagram_label}"), new_x="LMARGIN", new_y="NEXT")
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
                    x_range=x_range,
                )
                # PDF-specific layout: larger fonts, enough left margin for person
                # name labels, legend below chart. Only affects the exported PNG.
                fig.update_layout(
                    title=dict(font=dict(size=16)),
                    yaxis=dict(tickfont=dict(size=14)),
                    xaxis=dict(tickfont=dict(size=12)),
                    legend=dict(
                        orientation="h",
                        y=-0.26,
                        x=0,
                        font=dict(size=11),
                        bgcolor="rgba(255,255,255,0.8)",
                    ),
                    margin=dict(l=120, r=20, t=50, b=110),
                )
                png_bytes = fig.to_image(format="png", width=1600, height=480)
                pdf.image(io.BytesIO(png_bytes), w=pdf.epw)
            except Exception:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(
                    0, 6, "(Diagram unavailable — install kaleido to enable)",
                    new_x="LMARGIN", new_y="NEXT",
                )
            pdf.ln(4)

    # --- Criteria ---
    for scenario_key, scenario_label in [
        ("source", "Source scenario"),
        ("spread", "Spread scenario"),
    ]:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(
            0, 8, _pdf_safe(f"Criteria - {scenario_label} (average tier)"),
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.ln(2)
        for key, val in result.criteria[scenario_key].items():
            label = _labels.get(key, key.replace("_", " ").title())
            status = _status_text.get(val["status"], "?")
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"[{status}]  {label}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, _pdf_safe(val["detail"]))
            pdf.ln(2)

    # --- Interview period ---
    if p1_symptom:
        pdf.ln(3)
        if p1_symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
            ip_days, ip_label = INTERVIEW_PERIOD_PRIMARY_DAYS, "primary"
        else:
            ip_days, ip_label = INTERVIEW_PERIOD_SECONDARY_DAYS, "secondary"
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Interview Period", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Anchor onset: {p1_symptom.onset}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(
            0, 6,
            f"Elicit contacts back to: {p1_symptom.onset - timedelta(days=ip_days)}",
            new_x="LMARGIN", new_y="NEXT",
        )
        pdf.cell(0, 6, f"Window: {ip_days} d ({ip_label})", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


st.divider()
st.subheader("Source / Spread Analysis")

_pdf_bytes = _build_pdf(result, inp, st.session_state.get("qv_mode", "Traditional VCA"))
st.download_button(
    "⬇ Download PDF report",
    data=_pdf_bytes,
    file_name=f"quickvca_{date.today()}.pdf",
    mime="application/pdf",
)

sc, sp = result.source_scenarios, result.spread_scenarios
_mode = st.session_state.get("qv_mode", "Traditional VCA")


def _warn_count(scenario_result) -> int:
    return sum(
        1 for c in scenario_result.range_data["expected"].values() if c["status"] == "warn"
    )


def _passes_expected(scenario_result) -> bool:
    return all(v["status"] != "fail" for v in scenario_result.range_data["expected"].values())


if _mode == "Traditional VCA":
    # ---- Traditional: single pass/fail derived from the average-constant tier ----
    src_ok = _passes_expected(sc)
    spr_ok = _passes_expected(sp)

    if src_ok and not spr_ok:
        st.success(f"**SOURCE — {result.case2_name} infected {result.case1_name}**")
    elif spr_ok and not src_ok:
        st.success(f"**SPREAD — {result.case1_name} infected {result.case2_name}**")
    elif src_ok and spr_ok:
        st.warning(
            f"**AMBIGUOUS — both directions pass under average constants. Manual review required.**"
        )
    else:
        st.error("**UNRELATED INFECTIONS — neither direction is supported under average constants.**")

    c1, c2 = st.columns(2)
    c1.metric(
        f"Source — did {result.case2_name} infect {result.case1_name}?",
        "✓ Pass" if src_ok else "✗ Fail",
        delta=f"{_warn_count(sc)} warning(s)" if _warn_count(sc) else None,
        delta_color="off",
    )
    c2.metric(
        f"Spread — did {result.case1_name} infect {result.case2_name}?",
        "✓ Pass" if spr_ok else "✗ Fail",
        delta=f"{_warn_count(sp)} warning(s)" if _warn_count(sp) else None,
        delta_color="off",
    )
    st.caption(
        "Traditional VCA evaluates the 4 criteria once, using average natural-history "
        "constants only — the standard NCSDDC methodology."
    )

else:
    # ---- Comprehensive: verdict across all 3 tiers, with confidence score ----
    verdict = result.verdict
    if "UNRELATED" in verdict:
        st.error(f"**{verdict}**")
    elif "AMBIGUOUS" in verdict:
        st.warning(f"**{verdict}**")
    else:
        st.success(f"**{verdict}**")

    c1, c2 = st.columns(2)
    c1.metric(
        f"Source — did {result.case2_name} infect {result.case1_name}?",
        f"{sc.confidence} · {sc.pass_count}/3 tiers",
        delta=f"{_warn_count(sc)} warning(s)" if _warn_count(sc) else None,
        delta_color="off",
    )
    c2.metric(
        f"Spread — did {result.case1_name} infect {result.case2_name}?",
        f"{sp.confidence} · {sp.pass_count}/3 tiers",
        delta=f"{_warn_count(sp)} warning(s)" if _warn_count(sp) else None,
        delta_color="off",
    )

    with st.expander("How the tier score is calculated"):
        st.markdown(
            "The 4 criteria are re-run **three times**, once per natural-history tier, "
            "each time using a different set of syphilis progression constants. "
            "A tier **passes** when none of its 4 criteria return Fail (warnings are allowed). "
            "The score counts how many tiers pass.\n\n"
            "| Score | Label | Interpretation |\n"
            "|---|---|---|\n"
            "| 3 / 3 | **Robust** | Scenario holds under fastest, average, and slowest progression |\n"
            "| 2 / 3 | **Likely** | Holds under two of the three timing assumptions |\n"
            "| 1 / 3 | **Possible** | Holds under only the most favorable timing assumption |\n"
            "| 0 / 3 | **Unrelated** | Fails under all three — transmission unlikely on this timeline |\n"
        )
        st.markdown("**Constant values used per tier** (all durations in days):")
        st.dataframe(
            pd.DataFrame([
                {
                    "Tier": "Optimistic",
                    "Constants used": "minimum",
                    "Rationale": "Fastest possible progression",
                    f"Incubation ({INCUBATION['min']}–{INCUBATION['max']} d)": INCUBATION["min"],
                    f"Primary chancre ({PRIMARY['min']}–{PRIMARY['max']} d)": PRIMARY["min"],
                    f"Latency ({LATENCY['min']}–{LATENCY['max']} d)": LATENCY["min"],
                    f"Secondary ({SECONDARY['min']}–{SECONDARY['max']} d)": SECONDARY["min"],
                },
                {
                    "Tier": "Expected",
                    "Constants used": "average",
                    "Rationale": "Average progression (used in Criteria tab above)",
                    f"Incubation ({INCUBATION['min']}–{INCUBATION['max']} d)": INCUBATION["avg"],
                    f"Primary chancre ({PRIMARY['min']}–{PRIMARY['max']} d)": PRIMARY["avg"],
                    f"Latency ({LATENCY['min']}–{LATENCY['max']} d)": LATENCY["avg"],
                    f"Secondary ({SECONDARY['min']}–{SECONDARY['max']} d)": SECONDARY["avg"],
                },
                {
                    "Tier": "Conservative",
                    "Constants used": "maximum",
                    "Rationale": "Slowest possible progression",
                    f"Incubation ({INCUBATION['min']}–{INCUBATION['max']} d)": INCUBATION["max"],
                    f"Primary chancre ({PRIMARY['min']}–{PRIMARY['max']} d)": PRIMARY["max"],
                    f"Latency ({LATENCY['min']}–{LATENCY['max']} d)": LATENCY["max"],
                    f"Secondary ({SECONDARY['min']}–{SECONDARY['max']} d)": SECONDARY["max"],
                },
            ]),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Source: NCSDDC VCA Training (2022), slide 10.")

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

_CRITERIA_META: dict[str, dict[str, str]] = {
    "exposure": {
        "label": "Exposure overlap",
        "description": (
            "The alleged source's **infectious period** (from max inoculation date to treatment) "
            "must overlap the **reported contact window** between the two people. "
            "No overlap means transmission was physically impossible on this timeline."
        ),
    },
    "exposure_modality": {
        "label": "Anatomical compatibility",
        "description": (
            "Each party's **primary chancre site** must match a body part they reported using "
            "during sexual contact. A penile lesion on someone who reported only oral contact, "
            "for example, is anatomically inconsistent with the proposed route."
        ),
    },
    "latency": {
        "label": "Latency to secondary",
        "description": (
            "Enough time must separate the **end of the ghosted primary lesion** from the "
            "recipient's earliest secondary symptom. Natural syphilis progression requires "
            "the chancre to resolve before secondary stage begins (0–70 days of latency)."
        ),
    },
    "natural_order": {
        "label": "Natural progression order",
        "description": (
            "The recipient's symptoms must follow the expected syphilis sequence: "
            "**primary before secondary**. If secondary symptoms appear before or during "
            "the ghosted primary window, the scenario violates known disease biology."
        ),
    },
}

_STATUS_BADGE = {
    "pass": "🟢 Pass",
    "fail": "🔴 Fail",
    "warn": "🟡 Warn",
    "na":   "⚪ N/A",
}


def _render_criteria(criteria: dict) -> None:
    for key, val in criteria.items():
        meta = _CRITERIA_META.get(
            key,
            {"label": key.replace("_", " ").title(), "description": ""},
        )
        status = val["status"]
        badge = _STATUS_BADGE.get(status, "? Unknown")
        with st.expander(
            f"{badge} — {meta['label']}",
            expanded=(status in ("fail", "warn")),
        ):
            if meta["description"]:
                st.markdown(meta["description"])
                st.divider()
            st.markdown(f"**Engine output:** {val['detail']}")


st.markdown(
    "Each scenario is evaluated against **4 independent criteria** "
    "(average natural-history tier shown). Failures rule a scenario out; "
    "warnings weaken it. Failing/warning criteria are expanded automatically."
)

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
