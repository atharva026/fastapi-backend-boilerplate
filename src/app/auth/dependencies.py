from functools import lru_cache
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.email.service import EmailService, get_email_service
from src.app.users.dependencies import get_user_service
from src.app.users.service import UserService
from src.app.auth.service import AuthService
from src.app.core.database import get_db

def get_auth_service(
    db: AsyncSession = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
    email_service: EmailService = Depends(get_email_service),
) -> AuthService:
    return AuthService(
        db=db,
        user_service=user_service,
        email_service=email_service,
    )