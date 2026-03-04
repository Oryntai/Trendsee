from app.core.config import settings
from app.services.providers.base import ModelProvider
from app.services.providers.mock import MockProvider
from app.services.providers.openrouter import OpenRouterProvider


def get_provider() -> ModelProvider:
    if settings.model_provider.lower() == "openrouter" and settings.openrouter_api_key:
        return OpenRouterProvider()
    return MockProvider()
