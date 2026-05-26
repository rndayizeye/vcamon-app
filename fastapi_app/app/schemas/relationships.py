from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CasePartnerRelationshipCreate(BaseModel):
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    op_body_parts: list[str] = []
    partner_body_parts: list[str] = []


class CasePartnerRelationshipUpdate(BaseModel):
    exposure_first_date: date | None = None
    exposure_last_date: date | None = None
    op_body_parts: list[str] | None = None
    partner_body_parts: list[str] | None = None


def _parse_body_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return [str(v) for v in parsed if v] if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


class CasePartnerRelationshipRead(ORMBaseModel):
    id: int
    case_id: int
    partner_id: int
    exposure_first_date: date | None
    exposure_last_date: date | None
    op_body_parts: list[str] = []
    partner_body_parts: list[str] = []

    @field_validator("op_body_parts", "partner_body_parts", mode="before")
    @classmethod
    def parse_body_parts_field(cls, value: Any) -> list[str]:
        return _parse_body_parts(value)


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
