from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.models import GhostingType
from app.db.queries import (
    create_ghosting,
    delete_ghosting,
    get_case_by_id,
    get_case_partner_relationship,
    get_ghosting_by_id,
    get_ghostings,
    get_partner_by_id,
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
    GhostingScenarioLesionsRead,
    GhostingScenarioRangesRead,
    GhostingScenarioRead,
    GhostingSymptomInput,
    GhostingUpdate,
    SuggestedGhostingRecordRead,
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
        exposure_modalities=exposure.exposure_modalities,
    )


def _relationship_exposure_to_engine(relationship) -> Exposure | None:
    if not relationship:
        return None
    if not relationship.exposure_first_date or not relationship.exposure_last_date:
        return None
    return Exposure(
        first=relationship.exposure_first_date,
        last=relationship.exposure_last_date,
        exposure_modalities=_parse_modalities(relationship.exposure_modalities),
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
        range_data=GhostingScenarioRangesRead(
            aggressive=_serialize_range_criteria(result.range_data["aggressive"]),
            expected=_serialize_range_criteria(result.range_data["expected"]),
            conservative=_serialize_range_criteria(result.range_data["conservative"]),
        ),
        range_lesions=GhostingScenarioLesionsRead(
            aggressive=_serialize_lesion(result.range_lesions["aggressive"]),
            expected=_serialize_lesion(result.range_lesions["expected"]),
            conservative=_serialize_lesion(result.range_lesions["conservative"]),
        ),
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


@router.delete("/cases/ghostings/{ghosting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ghosting_endpoint(
    ghosting_id: int,
    db: Annotated[Session, Depends(get_db)],
    _actor: SupervisorAccess,
):
    _get_ghosting_or_404(db, ghosting_id)
    delete_ghosting(db, ghosting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
