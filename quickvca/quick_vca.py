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
    calc_date1,
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

def _partner_defaults(n: int) -> dict:
    return {
        f"qv_p{n}_name":   f"Contact {n}",
        f"qv_p{n}_df":     _empty_sym_df(),
        f"qv_p{n}_ef":     None,
        f"qv_p{n}_el":     None,
        f"qv_p{n}_sex":    [],
        f"qv_p{n}_tx":     None,
        # OP's side of this specific pair (exposure and sex type differ per contact)
        f"qv_p{n}_op_ef":  None,
        f"qv_p{n}_op_el":  None,
        f"qv_p{n}_op_sex": [],
    }


_DEFAULTS: dict = {
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
    "qv_investigation_mode": "Single Pair",
    "qv_ver": 0,
    "qv_feedback": [],
    "qv_mode": "Traditional VCA",
}
for _n in range(1, 6):
    _DEFAULTS.update(_partner_defaults(_n))

for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _reset_partner(n: int) -> None:
    for k, v in _partner_defaults(n).items():
        st.session_state[k] = v


def _load_preset(name: str) -> None:
    preset = PRESETS.get(name)
    for _n in range(1, 6):
        _reset_partner(_n)

    if not preset:  # blank form
        st.session_state["qv_investigation_mode"] = "Single Pair"
        for side in ("a", "b"):
            st.session_state[f"qv_{side}_name"] = _DEFAULTS[f"qv_{side}_name"]
            st.session_state[f"qv_{side}_df"] = _empty_sym_df()
            st.session_state[f"qv_{side}_ef"] = None
            st.session_state[f"qv_{side}_el"] = None
            st.session_state[f"qv_{side}_sex"] = []
            st.session_state[f"qv_{side}_tx"] = None

    elif preset.get("mode") == "multi":  # multi-partner preset
        st.session_state["qv_investigation_mode"] = "Multi-Partner (OP + up to 5 contacts)"
        op = preset["op"]
        st.session_state["qv_a_name"] = op["name"]
        st.session_state["qv_a_df"] = _sym_df_from_rows(op["symptoms"])
        st.session_state["qv_a_tx"] = op["treat"]
        st.session_state["qv_a_ef"] = None
        st.session_state["qv_a_el"] = None
        st.session_state["qv_a_sex"] = []
        for _i, _c in enumerate(preset["contacts"][:5], 1):
            st.session_state[f"qv_p{_i}_name"] = _c["name"]
            st.session_state[f"qv_p{_i}_df"]   = _sym_df_from_rows(_c["symptoms"])
            st.session_state[f"qv_p{_i}_ef"]   = _c["exp_first"]
            st.session_state[f"qv_p{_i}_el"]   = _c["exp_last"]
            st.session_state[f"qv_p{_i}_sex"]  = _c["sex"]
            st.session_state[f"qv_p{_i}_tx"]   = _c["treat"]
            st.session_state[f"qv_p{_i}_op_ef"]  = _c["op_exp_first"]
            st.session_state[f"qv_p{_i}_op_el"]  = _c["op_exp_last"]
            st.session_state[f"qv_p{_i}_op_sex"] = _c["op_sex"]

    else:  # single-pair preset
        st.session_state["qv_investigation_mode"] = "Single Pair"
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
    st.session_state.pop("qv_multi_results", None)


# ---------------------------------------------------------------------------
# Sidebar — investigation mode + reference + presets
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Quick VCA")
    st.caption(
        "Test the VCA syphilis ghosting methodology. "
        "Nothing is saved; this is a sandbox for evaluating the logic."
    )
    st.divider()

    st.subheader("Investigation mode")
    st.radio(
        "Investigation mode",
        ["Single Pair", "Multi-Partner (OP + up to 5 contacts)"],
        key="qv_investigation_mode",
        label_visibility="collapsed",
        help=(
            "**Single Pair** — evaluate two people head-to-head (standard workflow).\n\n"
            "**Multi-Partner** — enter the index patient once and up to 5 contacts; "
            "the tool ranks them by who is the most plausible source."
        ),
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
_inv_mode = st.session_state.get("qv_investigation_mode", "Single Pair")

if _inv_mode == "Single Pair":
    st.caption(
        "Enter symptom and exposure data for two people, then **Run** to see which "
        "direction the clinical timing supports. No case record or login required."
    )
else:
    st.caption(
        "Enter the index patient's data once, then fill in up to 5 contacts. "
        "The tool runs the analysis for each pair and ranks contacts by how well "
        "the timing supports them as the source."
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


def _person_inputs(side: str, heading: str, show_exposure_sex: bool = True) -> dict:
    if heading:
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
    ef = el = None
    sex: list = []
    if show_exposure_sex:
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


if _inv_mode == "Single Pair":
    col_a, col_b = st.columns(2)
    with col_a:
        a = _person_inputs("a", "Person A")
    with col_b:
        b = _person_inputs("b", "Person B")
    _contacts_input = None

else:
    st.subheader("Index Patient (OP)")
    st.caption("Symptoms and treatment are shared across all pairs. Exposure and sex type are entered per contact below.")
    op_col, _ = st.columns([2, 1])
    with op_col:
        a = _person_inputs("a", "", show_exposure_sex=False)

    st.divider()
    st.subheader("Contacts")
    st.caption(
        "Each tab captures both the contact's data and the OP's exposure with that specific contact. "
        "Contacts without at least one symptom are skipped automatically."
    )
    _contact_tabs = st.tabs([f"Contact {i}" for i in range(1, 6)])
    _contacts_input = []
    for _ci, _ctab in enumerate(_contact_tabs, 1):
        with _ctab:
            col_contact, col_op = st.columns(2)
            with col_contact:
                st.markdown(f"**Contact {_ci}**")
                _cp = _person_inputs(f"p{_ci}", "")
            with col_op:
                st.markdown(f"**OP with Contact {_ci}**")
                st.caption("OP's reported exposure and sex type for this specific pair.")
                _op_ef = st.date_input(
                    "OP first exposure",
                    value=st.session_state[f"qv_p{_ci}_op_ef"],
                    key=f"op_ef_p{_ci}_{ver}",
                    format="MM/DD/YYYY",
                )
                _op_el = st.date_input(
                    "OP last exposure",
                    value=st.session_state[f"qv_p{_ci}_op_el"],
                    key=f"op_el_p{_ci}_{ver}",
                    format="MM/DD/YYYY",
                )
                _op_sex = st.multiselect(
                    "OP sex type(s)",
                    SEX_DISPLAY,
                    default=st.session_state[f"qv_p{_ci}_op_sex"],
                    key=f"op_sex_p{_ci}_{ver}",
                )
            _contacts_input.append({**_cp, "op_ef": _op_ef, "op_el": _op_el, "op_sex": _op_sex})
    b = None

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
        "**Comprehensive** re-runs all 4 criteria under five constant sets "
        "(aggressive / expected / conservative / fast-infection / slow-infection) "
        "and scores how many tiers pass."
    ),
)
run_btn = st.button("▶  Run analysis", type="primary")

# ---------------------------------------------------------------------------
# Run button handler
# ---------------------------------------------------------------------------

if run_btn:
    if _inv_mode == "Single Pair":
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
        st.session_state.pop("qv_multi_results", None)

    else:
        # Multi-partner: run engine for every contact that has symptoms
        a_syms = _rows_to_symptoms(_translate_location_col(a["df"]))
        if not a_syms:
            st.error("The index patient needs at least one symptom row.")
            st.stop()

        op_name = a["name"].strip() or "OP"

        multi_results = []
        warnings_out = []
        for _ci, _cp in enumerate(_contacts_input, 1):
            _cp_name = _cp["name"].strip() or f"Contact {_ci}"
            _cp_syms = _rows_to_symptoms(_translate_location_col(_cp["df"]))
            if not _cp_syms:
                continue  # silently skip contacts with no symptoms
            # Per-pair OP fields (exposure window and sex type differ per contact)
            _a_exp_val = Exposure(first=_cp["op_ef"], last=_cp["op_el"]) if _cp["op_ef"] and _cp["op_el"] else None
            _a_vals = _sex_values(_cp["op_sex"])
            _cp_exp = Exposure(first=_cp["ef"], last=_cp["el"]) if _cp["ef"] and _cp["el"] else None
            _cp_vals = _sex_values(_cp["sex"])
            try:
                _r = run_ghosting_analysis(
                    op_name=op_name,
                    op_symptoms=a_syms,
                    op_exposure=_a_exp_val,
                    op_treatment_date=a["tx"],
                    partner_name=_cp_name,
                    partner_symptoms=_cp_syms,
                    partner_exposure=_cp_exp,
                    partner_treatment_date=_cp["tx"],
                    op_body_parts=_body_parts(_a_vals),
                    partner_body_parts=_body_parts(_cp_vals),
                )
                multi_results.append({
                    "n": _ci,
                    "result": _r,
                    "inp": {
                        "a_name": op_name,
                        "b_name": _cp_name,
                        "a_syms": a_syms,
                        "b_syms": _cp_syms,
                        "a_exp": _a_exp_val,
                        "b_exp": _cp_exp,
                        "a_tx": a["tx"],
                        "b_tx": _cp["tx"],
                    },
                })
            except ValueError as exc:
                warnings_out.append(f"Contact {_ci} ({_cp_name}): {exc}")

        for _w in warnings_out:
            st.warning(_w)

        if not multi_results:
            st.error("No contacts had enough data to run. Add at least one symptom row per contact.")
            st.stop()

        st.session_state["qv_multi_results"] = multi_results
        st.session_state["qv_multi_op_name"] = op_name
        st.session_state.pop("qv_result", None)
        st.session_state.pop("qv_inputs", None)

# ---------------------------------------------------------------------------
# Shared helper functions (PDF, display, criteria)
# ---------------------------------------------------------------------------

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


def _passes_expected(scenario_result) -> bool:
    return all(v["status"] != "fail" for v in scenario_result.range_data["expected"].values())


def _trad_verdict_strings(sc, sp, case1_name: str, case2_name: str) -> tuple:
    """Single source of truth for Traditional VCA verdict text — used in both PDF and display."""
    src_ok = _passes_expected(sc)
    spr_ok = _passes_expected(sp)
    if src_ok and not spr_ok:
        text = f"SOURCE — {case2_name} infected {case1_name}"
    elif spr_ok and not src_ok:
        text = f"SPREAD — {case1_name} infected {case2_name}"
    elif src_ok and spr_ok:
        text = "AMBIGUOUS — both directions pass under average constants. Manual review required."
    else:
        text = "UNRELATED INFECTIONS — neither direction supported under average constants."
    summary = f"Source: {'Pass' if src_ok else 'Fail'}  |  Spread: {'Pass' if spr_ok else 'Fail'}"
    return src_ok, spr_ok, text, summary


def _build_pdf(result, inp: dict, mode: str, p1_symptom, p2_syms, p2_exp, x_range) -> bytes:
    from fpdf import FPDF

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
        _, _, verdict_text, direction_summary = _trad_verdict_strings(
            sc, sp, result.case1_name, result.case2_name
        )
    else:
        mode_detail = (
            "5 tiers: aggressive (min) / expected (avg) / conservative (max) / "
            "fast-infection / slow-infection constants"
        )
        verdict_text = result.verdict
        direction_summary = (
            f"Source: {sc.confidence} ({sc.pass_count}/5 tiers)  |  "
            f"Spread: {sp.confidence} ({sp.pass_count}/5 tiers)"
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
            except Exception as _exc:
                pdf.set_font("Helvetica", "I", 9)
                pdf.cell(
                    0, 6, _pdf_safe(f"(Diagram unavailable: {_exc})"),
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


def _warn_count(scenario_result) -> int:
    return sum(
        1 for c in scenario_result.range_data["expected"].values() if c["status"] == "warn"
    )


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


# ---------------------------------------------------------------------------
# Single-pair results renderer
# ---------------------------------------------------------------------------

def _show_pair_result(result, inp: dict, show_feedback: bool = True) -> None:
    mode = st.session_state.get("qv_mode", "Traditional VCA")

    p1_is_a = result.case1_name == inp["a_name"]
    p1_symptom = result.case1_symptom
    p2_syms = inp["b_syms"] if p1_is_a else inp["a_syms"]
    p2_exp = inp["b_exp"] if p1_is_a else inp["a_exp"]
    anchor = inp["a_tx"] or inp["b_tx"] or (p1_symptom.onset if p1_symptom else date.today())
    x_range = (anchor - timedelta(days=274), anchor + timedelta(days=91))

    sc, sp = result.source_scenarios, result.spread_scenarios

    # PDF download
    _pdf_cache_key = (id(result), mode)
    if st.session_state.get("_qv_pdf_cache_key") != _pdf_cache_key:
        st.session_state["_qv_pdf_bytes"] = _build_pdf(
            result, inp, mode, p1_symptom, p2_syms, p2_exp, x_range
        )
        st.session_state["_qv_pdf_cache_key"] = _pdf_cache_key
    st.download_button(
        "⬇ Download PDF report",
        data=st.session_state["_qv_pdf_bytes"],
        file_name=f"quickvca_{date.today()}.pdf",
        mime="application/pdf",
    )

    # Verdict
    if mode == "Traditional VCA":
        src_ok, spr_ok, _verdict_text, _ = _trad_verdict_strings(
            sc, sp, result.case1_name, result.case2_name
        )
        if src_ok and not spr_ok:
            st.success(f"**{_verdict_text}**")
        elif spr_ok and not src_ok:
            st.success(f"**{_verdict_text}**")
        elif src_ok and spr_ok:
            st.warning(f"**{_verdict_text}**")
        else:
            st.error(f"**{_verdict_text}**")

        _sc_warns, _sp_warns = _warn_count(sc), _warn_count(sp)
        c1, c2 = st.columns(2)
        c1.metric(
            f"Source — did {result.case2_name} infect {result.case1_name}?",
            "✓ Pass" if src_ok else "✗ Fail",
            delta=f"{_sc_warns} warning(s)" if _sc_warns else None,
            delta_color="off",
        )
        c2.metric(
            f"Spread — did {result.case1_name} infect {result.case2_name}?",
            "✓ Pass" if spr_ok else "✗ Fail",
            delta=f"{_sp_warns} warning(s)" if _sp_warns else None,
            delta_color="off",
        )
        st.caption(
            "Traditional VCA evaluates the 4 criteria once, using average natural-history "
            "constants only — the standard NCSDDC methodology."
        )

    else:
        verdict = result.verdict
        if "UNRELATED" in verdict:
            st.error(f"**{verdict}**")
        elif "AMBIGUOUS" in verdict:
            st.warning(f"**{verdict}**")
        else:
            st.success(f"**{verdict}**")

        _sc_warns, _sp_warns = _warn_count(sc), _warn_count(sp)
        c1, c2 = st.columns(2)
        c1.metric(
            f"Source — did {result.case2_name} infect {result.case1_name}?",
            f"{sc.confidence} · {sc.pass_count}/5 tiers",
            delta=f"{_sc_warns} warning(s)" if _sc_warns else None,
            delta_color="off",
        )
        c2.metric(
            f"Spread — did {result.case1_name} infect {result.case2_name}?",
            f"{sp.confidence} · {sp.pass_count}/5 tiers",
            delta=f"{_sp_warns} warning(s)" if _sp_warns else None,
            delta_color="off",
        )

        with st.expander("How the tier score is calculated"):
            st.markdown(
                "The 4 criteria are re-run **five times**, once per natural-history tier, "
                "each time using a different combination of syphilis progression constants. "
                "A tier **passes** when none of its 4 criteria return Fail (warnings are allowed). "
                "The score counts how many tiers pass.\n\n"
                "| Score | Label | Interpretation |\n"
                "|---|---|---|\n"
                "| 5 / 5 | **Robust** | Holds across all five timing combinations |\n"
                "| 4 / 5 | **Likely** | Holds under four of five combinations |\n"
                "| 3 / 5 | **Possible** | Holds in at least half of combinations |\n"
                "| 2 / 5 | **Weak** | Holds in a minority of combinations |\n"
                "| 1 / 5 | **Unlikely** | Holds under only one combination |\n"
                "| 0 / 5 | **Unrelated** | Fails under all — transmission unlikely on this timeline |\n"
            )
            st.markdown("**Constant values used per tier** (all durations in days):")
            _ic, _pr, _la, _se = (
                f"Incubation ({INCUBATION['min']}–{INCUBATION['max']} d)",
                f"Primary chancre ({PRIMARY['min']}–{PRIMARY['max']} d)",
                f"Latency ({LATENCY['min']}–{LATENCY['max']} d)",
                f"Secondary ({SECONDARY['min']}–{SECONDARY['max']} d)",
            )
            st.dataframe(
                pd.DataFrame([
                    {
                        "Tier": "Optimistic",
                        "Rationale": "Fastest possible progression",
                        _ic: INCUBATION["min"], _pr: PRIMARY["min"],
                        _la: LATENCY["min"], _se: SECONDARY["min"],
                    },
                    {
                        "Tier": "Expected",
                        "Rationale": "Average progression (used in Criteria tab)",
                        _ic: INCUBATION["avg"], _pr: PRIMARY["avg"],
                        _la: LATENCY["avg"], _se: SECONDARY["avg"],
                    },
                    {
                        "Tier": "Conservative",
                        "Rationale": "Slowest possible progression",
                        _ic: INCUBATION["max"], _pr: PRIMARY["max"],
                        _la: LATENCY["max"], _se: SECONDARY["max"],
                    },
                    {
                        "Tier": "Fast infection, slow disease",
                        "Rationale": "Infected quickly; long-lasting chancre and late secondary",
                        _ic: INCUBATION["min"], _pr: PRIMARY["max"],
                        _la: LATENCY["max"], _se: SECONDARY["max"],
                    },
                    {
                        "Tier": "Slow infection, fast disease",
                        "Rationale": "Long incubation; rapid progression to secondary",
                        _ic: INCUBATION["max"], _pr: PRIMARY["min"],
                        _la: LATENCY["min"], _se: SECONDARY["min"],
                    },
                ]),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("Source: NCSDDC VCA Training (2022), slide 10. Cross-scenarios cover independent stage variation.")

    # Important Dates
    if p1_symptom:
        st.markdown("#### Important Dates")
        _d1 = calc_date1(p1_symptom, constant_key="avg")
        _ip_days = (
            INTERVIEW_PERIOD_PRIMARY_DAYS
            if p1_symptom.type in ("Primary Chancre", "Historical Primary", "Ghosted Primary")
            else INTERVIEW_PERIOD_SECONDARY_DAYS
        )
        _elicit_back = p1_symptom.onset - timedelta(days=_ip_days)
        st.markdown(
            f"- **{result.case1_name} was likely infected on:** {_d1}  \n"
            f"- **Elicit contacts back to:** {_elicit_back}  \n"
            f"- **The likely source was infectious between:** "
            f"{result.ghosted_source.onset} and {result.ghosted_source.end}"
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Source lesion onset", str(result.ghosted_source.onset))
    m2.metric("Source lesion end", str(result.ghosted_source.end))
    m3.metric("Spread lesion onset", str(result.ghosted_spread.onset))
    m4.metric("Spread lesion end", str(result.ghosted_spread.end))

    # Scenario diagrams
    st.divider()
    st.subheader("Scenario diagrams")

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
                        x_range=x_range,
                    )
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as exc:
                    st.warning(f"Could not render {scenario} diagram: {exc}")
    else:
        st.info("No anchor symptom — diagrams cannot be rendered.")

    # Criteria
    st.divider()
    st.subheader("Criteria (average tier)")
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

    # Feedback
    if show_feedback:
        st.divider()
        st.subheader("Was this verdict reasonable?")
        with st.form(f"qv_feedback_form_{id(result)}", clear_on_submit=True):
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


# ---------------------------------------------------------------------------
# Multi-partner confidence ranking helpers
# ---------------------------------------------------------------------------

_CONF_RANK: dict[str, int] = {
    "Robust": 5, "Likely": 4, "Possible": 3, "Weak": 2, "Unlikely": 1, "Unrelated": 0
}


def _partner_infects_op_scenario(result, op_name: str):
    """Return the scenario result that evaluates 'did the partner infect the OP?'."""
    if result.case1_name == op_name:
        return result.source_scenarios   # source = case2 (partner) infected case1 (OP)
    return result.spread_scenarios       # spread = case1 (partner) infected case2 (OP)


def _partner_verdict_direction(result, op_name: str) -> int:
    """Return 1 if partner is clearly the source, -1 if OP is the source, 0 otherwise."""
    partner_sc = _partner_infects_op_scenario(result, op_name)
    op_sc = result.spread_scenarios if result.case1_name == op_name else result.source_scenarios
    p_rank = _CONF_RANK.get(partner_sc.confidence, 0)
    o_rank = _CONF_RANK.get(op_sc.confidence, 0)
    if p_rank > o_rank and p_rank >= 2:
        return 1
    if o_rank > p_rank and o_rank >= 2:
        return -1
    return 0


def _source_sort_key(item: dict, op_name: str, mode: str) -> tuple:
    sc = _partner_infects_op_scenario(item["result"], op_name)
    vdir = _partner_verdict_direction(item["result"], op_name)
    if mode == "Traditional VCA":
        return (vdir, 1 if _passes_expected(sc) else 0, 0)
    return (vdir, _CONF_RANK.get(sc.confidence, 0), sc.pass_count)


# ---------------------------------------------------------------------------
# Multi-partner results renderer
# ---------------------------------------------------------------------------

def _show_multi_results() -> None:
    multi_results = st.session_state["qv_multi_results"]
    op_name = st.session_state.get("qv_multi_op_name", "OP")
    mode = st.session_state.get("qv_mode", "Traditional VCA")

    ranked = sorted(
        multi_results,
        key=lambda item: _source_sort_key(item, op_name, mode),
        reverse=True,
    )

    # Summary table
    st.divider()
    st.subheader("Ranked Source Candidates")
    st.caption(
        f"Index patient: **{op_name}** · "
        f"{len(ranked)} contact(s) evaluated · "
        "Sorted by plausibility as source (highest first)"
    )

    _VDIR_LABEL = {1: "⬆ Contact → OP", -1: "⬇ OP → Contact", 0: "↔ Ambiguous / Unrelated"}

    table_rows = []
    for item in ranked:
        r = item["result"]
        sc = r.source_scenarios
        sp = r.spread_scenarios
        partner_sc = _partner_infects_op_scenario(r, op_name)
        contact_name = r.case2_name if r.case1_name == op_name else r.case1_name
        vdir = _partner_verdict_direction(r, op_name)

        if mode == "Traditional VCA":
            src_label = "✓ Pass" if _passes_expected(partner_sc) else "✗ Fail"
            tiers_label = "—"
        else:
            src_label = partner_sc.confidence
            tiers_label = f"{partner_sc.pass_count}/5"

        table_rows.append({
            "Contact": contact_name,
            "Direction": _VDIR_LABEL[vdir],
            f"Contact → {op_name}": src_label,
            "Tiers": tiers_label,
            "Verdict": _trad_verdict_strings(sc, sp, r.case1_name, r.case2_name)[2]
                       if mode == "Traditional VCA" else r.verdict,
        })

    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    # Best candidate banner
    best = ranked[0]
    best_name = best["result"].case2_name if best["result"].case1_name == op_name else best["result"].case1_name
    best_vdir = _partner_verdict_direction(best["result"], op_name)
    if best_vdir == 1:
        st.success(f"**Most plausible source: {best_name}**")
    elif best_vdir == -1:
        st.warning(
            f"No contact is a plausible source. The engine favors **{op_name}** spreading "
            f"to {best_name}. Manual review required."
        )
    else:
        st.warning(
            f"No contact meets the threshold for a directional conclusion. "
            f"Closest match: **{best_name}** — manual review required."
        )

    # CSV summary download
    buf = io.StringIO()
    pd.DataFrame(table_rows).to_csv(buf, index=False)
    st.download_button(
        "⬇ Download summary as CSV",
        buf.getvalue(),
        file_name=f"quickvca_multi_{date.today()}.csv",
        mime="text/csv",
    )

    # Per-pair detail in expanders
    st.divider()
    st.subheader("Pair Detail")
    st.caption("Each pair includes a full analysis and individual PDF download.")
    for i, item in enumerate(ranked):
        r = item["result"]
        contact_name = r.case2_name if r.case1_name == op_name else r.case1_name
        partner_sc = _partner_infects_op_scenario(r, op_name)
        if mode == "Traditional VCA":
            badge = "✓ Pass" if _passes_expected(partner_sc) else "✗ Fail"
        else:
            badge = f"{partner_sc.confidence} · {partner_sc.pass_count}/5 tiers"
        with st.expander(
            f"{'🥇' if i == 0 else f'#{i + 1}'} {contact_name} — {badge}",
            expanded=(i == 0),
        ):
            _show_pair_result(item["result"], item["inp"], show_feedback=False)

    # Shared feedback at the bottom
    st.divider()
    st.subheader("Feedback")
    with st.form("qv_multi_feedback_form", clear_on_submit=True):
        fb_contact = st.selectbox(
            "Which pair are you rating?",
            [
                (r["result"].case2_name if r["result"].case1_name == op_name else r["result"].case1_name)
                for r in ranked
            ],
        )
        rating = st.radio("Your assessment", ["Reasonable", "Unsure", "Wrong"], horizontal=True)
        note = st.text_input("Notes (optional)")
        if st.form_submit_button("Record feedback"):
            st.session_state["qv_feedback"].append(
                {"op": op_name, "contact": fb_contact, "rating": rating, "note": note}
            )
            st.success("Recorded.")

    if st.session_state["qv_feedback"]:
        fb_df = pd.DataFrame(st.session_state["qv_feedback"])
        buf2 = io.StringIO()
        fb_df.to_csv(buf2, index=False)
        st.download_button(
            f"⬇ Download feedback ({len(fb_df)} row(s)) as CSV",
            buf2.getvalue(),
            file_name="quickvca_feedback.csv",
            mime="text/csv",
        )


# ---------------------------------------------------------------------------
# Results dispatch
# ---------------------------------------------------------------------------

if _inv_mode == "Multi-Partner (OP + up to 5 contacts)":
    if "qv_multi_results" not in st.session_state:
        st.stop()
    _show_multi_results()
else:
    if "qv_result" not in st.session_state:
        st.stop()

    st.divider()
    st.subheader("Source / Spread Analysis")
    _show_pair_result(
        st.session_state["qv_result"],
        st.session_state["qv_inputs"],
        show_feedback=True,
    )
