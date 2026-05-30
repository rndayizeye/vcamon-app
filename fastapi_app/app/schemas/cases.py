from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from app.db.models import (
    LabResult,
    LesionType,
    ReasonForExam,
    Symptom,
    SymptomClassification,
    Treatment,
    TreponemalResult,
)


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DiagnosisCodeInputAliasModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def alias_diagnosis_code(cls, data):
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        diagnosis_code = normalized.get("diagnosis_code")
        lot = normalized.get("lot")

        if diagnosis_code is not None and (lot is None or lot == ""):
            normalized["lot"] = diagnosis_code

        return normalized


class CaseBase(DiagnosisCodeInputAliasModel):
    patient_name: str
    lot: str | None = None
    case_manager: str | None = None
    initial_contact_date: date | None = None
    reason_for_exam: ReasonForExam | None = None
    treatment_date: date | None = None
    medical_info: str | None = None
    lab_1: LabResult | None = None
    lab_2: TreponemalResult | None = None
    lab_3: str | None = None
    treatment: Treatment | None = None
    lesion_type: LesionType | None = None
    symptom: Symptom | None = None
    symptom_classification: SymptomClassification | None = None
    symptom_onset_date: date | None = None
    symptom_duration_days: int | None = None
    symptom_ongoing: bool = False
    historical_primary_chancre: bool | None = None
    historical_primary_date: date | None = None
    lab_1_date: date | None = None
    lab_2_date: date | None = None
    lab_3_date: date | None = None


class CaseCreate(CaseBase):
    pass


class CaseUpdate(DiagnosisCodeInputAliasModel):
    patient_name: str | None = None
    lot: str | None = None
    case_manager: str | None = None
    initial_contact_date: date | None = None
    reason_for_exam: ReasonForExam | None = None
    treatment_date: date | None = None
    medical_info: str | None = None
    lab_1: LabResult | None = None
    lab_2: TreponemalResult | None = None
    lab_3: str | None = None
    treatment: Treatment | None = None
    lesion_type: LesionType | None = None
    symptom: Symptom | None = None
    symptom_classification: SymptomClassification | None = None
    symptom_onset_date: date | None = None
    symptom_duration_days: int | None = None
    symptom_ongoing: bool | None = None
    historical_primary_chancre: bool | None = None
    historical_primary_date: date | None = None
    lab_1_date: date | None = None
    lab_2_date: date | None = None
    lab_3_date: date | None = None


class CaseSummary(ORMBaseModel):
    id: int
    patient_name: str
    lot: str | None
    case_manager: str | None
    initial_contact_date: date | None
    updated_at: datetime | None
    reason_for_exam: ReasonForExam | None = None
    treatment_date: date | None = None
    partner_count: int = 0

    @computed_field(return_type=str | None)
    @property
    def diagnosis_code(self) -> str | None:
        return self.lot


class DashboardSummary(BaseModel):
    total_cases: int
    total_partners: int
    treated_count: int
    untreated_count: int



class CaseRead(ORMBaseModel):
    id: int
    patient_name: str
    lot: str | None
    case_manager: str | None
    initial_contact_date: date | None
    reason_for_exam: ReasonForExam | None
    treatment_date: date | None
    medical_info: str | None
    lab_1: LabResult | None
    lab_2: TreponemalResult | None
    lab_3: str | None
    treatment: Treatment | None
    lesion_type: LesionType | None
    symptom: Symptom | None
    symptom_classification: SymptomClassification | None
    symptom_onset_date: date | None
    symptom_duration_days: int | None
    symptom_ongoing: bool
    historical_primary_chancre: bool | None
    historical_primary_date: date | None
    lab_1_date: date | None
    lab_2_date: date | None
    lab_3_date: date | None
    created_at: datetime | None
    updated_at: datetime | None

    @computed_field(return_type=str | None)
    @property
    def diagnosis_code(self) -> str | None:
        return self.lot


class PartnerBase(BaseModel):
    name: str | None = None
    partner_number: int | None = None
    reason_for_exam: ReasonForExam | None = None
    treatment_date: date | None = None
    medical_info: str | None = None
    lab_1: LabResult | None = None
    lab_2: TreponemalResult | None = None
    lab_3: str | None = None
    treatment: Treatment | None = None
    lesion_type: LesionType | None = None
    symptom: Symptom | None = None
    symptom_classification: SymptomClassification | None = None
    symptom_onset_date: date | None = None
    symptom_duration_days: int | None = None
    symptom_ongoing: bool = False
    historical_primary_chancre: bool | None = None
    historical_primary_date: date | None = None
    lab_1_date: date | None = None
    lab_2_date: date | None = None
    lab_3_date: date | None = None


class PartnerCreate(PartnerBase):
    pass


class PartnerUpdate(BaseModel):
    name: str | None = None
    partner_number: int | None = None
    reason_for_exam: ReasonForExam | None = None
    treatment_date: date | None = None
    medical_info: str | None = None
    lab_1: LabResult | None = None
    lab_2: TreponemalResult | None = None
    lab_3: str | None = None
    treatment: Treatment | None = None
    lesion_type: LesionType | None = None
    symptom: Symptom | None = None
    symptom_classification: SymptomClassification | None = None
    symptom_onset_date: date | None = None
    symptom_duration_days: int | None = None
    symptom_ongoing: bool | None = None
    historical_primary_chancre: bool | None = None
    historical_primary_date: date | None = None
    lab_1_date: date | None = None
    lab_2_date: date | None = None
    lab_3_date: date | None = None


class PartnerLinkCase(BaseModel):
    linked_case_id: int | None = None


class PartnerRead(ORMBaseModel):
    id: int
    case_id: int
    partner_number: int
    name: str | None
    reason_for_exam: ReasonForExam | None
    treatment_date: date | None
    medical_info: str | None
    lab_1: LabResult | None
    lab_2: TreponemalResult | None
    lab_3: str | None
    treatment: Treatment | None
    lesion_type: LesionType | None
    symptom: Symptom | None
    symptom_classification: SymptomClassification | None
    symptom_onset_date: date | None
    symptom_duration_days: int | None
    symptom_ongoing: bool
    historical_primary_chancre: bool | None
    historical_primary_date: date | None
    lab_1_date: date | None
    lab_2_date: date | None
    lab_3_date: date | None
    created_at: datetime | None
    linked_case_id: int | None = None
