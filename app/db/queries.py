"""
app/db/queries.py

Database access functions for the vcamon app.
Each page imports only what it needs — functions are added here
as new pages are built rather than all upfront.
"""

import json
from datetime import date
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    ArrowLink,
    Case,
    CasePartnerRelationship,
    Ghosting,
    LabResultEntry,
    MAPEntry,
    Partner,
    Person,
    RelationshipReport,
    SUBJECT_FIELDS,
    Subject,
    SymptomDateKind,
    SymptomDurationSource,
    SymptomEntry,
    TimelineEvent,
)


# ---------------------------------------------------------------------------
# Subject helpers
# ---------------------------------------------------------------------------


def _split_subject_kwargs(kwargs: dict) -> tuple[dict, dict]:
    """Split kwargs into (subject_fields, non_subject_fields)."""
    subject_kw = {k: v for k, v in kwargs.items() if k in SUBJECT_FIELDS}
    other_kw = {k: v for k, v in kwargs.items() if k not in SUBJECT_FIELDS}
    return subject_kw, other_kw


# ---------------------------------------------------------------------------
# CasePartnerRelationship queries
# ---------------------------------------------------------------------------


def get_case_partner_relationship(
    db: Session, case_id: int, partner_id: int
) -> CasePartnerRelationship | None:
    """Retrieve a specific relationship entry."""
    return (
        db.query(CasePartnerRelationship)
        .filter(
            CasePartnerRelationship.case_id == case_id,
            CasePartnerRelationship.partner_id == partner_id,
        )
        .first()
    )


def get_case_partner_relationship_by_id(
    db: Session, relationship_id: int
) -> CasePartnerRelationship | None:
    """Retrieve a relationship entry by ID."""
    return (
        db.query(CasePartnerRelationship)
        .filter(CasePartnerRelationship.id == relationship_id)
        .first()
    )


def _serialize_body_parts(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return json.dumps(value) if value else None
    return value  # already a string


def create_case_partner_relationship(
    db: Session,
    case_id: int,
    partner_id: int,
    exposure_first_date: date | None = None,
    exposure_last_date: date | None = None,
    op_body_parts: Any = None,
    partner_body_parts: Any = None,
) -> CasePartnerRelationship:
    """Create a new relationship entry."""
    rel = CasePartnerRelationship(
        case_id=case_id,
        partner_id=partner_id,
        exposure_first_date=exposure_first_date,
        exposure_last_date=exposure_last_date,
        op_body_parts=_serialize_body_parts(op_body_parts),
        partner_body_parts=_serialize_body_parts(partner_body_parts),
    )
    db.add(rel)
    db.flush()
    db.refresh(rel)
    return rel


def update_case_partner_relationship(
    db: Session, relationship_id: int, **kwargs
) -> CasePartnerRelationship | None:
    """Update an existing relationship entry."""
    rel = get_case_partner_relationship_by_id(db, relationship_id)
    if not rel:
        return None
    for field, value in kwargs.items():
        if field in ("op_body_parts", "partner_body_parts"):
            value = _serialize_body_parts(value)
        setattr(rel, field, value)
    db.flush()
    db.refresh(rel)
    return rel


def delete_case_partner_relationship(db: Session, relationship_id: int) -> bool:
    """Delete a relationship entry."""
    rel = get_case_partner_relationship_by_id(db, relationship_id)
    if not rel:
        return False
    db.delete(rel)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# RelationshipReport queries
# ---------------------------------------------------------------------------


def get_reports_for_relationship(
    db: Session, relationship_id: int
) -> list[RelationshipReport]:
    """Retrieve all reports for a specific relationship."""
    return (
        db.query(RelationshipReport)
        .filter(RelationshipReport.relationship_id == relationship_id)
        .order_by(RelationshipReport.created_at.desc(), RelationshipReport.id.desc())
        .all()
    )


def get_relationship_report_by_id(
    db: Session, report_id: int
) -> RelationshipReport | None:
    """Retrieve a specific report by ID."""
    return db.query(RelationshipReport).filter(RelationshipReport.id == report_id).first()


def create_relationship_report(
    db: Session,
    relationship_id: int,
    reporter: str,
    exposure_first_date: date | None = None,
    exposure_last_date: date | None = None,
    exposure_modalities: str | None = None,
) -> RelationshipReport:
    """Create a new evidence report."""
    report = RelationshipReport(
        relationship_id=relationship_id,
        reporter=reporter,
        exposure_first_date=exposure_first_date,
        exposure_last_date=exposure_last_date,
        exposure_modalities=exposure_modalities,
    )
    db.add(report)
    db.flush()
    db.refresh(report)
    return report


def delete_relationship_report(db: Session, report_id: int) -> bool:
    """Delete a specific report."""
    report = get_relationship_report_by_id(db, report_id)
    if not report:
        return False
    db.delete(report)
    db.flush()
    return True


def update_relationship_report(
    db: Session, report_id: int, **kwargs
) -> RelationshipReport | None:
    """Update an existing evidence report."""
    report = get_relationship_report_by_id(db, report_id)
    if not report:
        return None
    for field, value in kwargs.items():
        setattr(report, field, value)
    db.flush()
    db.refresh(report)
    return report


# ---------------------------------------------------------------------------
# LabResultEntry queries
# ---------------------------------------------------------------------------


def get_lab_results(db: Session, subject_id: int) -> list[LabResultEntry]:
    """Retrieve all lab results for a given subject."""
    return (
        db.query(LabResultEntry)
        .filter(LabResultEntry.subject_id == subject_id)
        .order_by(LabResultEntry.collection_date, LabResultEntry.id)
        .all()
    )


def get_lab_results_for_case(db: Session, case_id: int) -> list[LabResultEntry]:
    """Retrieve all lab results for a case (via its subject)."""
    case = get_case_by_id(db, case_id)
    if not case:
        return []
    return get_lab_results(db, case.subject_id)


def get_lab_results_for_partner(db: Session, partner_id: int) -> list[LabResultEntry]:
    """Retrieve all lab results for a partner (via its subject)."""
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        return []
    return get_lab_results(db, partner.subject_id)


def get_lab_result_entry_by_id(db: Session, entry_id: int) -> LabResultEntry | None:
    """Retrieve a specific lab result entry by ID."""
    return db.query(LabResultEntry).filter(LabResultEntry.id == entry_id).first()


def create_lab_result_entry(
    db: Session,
    test_category: str,
    test_type: str,
    collection_date: date,
    case_id: int | None = None,
    partner_id: int | None = None,
    subject_id: int | None = None,
    titer: str | None = None,
    result: str | None = None,
) -> LabResultEntry:
    """Create a new lab result entry.

    Pass case_id or partner_id for backward compatibility; subject_id takes
    precedence if provided directly.
    """
    if subject_id is None:
        if case_id is not None:
            case = get_case_by_id(db, case_id)
            subject_id = case.subject_id if case else None
        elif partner_id is not None:
            partner = get_partner_by_id(db, partner_id)
            subject_id = partner.subject_id if partner else None
    lab_entry = LabResultEntry(
        subject_id=subject_id,
        test_category=test_category,
        test_type=test_type,
        collection_date=collection_date,
        titer=titer,
        result=result,
    )
    db.add(lab_entry)
    db.flush()
    db.refresh(lab_entry)
    return lab_entry


def update_lab_result_entry(
    db: Session, entry_id: int, **kwargs
) -> LabResultEntry | None:
    """Update an existing lab result entry."""
    lab_entry = get_lab_result_entry_by_id(db, entry_id)
    if not lab_entry:
        return None
    for field, value in kwargs.items():
        setattr(lab_entry, field, value)
    db.flush()
    db.refresh(lab_entry)
    return lab_entry


def delete_lab_result_entry(db: Session, entry_id: int) -> bool:
    """Delete a lab result entry."""
    lab_entry = get_lab_result_entry_by_id(db, entry_id)
    if not lab_entry:
        return False
    db.delete(lab_entry)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# SymptomEntry queries
# ---------------------------------------------------------------------------


def get_symptoms(db: Session, subject_id: int) -> list[SymptomEntry]:
    """Retrieve all symptoms for a given subject."""
    return (
        db.query(SymptomEntry)
        .filter(SymptomEntry.subject_id == subject_id)
        .order_by(SymptomEntry.onset_date, SymptomEntry.id)
        .all()
    )


def get_symptoms_for_case(db: Session, case_id: int) -> list[SymptomEntry]:
    """Retrieve all symptoms for a case (via its subject)."""
    case = get_case_by_id(db, case_id)
    if not case:
        return []
    return get_symptoms(db, case.subject_id)


def get_symptoms_for_partner(db: Session, partner_id: int) -> list[SymptomEntry]:
    """Retrieve all symptoms for a partner (via its subject)."""
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        return []
    return get_symptoms(db, partner.subject_id)


def get_symptom_entry_by_id(db: Session, entry_id: int) -> SymptomEntry | None:
    """Retrieve a specific symptom entry by ID."""
    return db.query(SymptomEntry).filter(SymptomEntry.id == entry_id).first()


def create_symptom_entry(
    db: Session,
    symptom_type: str,
    classification: str | None = None,
    onset_date: date | None = None,
    date_kind: str | None = None,
    duration_days: int | None = None,
    duration_source: str | None = None,
    ongoing: bool = False,
    case_id: int | None = None,
    partner_id: int | None = None,
    subject_id: int | None = None,
) -> SymptomEntry:
    """Create a new symptom entry.

    Pass case_id or partner_id for backward compatibility; subject_id takes
    precedence if provided directly.
    """
    if subject_id is None:
        if case_id is not None:
            case = get_case_by_id(db, case_id)
            subject_id = case.subject_id if case else None
        elif partner_id is not None:
            partner = get_partner_by_id(db, partner_id)
            subject_id = partner.subject_id if partner else None
    entry = SymptomEntry(
        subject_id=subject_id,
        symptom_type=symptom_type,
        classification=classification,
        onset_date=onset_date,
        date_kind=date_kind or SymptomDateKind.ONSET_REPORTED,
        duration_days=duration_days,
        duration_source=duration_source or SymptomDurationSource.UNKNOWN,
        ongoing=ongoing,
    )
    db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def update_symptom_entry(
    db: Session, entry_id: int, **kwargs
) -> Optional[SymptomEntry]:
    """Update an existing symptom entry."""
    entry = get_symptom_entry_by_id(db, entry_id)
    if not entry:
        return None
    for field, value in kwargs.items():
        setattr(entry, field, value)
    db.flush()
    db.refresh(entry)
    return entry


def delete_symptom_entry(db: Session, entry_id: int) -> bool:
    """Delete a specific symptom entry."""
    entry = get_symptom_entry_by_id(db, entry_id)
    if not entry:
        return False
    db.delete(entry)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Case queries
# ---------------------------------------------------------------------------


def get_all_cases(db: Session) -> list[Case]:
    """Return all cases ordered by most recently updated."""
    return db.query(Case).order_by(Case.updated_at.desc()).all()


def get_case_by_id(db: Session, case_id: int) -> Case | None:
    return db.query(Case).filter(Case.id == case_id).first()


def create_case(
    db: Session, patient_name: str, initial_contact_date: date | None = None, **kwargs
) -> Case:
    subject_kwargs, case_kwargs = _split_subject_kwargs(kwargs)
    person = Person()
    subject = Subject(**subject_kwargs)
    case = Case(
        patient_name=patient_name,
        initial_contact_date=initial_contact_date,
        person=person,
        subject=subject,
        **case_kwargs,
    )
    db.add(case)
    db.flush()
    db.refresh(case)
    return case


def update_case(db: Session, case_id: int, **kwargs) -> Case | None:
    case = get_case_by_id(db, case_id)
    if not case:
        return None
    subject_kwargs, case_kwargs = _split_subject_kwargs(kwargs)
    for field, value in case_kwargs.items():
        setattr(case, field, value)
    if subject_kwargs and case.subject:
        for field, value in subject_kwargs.items():
            setattr(case.subject, field, value)
    db.flush()
    db.refresh(case)
    return case


def delete_case(db: Session, case_id: int) -> bool:
    case = get_case_by_id(db, case_id)
    if not case:
        return False
    db.delete(case)
    db.flush()
    return True


def search_cases(db: Session, query: str) -> list[Case]:
    return (
        db.query(Case)
        .filter(Case.patient_name.ilike(f"%{query}%"))
        .order_by(Case.updated_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Partner queries
# ---------------------------------------------------------------------------


def get_partners_for_case(db: Session, case_id: int) -> list[Partner]:
    return (
        db.query(Partner)
        .filter(Partner.case_id == case_id)
        .order_by(Partner.partner_number)
        .all()
    )


def get_partners_linked_to_case(db: Session, case_id: int) -> list[Partner]:
    """Return all Partner records whose linked_case_id points to this case."""
    return db.query(Partner).filter(Partner.linked_case_id == case_id).all()


def get_partner_by_id(db: Session, partner_id: int) -> Partner | None:
    return db.query(Partner).filter(Partner.id == partner_id).first()


def create_partner(
    db: Session,
    case_id: int,
    partner_number: int,
    **kwargs,
) -> Partner:
    linked_case_id = kwargs.pop("linked_case_id", None)
    subject_kwargs, partner_kwargs = _split_subject_kwargs(kwargs)

    if linked_case_id is not None:
        linked_case = get_case_by_id(db, linked_case_id)
        shared_subject_id = linked_case.subject_id if linked_case else None
        shared_person_id = linked_case.person_id if linked_case else None
    else:
        shared_subject_id = None
        shared_person_id = None

    if shared_subject_id is not None:
        partner = Partner(
            case_id=case_id,
            partner_number=partner_number,
            linked_case_id=linked_case_id,
            subject_id=shared_subject_id,
            person_id=shared_person_id,
            **partner_kwargs,
        )
    else:
        subject = Subject(**subject_kwargs)
        person = Person()
        partner = Partner(
            case_id=case_id,
            partner_number=partner_number,
            linked_case_id=linked_case_id,
            subject=subject,
            person=person,
            **partner_kwargs,
        )
    db.add(partner)
    db.flush()
    db.refresh(partner)
    return partner


def update_partner(db: Session, partner_id: int, **kwargs) -> Partner | None:
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        return None
    subject_kwargs, partner_kwargs = _split_subject_kwargs(kwargs)
    for field, value in partner_kwargs.items():
        setattr(partner, field, value)
    if subject_kwargs and partner.subject:
        for field, value in subject_kwargs.items():
            setattr(partner.subject, field, value)
    db.flush()
    db.refresh(partner)
    return partner


def delete_partner(db: Session, partner_id: int) -> bool:
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        return False
    db.delete(partner)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# MAP entry queries
# ---------------------------------------------------------------------------


def get_map_entries(
    db: Session, case_id: int, partner_id: int | None = None
) -> dict[int, MAPEntry]:
    """Return a dict keyed by item_number for fast lookup in the MAP form."""
    q = db.query(MAPEntry).filter(MAPEntry.case_id == case_id)
    if partner_id is None:
        q = q.filter(MAPEntry.partner_id.is_(None))
    else:
        q = q.filter(MAPEntry.partner_id == partner_id)
    return {entry.item_number: entry for entry in q.all()}


def upsert_map_entry(
    db: Session,
    case_id: int,
    item_number: int,
    p_value: bool,
    c_value: bool,
    notes: str = "",
    high_priority: bool = False,
    partner_id: int | None = None,
) -> MAPEntry:
    """Create or update a single MAP checklist item."""
    entry = (
        db.query(MAPEntry)
        .filter(
            MAPEntry.case_id == case_id,
            MAPEntry.item_number == item_number,
            MAPEntry.partner_id == partner_id,
        )
        .first()
    )
    if entry:
        entry.p_value = p_value
        entry.c_value = c_value
        entry.notes = notes
        entry.high_priority = high_priority
    else:
        entry = MAPEntry(
            case_id=case_id,
            item_number=item_number,
            p_value=p_value,
            c_value=c_value,
            notes=notes,
            high_priority=high_priority,
            partner_id=partner_id,
        )
        db.add(entry)
    db.flush()
    db.refresh(entry)
    return entry


def delete_map_entries(db: Session, case_id: int, partner_id: int | None = None) -> int:
    q = db.query(MAPEntry).filter(MAPEntry.case_id == case_id)
    if partner_id is None:
        q = q.filter(MAPEntry.partner_id.is_(None))
    else:
        q = q.filter(MAPEntry.partner_id == partner_id)
    deleted = q.delete(synchronize_session=False)
    db.flush()
    return deleted


# ---------------------------------------------------------------------------
# Arrow link queries  (used by 05_network_graph.py)
# ---------------------------------------------------------------------------


def get_arrow_links(db: Session, case_id: int) -> list[ArrowLink]:
    return (
        db.query(ArrowLink)
        .filter(ArrowLink.case_id == case_id)
        .order_by(ArrowLink.id)
        .all()
    )


def get_arrow_link_by_id(db: Session, link_id: int) -> ArrowLink | None:
    return db.query(ArrowLink).filter(ArrowLink.id == link_id).first()


def create_arrow_link(
    db: Session, case_id: int, from_ref: str, to_ref: str
) -> ArrowLink:
    link = ArrowLink(case_id=case_id, from_ref=from_ref, to_ref=to_ref)
    db.add(link)
    db.flush()
    db.refresh(link)
    return link


def delete_arrow_link(db: Session, link_id: int) -> bool:
    link = db.query(ArrowLink).filter(ArrowLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.flush()
    return True


def arrow_link_exists(db: Session, case_id: int, from_ref: str, to_ref: str) -> bool:
    return (
        db.query(ArrowLink)
        .filter(
            ArrowLink.case_id == case_id,
            ArrowLink.from_ref == from_ref,
            ArrowLink.to_ref == to_ref,
        )
        .first()
    ) is not None


# ---------------------------------------------------------------------------
# Ghosting queries  (used by 05_network_graph.py)
# ---------------------------------------------------------------------------


def get_ghostings(db: Session, case_id: int) -> list[Ghosting]:
    return (
        db.query(Ghosting)
        .filter(Ghosting.case_id == case_id)
        .order_by(Ghosting.id)
        .all()
    )


def get_ghosting_by_id(db: Session, ghosting_id: int) -> Ghosting | None:
    return db.query(Ghosting).filter(Ghosting.id == ghosting_id).first()


def create_ghosting(
    db: Session,
    case_id: int,
    ghosting_type: str,
    from_ref: str | None,
    to_ref: str | None,
    notes: str | None,
) -> Ghosting:
    g = Ghosting(
        case_id=case_id,
        ghosting_type=ghosting_type,
        from_ref=from_ref,
        to_ref=to_ref,
        notes=notes,
    )
    db.add(g)
    db.flush()
    db.refresh(g)
    return g


def update_ghosting(db: Session, ghosting_id: int, **kwargs) -> Ghosting | None:
    g = get_ghosting_by_id(db, ghosting_id)
    if not g:
        return None
    for field, value in kwargs.items():
        setattr(g, field, value)
    db.flush()
    db.refresh(g)
    return g


def delete_ghosting(db: Session, ghosting_id: int) -> bool:
    g = get_ghosting_by_id(db, ghosting_id)
    if not g:
        return False
    db.delete(g)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Timeline event queries  (used by 06_timeline.py and 08_vca_chart.py)
# ---------------------------------------------------------------------------


def get_timeline_events(db: Session, case_id: int) -> list[TimelineEvent]:
    return (
        db.query(TimelineEvent)
        .filter(TimelineEvent.case_id == case_id)
        .order_by(TimelineEvent.event_date, TimelineEvent.id)
        .all()
    )


def get_timeline_event_by_id(db: Session, event_id: int) -> TimelineEvent | None:
    return db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()


def create_timeline_event(
    db: Session,
    case_id: int,
    event_date,
    event_type: str,
    notes: str | None = None,
    partner_id: int | None = None,
):
    evt = TimelineEvent(
        case_id=case_id,
        event_date=event_date,
        event_type=event_type,
        notes=notes,
        partner_id=partner_id,
    )
    db.add(evt)
    db.flush()
    db.refresh(evt)
    return evt


def update_timeline_event(db: Session, event_id: int, **kwargs) -> TimelineEvent | None:
    evt = get_timeline_event_by_id(db, event_id)
    if not evt:
        return None
    for field, value in kwargs.items():
        setattr(evt, field, value)
    db.flush()
    db.refresh(evt)
    return evt


def delete_timeline_event(db: Session, event_id: int) -> bool:
    evt = get_timeline_event_by_id(db, event_id)
    if not evt:
        return False
    db.delete(evt)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Dashboard queries
# ---------------------------------------------------------------------------


def get_cases_summary(db: Session) -> dict:
    """Return global aggregate metrics for the dashboard."""
    total_cases = db.query(func.count(Case.id)).scalar()
    total_partners = db.query(func.count(Partner.id)).scalar()
    treated_count = (
        db.query(func.count(Case.id))
        .join(Subject, Case.subject_id == Subject.id)
        .filter(Subject.treatment_date.is_not(None))
        .scalar()
    )
    untreated_count = (
        db.query(func.count(Case.id))
        .join(Subject, Case.subject_id == Subject.id)
        .filter(Subject.treatment_date.is_(None))
        .scalar()
    )

    return {
        "total_cases": total_cases or 0,
        "total_partners": total_partners or 0,
        "treated_count": treated_count or 0,
        "untreated_count": untreated_count or 0,
    }


def get_case_summaries_with_counts(db: Session, search: str | None = None) -> list[Case]:
    """Return cases with their partner counts, optionally filtered by name."""
    query = (
        db.query(Case)
        .outerjoin(Partner, Case.id == Partner.case_id)
        .group_by(Case.id)
        .order_by(Case.updated_at.desc())
    )

    if search:
        query = query.filter(Case.patient_name.ilike(f"%{search}%"))

    results = []
    cases = query.all()
    for case in cases:
        count = db.query(func.count(Partner.id)).filter(Partner.case_id == case.id).scalar()
        case.partner_count = count or 0
        results.append(case)

    return results


def get_latest_lab_for_case(db: Session, case_id: int) -> LabResultEntry | None:
    """Retrieve the most recent lab result for a specific case."""
    case = get_case_by_id(db, case_id)
    if not case:
        return None
    return (
        db.query(LabResultEntry)
        .filter(LabResultEntry.subject_id == case.subject_id)
        .order_by(LabResultEntry.collection_date.desc(), LabResultEntry.id.desc())
        .first()
    )
