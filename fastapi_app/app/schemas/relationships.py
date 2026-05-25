from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CasePartnerRelationshipCreate(BaseModel):
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    exposure_modalities: str | None = None


class CasePartnerRelationshipUpdate(BaseModel):
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    exposure_modalities: str | None = None


class CasePartnerRelationshipRead(ORMBaseModel):
    id: int
    case_id: int
    partner_id: int
    exposure_first_date: date | None
    exposure_last_date: date | None
    exposure_modalities: str | None


class RelationshipReportCreate(BaseModel):
    reporter: str = Field(min_length=1)
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    exposure_modalities: str | None = None


class RelationshipReportUpdate(BaseModel):
    reporter: str | None = Field(default=None, min_length=1)
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    exposure_modalities: str | None = None


class RelationshipReportRead(ORMBaseModel):
    id: int
    relationship_id: int
    reporter: str
    exposure_first_date: date | None
    exposure_last_date: date | None
    exposure_modalities: str | None
    created_at: datetime | None
