"""
Auth Middleware - Protege todas las rutas /api/* excepto /api/auth/*
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from app.auth.security import verify_token
from app.models.database import get_db, get_user_by_username

logger = logging.getLogger(__name__)

PUBLIC_PATHS = [
    "/",
    "/login",
    "/setup",
    "/dashboard",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health",
    "/api/auth/login",
    "/api/auth/setup"
]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para verificar autenticación en rutas protegidas"""
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        for public_path in PUBLIC_PATHS:
            if path.startswith(public_path):
                return await call_next(request)
        
        if not path.startswith("/api/"):
            return await call_next(request)
        
        if path.startswith("/api/auth/"):
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = auth_header.replace("Bearer ", "")
        payload = verify_token(token)
        
        if not payload:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        username = payload.get("sub")
        
        try:
            db_gen = get_db()
            db = next(db_gen)
            user = get_user_by_username(db, username)
            db.close()
            
            if not user or not user.is_active:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            request.state.user = user
            
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication error"
            )
        
        return await call_next(request)