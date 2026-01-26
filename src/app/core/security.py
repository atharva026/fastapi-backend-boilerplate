from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt as PyJWT
from passlib.context import CryptContext
from src.app.core.config import config

INVALID_TOKEN="Invalid token payload"

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = PyJWT.encode(
        to_encode, 
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM
    )
    
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = PyJWT.encode(to_encode, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    try:
        payload = PyJWT.decode(
            token, 
            config.JWT_SECRET_KEY, 
            algorithms=[config.JWT_ALGORITHM]
        )
        
        email: str = payload.get("sub")
        token_type_payload: str = payload.get("type")
        
        if email is None or token_type_payload != token_type:
            raise PyJWT.InvalidTokenError(INVALID_TOKEN)
        return email
    except (PyJWT.ExpiredSignatureError, PyJWT.InvalidTokenError):
        return None
    
def create_reset_token(data: dict) -> str:
    """
    Create a JWT reset token that includes user_id and password signature.
    
    The password signature ensures the token becomes invalid once password
    is changed, providing one-time use security without database storage.
        
    Returns:
        JWT token string
        
    Token Payload Structure:
        {
            'user_id': 123,
            'pwd_sig': 'a3f2c1b4e5d6f7a8',  # First 16 chars of password_hash
            'exp': 1234567890,  # Expiration timestamp
            'iat': 1234567800,  # Issued at timestamp
            'purpose': 'password_reset'
        }
    """
    to_encode = data.copy()
    # Build JWT payload
    payload = {
        'exp': datetime.now(timezone.utc) + timedelta(
            minutes=config.JWT_RESET_TOKEN_EXPIRE_MINUTES
        ),
        'iat': datetime.now(timezone.utc),
        'purpose': 'password_reset'
    }

    to_encode.update(payload)
    
    # Encode and return JWT token
    token = PyJWT.encode(
        to_encode,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM
    )
    
    return token
    
def verify_reset_token(token: str) -> dict | None:
    """
    Verify the reset token and return the payload if valid.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary containing:
            - user_id: User's ID
            - pwd_sig: Password signature from when token was created
        
    Raises:
        InvalidTokenException: If token is invalid, expired, or wrong purpose
        
    Example:
        payload = verify_reset_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
        # Returns: {'user_id': 123, 'pwd_sig': 'a3f2c1b4e5d6f7a8'}
    """
    try:
        # Decode JWT token
        payload = PyJWT.decode(
            token, 
            config.JWT_SECRET_KEY, 
            algorithms=[config.JWT_ALGORITHM]
        )
        
        # Verify this is a password reset token
        if payload.get('purpose') != 'password_reset':
            raise PyJWT.InvalidTokenError(INVALID_TOKEN)
        
         # Verify required fields are present
        if 'user_id' not in payload or 'pwd_sig' not in payload:
            raise PyJWT.InvalidTokenError(INVALID_TOKEN)
        
        # Extract and return relevant data
        return {
            'user_id': payload['user_id'],
            'pwd_sig': payload['pwd_sig']
        }
        
    except (PyJWT.ExpiredSignatureError, PyJWT.InvalidTokenError):
        return None