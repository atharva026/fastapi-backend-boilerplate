from src.app.common.response.build_example import build_example

# 401 Unauthorized
INVALID_CREDENTIALS_EXAMPLE = {
    "InvalidCredentials": build_example(
        summary="Invalid credentials",
        code="INVALID_CREDENTIALS",
        message="Invalid credentials",
    )
}

INVALID_TOKEN_EXAMPLE = {
    "InvalidToken": build_example(
        summary="Invalid token",
        code="INVALID_TOKEN",
        message="Invalid token",
    )
}

EXPIRED_TOKEN_EXAMPLE = {
    "ExpiredToken": build_example(
        summary="Token has expired",
        code="TOKEN_EXPIRED",
        message="Token has expired",
    )
}

NOT_AUTHENTICATED_EXAMPLE = {
    "NotAuthenticated": build_example(
        summary="Not authenticated",
        code="NOT_AUTHENTICATED",
        message="Not authenticated",
    )
}

# 403 Forbidden 
INSUFFICIENT_PERMISSIONS_EXAMPLE = {
    "InsufficientPermissions": build_example(
        summary="Not enough permissions",
        code="INSUFFICIENT_PERMISSIONS",
        message="Not enough permissions",
    )
}

# 404 Not Found 
USER_NOT_FOUND_EXAMPLE = {
    "UserNotFound": build_example(
        summary="User not found",
        code="USER_NOT_FOUND",
        message="User not found",
    )
}

ADMIN_USER_NOT_FOUND_EXAMPLE = {
    "AdminUserNotFound": build_example(
        summary="Admin user not found or not an ADMIN",
        code="ADMIN_USER_NOT_FOUND",
        message="Admin user with specified ID not found or is not an ADMIN.",
    )
}

# 409
USER_ALREADY_EXISTS_EXAMPLE = {
    "UserAlreadyExists": build_example(
        summary="User already exists",
        code="USER_ALREADY_EXISTS",
        message="User with this email already exists.",
    )
}

# 500
INTERNAL_SERVER_ERROR_EXAMPLE = {
    "InternalServerError": build_example(
        summary="Internal server error",
        code="INTERNAL_SERVER_ERROR",
        message="Something went wrong",
    )
}
