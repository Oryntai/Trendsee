from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TrendType
from app.schemas.common import Pagination


class TrendBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    type: TrendType
    preview_asset_id: int | None = None
    preview_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_popular: bool = False
    is_active: bool = True
    price_tokens: int = Field(ge=0)
    prompt_template: str | None = None


class TrendCreate(TrendBase):
    pass


class TrendPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    type: TrendType | None = None
    preview_asset_id: int | None = None
    preview_url: str | None = None
    tags: list[str] | None = None
    is_popular: bool | None = None
    is_active: bool | None = None
    price_tokens: int | None = Field(default=None, ge=0)
    prompt_template: str | None = None


class TrendOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    type: TrendType
    preview_asset_id: int | None
    preview_url: str | None
    tags: list[str]
    is_popular: bool
    is_active: bool
    price_tokens: int
    prompt_template: str | None
    created_at: datetime
    updated_at: datetime


class TrendListResponse(Pagination):
    items: list[TrendOut]
