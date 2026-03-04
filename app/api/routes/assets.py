from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.asset import AssetOut
from app.services.assets import asset_public_url, save_upload_file

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/upload", response_model=AssetOut)
async def upload_asset(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    _ = current_user
    asset = await save_upload_file(session, file)
    return AssetOut(
        id=asset.id,
        kind=asset.kind,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        url=asset_public_url(asset.storage_path),
        created_at=asset.created_at,
    )
