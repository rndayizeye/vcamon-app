from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimelineEventCreate(BaseModel):
    event_date: date
    event_type: str = Field(min_length=1)
    notes: str | None = None
    partner_id: int | None = None


class TimelineEventUpdate(BaseModel):
    event_date: date | None = None
    event_type: str | None = Field(default=None, min_length=1)
    notes: str | None = None
    partner_id: int | None = None


class TimelineEventRead(ORMBaseModel):
    id: int
    case_id: int
    partner_id: int | None
    event_date: date
    event_type: str | None
    notes: str | None
