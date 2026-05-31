from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TestCategory


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LabResultEntryBase(BaseModel):
    test_category: TestCategory
    test_type: str = Field(min_length=1)
    titer: str | None = None
    result: str | None = None
    collection_date: date


class LabResultEntryCreate(LabResultEntryBase):
    pass


class LabResultEntryUpdate(BaseModel):
    test_category: TestCategory | None = None
    test_type: str | None = Field(default=None, min_length=1)
    titer: str | None = None
    result: str | None = None
    collection_date: date | None = None


class LabResultEntryRead(ORMBaseModel):
    id: int
    subject_id: int
    test_category: TestCategory
    test_type: str
    titer: str | None
    result: str | None
    collection_date: date
