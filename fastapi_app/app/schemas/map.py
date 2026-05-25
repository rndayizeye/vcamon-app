from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MAPItemDefinitionRead(BaseModel):
    item_number: int
    section: str
    label: str


class MAPCatalogRead(BaseModel):
    section_order: list[str]
    items: list[MAPItemDefinitionRead]


class MAPSheetItemRead(MAPItemDefinitionRead):
    p_value: bool = False
    c_value: bool = False
    notes: str = ""
    high_priority: bool = False
    updated_at: datetime | None = None


class MAPSheetSummaryRead(BaseModel):
    total_items: int
    checked_p: int
    checked_c: int
    high_priority_flags: int


class MAPSheetRead(BaseModel):
    case_id: int
    partner_id: int | None = None
    subject_label: str
    section_order: list[str]
    items: list[MAPSheetItemRead]
    high_priority_comment: str = ""
    summary: MAPSheetSummaryRead


class MAPSheetItemUpsert(BaseModel):
    item_number: int = Field(ge=1, le=46)
    p_value: bool = False
    c_value: bool = False
    notes: str = ""
    high_priority: bool = False


class MAPSheetUpsert(BaseModel):
    items: list[MAPSheetItemUpsert] = Field(default_factory=list)
    high_priority_comment: str | None = None
