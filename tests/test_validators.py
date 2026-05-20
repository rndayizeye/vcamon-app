# tests/test_validators.py

from datetime import date, timedelta
from app.utils.validators import (
    validate_op_form,
    validate_partner_form,
    validate_arrow_link,
)


class TestOpFormValidation:

    def test_valid_form_returns_no_errors(self):
        errors = validate_op_form("Doe, Jane", date.today())
        assert errors == []

    def test_missing_patient_name_is_invalid(self):
        errors = validate_op_form("", date.today())
        assert any("name" in e.lower() for e in errors)

    def test_whitespace_only_name_is_invalid(self):
        errors = validate_op_form("   ", date.today())
        assert any("name" in e.lower() for e in errors)

    def test_future_treatment_date_is_invalid(self):
        future = date.today() + timedelta(days=1)
        errors = validate_op_form("Doe, Jane", future)
        assert any("future" in e.lower() for e in errors)

    def test_today_treatment_date_is_valid(self):
        errors = validate_op_form("Doe, Jane", date.today())
        assert not any("future" in e.lower() for e in errors)


class TestPartnerFormValidation:

    def test_valid_partner_name(self):
        assert validate_partner_form("Smith, John") == []

    def test_empty_name_is_invalid(self):
        errors = validate_partner_form("")
        assert len(errors) > 0

    def test_whitespace_name_is_invalid(self):
        errors = validate_partner_form("   ")
        assert len(errors) > 0


class TestArrowLinkValidation:

    def test_valid_link(self):
        assert validate_arrow_link("OP", "1") == []

    def test_self_link_is_invalid(self):
        errors = validate_arrow_link("1", "1")
        assert any("themselves" in e.lower() for e in errors)

    def test_missing_from_is_invalid(self):
        errors = validate_arrow_link("", "1")
        assert len(errors) > 0

    def test_missing_to_is_invalid(self):
        errors = validate_arrow_link("OP", "")
        assert len(errors) > 0

    def test_op_to_partner_is_valid(self):
        assert validate_arrow_link("OP", "2") == []

    def test_partner_to_partner_is_valid(self):
        assert validate_arrow_link("1", "3") == []