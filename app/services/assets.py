from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import bad_request, not_found
from app.models.asset import Asset
from app.models.enums import AssetKind


def asset_public_url(storage_path: str) -> str:
    return f"/uploads/{storage_path.replace('\\', '/')}"


def _kind_from_mime(mime_type: str) -> AssetKind:
    if mime_type.startswith("image/"):
        return AssetKind.image
    if mime_type.startswith("video/"):
        return AssetKind.video
    return AssetKind.other


async def save_upload_file(session: AsyncSession, upload: UploadFile) -> Asset:
    content_type = (upload.content_type or "").lower()
    if not (content_type.startswith("image/") or content_type.startswith("video/")):
        raise bad_request("Only image/* and video/* uploads are allowed")

    data = await upload.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise bad_request(f"File too large. Max size is {settings.max_upload_mb}MB")

    suffix = Path(upload.filename or "").suffix.lower()
    safe_name = f"{uuid4().hex}{suffix}"
    upload_path = settings.resolved_upload_dir / safe_name

    async with aiofiles.open(upload_path, "wb") as f:
        await f.write(data)

    digest = hashlib.sha256(data).hexdigest()
    asset = Asset(
        kind=_kind_from_mime(content_type),
        original_filename=upload.filename or safe_name,
        storage_path=safe_name,
        mime_type=content_type,
        size_bytes=len(data),
        sha256=digest,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def get_assets_by_ids(session: AsyncSession, asset_ids: list[int]) -> list[Asset]:
    if not asset_ids:
        return []

    stmt = select(Asset).where(Asset.id.in_(asset_ids))
    assets = list((await session.scalars(stmt)).all())
    if len(assets) != len(set(asset_ids)):
        raise not_found("One or more assets not found")

    by_id = {asset.id: asset for asset in assets}
    return [by_id[asset_id] for asset_id in asset_ids]
