from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.app.core.exceptions import AppException
from src.app.core.logging import get_logger

logger = get_logger(__name__)

# AppException handler
def app_exception_handler(
    request: Request, 
    exc: AppException
):
    logger.error(
        f"AppException: {exc.status_code} | {exc.code} | {exc.message} - Path: {request.url}",
        exc_info=exc,  # exc_info includes traceback
    )

    return JSONResponse(
        status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )

# Request validation exception handler
def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
):
    logger.info("Request validation error", exc_info=exc) # exc_info includes traceback

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "error": {
                "code": "REQUEST_VALIDATION_ERROR",
                "message": exc.errors(),
            },
        },
    )

# HTTPException handler (for exceptions raised with HTTPException)
def http_exception_handler(
    request: Request, 
    exc: HTTPException
):
    logger.error("HTTPException:", exc_info=exc) # exc_info includes traceback

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
            },
        },
    )

# Unhandled exception handler
def unhandled_exception_handler(
    request: Request, 
    exc: Exception
):
    logger.error("Unhandled exception:", exc_info=exc) # exc_info includes traceback

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Something went wrong",
            },
        },
    )
