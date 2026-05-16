# app/utils/validators.py

from datetime import date


def validate_op_form(
    patient_name: str,
    treatment_date: date | None,
) -> list[str]:
    """
    Returns a list of error messages. Empty list = valid.
    Call before saving in 02_op_form.py and 03_partner_form.py.
    """
    errors = []

    if not patient_name or not patient_name.strip():
        errors.append("Patient name is required.")

    if treatment_date and treatment_date > date.today():
        errors.append("Treatment date cannot be in the future.")

    return errors


def validate_partner_form(partner_name: str) -> list[str]:
    errors = []
    if not partner_name or not partner_name.strip():
        errors.append("Partner name is required.")
    return errors


def validate_arrow_link(from_ref: str, to_ref: str) -> list[str]:
    errors = []
    if not from_ref or not to_ref:
        errors.append("Both source and target are required.")
    if from_ref == to_ref:
        errors.append("A partner cannot link to themselves.")
    return errors