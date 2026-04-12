"""
app/db/queries.py

Database access functions for the vcamon app.
Each page imports only what it needs — functions are added here
as new pages are built rather than all upfront.
"""

from sqlalchemy.orm import Session
from app.db.models import Case, Partner, MAPEntry, ArrowLink, Ghosting, TimelineEvent
from app.db.models import ReasonForExam, LabResult, TreponemalResult, Treatment, LesionType, Symptom


# ---------------------------------------------------------------------------
# Case queries  (used by 01_dashboard.py and 02_op_form.py)
# ---------------------------------------------------------------------------

def get_all_cases(db: Session) -> list[Case]:
    """Return all cases ordered by most recently updated."""
    return db.query(Case).order_by(Case.updated_at.desc()).all()


def get_case_by_id(db: Session, case_id: int) -> Case | None:
    """Return a single case or None if not found."""
    return db.query(Case).filter(Case.id == case_id).first()


def create_case(db: Session, patient_name: str, **kwargs) -> Case:
    """
    Create a new case record.

    Usage:
        case = create_case(db, patient_name="Jane Doe", lot="710", case_manager="Smith")
    """
    case = Case(patient_name=patient_name, **kwargs)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def update_case(db: Session, case_id: int, **kwargs) -> Case | None:
    """
    Update fields on an existing case.
    Only fields passed as kwargs are updated — others are left unchanged.

    Usage:
        update_case(db, case_id=1, treatment_date=date(2024, 3, 15), lab_1="RPR 1:4")
    """
    case = get_case_by_id(db, case_id)
    if not case:
        return None
    for field, value in kwargs.items():
        setattr(case, field, value)
    db.commit()
    db.refresh(case)
    return case


def delete_case(db: Session, case_id: int) -> bool:
    """Delete a case and all its related records (cascade). Returns True if found."""
    case = get_case_by_id(db, case_id)
    if not case:
        return False
    db.delete(case)
    db.commit()
    return True


def search_cases(db: Session, query: str) -> list[Case]:
    """Simple name search — used by the dashboard search bar."""
    return (
        db.query(Case)
        .filter(Case.patient_name.ilike(f"%{query}%"))
        .order_by(Case.updated_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Partner queries  (used by 03_partner_form.py — stubs for now)
# ---------------------------------------------------------------------------

def get_partners_for_case(db: Session, case_id: int) -> list[Partner]:
    return (
        db.query(Partner)
        .filter(Partner.case_id == case_id)
        .order_by(Partner.partner_number)
        .all()
    )


def create_partner(db: Session, case_id: int, partner_number: int, **kwargs) -> Partner:
    partner = Partner(case_id=case_id, partner_number=partner_number, **kwargs)
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner


def update_partner(db: Session, partner_id: int, **kwargs) -> Partner | None:
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        return None
    for field, value in kwargs.items():
        setattr(partner, field, value)
    db.commit()
    db.refresh(partner)
    return partner


# ---------------------------------------------------------------------------
# MAP entry queries  (used by 04_map_sheet.py — stubs for now)
# ---------------------------------------------------------------------------

def get_map_entries(
    db: Session, case_id: int, partner_id: int | None = None
) -> dict[int, MAPEntry]:
    """
    Return a dict keyed by item_number for fast lookup in the MAP form.
    Pass partner_id=None for the OP MAP sheet, or a partner id for MAP1 etc.
    """
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