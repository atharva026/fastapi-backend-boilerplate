from datetime import datetime, timezone
from typing import Tuple
from fastapi import BackgroundTasks

from src.app.core.token_store import TokenStore
from src.app.users.service import UserService
from src.app.models.user import User, UserType
from src.app.users.schemas import UserCreate
from src.app.auth.schemas import LoginRequest

from src.app.core.exceptions import (
    ExpiredTokenException,
    InvalidCredentialsException,
    ConflictException,
    InvalidTokenException,
)
from src.app.email.service import EmailService
from src.app.core.security import (
    verify_password, 
    get_password_hash, 
    create_token,
    create_password_signature,
    create_reset_token,
    verify_reset_token,
    verify_token,
    exp_to_datetime,
    create_verification_token,
    verify_verification_token
)
from src.app.core.logging import get_logger

logger = get_logger(__name__)

class AuthService:
    def __init__(
        self, 
        user_service: UserService,
        email_service: EmailService,
        token_store: TokenStore,
    ):
        self.user_service = user_service
        self.email_service = email_service
        self.token_store = token_store
    
    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_user = await self.user_service.get_user_by_email_or_none(user_data.email)

        if existing_user and existing_user.email == user_data.email:
            raise ConflictException("Email already registered")
      
        # Hash password & create user
        password_hash = get_password_hash(user_data.password)

        db_user = await self.user_service.create_user(
            name=user_data.name,
            email=user_data.email,
            password_hash=password_hash,  # Store hashed password
            user_type=UserType.USER,      # Default to regular user
            is_verified=False
        )
            
        return db_user

    async def authenticate_user(self, login_data: LoginRequest) -> User:
        """Authenticate a user."""
        user = await self.user_service.get_user_by_email_or_none(email=login_data.email)

        # Validate user existence and password
        if not user:
            raise InvalidCredentialsException()
        
        if not user.password_hash:
            raise InvalidCredentialsException()
        
        if not verify_password(login_data.password, user.password_hash):
            raise InvalidCredentialsException()
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        return user

    async def create_tokens_for_user(self, user: User) -> Tuple[str, str]:
        """Create access and refresh tokens for a user."""
        access_token = create_token(data={"sub": str(user.id)}, token_type= "access")
        refresh_token, refresh_payload = create_token(data={"sub": str(user.id)}, token_type= "refresh", return_payload=True)

        # Store refresh token in Redis allowlist
        await self.token_store.store_refresh_token(
            user_id=str(user.id),
            jti=refresh_payload["jti"],
            expires_at=refresh_payload["exp"],
        )
        
        return access_token, refresh_token
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Refresh the access token using the refresh token."""
        
        if not refresh_token or refresh_token.strip() == "":
            raise InvalidTokenException("Refresh token missing")
    
        payload = verify_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        jti = payload.get("jti")

        if not user_id or not jti:
            raise InvalidTokenException("Invalid token payload")

        # Check if refresh token is still valid (not revoked)
        if not await self.token_store.is_refresh_token_valid(user_id=user_id, jti=jti):
            raise InvalidTokenException("Refresh token has been revoked")
            
        user = await self.user_service.get_user_by_id_or_raise(user_id)
        
        access_token = create_token(data={"sub": str(user.id)}, token_type="access")
        return access_token

    def queue_verification_email(
        self,
        user_id: str,
        email: str,
        name: str,
        background_tasks: BackgroundTasks,
    ) -> None:
        """ 
        Generate a verification token and dispatch the email. 
        Called right after registration (or on manual resend). 
        Does NOT raise — email failures are logged silently so registration still succeeds. 
        """
        token = create_verification_token(user_id=user_id, email=email)

        background_tasks.add_task(
            self.email_service.send_verification_email,
            user_id=user_id,
            to_email=email,
            verification_token=token,
            name=name,
        )

    async def verify_email(self, token: str) -> User | str:
        """
        Verify a user's email address from a signed token.

        Edge cases handled:
        - Expired token   → ExpiredTokenException
        - Tampered token  → InvalidTokenException
        - Wrong email     → InvalidTokenException  (email changed after token was issued)
        - Already verified → returns True immediately (idempotent, safe to re-click)
        - User not found  → NotFoundException

        Returns:
        - User object if verification successful
        - "already_verified" if already verified (idempotent)
        """
        token_data = verify_verification_token(token)

        user_id = token_data["sub"]
        token_email = token_data["email"]

        user = await self.user_service.get_user_by_id_or_raise(user_id)

        # Guard: email in token must match current DB email.
        # Prevents a stolen old token from verifying a new email address.
        if user.email != token_email:
            raise InvalidTokenException(
                "This verification link is no longer valid. Please request a new verification email."
            )

        # Idempotent — already verified, nothing to do
        if user.is_verified:
            return "already_verified"
        
        updated = await self.user_service.mark_verified_if_not_already(user_id)

        if not updated:
            return "already_verified"

        user.is_verified = True
        logger.info(f"Email verified for user {user_id}")
        return user

    async def resend_verification_email(self, email: str, background_tasks: BackgroundTasks) -> bool:
        """
        Re-send verification email. Always returns True (no email-enumeration leak).
        
        Abuse prevention:
        - Silently no-ops if user is already verified.
        """
        try:
            user = await self.user_service.get_user_by_email_or_none(email)
            if not user or user.is_verified:
                return True   # Don't reveal whether the address exists or is verified

            self.queue_verification_email(
                user_id=str(user.id), 
                email=user.email, 
                name=user.name, 
                background_tasks=background_tasks
            )
        except Exception as e:
            logger.error(f"resend_verification_email error: {e}")

        return True
    
    async def forgot_password(self, email: str, background_tasks: BackgroundTasks) -> bool:
        """
        Initiate the password reset process by sending an email with reset token.
        Always returns True for security (doesn't reveal if email exists)
        """
        try:
            # Get user by email
            user = await self.user_service.get_user_by_email_or_none(email)
            if not user:
                # Don't reveal if email exists or not
                return True

            token = create_reset_token(
                user_id= str(user.id), 
                pwd_sig= create_password_signature(user.password_hash)
            )

            # Send reset email - background task to avoid blocking responses 
            background_tasks.add_task(
                self.email_service.send_password_reset_email,
                user_id=user.id,
                to_email=user.email,
                reset_token=token,
                name=user.name
            )
        except Exception:
            # For security, still return True - don't reveal errors
            pass
        
        return True
    
    async def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset a user's password using a signed itsdangerous token.
        Validates the token and checks the password signature to ensure
        the password hasn't been changed since the token was issued.
        """
        
        # Verify token and extract payload. verify_reset_token will raise
        # ExpiredTokenException or InvalidTokenException on error.
        token_data = verify_reset_token(token)

        user_id = token_data["sub"]
        token_pwd_sig = token_data["pwd_sig"]

        #  Get user from database
        user = await self.user_service.get_user_by_id_or_raise(user_id)

        # Check password signature matches
        # This is the critical security check that prevents token reuse
        if create_password_signature(user.password_hash) != token_pwd_sig:
            raise InvalidTokenException(
                "This reset link has already been used or is no longer valid. "
                "Please request a new password reset."
            )
        
        # Update user's password with new hashed password
        user.password_hash = get_password_hash(new_password)
        
        logger.info(f"Password reset successful for user {user_id}")
        return True
    
    async def logout_user(self, access_token: str, refresh_token:str):
        """Logout the user by blocklisting the access token and removing the refresh token from allowlist."""
        
        # Blocklist the access token for its remaining TTL
        if access_token:
            try:
                payload = verify_token(access_token, token_type="access")
                await self.token_store.blocklist_access_token(
                    jti=payload["jti"],
                    expires_at=exp_to_datetime(payload),
                )
            except (InvalidTokenException, ExpiredTokenException) as e:
                # Token invalid/expired - still proceed with logout. Log and continue.
                logger.info(f"Access token verification failed during logout: {str(e)}")

        # Remove refresh token from allowlist
        if refresh_token:
            try:
                payload = verify_token(refresh_token, token_type="refresh")
                await self.token_store.revoke_refresh_token(
                    user_id=payload["sub"],
                    jti=payload["jti"],
                )
            except (InvalidTokenException, ExpiredTokenException) as e:
                # Token invalid/expired - still proceed with logout. Log and continue.
                logger.info(f"Refresh token verification failed during logout: {str(e)}")
