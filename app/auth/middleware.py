"""
Auth Middleware - Protege TODAS las rutas excepto las públicas
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import urllib.parse

from app.auth.security import verify_token
from app.models.database import get_db, get_user_by_username

logger = logging.getLogger(__name__)

PUBLIC_PATHS = [
    "/",
    "/login",
    "/dashboard",
    "/api/auth/login",
    "/api/auth/set-cookie",
    "/api/auth/setup",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/me",
    "/api/health",
]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para verificar autenticación en TODAS las rutas"""
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # Public paths - allow without authentication
        for public_path in PUBLIC_PATHS:
            if path == public_path or path.startswith(public_path + "/"):
                return await call_next(request)
        
        # Check for valid authentication
        auth_valid = False
        auth_header = None
        
        # Check cookie first
        auth_cookie = request.cookies.get("Authorization")
        if auth_cookie:
            auth_header = auth_cookie
        else:
            # Check header
            auth_header = request.headers.get("Authorization")
        
        if auth_header:
            # Remove "Bearer " prefix if present
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
            else:
                token = auth_header
            
            # Verify token
            payload = verify_token(token)
            if payload:
                username = payload.get("sub")
                if username:
                    try:
                        db_gen = get_db()
                        db = next(db_gen)
                        user = get_user_by_username(db, username)
                        db.close()
                        
                        if user and user.is_active:
                            auth_valid = True
                            request.state.user = user
                    except Exception as e:
                        logger.error(f"Auth middleware error: {e}")
        
        # If not authenticated, redirect to login
        if not auth_valid:
            next_param = urllib.parse.quote(path, safe='')
            return RedirectResponse(url=f"/login?next={next_param}")
        
        # For API paths, ensure we have the Authorization header or valid cookie
        if path.startswith("/api/"):
            # Check if we have valid auth (from cookie or header)
            if not auth_header:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header missing",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            
            # If using header (not cookie), ensure Bearer format
            auth_cookie = request.cookies.get("Authorization")
            if not auth_cookie and not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization header format",
                    headers={"WWW-Authenticate": "Bearer"}
                )
        
        return await call_next(request)
