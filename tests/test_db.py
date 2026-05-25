# tests/test_db.py

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.db.models import (
    MAPEntry,
    Partner,
    SymptomClassification,
    SymptomDateKind,
    SymptomDurationSource,
)
from app.db.models import (
    TestCategory as LabTestCategory,
)
from app.db.queries import (
    create_case,
    create_case_partner_relationship,
    create_lab_result_entry,
    create_partner,
    create_relationship_report,
    create_symptom_entry,
    create_timeline_event,
    delete_case,
    delete_case_partner_relationship,
    delete_lab_result_entry,
    delete_map_entries,
    delete_partner,
    delete_relationship_report,
    delete_symptom_entry,
    delete_timeline_event,
    get_all_cases,
    get_case_by_id,
    get_case_partner_relationship,
    get_case_partner_relationship_by_id,
    get_lab_result_entry_by_id,
    get_lab_results_for_case,
    get_map_entries,
    get_partners_for_case,
    get_relationship_report_by_id,
    get_reports_for_relationship,
    get_symptom_entry_by_id,
    get_symptoms_for_case,
    get_timeline_event_by_id,
    get_timeline_events,
    search_cases,
    update_case,
    update_case_partner_relationship,
    update_lab_result_entry,
    update_relationship_report,
    update_symptom_entry,
    update_timeline_event,
    upsert_map_entry,
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
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
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
    return create_partner(
        db, case_id=sample_case.id, partner_number=1, name="Smith, John"
    )


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
        partner = create_partner(
            db, case_id=sample_case.id, partner_number=1, name="Smith, John"
        )
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

    def test_delete_partner_removes_record(self, db, sample_case, sample_partner):
        partner_id = sample_partner.id
        assert delete_partner(db, partner_id) is True
        assert db.query(Partner).filter(Partner.id == partner_id).first() is None


# ---------------------------------------------------------------------------
# Relationship CRUD
# ---------------------------------------------------------------------------


class TestLabAndSymptomCRUD:
    def test_create_and_list_lab_results(self, db, sample_case):
        lab = create_lab_result_entry(
            db,
            case_id=sample_case.id,
            test_category=LabTestCategory.NON_TREPONEMAL,
            test_type="RPR",
            titer="1:8",
            collection_date=date(2024, 3, 1),
        )
        assert lab.id is not None
        assert get_lab_result_entry_by_id(db, lab.id) is not None
        assert [item.id for item in get_lab_results_for_case(db, sample_case.id)] == [
            lab.id
        ]

    def test_update_and_delete_lab_result(self, db, sample_case):
        lab = create_lab_result_entry(
            db,
            case_id=sample_case.id,
            test_category=LabTestCategory.TREPONEMAL,
            test_type="TP-AB",
            result="Reactive",
            collection_date=date(2024, 3, 2),
        )
        updated = update_lab_result_entry(db, lab.id, result="Non-reactive")
        assert updated is not None
        assert updated.result == "Non-reactive"
        assert delete_lab_result_entry(db, lab.id) is True
        assert get_lab_result_entry_by_id(db, lab.id) is None

    def test_create_and_update_symptom_entry(self, db, sample_case):
        entry = create_symptom_entry(
            db,
            case_id=sample_case.id,
            symptom_type="Penile LX",
            classification=SymptomClassification.PRIMARY,
            onset_date=date(2024, 2, 1),
            date_kind=SymptomDateKind.ONSET_REPORTED,
            duration_days=7,
            duration_source=SymptomDurationSource.REPORTED,
        )
        assert entry.id is not None
        assert [item.id for item in get_symptoms_for_case(db, sample_case.id)] == [
            entry.id
        ]

        updated = update_symptom_entry(
            db,
            entry.id,
            symptom_type="Rash",
            classification=SymptomClassification.SECONDARY,
            date_kind=SymptomDateKind.OBSERVED_DURING_EXAM,
            duration_source=SymptomDurationSource.ASSUMED_MAX,
            ongoing=True,
        )
        assert updated is not None
        assert updated.symptom_type == "Rash"
        assert updated.classification == SymptomClassification.SECONDARY
        assert updated.date_kind == SymptomDateKind.OBSERVED_DURING_EXAM
        assert updated.duration_source == SymptomDurationSource.ASSUMED_MAX
        assert updated.ongoing is True

    def test_delete_symptom_entry(self, db, sample_case):
        entry = create_symptom_entry(
            db,
            case_id=sample_case.id,
            symptom_type="Rash",
            classification=SymptomClassification.SECONDARY,
        )
        assert get_symptom_entry_by_id(db, entry.id) is not None
        assert delete_symptom_entry(db, entry.id) is True
        assert get_symptom_entry_by_id(db, entry.id) is None


class TestRelationshipCRUD:
    def test_create_relationship_persists(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(
            db,
            case_id=sample_case.id,
            partner_id=sample_partner.id,
            exposure_first_date=date(2024, 1, 1),
            exposure_last_date=date(2024, 1, 15),
            exposure_modalities='["Anal LX", "Oral LX"]',
        )
        assert rel.id is not None
        assert rel.exposure_first_date == date(2024, 1, 1)
        assert rel.exposure_modalities == '["Anal LX", "Oral LX"]'

    def test_get_relationship_returns_correct_record(
        self, db, sample_case, sample_partner
    ):
        create_case_partner_relationship(
            db,
            sample_case.id,
            sample_partner.id,
            exposure_first_date=date(2024, 1, 1),
        )
        fetched = get_case_partner_relationship(db, sample_case.id, sample_partner.id)
        assert fetched is not None
        assert fetched.exposure_first_date == date(2024, 1, 1)
        assert get_case_partner_relationship_by_id(db, fetched.id) is not None

    def test_update_relationship_changes_fields(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        updated = update_case_partner_relationship(
            db, rel.id, exposure_first_date=date(2024, 2, 1)
        )
        assert updated.exposure_first_date == date(2024, 2, 1)

    def test_delete_relationship_removes_record(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        rel_id = rel.id
        assert delete_case_partner_relationship(db, rel_id) is True
        assert (
            get_case_partner_relationship(db, sample_case.id, sample_partner.id) is None
        )


# ---------------------------------------------------------------------------
# RelationshipReport CRUD
# ---------------------------------------------------------------------------


class TestRelationshipReportCRUD:
    def test_create_report_persists(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        report = create_relationship_report(
            db,
            relationship_id=rel.id,
            reporter="OP",
            exposure_first_date=date(2024, 1, 1),
            exposure_last_date=date(2024, 1, 15),
            exposure_modalities='["Anal LX"]',
        )
        assert report.id is not None
        assert report.reporter == "OP"
        assert report.exposure_first_date == date(2024, 1, 1)

    def test_get_reports_for_relationship(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        create_relationship_report(db, rel.id, reporter="OP")
        create_relationship_report(db, rel.id, reporter="Partner")

        reports = get_reports_for_relationship(db, rel.id)
        assert len(reports) == 2
        assert {r.reporter for r in reports} == {"OP", "Partner"}

    def test_update_and_delete_report(self, db, sample_case, sample_partner):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        report = create_relationship_report(db, rel.id, reporter="OP")
        report_id = report.id

        updated = update_relationship_report(db, report_id, reporter="Partner 1")
        assert updated is not None
        assert updated.reporter == "Partner 1"
        assert get_relationship_report_by_id(db, report_id) is not None

        assert delete_relationship_report(db, report_id) is True
        assert len(get_reports_for_relationship(db, rel.id)) == 0

    def test_relationship_delete_cascades_to_reports(
        self, db, sample_case, sample_partner
    ):
        rel = create_case_partner_relationship(db, sample_case.id, sample_partner.id)
        create_relationship_report(db, rel.id, reporter="OP")

        rel_id = rel.id
        delete_case_partner_relationship(db, rel_id)

        # Verify no reports left for this relationship
        from app.db.models import RelationshipReport

        assert (
            db.query(RelationshipReport)
            .filter(RelationshipReport.relationship_id == rel_id)
            .count()
            == 0
        )


# ---------------------------------------------------------------------------
# Timeline CRUD
# ---------------------------------------------------------------------------


class TestTimelineCRUD:
    def test_create_list_update_and_delete_timeline_event(
        self, db, sample_case, sample_partner
    ):
        event = create_timeline_event(
            db,
            case_id=sample_case.id,
            partner_id=sample_partner.id,
            event_date=date(2024, 3, 5),
            event_type="Treatment",
            notes="Initial dose",
        )
        assert event.id is not None
        assert get_timeline_event_by_id(db, event.id) is not None
        assert [item.id for item in get_timeline_events(db, sample_case.id)] == [
            event.id
        ]

        updated = update_timeline_event(
            db, event.id, notes="Follow-up", event_type="Lab"
        )
        assert updated is not None
        assert updated.notes == "Follow-up"
        assert updated.event_type == "Lab"

        assert delete_timeline_event(db, event.id) is True
        assert get_timeline_event_by_id(db, event.id) is None


# ---------------------------------------------------------------------------
# MAP entries
# ---------------------------------------------------------------------------


class TestMAPEntries:
    def test_upsert_creates_new_entry(self, db, sample_case):
        entry = upsert_map_entry(
            db, sample_case.id, item_number=1, p_value=True, c_value=False
        )
        assert entry.id is not None
        assert entry.p_value is True
        assert entry.c_value is False

    def test_upsert_updates_existing_entry(self, db, sample_case):
        upsert_map_entry(
            db, sample_case.id, item_number=1, p_value=False, c_value=False
        )
        updated = upsert_map_entry(
            db, sample_case.id, item_number=1, p_value=True, c_value=True
        )
        assert updated.p_value is True
        assert updated.c_value is True
        # Only one row should exist
        count = (
            db.query(MAPEntry)
            .filter(
                MAPEntry.case_id == sample_case.id,
                MAPEntry.item_number == 1,
            )
            .count()
        )
        assert count == 1

    def test_get_map_entries_returns_dict_keyed_by_item(self, db, sample_case):
        upsert_map_entry(db, sample_case.id, item_number=5, p_value=True, c_value=False)
        upsert_map_entry(
            db, sample_case.id, item_number=12, p_value=False, c_value=True
        )
        entries = get_map_entries(db, sample_case.id)
        assert 5 in entries
        assert 12 in entries
        assert entries[5].p_value is True
        assert entries[12].c_value is True

    def test_map_entries_scoped_to_op_vs_partner(self, db, sample_case, sample_partner):
        upsert_map_entry(db, sample_case.id, item_number=1, p_value=True, c_value=False)
        upsert_map_entry(
            db,
            sample_case.id,
            item_number=1,
            p_value=False,
            c_value=True,
            partner_id=sample_partner.id,
        )
        op_entries = get_map_entries(db, sample_case.id, partner_id=None)
        partner_entries = get_map_entries(
            db, sample_case.id, partner_id=sample_partner.id
        )
        assert op_entries[1].p_value is True
        assert partner_entries[1].c_value is True

    def test_delete_map_entries_only_clears_requested_subject(
        self, db, sample_case, sample_partner
    ):
        upsert_map_entry(db, sample_case.id, item_number=1, p_value=True, c_value=False)
        upsert_map_entry(
            db,
            sample_case.id,
            item_number=2,
            p_value=False,
            c_value=True,
            partner_id=sample_partner.id,
        )

        deleted_partner = delete_map_entries(
            db, sample_case.id, partner_id=sample_partner.id
        )
        assert deleted_partner == 1
        assert 1 in get_map_entries(db, sample_case.id, partner_id=None)
        assert get_map_entries(db, sample_case.id, partner_id=sample_partner.id) == {}

        deleted_case = delete_map_entries(db, sample_case.id, partner_id=None)
        assert deleted_case == 1
        assert get_map_entries(db, sample_case.id, partner_id=None) == {}
