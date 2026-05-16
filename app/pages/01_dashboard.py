"""
app/pages/01_dashboard.py

Case list dashboard — the entry point to the application.
Displays all cases in a searchable table, shows summary metrics,
and lets the user open a case (routing to the OP form) or create a new one.
"""


import pandas as pd
import streamlit as st

from app.db.database import SessionLocal
from app.db.queries import get_all_cases, get_partners_for_case, search_cases
from app.utils.session_state import (
    init_session_state,
    require_password,
    set_active_case_id,
    set_active_partner_id,
)

st.set_page_config(
    page_title="Dashboard — VCA Monitor",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_session_state()
require_password()
# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_dashboard_data(search_term: str = "") -> tuple[list, dict]:
    """
    Returns (cases, partner_counts).
    partner_counts is a dict of {case_id: int}.
    """
    with SessionLocal() as db:
        if search_term.strip():
            cases = search_cases(db, search_term)
        else:
            cases = get_all_cases(db)

        partner_counts = {}
        for c in cases:
            partners = get_partners_for_case(db, c.id)
            partner_counts[c.id] = len(partners)

    return cases, partner_counts


def cases_to_dataframe(cases, partner_counts: dict) -> pd.DataFrame:
    """Convert case objects to a display-ready DataFrame."""
    rows = []
    for c in cases:
        rows.append({
            "ID":             c.id,
            "Patient name":   c.patient_name,
            "Lot":            c.lot or "—",
            "Case manager":   c.case_manager or "—",
            "Reason":         c.reason_for_exam or "—",
            "Treatment date": str(c.treatment_date) if c.treatment_date else "—",
            "Lab 1":          c.lab_1 or "—",
            "Partners":       partner_counts.get(c.id, 0),
            "Last updated":   c.updated_at.strftime("%Y-%m-%d %H:%M") if c.updated_at else "—",
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("VCA Monitor")
st.caption("Contact tracing and case management")

st.divider()

# ---------------------------------------------------------------------------
# Search + actions bar
# ---------------------------------------------------------------------------

col_search, col_new = st.columns([4, 1])

with col_search:
    search_term = st.text_input(
        "Search cases",
        placeholder="Type a patient name...",
        label_visibility="collapsed",
    )

with col_new:
    if st.button("➕  New case", type="primary", use_container_width=True):
        set_active_case_id(None)
        set_active_partner_id(None)
        st.switch_page("pages/02_op_form.py")

# ---------------------------------------------------------------------------
# Load + metrics row
# ---------------------------------------------------------------------------

cases, partner_counts = load_dashboard_data(search_term)

total_cases    = len(cases)
total_partners = sum(partner_counts.values())
treated_count  = sum(1 for c in cases if c.treatment_date is not None)
untreated      = total_cases - treated_count

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total cases",    total_cases)
m2.metric("Total partners", total_partners)
m3.metric("Treated",        treated_count)
m4.metric("Pending treatment", untreated,
          delta=f"-{untreated}" if untreated else None,
          delta_color="inverse")

st.divider()

# ---------------------------------------------------------------------------
# Case table
# ---------------------------------------------------------------------------

if not cases:
    if search_term:
        st.info(f"No cases found matching **{search_term}**.")
    else:
        st.info("No cases yet. Click **➕ New case** to get started.")
else:
    df = cases_to_dataframe(cases, partner_counts)

    # Highlight rows where no treatment date is set
    def highlight_untreated(row):
        if row["Treatment date"] == "—":
            return ["background-color: #fff8e1"] * len(row)
        return [""] * len(row)

    st.caption(f"Showing {len(cases)} case{'s' if len(cases) != 1 else ''}"
               + (f" matching '{search_term}'" if search_term else ""))

    # Render the styled table
    st.dataframe(
        df.style.apply(highlight_untreated, axis=1),
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Partners": st.column_config.NumberColumn("Partners", width="small"),
            "Treatment date": st.column_config.TextColumn("Treatment date", width="medium"),
            "Last updated": st.column_config.TextColumn("Last updated", width="medium"),
        },
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Open a case
    # ---------------------------------------------------------------------------

    st.subheader("Open a case")

    col_select, col_open, col_partners = st.columns([3, 1, 1])

    case_options = {c.id: f"#{c.id} — {c.patient_name}" for c in cases}

    with col_select:
        selected_id = st.selectbox(
            "Select case to open",
            options=list(case_options.keys()),
            format_func=lambda k: case_options[k],
            label_visibility="collapsed",
        )

    with col_open:
        if st.button("Open OP form", use_container_width=True, type="primary"):
            set_active_case_id(selected_id)
            set_active_partner_id(None)
            st.switch_page("pages/02_op_form.py")

    with col_partners:
        if st.button("Open partners", use_container_width=True):
            set_active_case_id(selected_id)
            set_active_partner_id(None)
            st.switch_page("pages/03_partner_form.py")

    # Inline summary of the selected case
    if selected_id:
        selected_case = next((c for c in cases if c.id == selected_id), None)
        if selected_case:
            with st.expander(f"Quick view — {selected_case.patient_name}", expanded=True):
                q1, q2, q3, q4, q5 = st.columns(5)
                q1.metric("Lot",            selected_case.lot or "—")
                q2.metric("Case manager",   selected_case.case_manager or "—")
                q3.metric("Reason",         selected_case.reason_for_exam or "—")
                
                # Sync the summary view with the latest lab result
                with SessionLocal() as db:
                    from app.db.queries import get_lab_results_for_case
                    latest_labs = get_lab_results_for_case(db, selected_case.id)
                    lab_display = "—"
                    if latest_labs:
                        latest = latest_labs[-1]
                        lab_display = f"{latest.test_type}: {latest.titer or latest.result or 'N/A'}"
                
                q4.metric("Latest Lab",      lab_display)
                q5.metric("Partners",       partner_counts.get(selected_id, 0))

                if selected_case.medical_info:
                    st.caption("Medical info")
                    st.write(selected_case.medical_info)

                nav1, nav2, nav3 = st.columns(3)
                with nav1:
                    if st.button("MAP sheet", key="nav_map", use_container_width=True):
                        set_active_case_id(selected_id)
                        st.switch_page("pages/04_map_sheet.py")
                with nav2:
                    if st.button("Network graph", key="nav_net", use_container_width=True):
                        set_active_case_id(selected_id)
                        st.switch_page("pages/05_network_graph.py")
                with nav3:
                    if st.button("Timeline", key="nav_tl", use_container_width=True):
                        set_active_case_id(selected_id)
                        st.switch_page("pages/06_timeline.py")
