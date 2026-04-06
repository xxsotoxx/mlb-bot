"""
MLB Betting Bot - FastAPI Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.models.database import init_db
from app.routes import games, predictions, stats
from app.auth.router import router as auth_router
from app.auth.middleware import AuthMiddleware
from app.routes.ml import router as ml_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="MLB Betting Bot",
    description="Bot de predicciones de apuestas MLB usando sabermetría avanzada",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Cookie middleware for session management
from starlette.middleware.cookies import CookieMiddleware
app.add_middleware(CookieMiddleware)

# Add Cookie middleware for session management
from starlette.middleware.cookies import CookieMiddleware
app.add_middleware(CookieMiddleware)

app.add_middleware(AuthMiddleware)

app.include_router(auth_router)
app.include_router(ml_router)
app.include_router(games.router)
app.include_router(predictions.router)
app.include_router(stats.router)

# Route /login directly (without /api/auth prefix)
@app.get("/login", response_class=HTMLResponse)
async def login_page_root(next_url: str = None):
    """Página de login en ruta raíz /login"""
    from app.auth.router import login_page
    return await login_page(next_url)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard principal - autenticación verificada por middleware"""
    from app.models.database import get_db, get_user_by_username
    from app.auth.security import verify_token
    
    # Token is verified by middleware - just get user from state
    user = getattr(request.state, "user", None)
    
    if not user:
        # Fallback: try to get from header/cookie
        auth_header = request.headers.get("Authorization") or request.cookies.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            payload = verify_token(token)
            if payload:
                db_gen = get_db()
                db = next(db_gen)
                user = get_user_by_username(db, payload.get("sub"))
                db.close()
    
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@app.on_event("startup")
async def startup_event():
    """Inicializa la base de datos y scheduler al arrancar"""
    logger.info("Inicializando base de datos...")
    init_db()
    
    from app.services.migrate_results import migrate_historical_results
    try:
        migrate_historical_results()
    except Exception as e:
        logger.warning(f"Migración de resultados históricos: {e}")
    
    logger.info("Iniciando scheduler de jobs automáticos...")
    start_scheduler()
    
    logger.info("MLB Betting Bot iniciado correctamente")


@app.on_event("shutdown")
async def shutdown_event():
    """Detiene el scheduler al apagar"""
    logger.info("Deteniendo scheduler...")
    stop_scheduler()
    logger.info("MLB Betting Bot apagado correctamente")


@app.get("/api/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {"status": "healthy", "service": "mlb-bot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)