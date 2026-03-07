from dataclasses import dataclass
from datetime import datetime


@dataclass
class Address:
    type: str  # "shipping" | "billing"
    first_name: str
    last_name: str
    address_line_1: str
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool = False
    user_id: int | None = None
    company: str | None = None
    address_line_2: str | None = None
    phone: str | None = None
    id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
