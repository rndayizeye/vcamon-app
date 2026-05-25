from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.queries import (
    arrow_link_exists,
    create_arrow_link,
    delete_arrow_link,
    get_arrow_link_by_id,
    get_arrow_links,
    get_case_by_id,
    get_partners_for_case,
)
from app.utils.network_analysis import (
    build_nx_graph,
    calculate_centralities,
    detect_clusters,
    get_first_date,
)
from app.utils.validators import validate_arrow_link
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    AnalyticsCentralityRead,
    AnalyticsClusterRead,
    AnalyticsNodeRead,
    AnalyticsSummaryRead,
    ArrowLinkCreate,
    ArrowLinkRead,
)

router = APIRouter(prefix="/cases", tags=["analytics"])

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


def _get_link_or_404(db: Session, link_id: int):
    link = get_arrow_link_by_id(db, link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arrow link {link_id} not found",
        )
    return link


def _build_ref_maps(case, partners):
    ref_to_label: dict[str, str] = {"OP": f"OP — {case.patient_name}"}
    node_map: dict[str, AnalyticsNodeRead] = {
        "OP": AnalyticsNodeRead(
            ref="OP",
            label=ref_to_label["OP"],
            entity_type="case",
            case_id=case.id,
            partner_id=None,
            partner_number=None,
            treated=case.treatment_date is not None,
            first_date=get_first_date(case, None),
        )
    }

    for partner in partners:
        ref = str(partner.partner_number)
        label = f"Partner {partner.partner_number} — {partner.name or 'Unnamed'}"
        ref_to_label[ref] = label
        node_map[ref] = AnalyticsNodeRead(
            ref=ref,
            label=label,
            entity_type="partner",
            case_id=case.id,
            partner_id=partner.id,
            partner_number=partner.partner_number,
            treated=partner.treatment_date is not None,
            first_date=get_first_date(partner, None),
        )

    return ref_to_label, node_map


def _validate_link_refs(case, partners, from_ref: str, to_ref: str):
    errors = validate_arrow_link(from_ref, to_ref)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=errors,
        )

    valid_refs = {"OP", *(str(partner.partner_number) for partner in partners)}
    invalid_refs = [ref for ref in (from_ref, to_ref) if ref not in valid_refs]
    if invalid_refs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Invalid link reference(s) for case {case.id}: "
                + ", ".join(sorted(set(invalid_refs)))
            ),
        )


@router.get("/{case_id}/links", response_model=list[ArrowLinkRead])
def list_case_links(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_arrow_links(db, case_id)


@router.post(
    "/{case_id}/links",
    response_model=ArrowLinkRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case_link(
    case_id: int,
    payload: ArrowLinkCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    case = _get_case_or_404(db, case_id)
    partners = get_partners_for_case(db, case_id)

    from_ref = payload.from_ref.strip()
    to_ref = payload.to_ref.strip()
    _validate_link_refs(case, partners, from_ref, to_ref)

    if arrow_link_exists(db, case_id, from_ref, to_ref):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Arrow link {from_ref} -> {to_ref} already exists for case {case_id}"
            ),
        )

    return create_arrow_link(db, case_id=case_id, from_ref=from_ref, to_ref=to_ref)


@router.get("/links/{link_id}", response_model=ArrowLinkRead)
def get_case_link(link_id: int, db: Annotated[Session, Depends(get_db)]):
    return _get_link_or_404(db, link_id)


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case_link(
    link_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_link_or_404(db, link_id)
    delete_arrow_link(db, link_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{case_id}/analytics", response_model=AnalyticsSummaryRead)
def get_case_analytics(
    case_id: int,
    db: Annotated[Session, Depends(get_db)],
    as_of_date: date | None = Query(default=None),
):
    case = _get_case_or_404(db, case_id)
    partners = get_partners_for_case(db, case_id)
    links = get_arrow_links(db, case_id)

    ref_to_label, node_map = _build_ref_maps(case, partners)
    label_to_ref = {label: ref for ref, label in ref_to_label.items()}

    graph = build_nx_graph(case, partners, links, ref_to_label, as_of_date)
    visible_refs = list(graph.nodes)
    visible_ref_set = set(visible_refs)

    visible_nodes = [node_map[ref] for ref in visible_refs if ref in node_map]
    visible_edges = [
        link
        for link in links
        if link.from_ref in visible_ref_set and link.to_ref in visible_ref_set
    ]

    centralities = [
        AnalyticsCentralityRead(
            node_ref=label_to_ref.get(item["Node"], item["Node"]),
            label=item["Node"],
            in_degree=item["In-Degree"],
            out_degree=item["Out-Degree"],
            betweenness=item["Betweenness"],
        )
        for item in calculate_centralities(graph)
    ]

    cluster_data = detect_clusters(graph)

    return AnalyticsSummaryRead(
        case_id=case_id,
        as_of_date=as_of_date,
        node_count=len(visible_nodes),
        edge_count=len(visible_edges),
        nodes=visible_nodes,
        edges=visible_edges,
        centralities=centralities,
        clusters=AnalyticsClusterRead(**cluster_data),
    )
