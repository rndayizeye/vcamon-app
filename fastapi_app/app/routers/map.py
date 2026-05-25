from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.models import MAP_ITEMS
from app.db.queries import (
    delete_map_entries,
    get_case_by_id,
    get_map_entries,
    get_partner_by_id,
    upsert_map_entry,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    MAPCatalogRead,
    MAPItemDefinitionRead,
    MAPSheetItemRead,
    MAPSheetRead,
    MAPSheetSummaryRead,
    MAPSheetUpsert,
)

router = APIRouter(tags=["map"])

OperatorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*OPERATOR_ROLES))
]
SupervisorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*SUPERVISOR_ROLES))
]

SECTION_ORDER = [
    "Social History",
    "Medical History",
    "Partners",
    "Clusters",
    "Risk Reduction",
    "Other",
]

_RENDERED_MAP_ITEMS = {
    item_number: metadata
    for item_number, metadata in MAP_ITEMS.items()
    if metadata["label"]
}


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


def _get_subject_label(case, partner=None) -> str:
    if partner is None:
        return f"OP — {case.patient_name}"
    return f"Partner {partner.partner_number} — {partner.name or 'Unnamed'}"


def _catalog_items() -> list[MAPItemDefinitionRead]:
    return [
        MAPItemDefinitionRead(
            item_number=item_number,
            section=metadata["section"],
            label=metadata["label"],
        )
        for item_number, metadata in _RENDERED_MAP_ITEMS.items()
    ]


def _serialize_sheet(case, entries, *, partner=None) -> MAPSheetRead:
    items = []
    for item_number, metadata in _RENDERED_MAP_ITEMS.items():
        entry = entries.get(item_number)
        items.append(
            MAPSheetItemRead(
                item_number=item_number,
                section=metadata["section"],
                label=metadata["label"],
                p_value=entry.p_value if entry else False,
                c_value=entry.c_value if entry else False,
                notes=entry.notes if entry and entry.notes else "",
                high_priority=entry.high_priority if entry else False,
                updated_at=entry.updated_at if entry else None,
            )
        )

    summary = MAPSheetSummaryRead(
        total_items=len(items),
        checked_p=sum(1 for item in items if item.p_value),
        checked_c=sum(1 for item in items if item.c_value),
        high_priority_flags=sum(1 for item in items if item.high_priority),
    )

    comment_entry = entries.get(-1)

    return MAPSheetRead(
        case_id=case.id,
        partner_id=partner.id if partner else None,
        subject_label=_get_subject_label(case, partner),
        section_order=SECTION_ORDER,
        items=items,
        high_priority_comment=(
            comment_entry.notes if comment_entry and comment_entry.notes else ""
        ),
        summary=summary,
    )


def _upsert_sheet(
    db: Session,
    case_id: int,
    payload: MAPSheetUpsert,
    *,
    partner_id: int | None = None,
):
    seen_item_numbers: set[int] = set()
    invalid_item_numbers: list[int] = []

    for item in payload.items:
        if item.item_number in seen_item_numbers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Duplicate MAP item {item.item_number} in request payload",
            )
        seen_item_numbers.add(item.item_number)

        if item.item_number not in _RENDERED_MAP_ITEMS:
            invalid_item_numbers.append(item.item_number)

    if invalid_item_numbers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "Unsupported MAP item number(s): "
                + ", ".join(str(item_number) for item_number in invalid_item_numbers)
            ),
        )

    for item in payload.items:
        upsert_map_entry(
            db,
            case_id=case_id,
            partner_id=partner_id,
            item_number=item.item_number,
            p_value=item.p_value,
            c_value=item.c_value,
            notes=item.notes,
            high_priority=item.high_priority,
        )

    if payload.high_priority_comment is not None:
        upsert_map_entry(
            db,
            case_id=case_id,
            partner_id=partner_id,
            item_number=-1,
            p_value=False,
            c_value=False,
            notes=payload.high_priority_comment.strip(),
            high_priority=bool(payload.high_priority_comment.strip()),
        )


@router.get("/map/items", response_model=MAPCatalogRead)
def get_map_catalog():
    return MAPCatalogRead(section_order=SECTION_ORDER, items=_catalog_items())


@router.get("/cases/{case_id}/map", response_model=MAPSheetRead)
def get_case_map_sheet(case_id: int, db: Annotated[Session, Depends(get_db)]):
    case = _get_case_or_404(db, case_id)
    entries = get_map_entries(db, case_id, partner_id=None)
    return _serialize_sheet(case, entries)


@router.put("/cases/{case_id}/map", response_model=MAPSheetRead)
def upsert_case_map_sheet(
    case_id: int,
    payload: MAPSheetUpsert,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    case = _get_case_or_404(db, case_id)
    _upsert_sheet(db, case_id, payload, partner_id=None)
    entries = get_map_entries(db, case_id, partner_id=None)
    return _serialize_sheet(case, entries)


@router.delete("/cases/{case_id}/map", status_code=status.HTTP_204_NO_CONTENT)
def clear_case_map_sheet(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_case_or_404(db, case_id)
    delete_map_entries(db, case_id, partner_id=None)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/cases/{case_id}/partners/{partner_id}/map", response_model=MAPSheetRead)
def get_partner_map_sheet(
    case_id: int,
    partner_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    case = _get_case_or_404(db, case_id)
    partner = _get_partner_for_case_or_404(db, case_id, partner_id)
    entries = get_map_entries(db, case_id, partner_id=partner_id)
    return _serialize_sheet(case, entries, partner=partner)


@router.put("/cases/{case_id}/partners/{partner_id}/map", response_model=MAPSheetRead)
def upsert_partner_map_sheet(
    case_id: int,
    partner_id: int,
    payload: MAPSheetUpsert,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    case = _get_case_or_404(db, case_id)
    partner = _get_partner_for_case_or_404(db, case_id, partner_id)
    _upsert_sheet(db, case_id, payload, partner_id=partner_id)
    entries = get_map_entries(db, case_id, partner_id=partner_id)
    return _serialize_sheet(case, entries, partner=partner)


@router.delete(
    "/cases/{case_id}/partners/{partner_id}/map",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_partner_map_sheet(
    case_id: int,
    partner_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_case_or_404(db, case_id)
    _get_partner_for_case_or_404(db, case_id, partner_id)
    delete_map_entries(db, case_id, partner_id=partner_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
