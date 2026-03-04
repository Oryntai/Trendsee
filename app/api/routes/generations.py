from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_current_user, get_user_by_api_key
from app.core.config import settings
from app.core.errors import unauthorized
from app.db.session import get_db, get_sessionmaker
from app.models.enums import GenerationStatus
from app.models.user import User
from app.schemas.generation import GenerationCreate, GenerationCreateResponse, GenerationListResponse, GenerationOut
from app.services import generations as generations_service

router = APIRouter(prefix="/generations", tags=["generations"])


@router.post("", response_model=GenerationCreateResponse, status_code=201)
async def create_generation(
    payload: GenerationCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    result = await generations_service.create_generation(
        session,
        user=current_user,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.status_code = 200 if result.replayed else 201
    body = GenerationCreateResponse(
        id=result.generation.id,
        status=result.generation.status,
        price_tokens=result.generation.price_tokens,
        balance_after=result.balance_after,
    )
    return body


@router.get("/{generation_id}", response_model=GenerationOut)
async def get_generation(
    generation_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    generation = await generations_service.get_generation_for_user(session, generation_id, current_user)
    return GenerationOut.model_validate(generations_service.generation_to_dict(generation))


@router.get("", response_model=GenerationListResponse)
async def list_generations(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    mine: bool = True,
    trend_id: int | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    page = await generations_service.list_generations(
        session,
        user=current_user,
        mine=mine,
        trend_id=trend_id,
        limit=limit,
        offset=offset,
    )
    return GenerationListResponse(
        items=[GenerationOut.model_validate(generations_service.generation_to_dict(item)) for item in page.items],
        limit=limit,
        offset=offset,
        total=page.total,
    )


@router.get("/{generation_id}/events")
async def generation_events(
    generation_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
    api_key: str | None = Query(default=None),
):
    user = current_user
    if user is None:
        user = await get_user_by_api_key(session, api_key)
    if user is None:
        raise unauthorized("Authentication required for events stream")

    sessionmaker = get_sessionmaker()

    async def event_stream():
        last_signature: tuple[str, str] | None = None
        while True:
            async with sessionmaker() as poll_session:
                generation = await generations_service.get_generation_for_user(poll_session, generation_id, user)
            updated_at = (generation.updated_at or generation.created_at).isoformat()
            signature = (generation.status.value, updated_at)
            if signature != last_signature:
                payload = {
                    "id": generation.id,
                    "status": generation.status.value,
                    "updated_at": updated_at,
                    "result_text": generation.result_text,
                    "error_message": generation.error_message,
                }
                event_name = "status"
                if generation.status == GenerationStatus.done:
                    event_name = "done"
                elif generation.status == GenerationStatus.failed:
                    event_name = "failed"

                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_signature = signature

                if generation.status in {GenerationStatus.done, GenerationStatus.failed}:
                    break

            await asyncio.sleep(settings.sse_poll_interval_sec)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
