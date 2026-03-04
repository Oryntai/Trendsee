from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


engine: AsyncEngine | None = None
AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    global engine, AsyncSessionLocal
    url = database_url or settings.database_url
    kwargs = {"future": True}
    if url.startswith("sqlite+aiosqlite://"):
        kwargs["poolclass"] = NullPool

    engine = create_async_engine(url, **kwargs)
    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, AsyncSessionLocal


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        init_engine()
    assert AsyncSessionLocal is not None
    return AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


init_engine()
