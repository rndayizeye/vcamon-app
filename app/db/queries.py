"""
app/db/queries.py

Database access functions for the vcamon app.
Each page imports only what it needs — functions are added here
as new pages are built rather than all upfront.
"""

from sqlalchemy.orm import Session
from datetime import date
from app.db.models import Case, Partner, MAPEntry, ArrowLink, Ghosting, CasePartnerRelationship, TimelineEvent, LabResultEntry, SymptomClassification, TestCategory



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

def create_case_partner_relationship(
    db: Session,
    case_id: int,
    partner_id: int,
    exposure_first_date: date | None = None,
    exposure_last_date: date | None = None,
    sex_types: str | None = None,
) -> CasePartnerRelationship:
    """Create a new relationship entry."""
    rel = CasePartnerRelationship(
        case_id=case_id,
        partner_id=partner_id,
        exposure_first_date=exposure_first_date,
        exposure_last_date=exposure_last_date,
        sex_types=sex_types,
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel

def update_case_partner_relationship(
    db: Session, relationship_id: int, **kwargs
) -> CasePartnerRelationship | None:
    """Update an existing relationship entry."""
    rel = db.query(CasePartnerRelationship).filter(CasePartnerRelationship.id == relationship_id).first()
    if not rel:
        return None
    for field, value in kwargs.items():
        setattr(rel, field, value)
    db.commit()
    db.refresh(rel)
    return rel

def delete_case_partner_relationship(db: Session, relationship_id: int) -> bool:
    """Delete a relationship entry."""
    rel = db.query(CasePartnerRelationship).filter(CasePartnerRelationship.id == relationship_id).first()
    if not rel:
        return False
    db.delete(rel)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# LabResultEntry queries
# ---------------------------------------------------------------------------

def get_lab_results_for_case(db: Session, case_id: int) -> list[LabResultEntry]:
    """Retrieve all lab results for a given case."""
    return db.query(LabResultEntry).filter(LabResultEntry.case_id == case_id).order_by(LabResultEntry.collection_date).all()

def get_lab_results_for_partner(db: Session, partner_id: int) -> list[LabResultEntry]:
    """Retrieve all lab results for a given partner."""
    return db.query(LabResultEntry).filter(LabResultEntry.partner_id == partner_id).order_by(LabResultEntry.collection_date).all()

def create_lab_result_entry(
    db: Session,
    test_category: str,
    test_type: str,
    collection_date: date,
    case_id: int | None = None,
    partner_id: int | None = None,
    titer: str | None = None,
    result: str | None = None,
) -> LabResultEntry:
    """Create a new lab result entry."""
    lab_entry = LabResultEntry(
        case_id=case_id,
        partner_id=partner_id,
        test_category=test_category,
        test_type=test_type,
        collection_date=collection_date,
        titer=titer,
        result=result,
    )
    db.add(lab_entry)
    db.commit()
    db.refresh(lab_entry)
    return lab_entry

def update_lab_result_entry(db: Session, entry_id: int, **kwargs) -> LabResultEntry | None:
    """Update an existing lab result entry."""
    lab_entry = db.query(LabResultEntry).filter(LabResultEntry.id == entry_id).first()
    if not lab_entry:
        return None
    for field, value in kwargs.items():
        setattr(lab_entry, field, value)
    db.commit()
    db.refresh(lab_entry)
    return lab_entry

def delete_lab_result_entry(db: Session, entry_id: int) -> bool:
    """Delete a lab result entry."""
    lab_entry = db.query(LabResultEntry).filter(LabResultEntry.id == entry_id).first()
    if not lab_entry:
        return False
    db.delete(lab_entry)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Case queries
# ---------------------------------------------------------------------------

def get_all_cases(db: Session) -> list[Case]:
    """Return all cases ordered by most recently updated."""
    return db.query(Case).order_by(Case.updated_at.desc()).all()


def get_case_by_id(db: Session, case_id: int) -> Case | None:
    return db.query(Case).filter(Case.id == case_id).first()


def create_case(db: Session, patient_name: str, initial_contact_date: date | None = None, **kwargs) -> Case:
    case = Case(patient_name=patient_name, initial_contact_date=initial_contact_date, **kwargs)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update_case(db: Session, case_id: int, **kwargs) -> Case | None:
    case = get_case_by_id(db, case_id)
    if not case:
        return None
    for field, value in kwargs.items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


def delete_case(db: Session, case_id: int) -> bool:
    case = get_case_by_id(db, case_id)
    if not case:
        return False
    db.delete(case)
    db.commit()
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


def get_partner_by_id(db: Session, partner_id: int) -> Partner | None:
    return db.query(Partner).filter(Partner.id == partner_id).first()


def create_partner(
    db: Session, 
    case_id: int, 
    partner_number: int, 
    symptom_classification: str | None = None,
    symptom_ongoing: bool = False,
    historical_primary_chancre: bool | None = None,
    historical_primary_date: date | None = None,
    **kwargs
) -> Partner:
    partner = Partner(
        case_id=case_id,
        partner_number=partner_number,
        symptom_classification=symptom_classification,
        symptom_ongoing=symptom_ongoing,
        historical_primary_chancre=historical_primary_chancre,
        historical_primary_date=historical_primary_date,
        **kwargs
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def update_partner(db: Session, partner_id: int, **kwargs) -> Partner | None:
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        return None
    for field, value in kwargs.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner


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
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Arrow link queries  (used by 05_network_graph.py)
# ---------------------------------------------------------------------------

def get_arrow_links(db: Session, case_id: int) -> list[ArrowLink]:
    return (
        db.query(ArrowLink)
        .filter(ArrowLink.case_id == case_id)
        .all()
    )


def create_arrow_link(db: Session, case_id: int, from_ref: str, to_ref: str) -> ArrowLink:
    link = ArrowLink(case_id=case_id, from_ref=from_ref, to_ref=to_ref)
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_arrow_link(db: Session, link_id: int) -> bool:
    link = db.query(ArrowLink).filter(ArrowLink.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


def arrow_link_exists(
    db: Session, case_id: int, from_ref: str, to_ref: str
) -> bool:
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
    return db.query(Ghosting).filter(Ghosting.case_id == case_id).all()


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
    db.commit()
    db.refresh(g)
    return g


def delete_ghosting(db: Session, ghosting_id: int) -> bool:
    g = db.query(Ghosting).filter(Ghosting.id == ghosting_id).first()
    if not g:
        return False
    db.delete(g)
    db.commit()
    return True

# ---------------------------------------------------------------------------
# Timeline event queries  (used by 06_timeline.py and 08_vca_chart.py)
# ---------------------------------------------------------------------------

def get_timeline_events(db: Session, case_id: int):
    return (
        db.query(TimelineEvent)
        .filter(TimelineEvent.case_id == case_id)
        .order_by(TimelineEvent.event_date)
        .all()
    )


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
    db.commit()
    db.refresh(evt)
    return evt


def delete_timeline_event(db: Session, event_id: int) -> bool:
    evt = db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()
    if not evt:
        return False
    db.delete(evt)
    db.commit()
    return True