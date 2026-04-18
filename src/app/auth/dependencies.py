from fastapi import Depends

from src.app.email.service import EmailService, get_email_service
from src.app.users.dependencies import get_user_service
from src.app.users.service import UserService
from src.app.auth.service import AuthService
from src.app.core.token_store import TokenStore, get_token_store


def get_auth_service(
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
    token_store: TokenStore = Depends(get_token_store),
) -> AuthService:
    return AuthService(
        user_service=user_service,
        email_service=email_service,
        token_store=token_store,
    )
