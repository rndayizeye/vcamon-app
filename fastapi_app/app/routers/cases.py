from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    create_case,
    create_partner,
    delete_case,
    delete_partner,
    get_all_cases,
    get_case_by_id,
    get_case_summaries_with_counts,
    get_cases_summary,
    get_latest_lab_for_case,
    get_partner_by_id,
    get_partners_for_case,
    search_cases,
    update_case,
    update_partner,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    CaseCreate,
    CaseRead,
    CaseSummary,
    DashboardSummary,
    CaseUpdate,
    PartnerCreate,
    PartnerLinkCase,
    PartnerRead,
    PartnerUpdate,
)

router = APIRouter(prefix="/cases", tags=["cases"])

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


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(db: Annotated[Session, Depends(get_db)]):
    return get_cases_summary(db)


@router.get("/", response_model=list[CaseSummary])
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    search: str | None = Query(default=None, min_length=1),
):
    return get_case_summaries_with_counts(db, search)


@router.post("/", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case_endpoint(
    payload: CaseCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    data = payload.model_dump(exclude_none=True)
    patient_name = data.pop("patient_name")
    initial_contact_date = data.pop("initial_contact_date", None)
    return create_case(
        db,
        patient_name=patient_name,
        initial_contact_date=initial_contact_date,
        **data,
    )


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: int, db: Annotated[Session, Depends(get_db)]):
    return _get_case_or_404(db, case_id)


@router.get("/{case_id}/latest-lab")
def get_latest_lab(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    lab = get_latest_lab_for_case(db, case_id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lab results found for case {case_id}",
        )
    return lab


@router.patch("/{case_id}", response_model=CaseRead)
def update_case_endpoint(
    case_id: int,
    payload: CaseUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    updated = update_case(db, case_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )
    return updated


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case_endpoint(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_case_or_404(db, case_id)
    delete_case(db, case_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{case_id}/partners", response_model=list[PartnerRead])
def list_case_partners(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_partners_for_case(db, case_id)


@router.post(
    "/{case_id}/partners",
    response_model=PartnerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case_partner(
    case_id: int,
    payload: PartnerCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    data = payload.model_dump(exclude_none=True)
    requested_number = data.pop("partner_number", None)
    existing_partners = get_partners_for_case(db, case_id)
    next_number = (
        requested_number
        if requested_number is not None
        else (existing_partners[-1].partner_number + 1 if existing_partners else 1)
    )
    return create_partner(db, case_id=case_id, partner_number=next_number, **data)


@router.get("/partners/{partner_id}", response_model=PartnerRead)
def get_partner(partner_id: int, db: Annotated[Session, Depends(get_db)]):
    return _get_partner_or_404(db, partner_id)


@router.patch("/partners/{partner_id}", response_model=PartnerRead)
def update_partner_endpoint(
    partner_id: int,
    payload: PartnerUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_partner_or_404(db, partner_id)
    updated = update_partner(db, partner_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found",
        )
    return updated


@router.delete("/partners/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_partner_endpoint(
    partner_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_partner_or_404(db, partner_id)
    delete_partner(db, partner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/partners/{partner_id}/link-case", response_model=PartnerRead)
def link_partner_to_case(
    partner_id: int,
    payload: PartnerLinkCase,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    """Set or clear the linked_case_id on a partner record."""
    _get_partner_or_404(db, partner_id)
    if payload.linked_case_id is not None:
        _get_case_or_404(db, payload.linked_case_id)
    updated = update_partner(db, partner_id, linked_case_id=payload.linked_case_id)
    return updated
