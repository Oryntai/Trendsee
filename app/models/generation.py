from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GenerationStatus


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    trend_id: Mapped[int] = mapped_column(ForeignKey("trends.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    resources: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[GenerationStatus] = mapped_column(
        SAEnum(GenerationStatus),
        nullable=False,
        default=GenerationStatus.queued,
        index=True,
    )
    price_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False, default="mock")
    model: Mapped[str] = mapped_column(String(150), nullable=False, default="mock-v1")
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="generations")
    trend = relationship("Trend", back_populates="generations")
    assets = relationship("GenerationAsset", back_populates="generation", cascade="all, delete-orphan")
    token_transactions = relationship("TokenTransaction", back_populates="generation")


class GenerationAsset(Base):
    __tablename__ = "generation_assets"
    __table_args__ = (UniqueConstraint("generation_id", "asset_id", name="uq_generation_asset"),)

    generation_id: Mapped[str] = mapped_column(
        ForeignKey("generations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)

    generation = relationship("Generation", back_populates="assets")
    asset = relationship("Asset", back_populates="generation_links")
