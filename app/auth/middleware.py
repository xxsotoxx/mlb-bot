"""
Auth Middleware - Protege TODAS las rutas excepto las públicas
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import urllib.parse

from app.auth.security import verify_token
from app.models.database import get_db, get_user_by_username

logger = logging.getLogger(__name__)

PUBLIC_PATHS = [
    "/login",
    "/api/auth/login",
    "/setup",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/auth/login",
    "/api/auth/setup",
    "/api/auth/me",
    "/api/health",
]

REDIRECT_TO_LOGIN = [
    "/",
    "/dashboard",
    "/analysis",
]

LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Bot - Sesión Expirada</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 50%, #1565c0 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 450px;
            text-align: center;
        }
        h2 { color: #1a237e; margin-bottom: 20px; }
        p { color: #666; margin-bottom: 30px; }
        .btn {
            padding: 16px 32px;
            background: linear-gradient(135deg, #c62828 0%, #b71c1c 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }
        .btn:hover { transform: translateY(-2px); }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚾ Sesión Expirada</h2>
        <p>Tu sesión ha expirado. Por favor, inicia sesión nuevamente.</p>
        <a href="/login" class="btn">Ir a Login</a>
    </div>
</body>
</html>
"""


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para verificar autenticación en TODAS las rutas"""
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        for public_path in PUBLIC_PATHS:
            if path == public_path or path.startswith(public_path + "/"):
                return await call_next(request)
        
        if path in REDIRECT_TO_LOGIN:
            next_param = urllib.parse.quote(path, safe='')
            return RedirectResponse(url=f"/login?next={next_param}")
        
        if path.startswith("/api/"):
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