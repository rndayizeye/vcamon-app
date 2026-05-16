import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="VCA Monitor",
    page_icon="🩺🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.db.database import SessionLocal, init_db
from app.db.queries import create_case, get_all_cases

init_db()


def seed_demo_data():
    try:
        with SessionLocal() as db:
            if not get_all_cases(db):
                create_case(
                    db,
                    patient_name="Demo, Patient",
                    lot="710",
                    case_manager="Beta Tester",
                )
    except Exception as e:
        st.warning(f"Could not seed demo data: {e}")

seed_demo_data()


def check_password():
    if st.session_state.get("authenticated"):
        return True
    st.subheader("VCA Monitor — Beta Access")
    pw = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pw == st.secrets["BETA_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

st.title("Visual Case Analysis Monitor (VCA Monitor)")
st.write("Select a page from the sidebar to get started.")
