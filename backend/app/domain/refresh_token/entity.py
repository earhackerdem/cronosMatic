from dataclasses import dataclass
from datetime import datetime


@dataclass
class RefreshToken:
    user_id: int
    token_jti: str
    expires_at: datetime
    id: int | None = None
    revoked_at: datetime | None = None
    created_at: datetime | None = None
