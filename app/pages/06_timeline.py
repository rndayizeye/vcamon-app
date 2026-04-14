"""
app/pages/06_timeline.py

Timeline — monthly calendar view of partner activity dates.
Corresponds to the Chart / AddPartner2 sheets in the Excel file.

Displays a heatmap-style calendar grid showing when each partner
had treatment dates, lab work, or other recorded events.
Also shows a summary chart of activity by month.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from calendar import month_abbr

from app.db.database import SessionLocal
from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_partner_by_id,
)
from app.db.models import TimelineEvent
from app.utils.session_state import (
    init_session_state,
    get_active_case_id,
    set_active_partner_id,
)

st.set_page_config(page_title="Timeline — VCA Monitor", layout="wide")
init_session_state()


# ---------------------------------------------------------------------------
# Import Timeline event DB helpers
# ---------------------------------------------------------------------------

from app.db.queries import (
    get_case_by_id,
    get_partners_for_case,
    get_partner_by_id,
    get_timeline_events,
    create_timeline_event,
    delete_timeline_event,
)

EVENT_TYPES = [
    "Treatment",
    "Lab work",
    "Interview",
    "Re-interview",
    "Field visit",
    "Phone contact",
    "Other",
]

# Color map for event types
EVENT_COLORS = {
    "Treatment":     "#1D9E75",
    "Lab work":      "#378ADD",
    "Interview":     "#534AB7",
    "Re-interview":  "#7F77DD",
    "Field visit":   "#D85A30",
    "Phone contact": "#BA7517",
    "Other":         "#888780",
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
        case = get_case_by_id(db, case_id)
        partners = get_partners_for_case(db, case_id)

    if not case:
        st.error("Case not found.")
        st.stop()

    st.write(f"**#{case.id} — {case.patient_name}**")
    st.caption(f"Lot: {case.lot or '—'}  |  Manager: {case.case_manager or '—'}")
    st.divider()

    if st.button("← Network graph", use_container_width=True):
        st.switch_page("pages/05_network_graph.py")
    if st.button("← Dashboard", use_container_width=True):
        st.switch_page("pages/01_dashboard.py")


# ---------------------------------------------------------------------------
# Load all data
# ---------------------------------------------------------------------------

with SessionLocal() as db:
    events = get_timeline_events(db, case_id)

# Build partner lookup
partner_map: dict[int, str] = {0: f"OP — {case.patient_name}"}
partner_map.update({
    p.id: f"Partner {p.partner_number} — {p.name or 'Unnamed'}"
    for p in partners
})

# Auto-seed treatment dates from OP + partners if no events yet
def seed_treatment_dates():
    """Populate timeline events from existing treatment dates on first visit."""
    seeded = []
    with SessionLocal() as db:
        existing = get_timeline_events(db, case_id)
        existing_keys = {(e.event_date, e.partner_id) for e in existing}

        # OP treatment date
        if case.treatment_date:
            key = (case.treatment_date, None)
            if key not in existing_keys:
                create_timeline_event(
                    db, case_id,
                    event_date=case.treatment_date,
                    event_type="Treatment",
                    notes="Auto-seeded from OP form",
                    partner_id=None,
                )
                seeded.append("OP")

        # Partner treatment dates
        for p in partners:
            if p.treatment_date:
                key = (p.treatment_date, p.id)
                if key not in existing_keys:
                    create_timeline_event(
                        db, case_id,
                        event_date=p.treatment_date,
                        event_type="Treatment",
                        notes=f"Auto-seeded from partner {p.partner_number}",
                        partner_id=p.id,
                    )
                    seeded.append(f"Partner {p.partner_number}")

    return seeded


# Seed on first load (idempotent)
if not events:
    seeded = seed_treatment_dates()
    if seeded:
        with SessionLocal() as db:
            events = get_timeline_events(db, case_id)
        st.info(f"Auto-loaded treatment dates for: {', '.join(seeded)}")


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------

st.title("Case Timeline")
st.caption(
    f"Case #{case.id} — {case.patient_name}  |  "
    f"{len(events)} event{'s' if len(events) != 1 else ''} recorded"
)

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------

if events:
    dates = [e.event_date for e in events]
    earliest = min(dates)
    latest   = max(dates)
    span_days = (latest - earliest).days

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total events",  len(events))
    m2.metric("Earliest",      str(earliest))
    m3.metric("Latest",        str(latest))
    m4.metric("Span (days)",   span_days)

st.divider()

# ---------------------------------------------------------------------------
# Main content: chart + add event form
# ---------------------------------------------------------------------------

col_main, col_form = st.columns([3, 1])

with col_main:

    if not events:
        st.info(
            "No timeline events yet. Add treatment dates on the OP and Partner "
            "forms, or use the **Add event** panel to record additional activity."
        )
    else:
        # --- Build DataFrame ---
        rows = []
        for e in events:
            subject = partner_map.get(e.partner_id or 0, "OP")
            rows.append({
                "id":          e.id,
                "Date":        e.event_date,
                "Subject":     subject,
                "Event type":  e.event_type or "Other",
                "Notes":       e.notes or "",
                "Year":        e.event_date.year,
                "Month":       e.event_date.month,
                "Month name":  month_abbr[e.event_date.month],
                "Day":         e.event_date.day,
            })
        df = pd.DataFrame(rows)

        # ── Tab 1: Gantt-style scatter timeline ──────────────────────────
        tab1, tab2, tab3 = st.tabs(["Timeline view", "Monthly heatmap", "Event table"])

        with tab1:
            st.caption("Each dot is a recorded event. Hover for details.")

            fig = px.scatter(
                df,
                x="Date",
                y="Subject",
                color="Event type",
                color_discrete_map=EVENT_COLORS,
                hover_data=["Notes", "Event type"],
                size_max=14,
                height=max(300, len(partner_map) * 60 + 100),
            )
            fig.update_traces(marker=dict(size=12, opacity=0.85))
            fig.update_layout(
                xaxis_title="",
                yaxis_title="",
                legend_title="Event type",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(size=12),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)")
            fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)")
            st.plotly_chart(fig, use_container_width=True)

        # ── Tab 2: Monthly activity heatmap ──────────────────────────────
        with tab2:
            st.caption("Total events per subject per month.")

            # Pivot: subjects × months
            df["YearMonth"] = df["Date"].apply(
                lambda d: f"{d.year}-{str(d.month).zfill(2)}"
            )
            pivot = (
                df.groupby(["Subject", "YearMonth"])
                .size()
                .reset_index(name="Count")
            )

            if not pivot.empty:
                all_months = sorted(pivot["YearMonth"].unique())
                all_subjects = sorted(pivot["Subject"].unique())

                heat_data = []
                for subj in all_subjects:
                    row_vals = []
                    for ym in all_months:
                        val = pivot.loc[
                            (pivot["Subject"] == subj) & (pivot["YearMonth"] == ym),
                            "Count"
                        ]
                        row_vals.append(int(val.iloc[0]) if not val.empty else 0)
                    heat_data.append(row_vals)

                fig2 = go.Figure(data=go.Heatmap(
                    z=heat_data,
                    x=all_months,
                    y=all_subjects,
                    colorscale=[
                        [0.0, "#F1EFE8"],
                        [0.5, "#5DCAA5"],
                        [1.0, "#085041"],
                    ],
                    showscale=True,
                    hoverongaps=False,
                ))
                fig2.update_layout(
                    height=max(250, len(all_subjects) * 50 + 100),
                    xaxis_title="Month",
                    yaxis_title="",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=10, b=10),
                    font=dict(size=12),
                )
                st.plotly_chart(fig2, use_container_width=True)

        # ── Tab 3: Raw event table ────────────────────────────────────────
        with tab3:
            display_df = df[["Date", "Subject", "Event type", "Notes"]].copy()
            display_df["Date"] = display_df["Date"].astype(str)

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Event type": st.column_config.TextColumn("Event type", width="medium"),
                },
            )

            # Delete an event
            st.divider()
            st.caption("Remove an event:")
            event_options = {
                e.id: f"{e.event_date}  |  {partner_map.get(e.partner_id or 0, 'OP')}  |  {e.event_type}"
                for e in events
            }
            del_col1, del_col2 = st.columns([3, 1])
            with del_col1:
                del_id = st.selectbox(
                    "Select event",
                    options=list(event_options.keys()),
                    format_func=lambda k: event_options[k],
                    label_visibility="collapsed",
                )
            with del_col2:
                if st.button("✕  Remove", use_container_width=True):
                    with SessionLocal() as db:
                        delete_timeline_event(db, del_id)
                    st.success("Event removed.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Add event form (right column)
# ---------------------------------------------------------------------------

with col_form:
    st.subheader("Add event")

    subject_options = list(partner_map.items())  # [(id, label), ...]

    with st.form("add_event_form"):
        event_date = st.date_input(
            "Date",
            value=date.today(),
            min_value=date(2000, 1, 1),
            max_value=date.today() + timedelta(days=365),
            format="MM/DD/YYYY",
        )
        subject_id = st.selectbox(
            "Subject",
            options=[k for k, _ in subject_options],
            format_func=lambda k: partner_map[k],
        )
        event_type = st.selectbox("Event type", options=EVENT_TYPES)
        notes = st.text_area(
            "Notes",
            height=80,
            placeholder="Optional details...",
        )
        add_btn = st.form_submit_button(
            "➕  Add event",
            type="primary",
            use_container_width=True,
        )

    if add_btn:
        partner_id_val = subject_id if subject_id != 0 else None
        with SessionLocal() as db:
            create_timeline_event(
                db,
                case_id=case_id,
                event_date=event_date,
                event_type=event_type,
                notes=notes or None,
                partner_id=partner_id_val,
            )
        st.success(
            f"Added: {event_type} on {event_date} "
            f"for {partner_map[subject_id]}"
        )
        st.rerun()

    # Legend
    st.divider()
    st.caption("Event types")
    for etype, color in EVENT_COLORS.items():
        st.markdown(
            f'<span style="background:{color};color:#fff;padding:2px 8px;'
            f'border-radius:4px;font-size:11px;display:inline-block;'
            f'margin:2px 0">{etype}</span>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Partner treatment status summary
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Partner treatment status")

if not partners:
    st.info("No partners on file for this case.")
else:
    status_rows = []
    for p in partners:
        status_rows.append({
            "Partner #":       p.partner_number,
            "Name":            p.name or "—",
            "Treatment date":  str(p.treatment_date) if p.treatment_date else "Pending",
            "Lab 1":           p.lab_1 or "—",
            "Treatment":       p.treatment or "—",
            "Status":          "Treated" if p.treatment_date else "Pending",
        })

    status_df = pd.DataFrame(status_rows)

    def color_status(val):
        if val == "Treated":
            return "color: #0F6E56; font-weight: 500"
        elif val == "Pending":
            return "color: #854F0B; font-weight: 500"
        return ""

    st.dataframe(
        status_df.style.applymap(color_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Partner #": st.column_config.NumberColumn("Partner #", width="small"),
        },
    )

    treated = sum(1 for p in partners if p.treatment_date)
    pending = len(partners) - treated
    if pending:
        st.warning(
            f"{pending} partner{'s' if pending > 1 else ''} still pending treatment."
        )
    else:
        st.success("All partners have been treated.")
