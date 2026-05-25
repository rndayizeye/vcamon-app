from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    create_lab_result_entry,
    delete_lab_result_entry,
    get_case_by_id,
    get_lab_result_entry_by_id,
    get_lab_results_for_case,
    get_lab_results_for_partner,
    get_partner_by_id,
    update_lab_result_entry,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    LabResultEntryCreate,
    LabResultEntryRead,
    LabResultEntryUpdate,
)

router = APIRouter(prefix="/cases", tags=["labs"])

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


def _get_lab_or_404(db: Session, entry_id: int):
    entry = get_lab_result_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab result entry {entry_id} not found",
        )
    return entry


@router.get("/{case_id}/labs", response_model=list[LabResultEntryRead])
def list_case_labs(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_lab_results_for_case(db, case_id)


@router.post(
    "/{case_id}/labs",
    response_model=LabResultEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case_lab(
    case_id: int,
    payload: LabResultEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    return create_lab_result_entry(
        db,
        case_id=case_id,
        **payload.model_dump(exclude_none=True),
    )


@router.get("/partners/{partner_id}/labs", response_model=list[LabResultEntryRead])
def list_partner_labs(partner_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_partner_or_404(db, partner_id)
    return get_lab_results_for_partner(db, partner_id)


@router.post(
    "/partners/{partner_id}/labs",
    response_model=LabResultEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_partner_lab(
    partner_id: int,
    payload: LabResultEntryCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_partner_or_404(db, partner_id)
    return create_lab_result_entry(
        db,
        partner_id=partner_id,
        **payload.model_dump(exclude_none=True),
    )


@router.get("/labs/{entry_id}", response_model=LabResultEntryRead)
def get_lab(entry_id: int, db: Annotated[Session, Depends(get_db)]):
    return _get_lab_or_404(db, entry_id)


@router.patch("/labs/{entry_id}", response_model=LabResultEntryRead)
def update_lab(
    entry_id: int,
    payload: LabResultEntryUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_lab_or_404(db, entry_id)
    updated = update_lab_result_entry(
        db, entry_id, **payload.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab result entry {entry_id} not found",
        )
    return updated


@router.delete("/labs/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lab(
    entry_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_lab_or_404(db, entry_id)
    delete_lab_result_entry(db, entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
