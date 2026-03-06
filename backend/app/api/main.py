from fastapi import APIRouter

from app.api.routers import categories, health
from app.api.routers.auth import auth_status_router, router as auth_router
from app.api.routers.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(categories.router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(auth_status_router)
