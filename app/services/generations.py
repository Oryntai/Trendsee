from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.errors import ApiError, conflict, not_found
from app.models.asset import Asset
from app.models.enums import GenerationStatus
from app.models.generation import Generation, GenerationAsset
from app.models.idempotency_key import IdempotencyKey
from app.models.trend import Trend
from app.models.user import User
from app.schemas.generation import GenerationCreate
from app.services import billing
from app.services.assets import asset_public_url, get_assets_by_ids

logger = logging.getLogger(__name__)


@dataclass
class CreateGenerationResult:
    generation: Generation
    balance_after: int
    replayed: bool = False


@dataclass
class GenerationPage:
    items: list[Generation]
    total: int


def _request_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


async def _load_generation_with_relations(session: AsyncSession, generation_id: str) -> Generation | None:
    stmt = (
        select(Generation)
        .where(Generation.id == generation_id)
        .execution_options(populate_existing=True)
        .options(
            selectinload(Generation.trend),
            selectinload(Generation.assets).selectinload(GenerationAsset.asset),
        )
    )
    return await session.scalar(stmt)


async def create_generation(
    session: AsyncSession,
    *,
    user: User,
    payload: GenerationCreate,
    idempotency_key: str | None,
) -> CreateGenerationResult:
    trend = await session.get(Trend, payload.trend_id)
    if not trend:
        raise not_found("Trend not found")
    if not trend.is_active:
        raise ApiError(status_code=400, code="trend_inactive", message="Trend is inactive")

    assets = await get_assets_by_ids(session, payload.asset_ids)
    request_payload = {
        "trend_id": payload.trend_id,
        "prompt": payload.prompt,
        "resources": [r.model_dump() for r in payload.resources],
        "asset_ids": payload.asset_ids,
    }
    request_hash = _request_hash(request_payload)

    if idempotency_key:
        existing_key = await session.scalar(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user.id,
                IdempotencyKey.key == idempotency_key,
            )
        )
        if existing_key:
            if existing_key.request_hash != request_hash:
                raise conflict("Idempotency-Key was already used with a different payload")

            generation = await _load_generation_with_relations(session, existing_key.generation_id)
            if not generation:
                raise not_found("Generation not found")

            owner = await session.get(User, user.id)
            return CreateGenerationResult(
                generation=generation,
                balance_after=owner.token_balance if owner else 0,
                replayed=True,
            )

    try:
        locked_user = await billing.get_user_for_update(session, user.id)
        billing.assert_sufficient_balance(locked_user, trend.price_tokens)

        generation = Generation(
            user_id=locked_user.id,
            trend_id=trend.id,
            prompt=payload.prompt,
            resources=[r.model_dump() for r in payload.resources],
            status=GenerationStatus.queued,
            price_tokens=trend.price_tokens,
            provider="mock",
            model="mock-v1",
        )
        session.add(generation)
        await session.flush()

        for asset in assets:
            session.add(GenerationAsset(generation_id=generation.id, asset_id=asset.id, role="input"))

        balance_after = billing.apply_token_change(
            session,
            user=locked_user,
            amount=-trend.price_tokens,
            reason="generation_charge",
            generation_id=generation.id,
        )

        if idempotency_key:
            session.add(
                IdempotencyKey(
                    user_id=locked_user.id,
                    key=idempotency_key,
                    request_hash=request_hash,
                    generation_id=generation.id,
                )
            )

        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(generation)

    try:
        from app.tasks.generation_tasks import run_generation_async, run_generation_task

        if settings.celery_task_always_eager:
            await run_generation_async(generation.id)
        else:
            run_generation_task.delay(generation.id)
    except Exception as exc:
        logger.exception("failed_to_enqueue_generation generation_id=%s", generation.id)
        await mark_enqueue_failed_and_refund(
            session,
            generation_id=generation.id,
            user_id=user.id,
            amount=generation.price_tokens,
            reason=f"enqueue_failed: {exc}",
        )
        raise ApiError(status_code=503, code="enqueue_failed", message="Generation queue is unavailable")

    generation = await _load_generation_with_relations(session, generation.id)
    assert generation is not None
    return CreateGenerationResult(generation=generation, balance_after=balance_after, replayed=False)


async def mark_enqueue_failed_and_refund(
    session: AsyncSession,
    *,
    generation_id: str,
    user_id: int,
    amount: int,
    reason: str,
) -> None:
    try:
        generation = await session.get(Generation, generation_id, with_for_update=True)
        if generation is None:
            return
        if generation.status in {GenerationStatus.done, GenerationStatus.failed}:
            return

        generation.status = GenerationStatus.failed
        generation.error_message = reason
        generation.finished_at = datetime.now(tz=timezone.utc)

        user = await billing.get_user_for_update(session, user_id)
        billing.apply_token_change(
            session,
            user=user,
            amount=amount,
            reason="enqueue_refund",
            generation_id=generation_id,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def get_generation_for_user(session: AsyncSession, generation_id: str, user: User) -> Generation:
    generation = await _load_generation_with_relations(session, generation_id)
    if not generation:
        raise not_found("Generation not found")
    if generation.user_id != user.id and not user.is_admin:
        raise ApiError(status_code=403, code="forbidden", message="Access denied")
    return generation


async def list_generations(
    session: AsyncSession,
    *,
    user: User,
    mine: bool,
    trend_id: int | None,
    limit: int,
    offset: int,
) -> GenerationPage:
    stmt = select(Generation)
    if mine and not user.is_admin:
        stmt = stmt.where(Generation.user_id == user.id)
    if trend_id is not None:
        stmt = stmt.where(Generation.trend_id == trend_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.scalar(count_stmt)) or 0

    stmt = (
        stmt.options(
            selectinload(Generation.trend),
            selectinload(Generation.assets).selectinload(GenerationAsset.asset),
        )
        .order_by(Generation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    items = list((await session.scalars(stmt)).all())
    return GenerationPage(items=items, total=total)


def generation_to_dict(generation: Generation) -> dict:
    trend = generation.trend
    asset_items = []
    for link in generation.assets:
        asset: Asset = link.asset
        asset_items.append(
            {
                "id": asset.id,
                "kind": asset.kind,
                "original_filename": asset.original_filename,
                "mime_type": asset.mime_type,
                "size_bytes": asset.size_bytes,
                "url": asset_public_url(asset.storage_path),
                "created_at": asset.created_at,
            }
        )

    return {
        "id": generation.id,
        "status": generation.status,
        "trend": {
            "id": trend.id,
            "title": trend.title,
            "type": trend.type,
        },
        "prompt": generation.prompt,
        "resources": generation.resources,
        "assets": asset_items,
        "price_tokens": generation.price_tokens,
        "provider": generation.provider,
        "model": generation.model,
        "result_text": generation.result_text,
        "error_message": generation.error_message,
        "created_at": generation.created_at,
        "started_at": generation.started_at,
        "finished_at": generation.finished_at,
    }
