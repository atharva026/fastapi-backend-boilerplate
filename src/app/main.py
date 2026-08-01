from fastapi import FastAPI, HTTPException
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
from src.app.core.redis import (
    redis_on_startup,
    redis_on_shutdown,
    get_redis,
)
from src.app.core.rate_limiter import RedisRateLimiter

from fastapi.exceptions import RequestValidationError
from src.app.core.exceptions import AppException
from src.app.core.exception_handlers import (
    app_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
)
from src.app.middleware.rate_limit import RateLimitMiddleware
from src.app.middleware.auth import AuthenticationMiddleware
from src.app.core.token_store import TokenStore

# Configure logging
setup_logging()

logger = get_logger(__name__)

VERSION = "1.0.0"

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_on_startup()
    await redis_on_startup()

    redis = await get_redis()
    app.state.redis = redis
    app.state.rate_limiter = RedisRateLimiter(redis)
    app.state.token_store = TokenStore(redis)

    yield

    await redis_on_shutdown()
    await db_on_shutdown()
    
app = FastAPI(
    title="Fast Backend API Boilerplate",
    description="REST API documentation",
    version=VERSION,
    docs_url=None if config.ENVIRONMENT == "prod" else "/docs",
    redoc_url=None if config.ENVIRONMENT == "prod" else "/redoc",
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)

# FastAPI middleware reverse order execution: the last added middleware is executed first. 

# Rate limit middleware
app.add_middleware(
    RateLimitMiddleware,
)

# Authentication Middleware
app.add_middleware(
    AuthenticationMiddleware,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Include router from api.py
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=['Health Checks'])
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "FastAPI Backend Boilerplate",
        "version": VERSION,
        "docs": "/docs"
    }

@app.get("/health", tags=['Health Checks'])
async def health_check():
    logger.info("Health check performed")
    return {
        "status": "Ok" 
    }
