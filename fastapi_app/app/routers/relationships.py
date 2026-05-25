from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    create_case_partner_relationship,
    create_relationship_report,
    delete_case_partner_relationship,
    delete_relationship_report,
    get_case_by_id,
    get_case_partner_relationship,
    get_case_partner_relationship_by_id,
    get_partner_by_id,
    get_relationship_report_by_id,
    get_reports_for_relationship,
    update_case_partner_relationship,
    update_relationship_report,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    CasePartnerRelationshipCreate,
    CasePartnerRelationshipRead,
    CasePartnerRelationshipUpdate,
    RelationshipReportCreate,
    RelationshipReportRead,
    RelationshipReportUpdate,
)

router = APIRouter(prefix="/cases", tags=["relationships"])

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


def _get_partner_for_case_or_404(db: Session, case_id: int, partner_id: int):
    partner = get_partner_by_id(db, partner_id)
    if not partner or partner.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found for case {case_id}",
        )
    return partner


def _get_relationship_or_404(db: Session, relationship_id: int):
    relationship = get_case_partner_relationship_by_id(db, relationship_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship_id} not found",
        )
    return relationship


def _get_report_or_404(db: Session, report_id: int):
    report = get_relationship_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship report {report_id} not found",
        )
    return report


@router.get(
    "/{case_id}/partners/{partner_id}/relationship",
    response_model=CasePartnerRelationshipRead,
)
def get_relationship(
    case_id: int,
    partner_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    _get_case_or_404(db, case_id)
    _get_partner_for_case_or_404(db, case_id, partner_id)
    relationship = get_case_partner_relationship(db, case_id, partner_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Relationship for case {case_id} and partner {partner_id} not found"
            ),
        )
    return relationship


@router.post(
    "/{case_id}/partners/{partner_id}/relationship",
    response_model=CasePartnerRelationshipRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship(
    case_id: int,
    partner_id: int,
    payload: CasePartnerRelationshipCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    _get_partner_for_case_or_404(db, case_id, partner_id)
    existing = get_case_partner_relationship(db, case_id, partner_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Relationship for case {case_id} and partner {partner_id} "
                "already exists"
            ),
        )
    return create_case_partner_relationship(
        db,
        case_id=case_id,
        partner_id=partner_id,
        **payload.model_dump(exclude_none=True),
    )


@router.patch(
    "/{case_id}/partners/{partner_id}/relationship",
    response_model=CasePartnerRelationshipRead,
)
def update_relationship(
    case_id: int,
    partner_id: int,
    payload: CasePartnerRelationshipUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    _get_partner_for_case_or_404(db, case_id, partner_id)
    relationship = get_case_partner_relationship(db, case_id, partner_id)
    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Relationship for case {case_id} and partner {partner_id} not found"
            ),
        )
    updated = update_case_partner_relationship(
        db, relationship.id, **payload.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship {relationship.id} not found",
        )
    return updated


@router.delete(
    "/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship(
    relationship_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_relationship_or_404(db, relationship_id)
    delete_case_partner_relationship(db, relationship_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/relationships/{relationship_id}/reports",
    response_model=list[RelationshipReportRead],
)
def list_relationship_reports(
    relationship_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    _get_relationship_or_404(db, relationship_id)
    return get_reports_for_relationship(db, relationship_id)


@router.post(
    "/relationships/{relationship_id}/reports",
    response_model=RelationshipReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_relationship_report_endpoint(
    relationship_id: int,
    payload: RelationshipReportCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_relationship_or_404(db, relationship_id)
    return create_relationship_report(
        db,
        relationship_id=relationship_id,
        **payload.model_dump(exclude_none=True),
    )


@router.get(
    "/relationships/reports/{report_id}",
    response_model=RelationshipReportRead,
)
def get_relationship_report_endpoint(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return _get_report_or_404(db, report_id)


@router.patch(
    "/relationships/reports/{report_id}",
    response_model=RelationshipReportRead,
)
def update_relationship_report_endpoint(
    report_id: int,
    payload: RelationshipReportUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_report_or_404(db, report_id)
    updated = update_relationship_report(
        db, report_id, **payload.model_dump(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship report {report_id} not found",
        )
    return updated


@router.delete(
    "/relationships/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_relationship_report_endpoint(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_report_or_404(db, report_id)
    delete_relationship_report(db, report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
