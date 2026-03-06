from dataclasses import dataclass
from datetime import datetime


@dataclass
class Category:
    name: str
    slug: str
    description: str | None = None
    image_path: str | None = None
    is_active: bool = True
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
