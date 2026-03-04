from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AssetKind


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: AssetKind
    original_filename: str
    mime_type: str
    size_bytes: int
    url: str
    created_at: datetime
