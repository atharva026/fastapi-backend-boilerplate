from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.users.service import UserService
from src.app.core.database import get_db
from src.app.models.user import User
from src.app.core.exceptions import (
    EmailNotVerifiedException,
    NotAuthenticatedException
)

def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)

async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service),
) -> User:
    """
    Get the current user from the request.

    Depends:
        request (Request): The HTTP request object.
        user_service (UserService): The user service.

    Raises:
        NotAuthenticatedException: If the user is not authenticated.
        NotFoundException: If the user is not found.

    Returns:
        User: The current user if they are authenticated.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise NotAuthenticatedException()
    
    # Get user or raise if not found
    return await user_service.get_user_by_id_or_raise(user_id)

async def get_verified_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user if their email is verified.
    Depends:
        current_user (User): The current user obtained from the request.
    Raises:
        EmailNotVerifiedException: If the user's email is not verified.
        Propagates:
            Exceptions raised by `get_current_user`.
    Returns:
        User: The current user if their email is verified.
    """
    if not current_user.is_verified:
        raise EmailNotVerifiedException()

    return current_user