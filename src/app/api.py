import re

from fastapi import APIRouter, status

from src.app.core.config import config
from src.app.auth.routes import router as auth_routes
from src.app.users.routes import router as users_routes

from src.app.common.response.response_builder import ResponseBuilder
from src.app.common.response.examples import TOO_MANY_REQUESTS_EXAMPLE

EMAIL_ENDPOINTS = frozenset({
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/resend-verification"),
})

AUTH_ENDPOINTS = frozenset({
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/reset-password"),
    ("GET",  "/api/v1/auth/verify-email"),
    ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/resend-verification"),
})

# Public endpoints that do not require authentication
PUBLIC_ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/"),
    ("GET", "/health"),

    # Auth endpoints
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/signup"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/reset-password"),
    ("GET", "/api/v1/auth/verify-email"),
    ("POST", "/api/v1/auth/logout"),

    # Email 
    ("POST", "/api/v1/auth/forgot-password"),
    ("POST", "/api/v1/auth/resend-verification"),

    # Public data endpoints

    # Documentation endpoints - only in non-prod environments
    *([] if config.ENVIRONMENT == "prod" else [
        ("GET", "/docs"),
        ("GET", "/redoc"),
        ("GET", "/openapi.json"),
    ]),
]

# Public endpoints that match regex patterns (for dynamic paths)
PUBLIC_ENDPOINT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GET", re.compile(r"^/api/v1/users/[^/]+$")), # /api/v1/users/{user_id} GET is public (for profile viewing), but other methods on this path are private
]

def is_public_endpoint(method: str, path: str) -> bool:
    """
    Check if the given method and path correspond to a public endpoint.
    Args:
        method (str): The HTTP method (e.g., "GET", "POST").
        path (str): The request path.
    Returns:
        bool: True if the endpoint is public, False otherwise.
    """
    if (method, path) in PUBLIC_ENDPOINTS:
        return True

    return any(
        method == m and pattern.match(path)
        for m, pattern in PUBLIC_ENDPOINT_PATTERNS
    )

def is_auth_endpoint(method: str, path: str) -> bool:
    """
    Check if the given method and path correspond to a public auth endpoint.
    Args:
        method (str): The HTTP method (e.g., "GET", "POST").
        path (str): The request path.
        
    Returns:
        bool: True if the endpoint is a public auth endpoint, False otherwise.
    """
    return (method, path) in AUTH_ENDPOINTS

def is_email_endpoint(method: str, path: str) -> bool:
    """
    Check if the given method and path correspond to a email endpoint.
    Args:
        method (str): The HTTP method (e.g., "GET", "POST").
        path (str): The request path.
    Returns:
        bool: True if the endpoint is email related, False otherwise.
    """
    return (method, path) in EMAIL_ENDPOINTS

# ----------------------------------------------------------------------

api_router = APIRouter(
    # Set Too Many Requests response for all endpoints in this router by default.
    responses={
        **ResponseBuilder.build(status.HTTP_429_TOO_MANY_REQUESTS, TOO_MANY_REQUESTS_EXAMPLE),
    }
)

# Include routers
api_router.include_router(auth_routes, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_routes, prefix="/users", tags=["Users"])
