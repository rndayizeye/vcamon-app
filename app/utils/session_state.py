# app/utils/session_state.py

import streamlit as st


def require_password():
    """Call at the top of every page to enforce the beta password gate."""
    if st.session_state.get("authenticated"):
        return
    st.warning("Please log in from the main page.")
    st.stop()

# Central registry of all session state keys used in the app.
# Import these constants instead of using raw strings.

ACTIVE_CASE_ID   = "active_case_id"
ACTIVE_PARTNER_ID = "active_partner_id"
LAST_SAVED_MSG   = "last_saved_msg"
FORM_DIRTY       = "form_dirty"


def init_session_state():
    """
    Call once at the top of every page to ensure all keys exist.
    Prevents KeyError on first load before any values are set.
    """
    defaults = {
        ACTIVE_CASE_ID:    None,
        ACTIVE_PARTNER_ID: None,
        LAST_SAVED_MSG:    None,
        FORM_DIRTY:        False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def get_active_case_id() -> int | None:
    return st.session_state.get(ACTIVE_CASE_ID)

def set_active_case_id(case_id: int | None):
    st.session_state[ACTIVE_CASE_ID] = case_id

def get_active_partner_id() -> int | None:
    return st.session_state.get(ACTIVE_PARTNER_ID)

def set_active_partner_id(partner_id: int | None):
    st.session_state[ACTIVE_PARTNER_ID] = partner_id

def clear_active_case():
    st.session_state[ACTIVE_CASE_ID] = None
    st.session_state[ACTIVE_PARTNER_ID] = None
    st.session_state[FORM_DIRTY] = False