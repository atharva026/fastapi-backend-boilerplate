from fastapi import APIRouter
from src.app.auth.routes import router as auth_routes
from src.app.users.routes import router as users_routes

api_router = APIRouter()

# Include routers
api_router.include_router(auth_routes, prefix="/auth", tags=["Authentication"])
api_router.include_router(users_routes, prefix="/users", tags=["Users"])
