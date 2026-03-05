import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Category:
    name: dict[str, str]  # e.g., {"en": "Pocket", "es": "Bolsillo"}
    slug: str
    description: dict[str, str] | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
