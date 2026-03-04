from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import payment_required
from app.models.token_transaction import TokenTransaction
from app.models.user import User


async def get_user_for_update(session: AsyncSession, user_id: int) -> User:
    stmt = select(User).where(User.id == user_id).with_for_update()
    user = await session.scalar(stmt)
    if user is None:
        raise payment_required("User not found")
    return user


def assert_sufficient_balance(user: User, amount: int) -> None:
    if user.token_balance < amount:
        raise payment_required("Insufficient tokens")


def apply_token_change(
    session: AsyncSession,
    *,
    user: User,
    amount: int,
    reason: str,
    generation_id: str | None,
) -> int:
    before = user.token_balance
    after = before + amount
    if after < 0:
        raise payment_required("Insufficient tokens")

    user.token_balance = after
    tx = TokenTransaction(
        user_id=user.id,
        generation_id=generation_id,
        amount=amount,
        balance_before=before,
        balance_after=after,
        reason=reason,
    )
    session.add(tx)
    return after
