from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import not_found
from app.models.trend import Trend
from app.schemas.trend import TrendCreate, TrendPatch


async def list_trends(
    session: AsyncSession,
    *,
    active: bool | None,
    trend_type: str | None,
    popular: bool | None,
    tag: str | None,
    search: str | None,
    sort: str | None = None,
    limit: int,
    offset: int,
) -> tuple[list[Trend], int]:
    stmt = select(Trend)
    if active is not None:
        stmt = stmt.where(Trend.is_active == active)
    if trend_type is not None:
        stmt = stmt.where(Trend.type == trend_type)
    if popular is not None:
        stmt = stmt.where(Trend.is_popular == popular)
    if tag:
        stmt = stmt.where(Trend.tags.contains([tag]))
    if search:
        stmt = stmt.where(Trend.title.ilike(f"%{search}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.scalar(count_stmt)) or 0

    sort_mode = (sort or "popular").lower()
    if sort_mode == "newest":
        stmt = stmt.order_by(Trend.created_at.desc())
    elif sort_mode == "cheapest":
        stmt = stmt.order_by(Trend.price_tokens.asc(), Trend.created_at.desc())
    else:
        stmt = stmt.order_by(Trend.is_popular.desc(), Trend.created_at.desc())

    stmt = stmt.limit(limit).offset(offset)
    rows = (await session.scalars(stmt)).all()
    return list(rows), total


async def get_trend(session: AsyncSession, trend_id: int) -> Trend:
    trend = await session.get(Trend, trend_id)
    if not trend:
        raise not_found("Trend not found")
    return trend


async def create_trend(session: AsyncSession, payload: TrendCreate) -> Trend:
    trend = Trend(**payload.model_dump())
    session.add(trend)
    await session.commit()
    await session.refresh(trend)
    return trend


async def update_trend(session: AsyncSession, trend: Trend, payload: TrendPatch) -> Trend:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(trend, key, value)
    await session.commit()
    await session.refresh(trend)
    return trend
