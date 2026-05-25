from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ArrowLinkCreate(BaseModel):
    from_ref: str = Field(min_length=1)
    to_ref: str = Field(min_length=1)


class ArrowLinkRead(ORMBaseModel):
    id: int
    case_id: int
    from_ref: str
    to_ref: str


class AnalyticsNodeRead(BaseModel):
    ref: str
    label: str
    entity_type: str
    case_id: int
    partner_id: int | None = None
    partner_number: int | None = None
    treated: bool
    first_date: date | None = None


class AnalyticsCentralityRead(BaseModel):
    node_ref: str
    label: str
    in_degree: float
    out_degree: float
    betweenness: float


class AnalyticsClusterRead(BaseModel):
    components: list[list[str]]
    cliques: list[list[str]]


class AnalyticsSummaryRead(BaseModel):
    case_id: int
    as_of_date: date | None = None
    node_count: int
    edge_count: int
    nodes: list[AnalyticsNodeRead]
    edges: list[ArrowLinkRead]
    centralities: list[AnalyticsCentralityRead]
    clusters: AnalyticsClusterRead
