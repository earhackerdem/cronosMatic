from fastapi import APIRouter

from app.api.routers import health
from app.api.routers.addresses import router as addresses_router
from app.api.routers.auth import auth_status_router, router as auth_router
from app.api.routers.cart import router as cart_router
from app.api.routers.categories import admin_router as categories_admin_router
from app.api.routers.categories import router as categories_router
from app.api.routers.images import admin_router as images_admin_router
from app.api.routers.orders import router as orders_router
from app.api.routers.payments import router as payments_router
from app.api.routers.products import admin_router as products_admin_router
from app.api.routers.products import router as products_router
from app.api.routers.users import router as users_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(categories_router)
api_router.include_router(categories_admin_router)
api_router.include_router(products_router)
api_router.include_router(products_admin_router)
api_router.include_router(images_admin_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(auth_status_router)
api_router.include_router(cart_router)
api_router.include_router(addresses_router)
api_router.include_router(orders_router)
api_router.include_router(payments_router)
