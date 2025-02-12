"""API package containing all route handlers."""

from fastapi import APIRouter
from . import auth, settings, users, chat_users, docs, matrix, health
from .commands import router as commands_router

# Create API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(commands_router)
api_router.include_router(chat_users.router, prefix="/chat-users", tags=["chat-users"])
api_router.include_router(docs.router, prefix="/docs", tags=["documentation"], include_in_schema=True)
api_router.include_router(matrix.router, prefix="/matrix", tags=["matrix"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
