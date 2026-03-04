from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GenerationStatus, TrendType
from app.schemas.asset import AssetOut
from app.schemas.common import Pagination


class ResourceItem(BaseModel):
    url: str
    note: str | None = None


class GenerationCreate(BaseModel):
    trend_id: int
    prompt: str = Field(min_length=1)
    resources: list[ResourceItem] = Field(default_factory=list)
    asset_ids: list[int] = Field(default_factory=list)


class GenerationCreateResponse(BaseModel):
    id: str
    status: GenerationStatus
    price_tokens: int
    balance_after: int


class GenerationTrendInfo(BaseModel):
    id: int
    title: str
    type: TrendType


class GenerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: GenerationStatus
    trend: GenerationTrendInfo
    prompt: str
    resources: list[dict]
    assets: list[AssetOut]
    price_tokens: int
    provider: str
    model: str
    result_text: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class GenerationListResponse(Pagination):
    items: list[GenerationOut]
