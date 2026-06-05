from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.models import GhostingType


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GhostingCreate(BaseModel):
    ghosting_type: GhostingType
    from_ref: str | None = None
    to_ref: str | None = None
    notes: str | None = None


class GhostingUpdate(BaseModel):
    ghosting_type: GhostingType | None = None
    from_ref: str | None = None
    to_ref: str | None = None
    notes: str | None = None

    @field_validator("ghosting_type")
    @classmethod
    def validate_ghosting_type(cls, value: GhostingType | None):
        if value is None:
            raise ValueError("ghosting_type cannot be null")
        return value


class GhostingRead(ORMBaseModel):
    id: int
    case_id: int
    ghosting_type: GhostingType
    from_ref: str | None
    to_ref: str | None
    notes: str | None


class GhostingSymptomInput(BaseModel):
    type: str = Field(min_length=1)
    onset: date
    duration_days: int = Field(default=0, ge=0)
    anatomical_site: str | None = None


class GhostingExposureInput(BaseModel):
    first: date
    last: date

    @model_validator(mode="after")
    def validate_date_order(self) -> "GhostingExposureInput":
        if self.last < self.first:
            raise ValueError(
                "last exposure date must be on or after first exposure date"
            )
        return self


class GhostingAnalysisRequest(BaseModel):
    op_name: str = Field(min_length=1)
    op_symptoms: list[GhostingSymptomInput] = Field(default_factory=list)
    op_exposure: GhostingExposureInput | None = None
    op_treatment_date: date | None = None
    op_body_parts: list[str] = Field(default_factory=list)
    partner_name: str = Field(min_length=1)
    partner_symptoms: list[GhostingSymptomInput] = Field(default_factory=list)
    partner_exposure: GhostingExposureInput | None = None
    partner_treatment_date: date | None = None
    partner_body_parts: list[str] = Field(default_factory=list)


class GhostingCaseAnalysisRequest(BaseModel):
    op_symptoms: list[GhostingSymptomInput] | None = None
    op_exposure: GhostingExposureInput | None = None
    op_treatment_date: date | None = None
    partner_symptoms: list[GhostingSymptomInput] | None = None
    partner_exposure: GhostingExposureInput | None = None
    partner_treatment_date: date | None = None


class GhostingCriteriaCheckRead(BaseModel):
    status: str
    detail: str


class GhostingScenarioCriteriaRead(BaseModel):
    exposure: GhostingCriteriaCheckRead
    exposure_modality: GhostingCriteriaCheckRead
    latency: GhostingCriteriaCheckRead
    natural_order: GhostingCriteriaCheckRead


class GhostedLesionRead(BaseModel):
    lesion_type: str
    onset: date
    end: date
    derived_from_symptom: str
    assigned_to: str


class GhostingScenarioRead(BaseModel):
    # Keys are scenario names: aggressive, expected, conservative,
    # fast_infection_slow_disease, slow_infection_fast_disease
    range_data: dict[str, GhostingScenarioCriteriaRead]
    range_lesions: dict[str, GhostedLesionRead]
    confidence: str  # Robust | Likely | Possible | Weak | Unlikely | Unrelated
    pass_count: int  # 0–5


class SuggestedGhostingRecordRead(BaseModel):
    ghosting_type: GhostingType
    from_ref: str
    to_ref: str
    notes: str


class GhostingAnalysisRead(BaseModel):
    case1_name: str
    case2_name: str
    case1_ref: str | None = None
    case2_ref: str | None = None
    case1_symptom: GhostingSymptomInput
    ghosted_source: GhostedLesionRead
    ghosted_spread: GhostedLesionRead
    source_scenarios: GhostingScenarioRead
    spread_scenarios: GhostingScenarioRead
    verdict: str
    log: list[str]
    suggested_records: list[SuggestedGhostingRecordRead] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Transmission chain schemas
# ---------------------------------------------------------------------------


class TransmissionNode(BaseModel):
    id: str
    label: str
    type: str  # "case" | "partner"
    case_id: int | None = None
    partner_id: int | None = None
    linked_case_id: int | None = None


class TransmissionEdge(BaseModel):
    from_node_id: str
    to_node_id: str
    verdict: str
    source_confidence: str
    spread_confidence: str
    dominant_confidence: str
    is_ambiguous: bool


class TransmissionSkipped(BaseModel):
    case_id: int
    partner_id: int
    partner_label: str
    reason: str


class TransmissionChainRead(BaseModel):
    nodes: list[TransmissionNode]
    edges: list[TransmissionEdge]
    skipped: list[TransmissionSkipped]
    total_pairs_analyzed: int
    total_pairs_skipped: int
