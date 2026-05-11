import streamlit as st

def check_password():
    if st.session_state.get("authenticated"):
        return True
    pw = st.text_input("Beta access password", type="password")
    if st.button("Enter"):
        if pw == st.secrets["BETA_PASSWORD"]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False

if not check_password():
    st.stop()

st.set_page_config(
    page_title="VCA Monitor",
    page_icon="🩺🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

from app.db.database import init_db
init_db()

st.title("Visual Case Analysis Monitor (VCA Monitor)")
st.write("Select a page from the sidebar to get started.")