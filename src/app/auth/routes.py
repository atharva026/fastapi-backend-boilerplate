from fastapi import APIRouter, Depends, Response, status, Request
from fastapi.responses import JSONResponse

from src.app.core.exceptions import InvalidTokenException, UnexpectedException
from src.app.core.config import config

from src.app.models.user import User
from src.app.users.schemas import UserCreate, UserResponse
from src.app.users.dependencies import get_current_user
from src.app.auth.dependencies import get_auth_service
from src.app.auth.schemas import (
    LoginRequest, 
    ForgotPasswordRequest,
    MessageResponse, 
    ResetPasswordRequest,
)
from src.app.auth.service import AuthService
from src.app.common.response.response_groups import( 
    UNAUTHORIZED_RESPONSES,
    USER_ALREADY_EXISTS,
    INTERNAL_SERVER_ERROR, 
    USER_NOT_FOUND,
)
from src.app.common.response.examples import (
    INVALID_CREDENTIALS_EXAMPLE, 
    INVALID_TOKEN_EXAMPLE
)
from src.app.common.response.response_builder import ResponseBuilder
from src.app.utils.get_cookie_options import get_cookie_options
from src.app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post(
    "/signup", 
    response_model = UserResponse,
    status_code = status.HTTP_201_CREATED,
    responses = {
        **USER_ALREADY_EXISTS,
        **INTERNAL_SERVER_ERROR
    }
)
async def signup(
    user_data: UserCreate, 
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    return await auth_service.create_user(user_data)

@router.post(
    "/login", 
    response_model = None,
    responses = {
        status.HTTP_200_OK : {
            "description": "User logged in successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Login successful"
                    }
                }
            }
        },
        **ResponseBuilder.build(status.HTTP_401_UNAUTHORIZED,INVALID_CREDENTIALS_EXAMPLE),
        **USER_NOT_FOUND,
        **INTERNAL_SERVER_ERROR
    }
)
async def login(
    login_data: LoginRequest, 
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and set tokens in cookies"""

    user = await auth_service.authenticate_user(login_data)

    access_token, refresh_token = auth_service.create_tokens_for_user(user)
    
    cookie_opts = get_cookie_options(request)

    response = JSONResponse(
        status_code= status.HTTP_200_OK,
        content= {"message": "Login successful"}
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        **cookie_opts,
        max_age=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        **cookie_opts,
        max_age=config.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 # in seconds
    )

    return response

@router.post(
    "/refresh",
    response_model = dict,
    responses = {
        status.HTTP_200_OK : {
            "description": "Access Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Access token refreshed"
                    }
                }
            }
        },
        **ResponseBuilder.build(status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN_EXAMPLE),
        **INTERNAL_SERVER_ERROR
    }
)
def refresh_token(
    request: Request, 
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token and set cookie"""
    # Extract refresh token from HttpOnly cookie
    refresh_token = request.cookies.get("refresh_token")

    # Validate & generate new access token
    access_token = auth_service.refresh_access_token(refresh_token)

    cookie_opts = get_cookie_options(request)

    response = JSONResponse(
        status_code= status.HTTP_200_OK,
        content= {"message": "Access token refreshed"}
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        **cookie_opts,
        max_age=config.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60 # in seconds
    )

    return response

@router.post(
    "/forgot-password",
    responses = {
        status.HTTP_200_OK : {
            "description": "Password reset link sent to email successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "If the email exists, a password reset link has been sent"
                    }
                }
            }
        },
        **INTERNAL_SERVER_ERROR
    }
)
async def forgot_password_route(
    request_data: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Send password reset email"""
    await auth_service.forgot_password(request_data.email)
        
    return MessageResponse(
        message="If the email exists in our system, a password reset link has been sent"
    )

@router.post(
    "/reset-password",
    responses = {
        status.HTTP_200_OK : {
            "description": "Password reset successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Password reset successfully"
                    }
                }
            }
        },
        **ResponseBuilder.build(status.HTTP_401_UNAUTHORIZED, INVALID_TOKEN_EXAMPLE),
        **INTERNAL_SERVER_ERROR
    }
)
async def reset_password(
    reset_data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password using reset token"""
    success = await auth_service.reset_password(reset_data.token, reset_data.new_password)
        
    if success:
        return MessageResponse(
            message="Password reseted successfully"
        )
    else:
        raise InvalidTokenException()

@router.get(
    "/me", 
    response_model = UserResponse,
    responses = {
        **UNAUTHORIZED_RESPONSES,
        **USER_NOT_FOUND,
        **INTERNAL_SERVER_ERROR
    }
)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post(
    "/logout",
    responses = {
        status.HTTP_200_OK : {
            "description": "User logged out successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User logged out successfully"
                    }
                }
            }
        },
        **INTERNAL_SERVER_ERROR
    }
)
def logout(
    request: Request, 
    response: Response, 
):
    """
    Logout user by clearing cookies (access_token + refresh_token).
    """
    try:
        cookie_opts = get_cookie_options(request)

        response = JSONResponse(
            status_code= status.HTTP_200_OK,
            content= {"message": "Logout successful"}
        )
        response.delete_cookie("access_token", **cookie_opts)
        response.delete_cookie("refresh_token", **cookie_opts)

        return response

    except Exception as e:
        logger.exception(f"(auth) Unexpected logout error: {str(e)}")
        raise UnexpectedException()
    