from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import (
    SymptomClassification,
    SymptomDateKind,
    SymptomDurationSource,
)


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SymptomEntryCreate(BaseModel):
    symptom_type: str = Field(min_length=1)
    onset_date: date | None = None
    date_kind: SymptomDateKind = SymptomDateKind.ONSET_REPORTED
    duration_days: int | None = Field(default=None, ge=0)
    ongoing: bool | None = None


class SymptomEntryUpdate(BaseModel):
    symptom_type: str | None = Field(default=None, min_length=1)
    onset_date: date | None = None
    date_kind: SymptomDateKind | None = None
    duration_days: int | None = Field(default=None, ge=0)
    ongoing: bool | None = None


class SymptomEntryRead(ORMBaseModel):
    id: int
    subject_id: int
    symptom_type: str
    classification: SymptomClassification | None
    onset_date: date | None
    date_kind: SymptomDateKind
    duration_days: int | None
    duration_source: SymptomDurationSource
    ongoing: bool
