from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    create_symptom_entry,
    delete_symptom_entry,
    get_case_by_id,
    get_partner_by_id,
    get_symptom_entry_by_id,
    get_symptoms_for_case,
    get_symptoms_for_partner,
    update_symptom_entry,
)
from app.utils.clinical import (
    derive_symptom_capture_metadata,
    get_symptom_classification,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    SymptomEntryCreate,
    SymptomEntryRead,
    SymptomEntryUpdate,
)

router = APIRouter(prefix="/cases", tags=["symptoms"])

OperatorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*OPERATOR_ROLES))
]
SupervisorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*SUPERVISOR_ROLES))
]


def _get_case_or_404(db: Session, case_id: int):
    case = get_case_by_id(db, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    return case


def _get_partner_or_404(db: Session, partner_id: int):
    partner = get_partner_by_id(db, partner_id)
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found",
        )
    return partner


def _get_symptom_or_404(db: Session, entry_id: int):
    entry = get_symptom_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom entry {entry_id} not found",
        )
    return entry


@router.get("/{case_id}/symptoms", response_model=list[SymptomEntryRead])
def list_case_symptoms(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_symptoms_for_case(db, case_id)


@router.post(
    "/{case_id}/symptoms",
    response_model=SymptomEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case_symptom(
    case_id: int,
    payload: SymptomEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    data = payload.model_dump(exclude_none=True)
    classification = get_symptom_classification(data["symptom_type"])
    date_kind, duration_source, derived_ongoing = derive_symptom_capture_metadata(
        symptom_type=data["symptom_type"],
        anchor_date=data.get("onset_date"),
        duration_days=data.get("duration_days"),
        date_kind=data.get("date_kind"),
        classification=classification,
    )
    data["classification"] = classification
    data["date_kind"] = date_kind
    data["duration_source"] = duration_source
    data["ongoing"] = derived_ongoing
    return create_symptom_entry(db, case_id=case_id, **data)


@router.get(
    "/partners/{partner_id}/symptoms",
    response_model=list[SymptomEntryRead],
)
def list_partner_symptoms(partner_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_partner_or_404(db, partner_id)
    return get_symptoms_for_partner(db, partner_id)


@router.post(
    "/partners/{partner_id}/symptoms",
    response_model=SymptomEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_partner_symptom(
    partner_id: int,
    payload: SymptomEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_partner_or_404(db, partner_id)
    data = payload.model_dump(exclude_none=True)
    classification = get_symptom_classification(data["symptom_type"])
    date_kind, duration_source, derived_ongoing = derive_symptom_capture_metadata(
        symptom_type=data["symptom_type"],
        anchor_date=data.get("onset_date"),
        duration_days=data.get("duration_days"),
        date_kind=data.get("date_kind"),
        classification=classification,
    )
    data["classification"] = classification
    data["date_kind"] = date_kind
    data["duration_source"] = duration_source
    data["ongoing"] = derived_ongoing
    return create_symptom_entry(db, partner_id=partner_id, **data)


@router.get("/symptoms/{entry_id}", response_model=SymptomEntryRead)
def get_symptom(entry_id: int, db: Annotated[Session, Depends(get_db)]):
    return _get_symptom_or_404(db, entry_id)


@router.patch("/symptoms/{entry_id}", response_model=SymptomEntryRead)
def update_symptom(
    entry_id: int,
    payload: SymptomEntryUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    existing = _get_symptom_or_404(db, entry_id)
    data = payload.model_dump(exclude_unset=True)

    effective_symptom_type = data.get("symptom_type", existing.symptom_type)
    effective_onset_date = data.get("onset_date", existing.onset_date)
    effective_duration_days = data.get("duration_days", existing.duration_days)
    effective_date_kind = data.get("date_kind", existing.date_kind)
    effective_classification = get_symptom_classification(effective_symptom_type)

    date_kind, duration_source, derived_ongoing = derive_symptom_capture_metadata(
        symptom_type=effective_symptom_type,
        anchor_date=effective_onset_date,
        duration_days=effective_duration_days,
        date_kind=effective_date_kind,
        classification=effective_classification,
    )

    data["classification"] = effective_classification
    data["date_kind"] = date_kind
    data["duration_source"] = duration_source
    data["ongoing"] = derived_ongoing

    updated = update_symptom_entry(db, entry_id, **data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symptom entry {entry_id} not found",
        )
    return updated


@router.delete("/symptoms/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_symptom(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_symptom_or_404(db, entry_id)
    delete_symptom_entry(db, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
