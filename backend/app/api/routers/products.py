import math
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import require_admin
from app.db.engine import get_db_session
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    PaginatedProductsResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product import (
    ProductCategoryNotFoundError,
    ProductConflictError,
    ProductService,
)


# ─── Shared DI ───────────────────────────────────────────────────────────────


async def get_product_service(
    session=Depends(get_db_session),
) -> ProductService:
    product_repository = ProductRepository(session)
    category_repository = CategoryRepository(session)
    return ProductService(product_repository, category_repository)


# ─── Public Router ───────────────────────────────────────────────────────────

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedProductsResponse)
async def list_products(
    service: Annotated[ProductService, Depends(get_product_service)],
    category: str | None = None,
    search: str | None = None,
    sort_by: str = "name",
    sort_direction: str = "asc",
    page: int = 1,
    size: int = 12,
):
    try:
        items, total = await service.list_active(
            page=page,
            size=size,
            category_slug=category,
            search=search,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    except ProductCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedProductsResponse(
        items=items, total=total, page=page, pages=pages, size=size
    )


@router.get("/{slug}", response_model=ProductResponse)
async def get_product_by_slug(
    slug: str,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    product = await service.get_active_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


# ─── Admin Router ─────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/admin/products",
    tags=["admin", "products"],
    dependencies=[Depends(require_admin)],
)


@admin_router.get("", response_model=PaginatedProductsResponse)
async def list_products_admin(
    service: Annotated[ProductService, Depends(get_product_service)],
    page: int = 1,
    size: int = 15,
):
    items, total = await service.list_all_admin(page=page, size=size)
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedProductsResponse(
        items=items, total=total, page=page, pages=pages, size=size
    )


@admin_router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    data = body.model_dump(exclude_none=False)
    try:
        product = await service.create_product(data)
    except ProductCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProductConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return product


@admin_router.get("/{product_id}", response_model=ProductResponse)
async def get_product_admin(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    product = await service.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@admin_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    body: ProductUpdate,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    data = body.model_dump(exclude_unset=True)
    try:
        product = await service.update_product(product_id, data)
    except ProductCategoryNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProductConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@admin_router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    deleted = await service.delete_product(product_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found.")
    return Response(status_code=204)
