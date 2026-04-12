# app/components/dropdowns.py

from app.db.models import ReasonForExam, LabResult, TreponemalResult, Treatment, LesionType, Symptom
import streamlit as st

def enum_options(enum_cls) -> list[str]:
    return [""] + [e.value for e in enum_cls]

def val_or_none(v: str):
    return v if v else None

def reason_for_exam_select(current_value=None):
    opts = enum_options(ReasonForExam)
    idx = opts.index(current_value or "")
    return st.selectbox("Reason for exam", opts, index=idx)

def lab_1_select(current_value=None):
    opts = enum_options(LabResult)
    idx = opts.index(current_value or "")
    return st.selectbox("Lab 1 — RPR / VDRL", opts, index=idx)

def lab_2_select(current_value=None):
    opts = enum_options(TreponemalResult)
    idx = opts.index(current_value or "")
    return st.selectbox("Lab 2 — Treponemal", opts, index=idx)

def treatment_select(current_value=None):
    opts = enum_options(Treatment)
    idx = opts.index(current_value or "")
    return st.selectbox("Treatment given", opts, index=idx)

def lesion_select(current_value=None):
    opts = enum_options(LesionType)
    idx = opts.index(current_value or "")
    return st.selectbox("Lesion type", opts, index=idx)

def symptom_select(current_value=None):
    opts = enum_options(Symptom)
    idx = opts.index(current_value or "")
    return st.selectbox("Symptom", opts, index=idx)