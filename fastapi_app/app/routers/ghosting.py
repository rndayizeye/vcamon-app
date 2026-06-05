from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.models import GhostingType
from app.db.queries import (
    create_ghosting,
    delete_ghosting,
    get_all_cases,
    get_case_by_id,
    get_case_partner_relationship,
    get_ghosting_by_id,
    get_ghostings,
    get_lab_results_for_case,
    get_lab_results_for_partner,
    get_partner_by_id,
    get_partners_for_case,
    get_symptoms_for_case,
    get_symptoms_for_partner,
    update_ghosting,
)
from app.utils.clinical import (
    Exposure,
    GhostedLesion,
    ScenarioResult,
    Symptom,
    resolve_symptom_timing_for_analysis,
    run_ghosting_analysis,
    select_case1,
)
from fastapi_app.app.auth import (
    OPERATOR_ROLES,
    SUPERVISOR_ROLES,
    AuthenticatedUser,
    require_roles,
)
from fastapi_app.app.db import get_db
from fastapi_app.app.schemas import (
    GhostedLesionRead,
    GhostingAnalysisRead,
    GhostingAnalysisRequest,
    GhostingCaseAnalysisRequest,
    GhostingCreate,
    GhostingCriteriaCheckRead,
    GhostingExposureInput,
    GhostingRead,
    GhostingScenarioCriteriaRead,
    GhostingScenarioRead,
    GhostingSymptomInput,
    GhostingUpdate,
    SuggestedGhostingRecordRead,
    TransmissionChainRead,
    TransmissionEdge,
    TransmissionNode,
    TransmissionSkipped,
)

router = APIRouter(tags=["ghosting"])

OperatorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*OPERATOR_ROLES))
]
SupervisorAccess = Annotated[
    AuthenticatedUser | None, Depends(require_roles(*SUPERVISOR_ROLES))
]

_CLASSIFICATION_TO_VCA: dict[str, str] = {
    "Primary": "Primary Chancre",
    "Secondary": "Secondary Rash/Lesions",
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


def _get_ghosting_or_404(db: Session, ghosting_id: int):
    ghosting = get_ghosting_by_id(db, ghosting_id)
    if not ghosting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ghosting record {ghosting_id} not found",
        )
    return ghosting


def _non_reactive_treponemal_name(lab_results) -> str | None:
    """Return test_type if any treponemal result is Non-reactive, else None."""
    for lab in lab_results:
        if lab.test_category == "Treponemal" and lab.result == "Non-reactive":
            return lab.test_type
    return None


def _parse_modalities(raw_modalities: Any) -> list[str]:
    if raw_modalities is None:
        return []
    if isinstance(raw_modalities, list):
        return [str(item).strip() for item in raw_modalities if str(item).strip()]
    if not isinstance(raw_modalities, str):
        return [str(raw_modalities).strip()] if str(raw_modalities).strip() else []

    raw_modalities = raw_modalities.strip()
    if not raw_modalities:
        return []

    try:
        decoded = json.loads(raw_modalities)
    except json.JSONDecodeError:
        decoded = None

    if isinstance(decoded, list):
        return [str(item).strip() for item in decoded if str(item).strip()]

    return [
        token.strip().strip('"').strip("'")
        for token in raw_modalities.split(",")
        if token.strip().strip('"').strip("'")
    ]


def _symptom_entries_to_engine(
    entries,
    historical_primary_chancre: bool | None,
    historical_primary_date,
) -> list[Symptom]:
    symptoms: list[Symptom] = []

    for entry in entries:
        if not entry.onset_date:
            continue

        vca_type = _CLASSIFICATION_TO_VCA.get(entry.classification or "")
        if not vca_type:
            continue

        derived_onset, derived_duration = resolve_symptom_timing_for_analysis(
            symptom_type=entry.symptom_type,
            anchor_date=entry.onset_date,
            duration_days=entry.duration_days,
            date_kind=getattr(entry, "date_kind", None),
            classification=entry.classification,
        )
        if not derived_onset:
            continue

        symptoms.append(
            Symptom(
                type=vca_type,
                onset=derived_onset,
                duration_days=derived_duration,
                anatomical_site=(
                    entry.symptom_type if entry.classification == "Primary" else None
                ),
            )
        )

    if historical_primary_chancre and historical_primary_date:
        symptoms.append(
            Symptom(
                type="Historical Primary",
                onset=historical_primary_date,
                duration_days=0,
            )
        )

    return symptoms


def _payload_symptoms_to_engine(
    symptoms: list[GhostingSymptomInput] | None,
) -> list[Symptom]:
    return [
        Symptom(
            type=item.type,
            onset=item.onset,
            duration_days=item.duration_days,
            anatomical_site=item.anatomical_site,
        )
        for item in (symptoms or [])
    ]


def _payload_exposure_to_engine(
    exposure: GhostingExposureInput | None,
) -> Exposure | None:
    if not exposure:
        return None
    return Exposure(
        first=exposure.first,
        last=exposure.last,
    )


def _relationship_exposure_to_engine(relationship) -> Exposure | None:
    if not relationship:
        return None
    if not relationship.exposure_first_date or not relationship.exposure_last_date:
        return None
    return Exposure(
        first=relationship.exposure_first_date,
        last=relationship.exposure_last_date,
    )


def _serialize_criteria_check(criteria: dict[str, str]) -> GhostingCriteriaCheckRead:
    return GhostingCriteriaCheckRead(
        status=criteria["status"],
        detail=criteria["detail"],
    )


def _serialize_range_criteria(
    criteria: dict[str, dict[str, str]],
) -> GhostingScenarioCriteriaRead:
    return GhostingScenarioCriteriaRead(
        exposure=_serialize_criteria_check(criteria["exposure"]),
        exposure_modality=_serialize_criteria_check(criteria["exposure_modality"]),
        latency=_serialize_criteria_check(criteria["latency"]),
        natural_order=_serialize_criteria_check(criteria["natural_order"]),
    )


def _serialize_lesion(lesion: GhostedLesion) -> GhostedLesionRead:
    return GhostedLesionRead(
        lesion_type=lesion.lesion_type,
        onset=lesion.onset,
        end=lesion.end,
        derived_from_symptom=lesion.derived_from_symptom,
        assigned_to=lesion.assigned_to,
    )


def _serialize_scenario(result: ScenarioResult) -> GhostingScenarioRead:
    return GhostingScenarioRead(
        range_data={k: _serialize_range_criteria(v) for k, v in result.range_data.items()},
        range_lesions={k: _serialize_lesion(v) for k, v in result.range_lesions.items()},
        confidence=result.confidence,
        pass_count=result.pass_count,
    )


def _build_ghosting_note(
    result,
    ghosting_type: GhostingType,
) -> str:
    lesion = (
        result.ghosted_source
        if ghosting_type == GhostingType.SOURCE
        else result.ghosted_spread
    )
    label = "source" if ghosting_type == GhostingType.SOURCE else "spread"
    return (
        f"Ghosted {label}: {lesion.onset} → {lesion.end}. "
        f"Derived from: {lesion.derived_from_symptom}. "
        f"Verdict: {result.verdict}"
    )


def _serialize_analysis(
    result,
    *,
    case1_ref: str | None = None,
    case2_ref: str | None = None,
) -> GhostingAnalysisRead:
    suggested_records: list[SuggestedGhostingRecordRead] = []
    if case1_ref and case2_ref:
        for ghosting_type in (GhostingType.SOURCE, GhostingType.SPREAD):
            suggested_records.append(
                SuggestedGhostingRecordRead(
                    ghosting_type=ghosting_type,
                    from_ref=case1_ref,
                    to_ref=case2_ref,
                    notes=_build_ghosting_note(result, ghosting_type),
                )
            )

    return GhostingAnalysisRead(
        case1_name=result.case1_name,
        case2_name=result.case2_name,
        case1_ref=case1_ref,
        case2_ref=case2_ref,
        case1_symptom=GhostingSymptomInput(
            type=result.case1_symptom.type,
            onset=result.case1_symptom.onset,
            duration_days=result.case1_symptom.duration_days,
            anatomical_site=result.case1_symptom.anatomical_site,
        ),
        ghosted_source=_serialize_lesion(result.ghosted_source),
        ghosted_spread=_serialize_lesion(result.ghosted_spread),
        source_scenarios=_serialize_scenario(result.source_scenarios),
        spread_scenarios=_serialize_scenario(result.spread_scenarios),
        verdict=result.verdict,
        log=result.log,
        suggested_records=suggested_records,
    )


@router.post("/ghosting/analyze", response_model=GhostingAnalysisRead)
def analyze_ghosting(
    payload: GhostingAnalysisRequest,
    _actor: OperatorAccess,
):
    try:
        result = run_ghosting_analysis(
            op_name=payload.op_name,
            op_symptoms=_payload_symptoms_to_engine(payload.op_symptoms),
            op_exposure=_payload_exposure_to_engine(payload.op_exposure),
            op_treatment_date=payload.op_treatment_date,
            partner_name=payload.partner_name,
            partner_symptoms=_payload_symptoms_to_engine(payload.partner_symptoms),
            partner_exposure=_payload_exposure_to_engine(payload.partner_exposure),
            partner_treatment_date=payload.partner_treatment_date,
            op_body_parts=payload.op_body_parts,
            partner_body_parts=payload.partner_body_parts,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _serialize_analysis(result)


@router.post(
    "/cases/{case_id}/partners/{partner_id}/ghosting-analysis",
    response_model=GhostingAnalysisRead,
)
def analyze_case_partner_ghosting(
    case_id: int,
    partner_id: int,
    payload: GhostingCaseAnalysisRequest,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    case = _get_case_or_404(db, case_id)
    partner = _get_partner_for_case_or_404(db, case_id, partner_id)

    op_labs = get_lab_results_for_case(db, case_id)
    op_non_reactive = _non_reactive_treponemal_name(op_labs)
    if op_non_reactive:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"{case.patient_name} has a Non-reactive {op_non_reactive} result. "
                "A non-reactive treponemal test indicates the patient is not infected "
                "and cannot be included in ghosting analysis."
            ),
        )

    partner_label = partner.name or f"Partner {partner.partner_number}"
    partner_non_reactive = _non_reactive_treponemal_name(
        get_lab_results_for_partner(db, partner_id)
    )
    if partner_non_reactive:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"{partner_label} has a Non-reactive {partner_non_reactive} result. "
                "A non-reactive treponemal test indicates the patient is not infected "
                "and cannot be included in ghosting analysis."
            ),
        )

    relationship = get_case_partner_relationship(db, case_id, partner_id)
    shared_exposure = _relationship_exposure_to_engine(relationship)
    fields_set = payload.model_fields_set

    op_symptoms = (
        _payload_symptoms_to_engine(payload.op_symptoms)
        if "op_symptoms" in fields_set
        else _symptom_entries_to_engine(
            get_symptoms_for_case(db, case_id),
            case.historical_primary_chancre,
            case.historical_primary_date,
        )
    )
    partner_symptoms = (
        _payload_symptoms_to_engine(payload.partner_symptoms)
        if "partner_symptoms" in fields_set
        else _symptom_entries_to_engine(
            get_symptoms_for_partner(db, partner_id),
            partner.historical_primary_chancre,
            partner.historical_primary_date,
        )
    )
    op_exposure = (
        _payload_exposure_to_engine(payload.op_exposure)
        if "op_exposure" in fields_set
        else shared_exposure
    )
    partner_exposure = (
        _payload_exposure_to_engine(payload.partner_exposure)
        if "partner_exposure" in fields_set
        else shared_exposure
    )
    op_treatment_date = (
        payload.op_treatment_date
        if "op_treatment_date" in fields_set
        else case.treatment_date
    )
    partner_treatment_date = (
        payload.partner_treatment_date
        if "partner_treatment_date" in fields_set
        else partner.treatment_date
    )

    op_body_parts = (
        _parse_modalities(relationship.op_body_parts) if relationship else []
    )
    partner_body_parts = (
        _parse_modalities(relationship.partner_body_parts) if relationship else []
    )

    try:
        result = run_ghosting_analysis(
            op_name=case.patient_name,
            op_symptoms=op_symptoms,
            op_exposure=op_exposure,
            op_treatment_date=op_treatment_date,
            partner_name=partner.name or f"Partner {partner.partner_number}",
            partner_symptoms=partner_symptoms,
            partner_exposure=partner_exposure,
            partner_treatment_date=partner_treatment_date,
            op_body_parts=op_body_parts,
            partner_body_parts=partner_body_parts,
        )
        case1_role, _, _, _ = select_case1(op_symptoms, partner_symptoms)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    case1_ref = "OP" if case1_role == "OP" else str(partner.partner_number)
    case2_ref = str(partner.partner_number) if case1_role == "OP" else "OP"
    return _serialize_analysis(result, case1_ref=case1_ref, case2_ref=case2_ref)


@router.get("/cases/{case_id}/ghostings", response_model=list[GhostingRead])
def list_case_ghostings(case_id: int, db: Annotated[Session, Depends(get_db)]):
    _get_case_or_404(db, case_id)
    return get_ghostings(db, case_id)


@router.post(
    "/cases/{case_id}/ghostings",
    response_model=GhostingRead,
    status_code=status.HTTP_201_CREATED,
)
def create_case_ghosting_endpoint(
    case_id: int,
    payload: GhostingCreate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_case_or_404(db, case_id)
    return create_ghosting(
        db,
        case_id=case_id,
        **payload.model_dump(),
    )


@router.get("/cases/ghostings/{ghosting_id}", response_model=GhostingRead)
def get_ghosting_endpoint(
    ghosting_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    return _get_ghosting_or_404(db, ghosting_id)


@router.patch("/cases/ghostings/{ghosting_id}", response_model=GhostingRead)
def update_ghosting_endpoint(
    ghosting_id: int,
    payload: GhostingUpdate,
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    _get_ghosting_or_404(db, ghosting_id)
    updated = update_ghosting(db, ghosting_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ghosting record {ghosting_id} not found",
        )
    return updated


_CONFIDENCE_RANK: dict[str, int] = {
    "Robust": 4,
    "Likely": 3,
    "Possible": 2,
    "Unrelated": 0,
}


def _person_node_id(person_id: int | None, fallback_prefix: str, entity_id: int) -> str:
    """Use a person-scoped node ID when available; fall back to entity-scoped."""
    if person_id is not None:
        return f"person-{person_id}"
    return f"{fallback_prefix}-{entity_id}"


@router.get("/transmission-chain", response_model=TransmissionChainRead)
def get_transmission_chain(
    db: Annotated[Session, Depends(get_db)],
    _actor: OperatorAccess,
):
    """
    Run VCA ghosting analysis for every known case-partner pair and return
    a directed graph of plausible transmission links (UNRELATED pairs excluded).
    Pairs with insufficient data or non-reactive treponemal labs are skipped.
    Each real-world individual is keyed by person_id so mutual links between
    two cases are deduplicated and never produce duplicate edges.
    """
    nodes: list[TransmissionNode] = []
    edges: list[TransmissionEdge] = []
    skipped: list[TransmissionSkipped] = []

    seen_node_ids: set[str] = set()
    seen_pair_ids: set[frozenset[str]] = set()
    total_analyzed = 0

    for case in get_all_cases(db):
        case_node_id = _person_node_id(case.person_id, "case", case.id)
        op_name = case.patient_name or f"Case {case.id}"

        if case_node_id not in seen_node_ids:
            nodes.append(
                TransmissionNode(
                    id=case_node_id,
                    label=op_name,
                    type="case",
                    case_id=case.id,
                )
            )
            seen_node_ids.add(case_node_id)

        op_labs = get_lab_results_for_case(db, case.id)
        op_excluded = _non_reactive_treponemal_name(op_labs)

        for partner in get_partners_for_case(db, case.id):
            partner_label = partner.name or f"Partner {partner.partner_number}"

            # Resolve partner node — person_id takes priority (set by create_partner
            # for both linked and unlinked partners). Fall back to linked_case_id
            # resolution for rows that predate the persons table.
            if partner.person_id is not None:
                partner_node_id = f"person-{partner.person_id}"
                if partner_node_id not in seen_node_ids:
                    p_type = "case" if partner.linked_case_id else "partner"
                    nodes.append(
                        TransmissionNode(
                            id=partner_node_id,
                            label=partner_label,
                            type=p_type,
                            case_id=partner.linked_case_id,
                            partner_id=partner.id if not partner.linked_case_id else None,
                            linked_case_id=partner.linked_case_id,
                        )
                    )
                    seen_node_ids.add(partner_node_id)
            elif partner.linked_case_id:
                linked_case = get_case_by_id(db, partner.linked_case_id)
                partner_node_id = _person_node_id(
                    linked_case.person_id if linked_case else None,
                    "case",
                    partner.linked_case_id,
                )
                if partner_node_id not in seen_node_ids:
                    linked_label = (
                        linked_case.patient_name
                        if linked_case
                        else f"Case {partner.linked_case_id}"
                    )
                    nodes.append(
                        TransmissionNode(
                            id=partner_node_id,
                            label=linked_label,
                            type="case",
                            case_id=partner.linked_case_id,
                            linked_case_id=partner.linked_case_id,
                        )
                    )
                    seen_node_ids.add(partner_node_id)
            else:
                partner_node_id = f"partner-{partner.id}"
                if partner_node_id not in seen_node_ids:
                    nodes.append(
                        TransmissionNode(
                            id=partner_node_id,
                            label=partner_label,
                            type="partner",
                            case_id=case.id,
                            partner_id=partner.id,
                        )
                    )
                    seen_node_ids.add(partner_node_id)

            # Skip self-loops (partner linked to same case)
            if partner_node_id == case_node_id:
                continue

            # Skip pairs already analyzed from the other direction
            pair = frozenset({case_node_id, partner_node_id})
            if pair in seen_pair_ids:
                continue
            seen_pair_ids.add(pair)

            # Exclusion checks
            if op_excluded:
                skipped.append(
                    TransmissionSkipped(
                        case_id=case.id,
                        partner_id=partner.id,
                        partner_label=partner_label,
                        reason=f"{op_name}: Non-reactive {op_excluded}",
                    )
                )
                continue

            partner_non_reactive = _non_reactive_treponemal_name(
                get_lab_results_for_partner(db, partner.id)
            )
            if partner_non_reactive:
                skipped.append(
                    TransmissionSkipped(
                        case_id=case.id,
                        partner_id=partner.id,
                        partner_label=partner_label,
                        reason=f"{partner_label}: Non-reactive {partner_non_reactive}",
                    )
                )
                continue

            # Gather clinical inputs
            op_symptoms = _symptom_entries_to_engine(
                get_symptoms_for_case(db, case.id),
                case.historical_primary_chancre,
                case.historical_primary_date,
            )
            partner_symptoms = _symptom_entries_to_engine(
                get_symptoms_for_partner(db, partner.id),
                partner.historical_primary_chancre,
                partner.historical_primary_date,
            )
            relationship = get_case_partner_relationship(db, case.id, partner.id)
            shared_exposure = _relationship_exposure_to_engine(relationship)
            op_body_parts = _parse_modalities(relationship.op_body_parts) if relationship else []
            partner_body_parts = (
                _parse_modalities(relationship.partner_body_parts) if relationship else []
            )

            try:
                result = run_ghosting_analysis(
                    op_name=op_name,
                    op_symptoms=op_symptoms,
                    op_exposure=shared_exposure,
                    op_treatment_date=case.treatment_date,
                    partner_name=partner_label,
                    partner_symptoms=partner_symptoms,
                    partner_exposure=shared_exposure,
                    partner_treatment_date=partner.treatment_date,
                    op_body_parts=op_body_parts,
                    partner_body_parts=partner_body_parts,
                )
            except ValueError as exc:
                skipped.append(
                    TransmissionSkipped(
                        case_id=case.id,
                        partner_id=partner.id,
                        partner_label=partner_label,
                        reason=str(exc),
                    )
                )
                continue

            total_analyzed += 1

            if "UNRELATED" in result.verdict:
                continue

            # Determine edge direction from confidence ranks
            source_rank = _CONFIDENCE_RANK.get(result.source_scenarios.confidence, 0)
            spread_rank = _CONFIDENCE_RANK.get(result.spread_scenarios.confidence, 0)
            is_ambiguous = source_rank == spread_rank and source_rank > 0

            # case1 is the anchor; source = case2→case1, spread = case1→case2
            op_is_case1 = result.case1_name == op_name
            if op_is_case1:
                from_node_id = partner_node_id if source_rank >= spread_rank else case_node_id
                to_node_id = case_node_id if source_rank >= spread_rank else partner_node_id
            else:
                from_node_id = case_node_id if source_rank >= spread_rank else partner_node_id
                to_node_id = partner_node_id if source_rank >= spread_rank else case_node_id

            dominant_confidence = (
                result.source_scenarios.confidence
                if source_rank >= spread_rank
                else result.spread_scenarios.confidence
            )

            edges.append(
                TransmissionEdge(
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    verdict=result.verdict,
                    source_confidence=result.source_scenarios.confidence,
                    spread_confidence=result.spread_scenarios.confidence,
                    dominant_confidence=dominant_confidence,
                    is_ambiguous=is_ambiguous,
                )
            )

    return TransmissionChainRead(
        nodes=nodes,
        edges=edges,
        skipped=skipped,
        total_pairs_analyzed=total_analyzed,
        total_pairs_skipped=len(skipped),
    )


@router.delete("/cases/ghostings/{ghosting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ghosting_endpoint(
    ghosting_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_ghosting_or_404(db, ghosting_id)
    delete_ghosting(db, ghosting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
