# app/components/sidebar_case_selector.py

import streamlit as st
from app.db.database import SessionLocal
from app.db.queries import get_all_cases

def render_sidebar() -> int | None:
    """
    Renders the case selector in the sidebar.
    Returns the active case_id, or None if 'New case' is selected.
    Sets st.session_state['active_case_id'].
    """
    with st.sidebar:
        st.header("Active case")
        with SessionLocal() as db:
            all_cases = get_all_cases(db)

        options = {0: "➕  New case"}
        options.update({c.id: f"#{c.id} — {c.patient_name}" for c in all_cases})

        current = st.session_state.get("active_case_id", 0)
        idx = list(options.keys()).index(current) if current in options else 0

        selected = st.selectbox(
            "Select case",
            options=list(options.keys()),
            format_func=lambda k: options[k],
            index=idx,
        )
        st.session_state["active_case_id"] = selected if selected != 0 else None

        if selected:
            st.caption(f"Case ID: {selected}")

        return st.session_state["active_case_id"]