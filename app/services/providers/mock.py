from __future__ import annotations

import asyncio
import hashlib
import json

from app.core.config import settings
from app.models.asset import Asset
from app.models.trend import Trend
from app.services.providers.base import GenerationOutput


class MockProvider:
    provider_name = "mock"
    model_name = "mock-v1"

    tag_labels = {
        "fashion": "мода",
        "travel": "путешествия",
        "ecommerce": "электронная коммерция",
        "lifestyle": "лайфстайл",
        "reel": "рилс",
        "product": "товар",
        "studio": "студия",
        "montage": "монтаж",
    }

    async def generate(
        self,
        *,
        trend: Trend,
        prompt: str,
        resources: list[dict],
        assets: list[Asset],
    ) -> GenerationOutput:
        payload = {
            "trend_id": trend.id,
            "trend_title": trend.title,
            "prompt": prompt,
            "resources": resources,
            "asset_ids": [asset.id for asset in assets],
        }
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        delay = settings.mock_min_delay_sec
        if settings.mock_max_delay_sec > settings.mock_min_delay_sec:
            range_width = settings.mock_max_delay_sec - settings.mock_min_delay_sec
            delay += (int(fingerprint[:4], 16) / 0xFFFF) * range_width

        await asyncio.sleep(delay)

        tags_display = ", ".join(self.tag_labels.get(tag.lower(), tag) for tag in trend.tags) or "без тегов"

        result = (
            f"## Тренд: {trend.title}\n"
            f"Тип: {'видео' if trend.type.value == 'video' else 'фото'}\n"
            f"Отпечаток: `{fingerprint[:12]}`\n\n"
            f"### Концепт\n"
            f"{prompt.strip()}\n\n"
            f"### Рекомендации по исполнению\n"
            "1. Начните с главного визуального акцента в первые 2 секунды.\n"
            f"2. Сохраните стиль в рамках тегов тренда: {tags_display}.\n"
            "3. Завершите ролик четким CTA под формат короткого контента.\n"
        )

        return GenerationOutput(
            result_text=result,
            raw={"fingerprint": fingerprint, "resources_count": len(resources), "assets_count": len(assets)},
            model=self.model_name,
            provider=self.provider_name,
        )
