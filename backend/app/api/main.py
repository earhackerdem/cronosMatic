from fastapi import APIRouter

from app.api.routers import categories, health

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(categories.router)

