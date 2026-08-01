from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import uuid
import jwt as PyJWT
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from src.app.core.config import config
from src.app.core.exceptions import ExpiredTokenException, InvalidTokenException

_serializer = URLSafeTimedSerializer(
    secret_key=config.TOKEN_SERIALIZER_SECRET_KEY,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)

def create_password_signature(password_hash: str) -> str:
    """
    Create a signature from the password hash.
    This signature is used to validate that the password hasn't changed since token creation.
        
    Args:
        password_hash: The hashed password
        
    Returns:
        16-character signature string
    """
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def create_token(
    data: dict,
    token_type: str,
    expires_delta: Optional[timedelta] = None,
    return_payload: bool = False
) -> tuple[str, dict] | str:
    """
    Create a JWT token with the given data and token type (access or refresh).

    Args:
        data: Dictionary of data to include in the token payload (e.g. {"sub": user_id})
        token_type: "access" or "refresh" to determine expiration time
        expires_delta: Optional timedelta to override default expiration time
        return_payload: If True, return a tuple of (token string, payload dictionary) instead of just the token string

    Returns:
        Tuple of (token string, payload dictionary) or token string depending on return_payload flag
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
 
    if expires_delta:
        expire = now + expires_delta
    else:
        if token_type == "access":
            expire = now + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == "refresh":
            expire = now + timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            raise ValueError("Invalid token type")
  
    payload = {
        **to_encode,
        "iat": now,
        "exp": expire,
        "type": token_type,
        "jti": jti,
    }

    token = PyJWT.encode(
        payload,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )

    if return_payload:
        return token, payload
    
    return token

def verify_token(token: str, token_type: str = "access"): # -> Optional[str]:
    """
    Verify a JWT token and return the payload if valid.

    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh") to validate against the payload

    Returns:
        Payload dictionary if token is valid and matches the expected type, or None if invalid/expired
    """
    try:
        payload = PyJWT.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM]
        )

        sub: str = payload.get("sub")
        token_type_payload: str = payload.get("type")

        if sub is None or token_type_payload != token_type:
            # payload missing required fields or type mismatch
            raise InvalidTokenException("Invalid token payload")

        return payload
    except PyJWT.ExpiredSignatureError:
        # Token expired
        raise ExpiredTokenException("Token has expired")
    except PyJWT.InvalidTokenError:
        # Any other JWT decode issues
        raise InvalidTokenException("Invalid token")

def exp_to_datetime(payload: dict) -> datetime:
    """Convert the 'exp' claim from the token payload to a datetime object."""
    return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
   
def create_reset_token(user_id: str, pwd_sig: str) -> str:
    """
    Create a signed, time-limited password-reset token.

    pwd_sig (first 16 chars of bcrypt hash) ensures the token is
    one-time-use: once the password changes the signature no longer matches.

    Args:
        user_id: User ID for which the token is being created (required)
        pwd_sig: Password signature (required)
    """
    return _serializer.dumps(
        {"sub": user_id, "pwd_sig": pwd_sig},
        salt=config.PASSWORD_RESET_SALT
    )

def verify_reset_token(token: str) -> dict:
    """
    Validate a password-reset token.

    Returns:
        {"sub": "<user_id>", "pwd_sig": "<signature>"} on success.

    Raises:
        ExpiredTokenException: If the token has expired.
        InvalidTokenException: If the token is invalid or tampered.
    """
    try:
        data = _serializer.loads(
            token,
            max_age=(60 * config.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            salt=config.PASSWORD_RESET_SALT
        )

        if "sub" not in data or "pwd_sig" not in data:
            raise InvalidTokenException("Invalid reset token payload")

        return {
            "sub": data["sub"],
            "pwd_sig": data["pwd_sig"]
        }

    except SignatureExpired:
        # Token expired
        raise ExpiredTokenException("Reset token has expired")
    except BadSignature:
        # Token tampered or otherwise invalid
        raise InvalidTokenException("Invalid reset token")

def create_verification_token(user_id: str, email: str) -> str:
    """
    Create a signed, time-limited email-verification token.
    Payload includes the email so the token is invalidated automatically
    if the user changes their email before clicking the link.
    """
    return _serializer.dumps(
        {"sub": user_id, "email": email},
        salt=config.EMAIL_VERIFICATION_SALT
    )

def verify_verification_token(token: str) -> dict | None:
    """
    Validate an email-verification token.
    Returns:
        {"sub": "<user_id>", "email": "<email>"} on success
    Raises:
        ExpiredTokenException: If the token has expired.
        InvalidTokenException: If the token is invalid or tampered.
    """
    try:
        data = _serializer.loads(
            token,
            max_age=60 * 60 * config.VERIFICATION_TOKEN_EXPIRE_HOURS,
            salt=config.EMAIL_VERIFICATION_SALT
        )

        if "sub" not in data or "email" not in data:
            return InvalidTokenException()

        return {
            "sub": data["sub"], 
            "email": data["email"]
        }

    except SignatureExpired:
        # Token expired
        raise ExpiredTokenException()
    except BadSignature:
        # Token tampered or otherwise invalid
        raise InvalidTokenException()