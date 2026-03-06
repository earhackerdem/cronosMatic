from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.domain.user.entity import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", status_code=200, response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
