from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_sessionmaker
from app.models.enums import GenerationStatus
from app.models.generation import Generation, GenerationAsset
from app.services.providers import get_provider
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
_worker_loop: asyncio.AbstractEventLoop | None = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
    return _worker_loop


async def run_generation_async(generation_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = (
            select(Generation)
            .where(Generation.id == generation_id)
            .options(
                selectinload(Generation.trend),
                selectinload(Generation.assets).selectinload(GenerationAsset.asset),
            )
        )
        generation = await session.scalar(stmt)
        if not generation:
            logger.warning("generation_not_found generation_id=%s", generation_id)
            return

        if generation.status in {GenerationStatus.done, GenerationStatus.failed}:
            return

        generation.status = GenerationStatus.running
        generation.started_at = datetime.now(tz=timezone.utc)
        await session.commit()

        provider = get_provider()

        try:
            output = await provider.generate(
                trend=generation.trend,
                prompt=generation.prompt,
                resources=generation.resources,
                assets=[link.asset for link in generation.assets],
            )
            generation.status = GenerationStatus.done
            generation.result_text = output.result_text
            generation.result_json = output.raw
            generation.provider = output.provider
            generation.model = output.model
            generation.finished_at = datetime.now(tz=timezone.utc)
            generation.error_message = None
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("generation_failed generation_id=%s", generation_id)
            generation.status = GenerationStatus.failed
            generation.error_message = str(exc)
            generation.finished_at = datetime.now(tz=timezone.utc)
            await session.commit()


@celery_app.task(
    name="run_generation_task",
    bind=True,
    autoretry_for=(httpx.TransportError, httpx.TimeoutException),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def run_generation_task(self, generation_id: str) -> None:
    _ = self
    loop = _get_worker_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_generation_async(generation_id))
