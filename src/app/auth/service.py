import hashlib
from datetime import datetime, timezone
from typing import Tuple, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.users.service import UserService
from src.app.models.user import User
from src.app.users.schemas import UserCreate
from src.app.auth.schemas import LoginRequest

from src.app.core.exceptions import (
    ExpiredTokenException,
    InvalidCredentialsException,
    ConflictException,
    NotFoundException,
    InvalidTokenException,
)
from src.app.email.service import EmailService
from src.app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    create_reset_token,
    verify_reset_token,
    verify_token
)
from src.app.core.logging import get_logger

logger = get_logger(__name__)

class AuthService:
    def __init__(
        self, 
        db: AsyncSession,
        user_service: UserService,
        email_service: EmailService,
    ):
        self.db = db
        self.user_service = user_service
        self.email_service = email_service

    def _create_password_signature(self, password_hash: str) -> str:
        """
        Create a signature from the password hash.
        This signature is used to validate that the password hasn't changed since token creation.
        
        Args:
            password_hash: The hashed password
            
        Returns:
            16-character signature string
        """
        return hashlib.sha256(password_hash.encode()).hexdigest()[:16]
    
    async def get_user_by_email(
        self, 
        email: str
    ) -> Optional[User]:
        """Retrieve a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)

        user = result.scalar_one_or_none()
        return user
    
    async def get_user_by_id(
        self, 
        user_id: uuid.UUID
    ) -> Optional[User]:
        """Retrieve a user by their ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)

        user = result.scalar_one_or_none()
        return user
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)

        if existing_user and existing_user.email == user_data.email:
            raise ConflictException("Email already registered")
      
        # Hash password & create user
        password = get_password_hash(user_data.password)
        db_user = User(
            name=user_data.name,
            email=user_data.email,
            password_hash=password,
            user_type=user_data.user_type,
            is_verified=False
        )
            
        self.db.add(db_user)
        await self.db.flush()  # get ID
        await self.db.refresh(db_user)
            
        # Send welcome email (non-blocking)
        try:
            await self.email_service.send_welcome_email(
                user_id=db_user.id,
                to_email=db_user.email,
                name=db_user.name
            )
        except Exception:
            pass
            
        return db_user

    async def authenticate_user(self, login_data: LoginRequest) -> User:
        """Authenticate a user."""
        user = await self.user_service.get_user_by_email(email=login_data.email)
        
        if not user.password_hash:
            raise InvalidCredentialsException()
        
        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        return user

    def create_tokens_for_user(self, user: User) -> Tuple[str, str]:
        """Create access and refresh tokens for a user."""
        access_token = create_access_token(data={"sub": user.email})
        refresh_token = create_refresh_token(data={"sub": user.email})
        return access_token, refresh_token
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Refresh the access token using the refresh token."""
        
        if not refresh_token or refresh_token.strip() == "":
            raise InvalidTokenException("Refresh token missing")
    
        email = verify_token(refresh_token, token_type="refresh")
        if not email:
            raise InvalidTokenException()
        
        user = await self.get_user_by_email(email)
        if not user:
            raise InvalidTokenException()
        
        access_token = create_access_token(data={"sub": user.email})
        return access_token
    
    async def forgot_password(self, email: str) -> bool:
        """
        Initiate the password reset process by sending an email with reset token.
        
        Note:
            Always returns True for security (doesn't reveal if email exists)
        """
        user = None 
        try:
            # Get user by email
            user = await self.get_user_by_email(email)
            if not user:
                # Don't reveal if email exists or not
                return True

            # Generate JWT reset token
            reset_token = create_reset_token(data={
                "user_id": str(user.id), 
                "pwd_sig": self._create_password_signature(user.password_hash)
            })

            # Send reset email
            await self.email_service.send_password_reset_email(
                user_id=user.id,
                to_email=user.email,
                reset_token=reset_token, # Send raw token via email
                name=user.name
            )
        except Exception as e:
            # For security, still return True - don't reveal errors
            pass
        
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset a user's password using a valid reset token.
        Validates the token and checks the password signature to ensure
        the password hasn't been changed since the token was issued.
        """
        
        # Verify token and extract payload
        token_data = verify_reset_token(token)
        
        if token_data == None:
            raise ExpiredTokenException()

        user_id = token_data['user_id']
        token_pwd_sig = token_data['pwd_sig']

        #  Get user from database
        user = await self.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        # Check password signature matches
        # This is the critical security check that prevents token reuse
        if self._create_password_signature(user.password_hash) != token_pwd_sig:
            raise InvalidTokenException(
                "This reset link has already been used or is no longer valid. "
                "Please request a new password reset."
            )
        
        # Update password - Hash the new password
        new_password_hash = get_password_hash(new_password)
        
        # Update user's password
        user.password_hash = new_password_hash
        
        logger.info(f"Password reset successful for user {user_id}")
        return True