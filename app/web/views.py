from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from urllib.parse import urlencode
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_user_by_api_key, require_admin
from app.core.config import settings
from app.core.errors import bad_request, not_found, unauthorized
from app.core.security import is_admin_token_valid
from app.db.session import get_db
from app.models.trend import Trend
from app.models.user import User
from app.schemas.asset import AssetOut
from app.schemas.generation import GenerationCreate, GenerationCreateResponse, GenerationOut, ResourceItem
from app.schemas.trend import TrendCreate, TrendOut, TrendPatch
from app.services import generations as generations_service
from app.services.assets import asset_public_url, save_upload_file
from app.services.trends import create_trend, get_trend, list_trends, update_trend

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/web/templates")

STATUS_LABELS = {
    "queued": "В очереди",
    "running": "В работе",
    "done": "Готово",
    "failed": "Ошибка",
}

CATEGORY_TAGS = {
    "fashion": {"fashion"},
    "travel": {"travel"},
    "ecommerce": {"ecommerce", "product"},
    "lifestyle": {"lifestyle"},
    "greetings": {"greetings"},
    "animation": {"animation"},
    "social": {"social"},
    "photo_content": {"photo_content"},
    "family": {"family"},
}
CATEGORY_LABELS = {
    "fashion": "Мода",
    "travel": "Путешествия",
    "ecommerce": "Электронная коммерция",
    "lifestyle": "Лайфстайл",
    "greetings": "Поздравления",
    "animation": "Анимация фото",
    "social": "Соцсети",
    "photo_content": "Фото-контент",
    "family": "Семейные",
}

SORT_MODES = {"popular", "newest", "cheapest"}
TREND_TYPES = {"photo", "video"}
COLLECTION_MODES = {"popular", "new"}
RUS_MONTHS = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "мая",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}

TAG_LABELS = {
    "fashion": "мода",
    "travel": "путешествия",
    "ecommerce": "электронная коммерция",
    "lifestyle": "лайфстайл",
    "greetings": "поздравления",
    "animation": "анимация",
    "social": "соцсети",
    "photo_content": "фото-контент",
    "family": "семья",
    "reel": "рилс",
    "story": "сторис",
    "product": "товар",
    "studio": "студия",
    "portrait": "портрет",
    "flowers": "цветы",
    "romance": "романтика",
    "invite": "приглашение",
    "spring": "весна",
    "vintage": "винтаж",
    "new": "новинка",
    "montage": "монтаж",
}

CURATED_SECTION_ORDER = [
    (
        "popular",
        "Популярное",
        (
            "Оживить фото",
            "Story поздравление",
            "Reels поздравление",
            "Путешествие: монтаж",
        ),
    ),
    (
        "greetings",
        "Поздравления",
        (
            "Открытка: День рождения",
            "Поздравление для мамы",
            "Открытка для подруги",
            "Романтическое поздравление",
        ),
    ),
    (
        "animation",
        "Анимация фото",
        (
            "Оживить фото",
            "Фото говорит текст",
            "Старое фото в движение",
        ),
    ),
    (
        "social",
        "Социальные сети",
        (
            "Story поздравление",
            "Reels поздравление",
            "Видео-приглашение",
            "Городской стиль: рилс",
        ),
    ),
    (
        "photo",
        "Фото и портреты",
        (
            "Весенний портрет",
            "Портрет в студии",
            "Фото с цветами",
            "Студийное фото товара",
        ),
    ),
]

TRENDING_WEEK_TITLES = (
    "Оживить фото",
    "Story поздравление",
    "Reels поздравление",
    "Путешествие: монтаж",
)

DEMO_TOPUP_BALANCE = 1_000_000
DEMO_MIN_BALANCE = 5_000


def _parse_resources(raw_value: str) -> list[ResourceItem]:
    resources: list[ResourceItem] = []
    for raw_line in raw_value.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "|" in line:
            url, note = [part.strip() for part in line.split("|", maxsplit=1)]
        else:
            url, note = line, ""
        if not url:
            continue
        resources.append(ResourceItem(url=url, note=note or None))
    return resources


async def _get_user_by_key(session: AsyncSession, api_key: str) -> User:
    user = await session.scalar(select(User).where(User.api_key == api_key))
    if user:
        return user

    user = User(api_key=api_key, is_admin=False, token_balance=settings.initial_token_balance)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _get_demo_user(session: AsyncSession) -> User:
    user = await _get_user_by_key(session, settings.default_user_api_key)
    if settings.model_provider == "mock" and user.token_balance < DEMO_MIN_BALANCE:
        user.token_balance = DEMO_TOPUP_BALANCE
        await session.commit()
        await session.refresh(user)
    return user


def _admin_authenticated(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    if not token:
        token = request.headers.get("X-Admin-Token")
    return is_admin_token_valid(token)


def _normalize_type(raw_type: str | None) -> str | None:
    if not raw_type:
        return None
    normalized = raw_type.strip().lower()
    if normalized not in TREND_TYPES:
        return None
    return normalized


def _normalize_sort(raw_sort: str | None) -> str:
    if not raw_sort:
        return "popular"
    normalized = raw_sort.strip().lower()
    if normalized not in SORT_MODES:
        return "popular"
    return normalized


def _normalize_category(raw_category: str | None) -> str | None:
    if not raw_category:
        return None
    normalized = raw_category.strip().lower()
    if normalized not in CATEGORY_TAGS:
        return None
    return normalized


def _normalize_collection(raw_collection: str | None) -> str | None:
    if not raw_collection:
        return None
    normalized = raw_collection.strip().lower()
    if normalized not in COLLECTION_MODES:
        return None
    return normalized


def _matches_category(trend: Trend, category: str | None) -> bool:
    if not category:
        return True
    tags = {tag.lower() for tag in trend.tags}
    expected = CATEGORY_TAGS.get(category, set())
    return bool(tags.intersection(expected))


def _matches_collection(trend: Trend, collection: str | None) -> bool:
    if not collection:
        return True
    if collection == "popular":
        return bool(trend.is_popular)
    if collection == "new":
        tags = {tag.lower() for tag in trend.tags}
        return "new" in tags
    return True


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def _wants_json_response(request: Request) -> bool:
    forced = request.query_params.get("format", "").strip().lower()
    if forced == "json":
        return True

    if request.headers.get("x-api-key"):
        return True

    accept = request.headers.get("accept", "").lower()
    if "application/json" in accept:
        return True
    if "text/html" in accept:
        return False
    if "*/*" in accept:
        return True
    return False


def _map_by_title(trends: list[Trend]) -> dict[str, Trend]:
    indexed: dict[str, Trend] = {}
    for trend in trends:
        key = trend.title.strip().casefold()
        if key and key not in indexed:
            indexed[key] = trend
    return indexed


def _pick_trends_by_titles(indexed: dict[str, Trend], titles: tuple[str, ...]) -> list[Trend]:
    items: list[Trend] = []
    for title in titles:
        trend = indexed.get(title.casefold())
        if trend:
            items.append(trend)
    return items


def _build_catalog_sections(trends: list[Trend]) -> list[dict[str, object]]:
    indexed = _map_by_title(trends)
    sections: list[dict[str, object]] = []
    for slug, title, desired_titles in CURATED_SECTION_ORDER:
        items = _pick_trends_by_titles(indexed, desired_titles)
        if items:
            sections.append({"slug": slug, "title": title, "items": items})
    return sections


def _build_trending_week(trends: list[Trend]) -> list[Trend]:
    indexed = _map_by_title(trends)
    pinned = _pick_trends_by_titles(indexed, TRENDING_WEEK_TITLES)
    if pinned:
        return pinned
    return [trend for trend in trends if trend.is_popular][:4]


def _format_tags_ru(tags: list[str]) -> str:
    display: list[str] = []
    for tag in tags:
        display.append(TAG_LABELS.get(tag.lower(), tag))
    return ", ".join(display)


def _format_history_timestamp(value: datetime) -> str:
    user_tz = datetime.now().astimezone().tzinfo or timezone.utc
    source = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    local_time = source.astimezone(user_tz)
    now = datetime.now(tz=user_tz)
    delta = now - local_time

    if delta.total_seconds() < 60:
        return "только что"
    if delta.total_seconds() < 3600:
        minutes = int(delta.total_seconds() // 60)
        return f"{minutes} мин назад"
    if delta.total_seconds() < 86400:
        hours = int(delta.total_seconds() // 3600)
        return f"{hours} ч назад"

    month_name = RUS_MONTHS.get(local_time.month, "")
    return f"{local_time.day} {month_name} • {local_time:%H:%M}"


def _build_trends_url(
    *,
    category: str | None,
    collection: str | None,
    trend_type: str | None,
    sort: str | None,
    search: str | None,
) -> str:
    params: dict[str, str] = {}
    if category:
        params["category"] = category
    if collection:
        params["collection"] = collection
    if trend_type:
        params["type"] = trend_type
    if sort and sort != "popular":
        params["sort"] = sort
    if search:
        params["search"] = search
    if not params:
        return "/trends"
    return f"/trends?{urlencode(params)}"


@router.get("/", include_in_schema=False)
async def home_redirect() -> RedirectResponse:
    return RedirectResponse(url="/trends", status_code=302)


@router.get("/trends", response_class=HTMLResponse)
async def trends_page(
    request: Request,
    session: AsyncSession = Depends(get_db),
    active: bool | None = True,
    type: str | None = None,
    popular: bool | None = None,
    tag: str | None = None,
    category: str | None = None,
    collection: str | None = None,
    sort: str | None = "popular",
    search: str | None = None,
):
    selected_type = _normalize_type(type)
    selected_category = _normalize_category(category)
    selected_collection = _normalize_collection(collection)
    selected_sort = _normalize_sort(sort)
    query_search = (search or "").strip()
    has_active_filters = bool(selected_category or selected_collection or selected_type or selected_sort != "popular")
    filters_open = bool(has_active_filters or query_search)

    trends, total = await list_trends(
        session,
        active=active,
        trend_type=selected_type,
        popular=popular,
        tag=tag if tag and not selected_category else None,
        search=query_search or None,
        sort=selected_sort,
        limit=200,
        offset=0,
    )
    if selected_category:
        trends = [trend for trend in trends if _matches_category(trend, selected_category)]
        total = len(trends)
    if selected_collection:
        trends = [trend for trend in trends if _matches_collection(trend, selected_collection)]
        total = len(trends)

    if has_active_filters or query_search:
        catalog_sections = [{"slug": "results", "title": "Результаты", "items": trends}] if trends else []
        trending_week: list[Trend] = []
    else:
        catalog_sections = _build_catalog_sections(trends)
        if not catalog_sections and trends:
            catalog_sections = [{"slug": "all", "title": "Каталог", "items": trends}]
        trending_week = _build_trending_week(trends)

    if _wants_json_response(request):
        payload = {
            "items": [TrendOut.model_validate(item).model_dump(mode="json") for item in trends],
            "limit": len(trends),
            "offset": 0,
            "total": total,
        }
        return JSONResponse(content=payload)

    def build_trends_url(
        *,
        category: str | None = selected_category,
        collection: str | None = selected_collection,
        trend_type: str | None = selected_type,
        sort: str | None = selected_sort,
        search: str | None = query_search,
    ) -> str:
        normalized_category = _normalize_category(category)
        normalized_collection = _normalize_collection(collection)
        normalized_type = _normalize_type(trend_type)
        normalized_sort = _normalize_sort(sort)
        normalized_search = (search or "").strip() or None
        return _build_trends_url(
            category=normalized_category,
            collection=normalized_collection,
            trend_type=normalized_type,
            sort=normalized_sort,
            search=normalized_search,
        )

    user = await _get_demo_user(session)
    return templates.TemplateResponse(
        "trends_list.html",
        {
            "request": request,
            "title": "Каталог трендов",
            "trends": trends,
            "total": total,
            "user": user,
            "catalog_categories": tuple(CATEGORY_TAGS.keys()),
            "category_labels": CATEGORY_LABELS,
            "selected_category": selected_category,
            "selected_collection": selected_collection,
            "selected_type": selected_type,
            "selected_sort": selected_sort,
            "search_query": query_search,
            "build_trends_url": build_trends_url,
            "filters_open": filters_open,
            "catalog_sections": catalog_sections,
            "trending_week": trending_week,
        },
    )


@router.get("/trends/{trend_id}", response_class=HTMLResponse)
async def trend_detail_page(request: Request, trend_id: int, session: AsyncSession = Depends(get_db)):
    trend = await get_trend(session, trend_id)
    if _wants_json_response(request):
        return JSONResponse(content=TrendOut.model_validate(trend).model_dump(mode="json"))

    user = await _get_demo_user(session)
    return templates.TemplateResponse(
        "trend_detail.html",
        {
            "request": request,
            "title": trend.title,
            "trend": trend,
            "user": user,
            "tags_display": _format_tags_ru(trend.tags),
        },
    )


@router.post("/trends", dependencies=[Depends(require_admin)])
async def trends_create_root_api(payload: TrendCreate, session: AsyncSession = Depends(get_db)):
    trend = await create_trend(session, payload)
    return JSONResponse(status_code=HTTPStatus.CREATED, content=TrendOut.model_validate(trend).model_dump(mode="json"))


@router.patch("/trends/{trend_id}", dependencies=[Depends(require_admin)])
async def trends_patch_root_api(trend_id: int, payload: TrendPatch, session: AsyncSession = Depends(get_db)):
    trend = await get_trend(session, trend_id)
    trend = await update_trend(session, trend, payload)
    return JSONResponse(content=TrendOut.model_validate(trend).model_dump(mode="json"))


@router.get("/trends/{trend_id}/generate", response_class=HTMLResponse)
async def generate_form_page(request: Request, trend_id: int, session: AsyncSession = Depends(get_db)):
    trend = await get_trend(session, trend_id)
    user = await _get_demo_user(session)
    return templates.TemplateResponse(
        "generate_form.html",
        {
            "request": request,
            "title": f"Генерация: {trend.title}",
            "trend": trend,
            "user": user,
            "error": None,
        },
    )


@router.post("/trends/{trend_id}/generate", response_class=HTMLResponse)
async def generate_form_submit(
    request: Request,
    trend_id: int,
    prompt: str = Form(...),
    resources: str = Form(default=""),
    files: list[UploadFile] | None = None,
    session: AsyncSession = Depends(get_db),
):
    trend = await get_trend(session, trend_id)
    user = await _get_demo_user(session)

    if not prompt.strip():
        return templates.TemplateResponse(
            "generate_form.html",
            {
                "request": request,
                "title": f"Генерация: {trend.title}",
                "trend": trend,
                "user": user,
                "error": "Поле prompt обязательно",
            },
            status_code=400,
        )

    uploaded_asset_ids: list[int] = []
    if files:
        for file in files:
            if not file.filename:
                continue
            asset = await save_upload_file(session, file)
            uploaded_asset_ids.append(asset.id)

    payload = GenerationCreate(
        trend_id=trend.id,
        prompt=prompt,
        resources=_parse_resources(resources),
        asset_ids=uploaded_asset_ids,
    )

    result = await generations_service.create_generation(
        session,
        user=user,
        payload=payload,
        idempotency_key=str(uuid4()),
    )

    return RedirectResponse(url=f"/generations/{result.generation.id}", status_code=303)


@router.post("/assets/upload")
async def assets_upload_root_api(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    _ = current_user
    asset = await save_upload_file(session, file)
    payload = AssetOut(
        id=asset.id,
        kind=asset.kind,
        original_filename=asset.original_filename,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        url=asset_public_url(asset.storage_path),
        created_at=asset.created_at,
    )
    return JSONResponse(status_code=HTTPStatus.CREATED, content=payload.model_dump(mode="json"))


@router.post("/generations")
async def create_generation_root_api(
    payload: GenerationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    result = await generations_service.create_generation(
        session,
        user=current_user,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response_payload = GenerationCreateResponse(
        id=result.generation.id,
        status=result.generation.status,
        price_tokens=result.generation.price_tokens,
        balance_after=result.balance_after,
    )
    status_code = HTTPStatus.OK if result.replayed else HTTPStatus.CREATED
    return JSONResponse(status_code=status_code, content=response_payload.model_dump(mode="json"))


@router.get("/generations/{generation_id}", response_class=HTMLResponse)
async def generation_status_page(request: Request, generation_id: str, session: AsyncSession = Depends(get_db)):
    if _wants_json_response(request):
        api_key = request.headers.get("x-api-key") or request.query_params.get("api_key")
        current_user = await get_user_by_api_key(session, api_key)
        if current_user is None:
            raise unauthorized("Invalid or missing X-API-Key")
        generation = await generations_service.get_generation_for_user(session, generation_id, current_user)
        generation_data = generations_service.generation_to_dict(generation)
        return JSONResponse(content=GenerationOut.model_validate(generation_data).model_dump(mode="json"))

    user = await _get_demo_user(session)
    generation = await generations_service.get_generation_for_user(session, generation_id, user)
    return templates.TemplateResponse(
        "generation_status.html",
        {
            "request": request,
            "title": "Результат генерации",
            "generation": generation,
            "generation_data": generations_service.generation_to_dict(generation),
            "events_url": f"/api/generations/{generation.id}/events?api_key={user.api_key}",
            "status_label": _status_label(generation.status.value),
        },
    )


@router.get("/generations", response_class=HTMLResponse)
async def generation_history_page(request: Request, session: AsyncSession = Depends(get_db)):
    user = await _get_demo_user(session)
    page = await generations_service.list_generations(
        session,
        user=user,
        mine=True,
        trend_id=None,
        limit=20,
        offset=0,
    )
    rows = [generations_service.generation_to_dict(item) for item in page.items]
    for row in rows:
        status_value = row["status"].value if hasattr(row["status"], "value") else str(row["status"])
        row["status_value"] = status_value
        row["status_label"] = _status_label(status_value)
        created_at = row.get("created_at")
        if isinstance(created_at, datetime):
            row["created_at_display"] = _format_history_timestamp(created_at)
        else:
            row["created_at_display"] = str(created_at)

    return templates.TemplateResponse(
        "generation_history.html",
        {
            "request": request,
            "title": "История генераций",
            "rows": rows,
            "user": user,
        },
    )


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "title": "Вход администратора",
            "error": None,
        },
    )


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(request: Request, token: str = Form(...)):
    if not is_admin_token_valid(token):
        return templates.TemplateResponse(
            "admin_login.html",
            {
                "request": request,
                "title": "Вход администратора",
                "error": "Неверный токен администратора",
            },
            status_code=401,
        )
    response = RedirectResponse(url="/admin/trends", status_code=303)
    response.set_cookie("admin_token", token, httponly=True)
    return response


@router.get("/admin/trends", response_class=HTMLResponse)
async def admin_trends_page(request: Request, session: AsyncSession = Depends(get_db)):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    trends, _ = await list_trends(
        session,
        active=None,
        trend_type=None,
        popular=None,
        tag=None,
        search=None,
        limit=200,
        offset=0,
    )
    return templates.TemplateResponse(
        "admin_trends.html",
        {
            "request": request,
            "title": "Админ: тренды",
            "trends": trends,
            "now": datetime.utcnow(),
        },
    )


@router.get("/admin/trends/new", response_class=HTMLResponse)
async def admin_new_trend_page(request: Request):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    return templates.TemplateResponse(
        "admin_trend_form.html",
        {
            "request": request,
            "title": "Создать тренд",
            "trend": None,
            "action": "/admin/trends/new",
            "error": None,
        },
    )


@router.post("/admin/trends/new", response_class=HTMLResponse)
async def admin_new_trend_submit(
    request: Request,
    session: AsyncSession = Depends(get_db),
    title: str = Form(...),
    type: str = Form(...),
    preview_url: str = Form(default=""),
    tags: str = Form(default=""),
    is_popular: bool = Form(default=False),
    is_active: bool = Form(default=False),
    price_tokens: int = Form(default=0),
    prompt_template: str = Form(default=""),
):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    payload = TrendCreate(
        title=title,
        type=type,
        preview_url=preview_url or None,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        is_popular=is_popular,
        is_active=is_active,
        price_tokens=price_tokens,
        prompt_template=prompt_template or None,
    )

    await create_trend(session, payload)
    return RedirectResponse(url="/admin/trends", status_code=303)


@router.get("/admin/trends/{trend_id}/edit", response_class=HTMLResponse)
async def admin_edit_trend_page(request: Request, trend_id: int, session: AsyncSession = Depends(get_db)):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    trend = await get_trend(session, trend_id)
    return templates.TemplateResponse(
        "admin_trend_form.html",
        {
            "request": request,
            "title": f"Редактирование тренда #{trend.id}",
            "trend": trend,
            "action": f"/admin/trends/{trend.id}/edit",
            "error": None,
        },
    )


@router.post("/admin/trends/{trend_id}/edit", response_class=HTMLResponse)
async def admin_edit_trend_submit(
    request: Request,
    trend_id: int,
    session: AsyncSession = Depends(get_db),
    title: str = Form(...),
    type: str = Form(...),
    preview_url: str = Form(default=""),
    tags: str = Form(default=""),
    is_popular: bool = Form(default=False),
    is_active: bool = Form(default=False),
    price_tokens: int = Form(default=0),
    prompt_template: str = Form(default=""),
):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    trend = await get_trend(session, trend_id)
    payload = TrendPatch(
        title=title,
        type=type,
        preview_url=preview_url or None,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        is_popular=is_popular,
        is_active=is_active,
        price_tokens=price_tokens,
        prompt_template=prompt_template or None,
    )
    await update_trend(session, trend, payload)
    return RedirectResponse(url="/admin/trends", status_code=303)


@router.post("/admin/trends/{trend_id}/toggle", response_class=HTMLResponse)
async def admin_toggle_trend(
    request: Request,
    trend_id: int,
    session: AsyncSession = Depends(get_db),
    field: str = Form(...),
):
    if not _admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    trend = await get_trend(session, trend_id)
    if field == "is_active":
        payload = TrendPatch(is_active=not trend.is_active)
    elif field == "is_popular":
        payload = TrendPatch(is_popular=not trend.is_popular)
    else:
        raise bad_request("Unsupported toggle field")

    await update_trend(session, trend, payload)
    return RedirectResponse(url="/admin/trends", status_code=303)
