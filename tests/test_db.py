# tests/test_db.py

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import Case, Partner, MAPEntry
from app.db.queries import (
    create_case,
    get_case_by_id,
    update_case,
    delete_case,
    search_cases,
    get_all_cases,
    create_partner,
    get_partners_for_case,
    upsert_map_entry,
    get_map_entries,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """
    Fresh in-memory SQLite database for each test.
    Tears down automatically — no cleanup needed.
    """
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_case(db):
    """A minimal saved case for tests that need an existing record."""
    return create_case(db, patient_name="Doe, Jane", lot="710")


@pytest.fixture
def sample_partner(db, sample_case):
    """Partner attached to sample_case."""
    return create_partner(db, case_id=sample_case.id, partner_number=1, name="Smith, John")


# ---------------------------------------------------------------------------
# Case CRUD
# ---------------------------------------------------------------------------

class TestCaseCRUD:

    def test_create_case_persists(self, db):
        case = create_case(db, patient_name="Doe, Jane")
        assert case.id is not None
        assert case.patient_name == "Doe, Jane"

    def test_create_case_with_optional_fields(self, db):
        case = create_case(
            db,
            patient_name="Doe, Jane",
            lot="710",
            case_manager="Smith",
            treatment_date=date(2024, 3, 15),
        )
        assert case.lot == "710"
        assert case.treatment_date == date(2024, 3, 15)

    def test_get_case_by_id_returns_correct_record(self, db, sample_case):
        fetched = get_case_by_id(db, sample_case.id)
        assert fetched.id == sample_case.id
        assert fetched.patient_name == "Doe, Jane"

    def test_get_case_by_id_returns_none_for_missing(self, db):
        assert get_case_by_id(db, 99999) is None

    def test_update_case_changes_fields(self, db, sample_case):
        updated = update_case(db, sample_case.id, lot="720", case_manager="Jones")
        assert updated.lot == "720"
        assert updated.case_manager == "Jones"

    def test_update_case_does_not_touch_other_fields(self, db, sample_case):
        update_case(db, sample_case.id, lot="720")
        refetched = get_case_by_id(db, sample_case.id)
        assert refetched.patient_name == "Doe, Jane"  # unchanged

    def test_update_nonexistent_case_returns_none(self, db):
        assert update_case(db, 99999, lot="710") is None

    def test_delete_case_removes_record(self, db, sample_case):
        case_id = sample_case.id
        assert delete_case(db, case_id) is True
        assert get_case_by_id(db, case_id) is None

    def test_delete_nonexistent_case_returns_false(self, db):
        assert delete_case(db, 99999) is False

    def test_get_all_cases_returns_all(self, db):
        create_case(db, patient_name="Alpha")
        create_case(db, patient_name="Beta")
        create_case(db, patient_name="Gamma")
        cases = get_all_cases(db)
        assert len(cases) == 3

    def test_search_cases_finds_partial_match(self, db):
        create_case(db, patient_name="Doe, Jane")
        create_case(db, patient_name="Smith, John")
        results = search_cases(db, "doe")
        assert len(results) == 1
        assert results[0].patient_name == "Doe, Jane"

    def test_search_cases_is_case_insensitive(self, db):
        create_case(db, patient_name="Doe, Jane")
        assert len(search_cases(db, "DOE")) == 1
        assert len(search_cases(db, "doe")) == 1

    def test_search_cases_returns_empty_for_no_match(self, db):
        create_case(db, patient_name="Doe, Jane")
        assert search_cases(db, "xyz") == []


# ---------------------------------------------------------------------------
# Partner CRUD
# ---------------------------------------------------------------------------

class TestPartnerCRUD:

    def test_create_partner_links_to_case(self, db, sample_case):
        partner = create_partner(db, case_id=sample_case.id, partner_number=1, name="Smith, John")
        assert partner.case_id == sample_case.id
        assert partner.partner_number == 1

    def test_get_partners_for_case_ordered_by_number(self, db, sample_case):
        create_partner(db, case_id=sample_case.id, partner_number=3, name="C")
        create_partner(db, case_id=sample_case.id, partner_number=1, name="A")
        create_partner(db, case_id=sample_case.id, partner_number=2, name="B")
        partners = get_partners_for_case(db, sample_case.id)
        assert [p.partner_number for p in partners] == [1, 2, 3]

    def test_get_partners_returns_empty_for_no_partners(self, db, sample_case):
        assert get_partners_for_case(db, sample_case.id) == []

    def test_delete_case_cascades_to_partners(self, db, sample_case, sample_partner):
        partner_id = sample_partner.id
        delete_case(db, sample_case.id)
        assert db.query(Partner).filter(Partner.id == partner_id).first() is None


# ---------------------------------------------------------------------------
# MAP entries
# ---------------------------------------------------------------------------

class TestMAPEntries:

    def test_upsert_creates_new_entry(self, db, sample_case):
        entry = upsert_map_entry(db, sample_case.id, item_number=1, p_value=True, c_value=False)
        assert entry.id is not None
        assert entry.p_value is True
        assert entry.c_value is False

    def test_upsert_updates_existing_entry(self, db, sample_case):
        upsert_map_entry(db, sample_case.id, item_number=1, p_value=False, c_value=False)
        updated = upsert_map_entry(db, sample_case.id, item_number=1, p_value=True, c_value=True)
        assert updated.p_value is True
        assert updated.c_value is True
        # Only one row should exist
        count = db.query(MAPEntry).filter(
            MAPEntry.case_id == sample_case.id,
            MAPEntry.item_number == 1,
        ).count()
        assert count == 1

    def test_get_map_entries_returns_dict_keyed_by_item(self, db, sample_case):
        upsert_map_entry(db, sample_case.id, item_number=5, p_value=True, c_value=False)
        upsert_map_entry(db, sample_case.id, item_number=12, p_value=False, c_value=True)
        entries = get_map_entries(db, sample_case.id)
        assert 5 in entries
        assert 12 in entries
        assert entries[5].p_value is True
        assert entries[12].c_value is True

    def test_map_entries_scoped_to_op_vs_partner(self, db, sample_case, sample_partner):
        upsert_map_entry(db, sample_case.id, item_number=1, p_value=True, c_value=False)
        upsert_map_entry(
            db, sample_case.id, item_number=1, p_value=False, c_value=True,
            partner_id=sample_partner.id,
        )
        op_entries = get_map_entries(db, sample_case.id, partner_id=None)
        partner_entries = get_map_entries(db, sample_case.id, partner_id=sample_partner.id)
        assert op_entries[1].p_value is True
        assert partner_entries[1].c_value is True