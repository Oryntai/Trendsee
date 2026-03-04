from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import MeOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("", response_model=MeOut)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return MeOut(user_id=current_user.id, token_balance=current_user.token_balance, is_admin=current_user.is_admin)
