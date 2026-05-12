"""
app/pages/08_vca_chart.py

Visual Case Analysis (VCA) Timeline Chart.

The centrepiece visualisation of the tool — a Plotly timeline showing:
  - Exposure windows per person (dashed lines)
  - Symptom onset markers and duration bars
  - Lab result and treatment event markers
  - Critical period for the OP
  - Inoculation point markers (min / avg / max) calculated from clinical.py
  - Ghosted lesion windows from the ghosting analysis

Ported and redesigned from vca_app_v5/src/app.py, replacing dcc.Store
data sources with SQLAlchemy queries and integrating clinical.py inoculation
point calculations.

Color convention (matching VCA training materials):
  Exposure window (partner) : purple  #7F77DD  dashed
  Exposure window (OP)      : orange  #EF9F27  dotted
  Critical period           : green   #1D9E75  solid
  Inoculation points        : green   #1D9E75  diamond
  Lab result                : blue    #378ADD  circle
  Treatment                 : black   #2C2C2A  star
  Symptom onset             : red     #E24B4A  triangle-up
  Symptom duration bar      : red     #E24B4A  solid bar
  Ghosted source            : amber   #EF9F27  dashdot
  Ghosted spread            : coral   #D85A30  dashdot
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
import json

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_ghostings,
    get_timeline_events,
)
from app.utils.session_state import init_session_state, get_active_case_id, require_password
from app.utils.clinical import (
    Symptom, avg_inoculation_date,
    PRIMARY, INCUBATION,
)

st.set_page_config(page_title="VCA Chart — VCA Monitor", layout="wide")
init_session_state()
require_password()

# ---------------------------------------------------------------------------
# Clinical helper — inoculation points (min / avg / max)
# Ported from vca_app_v5 helper_functions.py
# ---------------------------------------------------------------------------

def _inoculation_points(symptom_type: str, onset: date, duration_days: int):
    """
    Return (min_date, avg_date, max_date) inoculation point estimates.
    Working backwards from symptom onset.
    """
    dur = duration_days if duration_days > 0 else PRIMARY["avg"]

    if symptom_type in ("Primary Chancre", "Historical Primary", "Ghosted Primary"):
        # Inoculation = onset - incubation
        avg_d = onset - timedelta(days=INCUBATION["avg"])
        min_d = onset - timedelta(days=INCUBATION["min"])
        max_d = onset - timedelta(days=INCUBATION["max"])
    elif symptom_type == "Secondary Rash/Lesions":
        from app.utils.clinical import LATENCY
        avg_d = onset - timedelta(days=INCUBATION["avg"] + PRIMARY["avg"] + LATENCY["avg"])
        min_d = onset - timedelta(days=INCUBATION["min"] + PRIMARY["min"] + LATENCY["min"])
        max_d = onset - timedelta(days=INCUBATION["max"] + PRIMARY["max"] + LATENCY["max"])
    else:
        return None, None, None

    return min_d, avg_d, max_d


# ---------------------------------------------------------------------------
# Color + style maps
# ---------------------------------------------------------------------------

COLORS = {
    "lab":              "#378ADD",
    "treatment":        "#2C2C2A",
    "symptom_onset":    "#E24B4A",
    "symptom_bar":      "#E24B4A",
    "exposure_partner": "#7F77DD",
    "exposure_op":      "#EF9F27",
    "critical":         "#1D9E75",
    "inoculation":      "#1D9E75",
    "ghosted_source":   "#EF9F27",
    "ghosted_spread":   "#D85A30",
    "interview":        "#1D9E75",
    "grid":             "rgba(180,178,169,0.25)",
}

SYMBOLS = {
    "lab":          "circle",
    "treatment":    "star",
    "symptom":      "triangle-up",
    "inoculation":  "diamond",
    "ghost_onset":  "diamond-open",
}

DASH = {
    "symptom_bar":      "solid",
    "exposure_partner": "dash",
    "exposure_op":      "dot",
    "critical":         "solid",
    "ghosted_source":   "dashdot",
    "ghosted_spread":   "dashdot",
    "interview":        "solid",
}

LINE_WIDTH = {
    "symptom_bar":      6,
    "exposure_partner": 5,
    "exposure_op":      5,
    "critical":         3,
    "ghosted_source":   4,
    "ghosted_spread":   4,
    "interview":        2,
}


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
        ghostings = get_ghostings(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")
    st.divider()

    show_durations  = st.toggle("Show symptom duration bars", value=True)
    show_inoc       = st.toggle("Show inoculation points",    value=True)
    show_ghosted    = st.toggle("Show ghosted lesions",       value=True)
    show_critical   = st.toggle("Show critical period",       value=True)
    show_interview  = st.toggle("Show interview period",      value=True)

    st.divider()
    if st.button("← Ghosting analysis", use_container_width=True):
        st.switch_page("pages/07_ghosting_analysis.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("VCA Timeline")
st.caption(
    f"Case #{case.id} — {case.patient_name}  |  "
    f"{len(partners)} partner{'s' if len(partners) != 1 else ''}  |  "
    f"{len(ghostings)} ghosting record{'s' if len(ghostings) != 1 else ''}"
)

# ---------------------------------------------------------------------------
# Collect all people and their data
# ---------------------------------------------------------------------------

# Build person list: OP first, then partners in order
people = []

# OP
op_entry = {
    "id":             "OP",
    "label":          f"{case.patient_name} (OP)",
    "lesion_type":    case.lesion_type,
    "symptom":        case.symptom,
    "treatment_date": case.treatment_date,
    "lab_1":          case.lab_1,
    "lab_2":          case.lab_2,
    "lot":            case.lot,
    "first_exposure": None,
    "last_exposure":  None,
    "sex_types":      [],
    "is_op":          True,
}
people.append(op_entry)

for p in partners:
    sex_raw = getattr(p, "sex_types", None)
    sex_list = []
    if sex_raw:
        try:
            sex_list = json.loads(sex_raw) if isinstance(sex_raw, str) else list(sex_raw)
        except Exception:
            sex_list = []

    people.append({
        "id":             str(p.partner_number),
        "label":          f"P{p.partner_number} — {p.name or 'Unnamed'}",
        "lesion_type":    p.lesion_type,
        "symptom":        p.symptom,
        "treatment_date": p.treatment_date,
        "lab_1":          p.lab_1,
        "lab_2":          p.lab_2,
        "lot":            p.lot,
        "first_exposure": getattr(p, "first_exposure", None),
        "last_exposure":  getattr(p, "last_exposure",  None),
        "sex_types":      sex_list,
        "is_op":          False,
    })

# Y-axis order: OP at top, partners below
y_order = [p["label"] for p in people]


# ---------------------------------------------------------------------------
# Determine date range
# ---------------------------------------------------------------------------

all_dates = []
for p in people:
    if p["treatment_date"]:
        all_dates.append(p["treatment_date"])
    if p["first_exposure"]:
        all_dates.append(p["first_exposure"])
    if p["last_exposure"]:
        all_dates.append(p["last_exposure"])

for g in ghostings:
    # Parse ghosted lesion dates from notes
    if g.notes:
        import re
        date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", g.notes)
        for dm in date_matches:
            try:
                all_dates.append(date.fromisoformat(dm))
            except ValueError:
                pass

if not all_dates:
    min_date = date.today() - timedelta(days=180)
    max_date = date.today() + timedelta(days=30)
else:
    min_date = min(all_dates) - timedelta(days=45)
    max_date = max(all_dates) + timedelta(days=45)


# ---------------------------------------------------------------------------
# Build Plotly figure
# ---------------------------------------------------------------------------

fig = go.Figure()
plotted_legends = set()


def _add_legend_once(key: str) -> bool:
    if key in plotted_legends:
        return False
    plotted_legends.add(key)
    return True


def _sym_type(person: dict) -> str:
    """Infer symptom type from ORM fields."""
    if person["lesion_type"]:
        return "Primary Chancre"
    sym = (person["symptom"] or "").lower()
    if any(k in sym for k in ["rash", "alopecia", "lata"]):
        return "Secondary Rash/Lesions"
    return None


def _sym_onset(person: dict):
    """Best proxy for symptom onset — treatment date is closest we have."""
    return person["treatment_date"]


# --- Draw per-person elements ---
for person in people:
    y = person["label"]
    sym_type  = _sym_type(person)
    sym_onset = _sym_onset(person)

    # --- Symptom duration bar ---
    if show_durations and sym_type and sym_onset:
        dur = PRIMARY["avg"]
        end = sym_onset + timedelta(days=dur)
        fig.add_trace(go.Scatter(
            x=[sym_onset, end], y=[y, y],
            mode="lines",
            line=dict(color=COLORS["symptom_bar"],
                      width=LINE_WIDTH["symptom_bar"],
                      dash=DASH["symptom_bar"]),
            name="Symptom duration",
            legendgroup="symptom_bar",
            showlegend=_add_legend_once("symptom_bar"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"{sym_type}<br>"
                f"Onset: {sym_onset}<br>"
                f"Est. end: {end}<extra></extra>"
            ),
        ))

    # --- Symptom onset marker ---
    if sym_type and sym_onset:
        fig.add_trace(go.Scatter(
            x=[sym_onset], y=[y],
            mode="markers",
            marker=dict(color=COLORS["symptom_onset"],
                        symbol=SYMBOLS["symptom"],
                        size=12),
            name="Symptom onset",
            legendgroup="symptom_onset",
            showlegend=_add_legend_once("symptom_onset"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"Symptom onset: {sym_onset}<br>"
                f"Type: {sym_type}<extra></extra>"
            ),
        ))

    # --- Inoculation points ---
    if show_inoc and sym_type and sym_onset:
        dur = PRIMARY["avg"]
        min_d, avg_d, max_d = _inoculation_points(sym_type, sym_onset, dur)
        inoc_dates  = [d for d in [min_d, avg_d, max_d] if d]
        inoc_labels = ["Min inoculation", "Avg inoculation", "Max inoculation"][:len(inoc_dates)]
        if inoc_dates:
            fig.add_trace(go.Scatter(
                x=inoc_dates, y=[y] * len(inoc_dates),
                mode="markers",
                marker=dict(color=COLORS["inoculation"],
                            symbol=SYMBOLS["inoculation"],
                            size=11),
                name="Inoculation points",
                legendgroup="inoculation",
                showlegend=_add_legend_once("inoculation"),
                hovertemplate="<b>" + y + "</b><br>%{text}<extra></extra>",
                text=inoc_labels,
            ))

    # --- Lab result marker ---
    if person["lab_1"] and sym_onset:
        lab_date = sym_onset  # best proxy
        fig.add_trace(go.Scatter(
            x=[lab_date], y=[y],
            mode="markers",
            marker=dict(color=COLORS["lab"],
                        symbol=SYMBOLS["lab"],
                        size=10),
            name="Lab result",
            legendgroup="lab",
            showlegend=_add_legend_once("lab"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"Lab: {person['lab_1']}"
                + (f" / {person['lab_2']}" if person["lab_2"] else "")
                + f"<br>Lot: {person['lot'] or '—'}<extra></extra>"
            ),
        ))

    # --- Treatment marker ---
    if person["treatment_date"]:
        fig.add_trace(go.Scatter(
            x=[person["treatment_date"]], y=[y],
            mode="markers",
            marker=dict(color=COLORS["treatment"],
                        symbol=SYMBOLS["treatment"],
                        size=13),
            name="Treatment",
            legendgroup="treatment",
            showlegend=_add_legend_once("treatment"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"Treatment: {person['treatment_date']}<extra></extra>"
            ),
        ))

    # --- Exposure window ---
    if person["first_exposure"] and person["last_exposure"]:
        exp_key   = "exposure_op" if person["is_op"] else "exposure_partner"
        exp_label = "OP elicited exposure" if person["is_op"] else "Partner reported exposure"
        fig.add_trace(go.Scatter(
            x=[person["first_exposure"], person["last_exposure"]],
            y=[y, y],
            mode="lines",
            line=dict(color=COLORS[exp_key],
                      width=LINE_WIDTH[exp_key],
                      dash=DASH[exp_key]),
            name=exp_label,
            legendgroup=exp_key,
            showlegend=_add_legend_once(exp_key),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"{exp_label}<br>"
                f"{person['first_exposure']} → {person['last_exposure']}<extra></extra>"
            ),
        ))

    # --- Critical period (OP only) ---
    if show_critical and person["is_op"] and sym_onset:
        min_inoc, _, _ = _inoculation_points(sym_type or "Primary Chancre", sym_onset, PRIMARY["avg"])
        crit_start = min_inoc or (sym_onset - timedelta(days=INCUBATION["max"] + PRIMARY["max"]))
        crit_end   = person["treatment_date"] or max_date
        fig.add_trace(go.Scatter(
            x=[crit_start, crit_end], y=[y, y],
            mode="lines",
            line=dict(color=COLORS["critical"],
                      width=LINE_WIDTH["critical"],
                      dash=DASH["critical"]),
            name="Critical period",
            legendgroup="critical",
            showlegend=_add_legend_once("critical"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"Critical period<br>"
                f"{crit_start} → {crit_end}<extra></extra>"
            ),
        ))

    # --- Interview period (OP only) ---
    if show_interview and person["is_op"] and sym_onset:
        from app.utils.clinical import INTERVIEW_PERIOD_PRIMARY_DAYS
        interview_start = sym_onset - timedelta(days=INTERVIEW_PERIOD_PRIMARY_DAYS)
        interview_end   = person["treatment_date"] or max_date
        fig.add_trace(go.Scatter(
            x=[interview_start, interview_end], y=[y, y],
            mode="lines",
            line=dict(color=COLORS["interview"],
                      width=LINE_WIDTH["interview"],
                      dash=DASH["interview"]),
            name="Interview period",
            legendgroup="interview",
            showlegend=_add_legend_once("interview"),
            hovertemplate=(
                f"<b>{y}</b><br>"
                f"Interview period<br>"
                f"{interview_start} → {interview_end}<extra></extra>"
            ),
        ))


# --- Ghosted lesions ---
if show_ghosted:
    partner_ref_map = {str(p.partner_number): f"P{p.partner_number} — {p.name or 'Unnamed'}"
                       for p in partners}
    partner_ref_map["OP"] = f"{case.patient_name} (OP)"

    for g in ghostings:
        # Parse onset/end from notes field
        import re
        date_matches = re.findall(r"\d{4}-\d{2}-\d{2}", g.notes or "")
        if len(date_matches) < 2:
            continue
        try:
            g_onset = date.fromisoformat(date_matches[0])
            g_end   = date.fromisoformat(date_matches[1])
        except ValueError:
            continue

        # Which y row does this belong to — the "to" party
        y_ref = partner_ref_map.get(g.to_ref, g.to_ref or "Unknown")

        is_source = "source" in (g.ghosting_type or "").lower()
        gkey      = "ghosted_source" if is_source else "ghosted_spread"
        glabel    = "Ghosted source lesion" if is_source else "Ghosted spread lesion"

        fig.add_trace(go.Scatter(
            x=[g_onset, g_end], y=[y_ref, y_ref],
            mode="lines",
            line=dict(color=COLORS[gkey],
                      width=LINE_WIDTH[gkey],
                      dash=DASH[gkey]),
            name=glabel,
            legendgroup=gkey,
            showlegend=_add_legend_once(gkey),
            hovertemplate=(
                f"<b>{y_ref}</b><br>"
                f"{glabel}<br>"
                f"{g_onset} → {g_end}<br>"
                f"From: {partner_ref_map.get(g.from_ref, g.from_ref or '?')}"
                f"<extra></extra>"
            ),
        ))

        # Onset + end markers for ghosted lesions
        fig.add_trace(go.Scatter(
            x=[g_onset, g_end], y=[y_ref, y_ref],
            mode="markers",
            marker=dict(color=COLORS[gkey],
                        symbol=SYMBOLS["ghost_onset"],
                        size=9),
            showlegend=False,
            hoverinfo="skip",
        ))


# --- Grid lines per person ---
for y in y_order:
    fig.add_shape(
        type="line",
        x0=min_date, y0=y,
        x1=max_date, y1=y,
        line=dict(color=COLORS["grid"], width=1, dash="dot"),
    )


# --- Layout ---
fig.update_layout(
    height=max(350, len(people) * 90 + 120),
    xaxis=dict(
        title="",
        type="date",
        range=[min_date, max_date],
        showgrid=True,
        gridcolor=COLORS["grid"],
        dtick="M1",
        tickformat="%b %Y",
        tickangle=-30,
    ),
    yaxis=dict(
        title="",
        categoryorder="array",
        categoryarray=list(reversed(y_order)),  # OP at top
        showgrid=False,
    ),
    legend=dict(
        orientation="h",
        y=1.02, x=0,
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor="rgba(180,178,169,0.4)",
        borderwidth=1,
        tracegroupgap=5,
    ),
    hovermode="closest",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=20, t=80, b=60),
    font=dict(size=12),
)

st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Legend key (plain text below chart)
# ---------------------------------------------------------------------------

with st.expander("Chart legend", expanded=False):
    col1, col2, col3 = st.columns(3)
    legend_items = [
        ("Symptom onset",           "▲", COLORS["symptom_onset"]),
        ("Symptom duration",        "━", COLORS["symptom_bar"]),
        ("Lab result",              "●", COLORS["lab"]),
        ("Treatment",               "★", COLORS["treatment"]),
        ("Inoculation points",      "◆", COLORS["inoculation"]),
        ("Critical period",         "━", COLORS["critical"]),
        ("Interview period",        "╌", COLORS["interview"]),
        ("Partner exposure window", "╌", COLORS["exposure_partner"]),
        ("OP elicited exposure",    "·····", COLORS["exposure_op"]),
        ("Ghosted source lesion",   "╌·╌", COLORS["ghosted_source"]),
        ("Ghosted spread lesion",   "╌·╌", COLORS["ghosted_spread"]),
    ]
    cols = [col1, col2, col3]
    for i, (label, symbol, color) in enumerate(legend_items):
        cols[i % 3].markdown(
            f'<span style="color:{color};font-size:16px">{symbol}</span> '
            f'<span style="font-size:13px">{label}</span>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Data completeness notice
# ---------------------------------------------------------------------------

missing = []
if not case.treatment_date and not case.lesion_type:
    missing.append("OP has no treatment date or lesion type — symptom timeline cannot be plotted")
for p in partners:
    if not getattr(p, "first_exposure", None):
        missing.append(f"Partner {p.partner_number} ({p.name or 'Unnamed'}) has no exposure dates")

if missing:
    with st.expander(f"⚠ {len(missing)} data gap(s) affecting chart", expanded=False):
        for m in missing:
            st.caption(f"• {m}")
        st.caption(
            "Add missing data on the OP Form, Partner Form, or Ghosting Analysis page "
            "then return here to refresh."
        )
