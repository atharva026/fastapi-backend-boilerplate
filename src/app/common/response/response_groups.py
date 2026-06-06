from fastapi import status
from src.app.common.response import examples
from src.app.common.response.response_builder import ResponseBuilder

# 401 response group
UNAUTHORIZED_RESPONSES = ResponseBuilder.build(
    status.HTTP_401_UNAUTHORIZED,
    examples.NOT_AUTHENTICATED_EXAMPLE,
    examples.INVALID_TOKEN_EXAMPLE,
    examples.EXPIRED_TOKEN_EXAMPLE
)

INVALID_OR_EXPIRED_TOKEN_RESPONSE = ResponseBuilder.build(
    status.HTTP_401_UNAUTHORIZED,
    examples.INVALID_TOKEN_EXAMPLE,
    examples.EXPIRED_TOKEN_EXAMPLE
)

# 403 response group
FORBIDDEN_RESPONSES = ResponseBuilder.build(
    status.HTTP_403_FORBIDDEN,
    examples.INSUFFICIENT_PERMISSIONS_EXAMPLE
)

# 404 
USER_NOT_FOUND = ResponseBuilder.build(
    status.HTTP_404_NOT_FOUND,
    examples.USER_NOT_FOUND_EXAMPLE
)

# 409
USER_ALREADY_EXISTS = ResponseBuilder.build(
    status.HTTP_409_CONFLICT,
    examples.USER_ALREADY_EXISTS_EXAMPLE
)

# 500
INTERNAL_SERVER_ERROR = ResponseBuilder.build(
    status.HTTP_500_INTERNAL_SERVER_ERROR,
    examples.INTERNAL_SERVER_ERROR_EXAMPLE
)