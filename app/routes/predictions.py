"""
Rutas para predicciones y resultados
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import logging

from ..models.database import (
    get_db,
    get_all_predictions,
    get_predictions_with_results,
    update_prediction_result,
    get_prediction_by_game,
    get_dashboard_stats,
    UserDB
)
from ..schemas.schemas import PredictionRecord, ResultInput, DashboardStats, APIResponse
from ..auth.deps import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/predictions/history", response_model=APIResponse)
async def get_predictions_history(
    db: Session = Depends(get_db),
    limit: int = 50,
    current_user: UserDB = Depends(get_current_user)
):
    """
    Obtiene el historial de predicciones
    """
    try:
        predictions = get_all_predictions(db, limit=limit)
        
        predictions_list = []
        for p in predictions:
            predictions_list.append({
                "id": p.id,
                "game_id": p.game_id,
                "game_date": p.game_date.isoformat() if p.game_date else None,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "predicted_home_score": p.predicted_home_score,
                "predicted_away_score": p.predicted_away_score,
                "predicted_total": p.predicted_total,
                "predicted_favorite": p.predicted_favorite,
                "home_win_probability": p.home_win_probability,
                "over_probability": p.over_probability,
                "over_line": p.over_line,
                "actual_home_score": p.actual_home_score,
                "actual_away_score": p.actual_away_score,
                "result_registered": p.result_registered,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })
        
        return APIResponse(
            success=True,
            message=f"Se encontraron {len(predictions_list)} predicciones",
            data={
                "predictions": predictions_list,
                "count": len(predictions_list)
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener historial",
            error=str(e)
        )


@router.get("/api/predictions/{game_id}", response_model=APIResponse)
async def get_prediction(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Obtiene una predicción específica por game_id
    """
    try:
        prediction = get_prediction_by_game(db, game_id)
        
        if not prediction:
            return APIResponse(
                success=False,
                message=f"No se encontró predicción para game_id {game_id}",
                error="Predicción no encontrada"
            )
        
        return APIResponse(
            success=True,
            message="Predicción encontrada",
            data={
                "id": prediction.id,
                "game_id": prediction.game_id,
                "game_date": prediction.game_date.isoformat() if prediction.game_date else None,
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "predicted_home_score": prediction.predicted_home_score,
                "predicted_away_score": prediction.predicted_away_score,
                "predicted_total": prediction.predicted_total,
                "predicted_favorite": prediction.predicted_favorite,
                "home_win_probability": prediction.home_win_probability,
                "over_probability": prediction.over_probability,
                "over_line": prediction.over_line,
                "actual_home_score": prediction.actual_home_score,
                "actual_away_score": prediction.actual_away_score,
                "result_registered": prediction.result_registered
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo predicción {game_id}: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener predicción",
            error=str(e)
        )


@router.post("/api/predictions/{game_id}/result", response_model=APIResponse)
async def register_result(
    game_id: int,
    result: ResultInput,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Registra el resultado real de un partido
    """
    try:
        success = update_prediction_result(db, game_id, result.home_score, result.away_score)
        
        if not success:
            return APIResponse(
                success=False,
                message=f"No se encontró predicción para game_id {game_id}",
                error="Primero debes consultar los partidos para generar la predicción"
            )
        
        return APIResponse(
            success=True,
            message=f"Resultado registrado: Home {result.home_score} - Away {result.away_score}",
            data={
                "game_id": game_id,
                "home_score": result.home_score,
                "away_score": result.away_score
            }
        )
        
    except Exception as e:
        logger.error(f"Error registrando resultado {game_id}: {e}")
        return APIResponse(
            success=False,
            message="Error al registrar resultado",
            error=str(e)
        )


@router.get("/api/dashboard", response_model=APIResponse)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    """
    Obtiene estadísticas del dashboard
    """
    try:
        stats = get_dashboard_stats(db)
        
        predictions_with_results = get_predictions_with_results(db)
        
        money_line_results = []
        over_under_results = []
        
        for p in predictions_with_results:
            home_won = p.actual_home_score > p.actual_away_score
            predicted_home_wins = p.predicted_favorite == p.home_team
            
            money_line_results.append({
                "game_date": p.game_date.isoformat() if p.game_date else None,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "prediction": p.predicted_favorite,
                "actual_winner": p.home_team if home_won else p.away_team,
                "correct": home_won == predicted_home_wins,
                "home_score": p.actual_home_score,
                "away_score": p.actual_away_score
            })
            
            actual_total = p.actual_home_score + p.actual_away_score
            predicted_over = p.over_probability > 0.5
            
            over_under_results.append({
                "game_date": p.game_date.isoformat() if p.game_date else None,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "over_line": p.over_line,
                "actual_total": actual_total,
                "predicted_over": predicted_over,
                "actual_over": actual_total > p.over_line,
                "correct": (actual_total > p.over_line) == predicted_over,
                "home_score": p.actual_home_score,
                "away_score": p.actual_away_score
            })
        
        return APIResponse(
            success=True,
            message="Dashboard actualizado",
            data={
                **stats,
                "money_line_details": money_line_results,
                "over_under_details": over_under_results
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo dashboard: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener dashboard",
            error=str(e)
        )
