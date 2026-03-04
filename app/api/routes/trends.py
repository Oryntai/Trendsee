from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_db
from app.schemas.trend import TrendCreate, TrendListResponse, TrendOut, TrendPatch
from app.services import trends as trends_service

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("", response_model=TrendListResponse)
async def list_trends(
    session: Annotated[AsyncSession, Depends(get_db)],
    active: bool | None = None,
    type: str | None = Query(default=None, alias="type"),
    popular: bool | None = None,
    tag: str | None = None,
    search: str | None = None,
    sort: str | None = Query(default="popular"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items, total = await trends_service.list_trends(
        session,
        active=active,
        trend_type=type,
        popular=popular,
        tag=tag,
        search=search,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return TrendListResponse(items=items, limit=limit, offset=offset, total=total)


@router.get("/{trend_id}", response_model=TrendOut)
async def get_trend(trend_id: int, session: Annotated[AsyncSession, Depends(get_db)]):
    trend = await trends_service.get_trend(session, trend_id)
    return TrendOut.model_validate(trend)


@router.post("", response_model=TrendOut, dependencies=[Depends(require_admin)])
async def create_trend(payload: TrendCreate, session: Annotated[AsyncSession, Depends(get_db)]):
    trend = await trends_service.create_trend(session, payload)
    return TrendOut.model_validate(trend)


@router.patch("/{trend_id}", response_model=TrendOut, dependencies=[Depends(require_admin)])
async def patch_trend(trend_id: int, payload: TrendPatch, session: Annotated[AsyncSession, Depends(get_db)]):
    trend = await trends_service.get_trend(session, trend_id)
    trend = await trends_service.update_trend(session, trend, payload)
    return TrendOut.model_validate(trend)
