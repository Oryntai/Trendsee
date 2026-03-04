from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import forbidden, unauthorized
from app.db.session import get_db
from app.models.user import User


async def get_user_by_api_key(session: AsyncSession, api_key: str | None) -> User | None:
    if not api_key:
        return None
    return await session.scalar(select(User).where(User.api_key == api_key))


async def get_optional_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User | None:
    return await get_user_by_api_key(session, x_api_key)


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User:
    user = await get_user_by_api_key(session, x_api_key)
    if not user:
        raise unauthorized("Invalid or missing X-API-Key")
    return user


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if not current_user.is_admin:
        raise forbidden("Admin access required")
    return current_user
