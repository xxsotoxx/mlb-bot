"""
MLB Betting Bot - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.models.database import init_db
from app.routes import games, predictions, stats
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

app.include_router(games.router)
app.include_router(predictions.router)
app.include_router(stats.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup_event():
    """Inicializa la base de datos y scheduler al arrancar"""
    logger.info("Inicializando base de datos...")
    init_db()
    
    # Migrar datos históricos a game_results table
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
