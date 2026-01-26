from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.openapi_tags import openapi_tags
from src.app.api import api_router

from src.app.core.logging import setup_logging, get_logger
from src.app.core.config import config

from contextlib import asynccontextmanager
from src.app.core.database import (
    on_startup as db_on_startup, 
    on_shutdown as db_on_shutdown
)

from fastapi.exceptions import RequestValidationError
from src.app.core.exceptions import AppException
from src.app.core.exception_handlers import (
    app_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

# Configure logging
setup_logging()

logger = get_logger(__name__)

VERSION = "1.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_on_startup()
    yield
    await db_on_shutdown()
    
app = FastAPI(
    title="Fast API Boilerplate",
    description="REST API documentation",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include router from api.py
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=['Health Checks'])
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "FastAPI ",
        "version": VERSION,
        "docs": "/docs"
    }

@app.get("/health", tags=['Health Checks'])
async def health_check():
    logger.info("Health check performed")
    return {
        "status": "Ok" 
    }

# TODO: Remove in production
CUSTOM_EXC_MSG = "This is a custom app exception"
@app.get("/test-app-exception", tags=['Health Checks'])
async def test_route1():
    raise AppException(CUSTOM_EXC_MSG)

@app.get("/test-request-validation-exception", tags=['Health Checks'])
async def test_route2():
    raise RequestValidationError(CUSTOM_EXC_MSG)

@app.get("/test-exception", tags=['Health Checks'])
async def test_route3():
    raise Exception(CUSTOM_EXC_MSG)
