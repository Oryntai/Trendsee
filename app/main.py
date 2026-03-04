from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIDMiddleware, setup_logging
from app.db.init_db import seed_demo_data
from app.web.views import router as web_router

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await seed_demo_data()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
register_error_handlers(app)

app.include_router(api_router)
app.include_router(web_router)

app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
app.mount("/uploads", StaticFiles(directory=settings.resolved_upload_dir), name="uploads")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
