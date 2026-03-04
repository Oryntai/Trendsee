from __future__ import annotations

from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_sessionmaker
from app.models.trend import Trend
from app.models.user import User
from app.models.enums import TrendType


LEGACY_TITLE_MAP = {
    "Street Style Reel": "Городской стиль: рилс",
    "Product Studio Photo": "Студийное фото товара",
    "Travel Montage": "Путешествие: монтаж",
}

LEGACY_PROMPT_MAP = {
    "Create a high energy vertical script with 3 scenes.": "Создай динамичный вертикальный сценарий из 3 сцен.",
    "Write a premium product photo concept with lighting setup.": "Опиши премиальную концепцию продуктового фото со схемой света.",
    "Generate a cinematic travel montage plan with transitions.": "Сгенерируй кинематографичный план тревел-монтажа с переходами.",
}

SYNC_FIELDS = ("type", "preview_url", "tags", "is_popular", "is_active", "price_tokens", "prompt_template")

DEMO_TRENDS: list[dict[str, object]] = [
    {
        "title": "Городской стиль: рилс",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/street-style-reel/900/1200",
        "tags": ["fashion", "lifestyle", "reel"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 40,
        "prompt_template": "Создай динамичный вертикальный сценарий из 3 сцен.",
    },
    {
        "title": "Студийное фото товара",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/studio-product-photo/900/1200",
        "tags": ["ecommerce", "product", "studio"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 25,
        "prompt_template": "Опиши премиальную концепцию продуктового фото со схемой света.",
    },
    {
        "title": "Путешествие: монтаж",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/travel-montage/900/1200",
        "tags": ["travel", "lifestyle", "montage"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 55,
        "prompt_template": "Сгенерируй кинематографичный план тревел-монтажа с переходами.",
    },
    {
        "title": "Открытка: День рождения",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/birthday-card/900/1200",
        "tags": ["greetings", "card", "lifestyle"],
        "is_popular": True,
        "is_active": True,
        "price_tokens": 22,
        "prompt_template": "Собери персонализированную открытку ко дню рождения с именем и праздничной подписью.",
    },
    {
        "title": "Поздравление для мамы",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/mom-greeting-video/900/1200",
        "tags": ["greetings", "family", "lifestyle"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 34,
        "prompt_template": "Сгенерируй короткий семейный клип с текстом благодарности для мамы.",
    },
    {
        "title": "Открытка для подруги",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/friend-card/900/1200",
        "tags": ["greetings", "card", "flowers", "fashion"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 24,
        "prompt_template": "Создай нежную открытку для подруги: цветы, мягкий стиль и короткая подпись.",
    },
    {
        "title": "Романтическое поздравление",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/romantic-greeting/900/1200",
        "tags": ["greetings", "romance", "lifestyle"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 38,
        "prompt_template": "Подготовь короткий love-reel для пары с тёплой романтической атмосферой.",
    },
    {
        "title": "Оживить фото",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/animate-photo/900/1200",
        "tags": ["animation", "portrait"],
        "is_popular": True,
        "is_active": True,
        "price_tokens": 45,
        "prompt_template": "Опиши, как оживить портрет: лицо начинает двигаться и мягко улыбаться.",
    },
    {
        "title": "Фото говорит текст",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/talking-photo/900/1200",
        "tags": ["animation", "portrait", "greetings"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 47,
        "prompt_template": "Сделай сценарий, где персонаж на фото «произносит» поздравительный текст.",
    },
    {
        "title": "Старое фото в движение",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/vintage-photo-motion/900/1200",
        "tags": ["animation", "vintage", "new"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 49,
        "prompt_template": "Сгенерируй план оживления винтажного снимка с бережным сохранением атмосферы эпохи.",
    },
    {
        "title": "Story поздравление",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/story-greeting/900/1200",
        "tags": ["social", "story"],
        "is_popular": True,
        "is_active": True,
        "price_tokens": 41,
        "prompt_template": "Создай вертикальную сторис с текстом поздравления и музыкальными акцентами.",
    },
    {
        "title": "Reels поздравление",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/reels-greeting/900/1200",
        "tags": ["social", "reel", "fashion"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 43,
        "prompt_template": "Собери динамичный монтаж для Reels/TikTok с быстрыми сменами сцен и CTA в конце.",
    },
    {
        "title": "Видео-приглашение",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/video-invitation/900/1200",
        "tags": ["social", "invite", "new"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 36,
        "prompt_template": "Подготовь короткое видео-приглашение на событие с понятной структурой и финальным призывом.",
    },
    {
        "title": "Фото с цветами",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/photo-with-flowers/900/1200",
        "tags": ["photo_content", "flowers", "portrait", "lifestyle"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 27,
        "prompt_template": "Опиши портретную фотосцену: человек, букет, мягкий свет и акцент на цветовой гармонии.",
    },
    {
        "title": "Весенний портрет",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/spring-portrait/900/1200",
        "tags": ["photo_content", "portrait", "spring", "fashion", "new"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 29,
        "prompt_template": "Создай весенний портрет в пастельной палитре с мягким рассеянным светом.",
    },
    {
        "title": "Портрет в студии",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/studio-portrait/900/1200",
        "tags": ["photo_content", "portrait", "studio", "ecommerce"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 31,
        "prompt_template": "Подготовь студийный портрет с чистым фоном и аккуратной схемой освещения.",
    },
    {
        "title": "Семейная открытка",
        "type": TrendType.photo,
        "preview_url": "https://picsum.photos/seed/family-card/900/1200",
        "tags": ["family", "greetings", "card", "lifestyle"],
        "is_popular": True,
        "is_active": True,
        "price_tokens": 26,
        "prompt_template": "Сгенерируй семейную открытку с праздничной подписью и тёплой атмосферой.",
    },
    {
        "title": "Видео-поздравление от семьи",
        "type": TrendType.video,
        "preview_url": "https://picsum.photos/seed/family-greeting-video/900/1200",
        "tags": ["family", "greetings"],
        "is_popular": False,
        "is_active": True,
        "price_tokens": 39,
        "prompt_template": "Собери короткий семейный клип-поздравление из нескольких сцен.",
    },
]


def _normalize_tags(raw_tags: list[str] | None) -> list[str]:
    if not raw_tags:
        return []
    return list(dict.fromkeys(tag.strip().lower() for tag in raw_tags if tag.strip()))


async def seed_demo_data() -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        existing_admin = await session.scalar(select(User).where(User.api_key == settings.default_admin_api_key))
        if existing_admin is None:
            session.add(
                User(
                    api_key=settings.default_admin_api_key,
                    is_admin=True,
                    token_balance=settings.initial_token_balance,
                )
            )

        existing_user = await session.scalar(select(User).where(User.api_key == settings.default_user_api_key))
        if existing_user is None:
            session.add(
                User(
                    api_key=settings.default_user_api_key,
                    is_admin=False,
                    token_balance=settings.initial_token_balance,
                )
            )

        existing_trends = (await session.scalars(select(Trend))).all()
        trends_by_title: dict[str, Trend] = {}

        for trend in existing_trends:
            trend.title = LEGACY_TITLE_MAP.get(trend.title, trend.title)
            if trend.prompt_template in LEGACY_PROMPT_MAP:
                trend.prompt_template = LEGACY_PROMPT_MAP[trend.prompt_template]
            trend.tags = _normalize_tags(trend.tags)

            title_key = trend.title.strip().lower()
            if title_key and title_key not in trends_by_title:
                trends_by_title[title_key] = trend

        for payload in DEMO_TRENDS:
            title = str(payload["title"]).strip()
            title_key = title.lower()
            trend = trends_by_title.get(title_key)

            normalized_tags = _normalize_tags(payload.get("tags"))  # type: ignore[arg-type]
            payload["tags"] = normalized_tags

            if trend is None:
                session.add(Trend(**payload))  # type: ignore[arg-type]
                continue

            trend.title = title
            for field_name in SYNC_FIELDS:
                setattr(trend, field_name, payload[field_name])

        await session.commit()
