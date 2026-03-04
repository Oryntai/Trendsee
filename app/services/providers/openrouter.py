from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.models.asset import Asset
from app.models.trend import Trend
from app.services.providers.base import GenerationOutput


class OpenRouterProvider:
    provider_name = "openrouter"

    def __init__(self) -> None:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for OpenRouterProvider")
        self._api_key = settings.openrouter_api_key
        self._model = settings.openrouter_model

    def _build_prompt(self, trend: Trend, prompt: str, resources: list[dict], assets: list[Asset]) -> str:
        resources_lines = "\n".join(
            [f"- url: {item.get('url', '')} | note: {item.get('note', '')}" for item in resources]
        )
        asset_lines = "\n".join([f"- /uploads/{asset.storage_path}" for asset in assets])
        return (
            "Trend context:\n"
            f"title: {trend.title}\n"
            f"type: {trend.type.value}\n"
            f"tags: {', '.join(trend.tags)}\n"
            f"template: {trend.prompt_template or ''}\n\n"
            f"user_prompt:\n{prompt}\n\n"
            f"resources:\n{resources_lines or '- none'}\n\n"
            f"assets:\n{asset_lines or '- none'}"
        )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def _call_openrouter(self, payload: dict) -> dict:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def generate(
        self,
        *,
        trend: Trend,
        prompt: str,
        resources: list[dict],
        assets: list[Asset],
    ) -> GenerationOutput:
        user_prompt = self._build_prompt(trend, prompt, resources, assets)
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are Trendsee assistant. Return practical output in Markdown.",
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        data = await self._call_openrouter(payload)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenRouter response does not contain choices")

        result_text = choices[0].get("message", {}).get("content", "").strip()
        return GenerationOutput(
            result_text=result_text or "No content returned by model",
            raw=data,
            model=self._model,
            provider=self.provider_name,
        )
