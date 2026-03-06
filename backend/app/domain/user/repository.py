from typing import Protocol

from app.domain.user.entity import User


class UserRepositoryInterface(Protocol):
    async def create(self, entity: User) -> User: ...

    async def get_by_id(self, user_id: int) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...
