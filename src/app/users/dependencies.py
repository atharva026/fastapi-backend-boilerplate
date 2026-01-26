from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.app.users.service import UserService
from src.app.core.database import get_db
from src.app.models.user import User
from src.app.core.security import verify_token
from src.app.core.exceptions import (
    InvalidCredentialsException,
    NotAuthenticatedException
)

def get_user_service(
    db: Session = Depends(get_db),
) -> UserService:
    return UserService(db)

async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service)
) -> User:
    """
    Get the current user from the request.

    Depends:
        request (Request): The HTTP request object.
        user_service (UserService): The user service.

    Raises:
        NotAuthenticatedException: If the user is not authenticated.
        InvalidCredentialsException: If the user token is valid.
        NotFoundException: If the user is not found.

    Returns:
        User: The current user if they are authenticated.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticatedException
    
    email = verify_token(token)
    if email is None:
        raise InvalidCredentialsException()
    
    user = await user_service.get_user_by_email(email)
    return user