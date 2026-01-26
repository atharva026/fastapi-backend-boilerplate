from fastapi import status

class AppException(Exception):
    """Base application exception"""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR  # default

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="NOT_FOUND")

class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, code="CONFLICT")

class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, code="UNAUTHORIZED")

class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, code="FORBIDDEN")

class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, code="VALIDATION_ERROR")

class UnexpectedException(AppException):
    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    def __init__(self, message: str = "Something went wrong"):
        super().__init__(message, code="INTERNAL_SERVER_ERROR")

        
# ----------------------------------------------------------------------

class AuthException(AppException):
    status_code: int = status.HTTP_401_UNAUTHORIZED # default

    def __init__(self, message: str, code="AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class NotAuthenticatedException(AuthException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, code="NOT_AUTHENTICATED")

class InvalidCredentialsException(AuthException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message, code="INVALID_CREDENTIALS")

class InvalidTokenException(AuthException):
    def __init__(self, message: str = "Invalid token"):
        super().__init__(message, code="INVALID_TOKEN")

class ExpiredTokenException(AuthException):
    def __init__(self, message: str ="Token has expired"):
        super().__init__(message, code="TOKEN_EXPIRED")
