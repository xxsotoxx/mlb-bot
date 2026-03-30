"""
Rutas para análisis y estadísticas de predicciones
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, timedelta
import logging

from ..services.stats_service import stats_service
from ..services.scheduler import get_scheduler_status, run_now
from ..services.results_fetcher import results_fetcher
from ..services.accuracy_calculator import accuracy_calculator
from ..models.database import get_db, get_accuracy_stats, get_game_results, save_game_result
from ..schemas.schemas import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """Página de análisis diario"""
    return templates.TemplateResponse("stats.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Página del dashboard de precisión"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/dashboard/stats", response_model=APIResponse)
async def get_dashboard_stats(days: int = 60):
    """
    Obtiene estadísticas del dashboard de precisión
    - ML Accuracy
    - O/U Accuracy
    - Run Line Accuracy
    - Error promedio de score
    """
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        stats = get_accuracy_stats(db, days)
        
        recent_results = get_game_results(db, days)
        
        recent_games = []
        for r in recent_results[:15]:
            recent_games.append({
                "game_date": r.game_date.isoformat() if r.game_date else None,
                "home_team": r.home_team,
                "away_team": r.away_team,
                "predicted_score": f"{int(r.predicted_home_score)}-{int(r.predicted_away_score)}",
                "actual_score": f"{r.actual_home_score}-{r.actual_away_score}",
                "predicted_total": r.predicted_total,
                "actual_total": r.actual_total,
                "ml_correct": r.ml_correct,
                "ou_correct": r.ou_correct,
                "rl_correct": r.rl_correct,
                "score_error": r.score_error,
                "total_error": r.total_error,
                "ml_prediction": r.ml_prediction,
                "ml_actual": r.ml_actual,
                "ou_prediction": r.ou_prediction,
                "ou_actual": r.ou_actual,
                "over_line": r.over_line
            })
        
        db.close()
        
        return APIResponse(
            success=True,
            message=f"Estadísticas de {days} días",
            data={
                "stats": stats,
                "recent_games": recent_games,
                "days_requested": days
            }
        )
        
    except Exception as e:
        logger.error(f"Error en dashboard stats: {e}")
        import traceback
        traceback.print_exc()
        return APIResponse(
            success=False,
            message="Error al obtener estadísticas",
            error=str(e)
        )


@router.get("/api/dashboard/trigger-fetch", response_model=APIResponse)
async def trigger_results_fetch():
    """
    Endpoint para ejecutar manualmente la obtención de resultados
    Útil para testing o para forzar una actualización
    """
    try:
        await run_now()
        
        return APIResponse(
            success=True,
            message="Job de resultados ejecutado manualmente"
        )
        
    except Exception as e:
        logger.error(f"Error ejecutando job manualmente: {e}")
        return APIResponse(
            success=False,
            message="Error al ejecutar job",
            error=str(e)
        )


@router.get("/api/dashboard/scheduler-status", response_model=APIResponse)
async def get_scheduler_status_endpoint():
    """Obtiene el estado del scheduler"""
    try:
        status = get_scheduler_status()
        
        return APIResponse(
            success=True,
            message="Estado del scheduler",
            data=status
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estado del scheduler: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener estado",
            error=str(e)
        )


@router.get("/api/analysis/today", response_model=APIResponse)
async def get_today_analysis():
    """
    Obtiene el análisis completo del día:
    1. Resultados de ayer
    2. Comparación con predicciones
    3. Estadísticas acumuladas
    """
    try:
        analysis = await stats_service.get_full_analysis()
        
        return APIResponse(
            success=True,
            message="Análisis completado",
            data=analysis
        )
        
    except Exception as e:
        logger.error(f"Error en análisis: {e}")
        import traceback
        traceback.print_exc()
        return APIResponse(
            success=False,
            message="Error al generar análisis",
            error=str(e)
        )


@router.get("/api/analysis/yesterday-results", response_model=APIResponse)
async def get_yesterday_results():
    """Obtiene los resultados reales de ayer"""
    try:
        results = await stats_service.get_yesterday_results()
        
        return APIResponse(
            success=True,
            message=f"{len(results)} partidos encontrados",
            data={
                "date": (date.today() - timedelta(days=1)).isoformat(),
                "games": results
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo resultados de ayer: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener resultados",
            error=str(e)
        )


@router.get("/api/analysis/all-time", response_model=APIResponse)
async def get_all_time_stats():
    """Obtiene estadísticas acumuladas de todas las predicciones"""
    try:
        stats = await stats_service.get_all_time_stats()
        
        return APIResponse(
            success=True,
            message="Estadísticas acumuladas",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error en estadísticas acumuladas: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener estadísticas",
            error=str(e)
        )


@router.get("/api/analysis/team/{team_name}", response_model=APIResponse)
async def get_team_analysis(team_name: str):
    """Obtiene análisis detallado de un equipo específico"""
    try:
        all_stats = await stats_service.get_all_time_stats()
        team_tracking = all_stats.get("team_tracking", {})
        
        team_data = None
        for name, data in team_tracking.items():
            if team_name.lower() in name.lower():
                team_data = {
                    "name": name,
                    **data
                }
                break
        
        if not team_data:
            return APIResponse(
                success=False,
                message=f"No se encontró información para {team_name}",
                error="Equipo no encontrado"
            )
        
        return APIResponse(
            success=True,
            message=f"Análisis de {team_data['name']}",
            data=team_data
        )
        
    except Exception as e:
        logger.error(f"Error en análisis de equipo: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener análisis de equipo",
            error=str(e)
        )
