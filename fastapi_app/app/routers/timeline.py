from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    create_timeline_event,
    delete_timeline_event,
    get_case_by_id,
    get_partner_by_id,
    get_timeline_event_by_id,
    get_timeline_events,
    update_timeline_event,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    TimelineEventCreate,
    TimelineEventRead,
    TimelineEventUpdate,
)

router = APIRouter(prefix="/cases", tags=["timeline"])

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


def _get_timeline_event_or_404(db: Session, event_id: int):
    event = get_timeline_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeline event {event_id} not found",
        )
    return event


def _validate_partner_for_case(
    db: Session, case_id: int, partner_id: int | None
) -> None:
    if partner_id is None:
        return
    partner = get_partner_by_id(db, partner_id)
    if not partner or partner.case_id != case_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partner {partner_id} not found for case {case_id}",
        )


@router.get("/{case_id}/timeline", response_model=list[TimelineEventRead])
def list_timeline_events(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_timeline_events(db, case_id)


@router.post(
    "/{case_id}/timeline",
    response_model=TimelineEventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_timeline_event_endpoint(
    case_id: int,
    payload: TimelineEventCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    data = payload.model_dump(exclude_none=True)
    _validate_partner_for_case(db, case_id, data.get("partner_id"))
    return create_timeline_event(db, case_id=case_id, **data)


@router.get("/timeline/{event_id}", response_model=TimelineEventRead)
def get_timeline_event_endpoint(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return _get_timeline_event_or_404(db, event_id)


@router.patch("/timeline/{event_id}", response_model=TimelineEventRead)
def update_timeline_event_endpoint(
    event_id: int,
    payload: TimelineEventUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    event = _get_timeline_event_or_404(db, event_id)
    data = payload.model_dump(exclude_unset=True)
    _validate_partner_for_case(
        db, event.case_id, data.get("partner_id", event.partner_id)
    )
    updated = update_timeline_event(db, event_id, **data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timeline event {event_id} not found",
        )
    return updated


@router.delete("/timeline/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_timeline_event_endpoint(
    event_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_timeline_event_or_404(db, event_id)
    delete_timeline_event(db, event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
