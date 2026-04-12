from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import uuid
import jwt as PyJWT
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from src.app.core.config import config

_reset_serializer = URLSafeTimedSerializer(
    secret_key=config.JWT_SECRET_KEY,
    salt="password-reset"
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
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT token with the given data and token type (access or refresh).

    Args:
        data: Dictionary of data to include in the token payload (e.g. {"sub": user_id})
        token_type: "access" or "refresh" to determine expiration time
        expires_delta: Optional timedelta to override default expiration time

    Returns:
            Encoded JWT token string
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
        
    to_encode.update({
        "iat": now,
        "exp": expire, 
        "type": token_type,
        "jti": jti
    })

    encoded_jwt = PyJWT.encode(
        to_encode, 
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM
    )
    
    return encoded_jwt

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
            raise PyJWT.InvalidTokenError("Invalid token payload")
        return payload
    except (PyJWT.ExpiredSignatureError, PyJWT.InvalidTokenError):
        return None

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
    return _reset_serializer.dumps(
        {
            "sub": user_id, 
            "pwd_sig": pwd_sig
        }
    )

def verify_reset_token(token: str) -> dict | None:
    """
    Validate a password-reset token.

    Returns:
        {"sub": "<user_id>", "pwd_sig": "<signature>"} on success
        None on expiry or tampering
    """
    try:
        data = _reset_serializer.loads(
            token,
            max_age=(60 * config.JWT_RESET_TOKEN_EXPIRE_MINUTES)
        )

        if "sub" not in data or "pwd_sig" not in data:
            return None

        return {
            "sub": data["sub"], 
            "pwd_sig": data["pwd_sig"]
        }

    except SignatureExpired:
        return None
    except BadSignature:
        return None
