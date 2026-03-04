from app.core.config import settings


def is_admin_token_valid(token: str | None) -> bool:
    return bool(token) and token == settings.admin_token
