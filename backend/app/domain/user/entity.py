from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    name: str
    email: str
    hashed_password: str
    id: int | None = None
    is_admin: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
