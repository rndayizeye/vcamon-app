import streamlit as st

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