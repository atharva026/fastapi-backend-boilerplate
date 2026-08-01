import uuid
from fastapi import APIRouter, Depends, Path, status

from src.app.users.schemas import UserResponse, UserUpdate
from src.app.models.user import User
from src.app.users.dependencies import get_verified_user, get_user_service
from src.app.users.service import UserService
from src.app.common.response.response_builder import ResponseBuilder
from src.app.common.response.examples import INSUFFICIENT_PERMISSIONS_EXAMPLE, EMAIL_NOT_VERIFIED_EXAMPLE
from src.app.common.response.response_groups import (
    UNAUTHORIZED_RESPONSES,
    USER_NOT_FOUND,
    INTERNAL_SERVER_ERROR,
)

router = APIRouter()

@router.get(
    "/{user_id}", 
    response_model = UserResponse,
    status_code = status.HTTP_200_OK,
    responses = {
        **USER_NOT_FOUND,
        **INTERNAL_SERVER_ERROR
    }
)
async def get_user(
    user_id: uuid.UUID = Path(..., description="User ID to retrieve"),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user by ID. This endpoint is public and does not require authentication.
    """
    return await user_service.get_user_by_id_or_raise(user_id)
    
@router.put(
    "/{user_id}", 
    response_model = UserResponse,
    status_code = status.HTTP_200_OK,
    responses = {
        **UNAUTHORIZED_RESPONSES,
        **ResponseBuilder.build(status.HTTP_403_FORBIDDEN, INSUFFICIENT_PERMISSIONS_EXAMPLE, EMAIL_NOT_VERIFIED_EXAMPLE),
        **USER_NOT_FOUND,
        **INTERNAL_SERVER_ERROR
    }
)
async def update_user(
    user_update: UserUpdate,
    user_id: uuid.UUID = Path(..., description="User ID to update"),
    current_user: User = Depends(get_verified_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user name - Users can only update their own profile.
    """
    return await user_service.update_user(
        user_id=user_id, 
        current_user=current_user, 
        user_update=user_update
    )
