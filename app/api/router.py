from fastapi import APIRouter

from app.api.routes import assets, generations, me, trends

api_router = APIRouter(prefix="/api")
api_router.include_router(trends.router)
api_router.include_router(assets.router)
api_router.include_router(generations.router)
api_router.include_router(me.router)
