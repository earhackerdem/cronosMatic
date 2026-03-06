from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.config import settings


class CategorySummary(BaseModel):
    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    category_id: int
    name: str
    slug: str | None = None
    sku: str
    description: str | None = None
    price: Decimal
    stock_quantity: int = 0
    brand: str | None = None
    movement_type: str | None = None
    image_path: str | None = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(ProductBase):
    """Create schema — slug is optional (auto-generated from name if not given)."""

    price: Decimal = Field(gt=0)
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Partial update — all fields optional."""

    category_id: int | None = None
    name: str | None = None
    slug: str | None = None
    sku: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    brand: str | None = None
    movement_type: str | None = None
    image_path: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(ProductBase):
    id: int
    slug: str  # always present in response
    created_at: datetime
    updated_at: datetime
    category: CategorySummary

    @computed_field  # type: ignore[prop-decorator]
    @property
    def image_url(self) -> str | None:
        if self.image_path is None:
            return None
        if self.image_path.startswith("http"):
            return self.image_path
        base = settings.storage_base_url.rstrip("/")
        return f"{base}/{self.image_path}" if base else self.image_path


class PaginatedProductsResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    pages: int
    size: int


class ImageUploadResponse(BaseModel):
    path: str
    url: str
