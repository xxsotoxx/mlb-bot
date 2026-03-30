"""
Rutas para análisis y estadísticas de predicciones
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, timedelta
import logging

from ..services.stats_service import stats_service
from ..schemas.schemas import APIResponse

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    """Página de análisis diario"""
    return templates.TemplateResponse("stats.html", {"request": request})


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
