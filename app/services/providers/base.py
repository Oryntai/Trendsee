from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.models.asset import Asset
from app.models.trend import Trend


@dataclass
class GenerationOutput:
    result_text: str
    raw: dict
    model: str
    provider: str


class ModelProvider(Protocol):
    async def generate(
        self,
        *,
        trend: Trend,
        prompt: str,
        resources: list[dict],
        assets: list[Asset],
    ) -> GenerationOutput: ...
