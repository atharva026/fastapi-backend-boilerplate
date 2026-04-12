from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.token_store import TokenStore, get_token_store
from src.app.users.service import UserService
from src.app.core.database import get_db
from src.app.models.user import User
from src.app.core.security import verify_token
from src.app.core.exceptions import (
    InvalidTokenException,
    NotAuthenticatedException
)

def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    return UserService(db)

async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service),
    token_store: TokenStore = Depends(get_token_store)
) -> User:
    """
    Get the current user from the request.

    Depends:
        request (Request): The HTTP request object.
        user_service (UserService): The user service.
        token_store (TokenStore): The token store for checking blocked tokens.

    Raises:
        NotAuthenticatedException: If the user is not authenticated.
        InvalidTokenException: If the user token is invalid.
        NotFoundException: If the user is not found.

    Returns:
        User: The current user if they are authenticated.
    """
    # Extract token from cookies
    token = request.cookies.get("access_token")
    if not token:
        raise NotAuthenticatedException
    
    # Verify token and extract user ID
    payload = verify_token(token, token_type= "access")
    user_id = payload['sub']
    if user_id is None:
        raise InvalidTokenException()
    
    # Check if token is blocked (e.g. user logged out or token revoked)
    if await token_store.is_access_token_blocked(payload["jti"]):
        raise InvalidTokenException()

    # Get user or raise if not found
    user = await user_service.get_user_by_id_or_raise(user_id)
    return user