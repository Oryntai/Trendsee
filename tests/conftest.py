import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_trendsee.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["MODEL_PROVIDER"] = "mock"
os.environ["DEFAULT_USER_API_KEY"] = "test-user-key"
os.environ["DEFAULT_ADMIN_API_KEY"] = "test-admin-key"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["INITIAL_TOKEN_BALANCE"] = "1000"
os.environ["UPLOAD_DIR"] = "uploads"

from app.db.base import Base
from app.db.init_db import seed_demo_data
from app.db.session import engine
from app.main import app


@pytest_asyncio.fixture(autouse=True)
async def reset_db():
    uploads_dir = Path(os.environ["UPLOAD_DIR"])
    uploads_dir.mkdir(parents=True, exist_ok=True)

    for path in uploads_dir.iterdir():
        if path.name != ".gitkeep" and path.is_file():
            path.unlink()

    assert engine is not None
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_demo_data()

    yield

    for path in uploads_dir.iterdir():
        if path.name != ".gitkeep" and path.is_file():
            path.unlink()

    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def user_headers():
    return {"X-API-Key": os.environ["DEFAULT_USER_API_KEY"]}


@pytest.fixture
def admin_headers():
    return {"X-API-Key": os.environ["DEFAULT_ADMIN_API_KEY"]}
