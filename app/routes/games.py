"""
Rutas para consulta de partidos y predicciones
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date, timezone
from typing import List, Optional, Dict
import logging

from ..models.database import get_db, save_prediction, get_prediction_by_game, save_line_history, detect_line_movement, UserDB
from ..schemas.schemas import GameWithPrediction, Prediction, GameInfo, APIResponse
from ..services.mlb_api import fetch_today_games, parse_game_info
from ..services.advanced_predictor import advanced_predictor
from ..services.casino_lines import casino_scraper, get_default_lines
from ..auth.deps import get_current_user


def _save_line_history(game_id: int, game_date: date, prediction: Dict, casino_line: Dict):
    """Guarda el histórico de líneas en la base de datos"""
    try:
        db_gen = get_db()
        db = next(db_gen)
        
        ml_data = casino_line.get("money_line", {})
        ou_data = casino_line.get("over_under", {})
        spread_data = casino_line.get("run_line", {})
        
        line_data = {
            "game_id": str(game_id),
            "game_date": game_date,
            "home_team": prediction.get("home_team", ""),
            "away_team": prediction.get("away_team", ""),
            "casino_source": casino_line.get("source", "The Odds API"),
            "casino_favorite": ml_data.get("favorite"),
            "casino_home_ml": ml_data.get("home"),
            "casino_away_ml": ml_data.get("away"),
            "casino_ou_line": ou_data.get("line"),
            "casino_over_odds": ou_data.get("over_odds"),
            "casino_under_odds": ou_data.get("under_odds"),
            "casino_spread_line": spread_data.get("line"),
            "casino_home_spread_odds": spread_data.get("home_odds"),
            "casino_away_spread_odds": spread_data.get("away_odds"),
            "consensus_favorite": casino_line.get("consensus_favorite"),
            "consensus_pct": casino_line.get("consensus_pct")
        }
        
        save_line_history(db, line_data)
        db.close()
        
        movement = detect_line_movement(db, str(game_id), threshold=0.5)
        if movement.get("has_movement"):
            logger.warning(f"LINE MOVEMENT DETECTED for game {game_id}: {movement}")
        
    except Exception as e:
        logger.warning(f"No se pudo guardar historial de líneas: {e}")


def calculate_casino_comparison(prediction: Dict, casino_line: Dict) -> Dict:
    """Calcula comparación completa entre predicción y línea del casino (ML, O/U, Run Line)"""
    if not casino_line or not casino_line.get("available"):
        return {"available": False}
    
    predicted_total = prediction.get("predicted_total", 8.0)
    predicted_favorite = prediction.get("predicted_favorite", "")
    
    comparison = {
        "available": True,
        "source": casino_line.get("source", casino_line.get("recommended_bookmaker", "Casino")),
        "recommended_bookmaker": casino_line.get("recommended_bookmaker"),
        "predicted_total": predicted_total,
    }
    
    ml_data = casino_line.get("money_line", {})
    if ml_data:
        casino_home_ml = ml_data.get("home")
        casino_away_ml = ml_data.get("away")
        casino_favorite_team = ml_data.get("favorite")
        
        if casino_favorite_team:
            comparison["money_line"] = {
                "favorite": casino_favorite_team,
                "favorite_margin": ml_data.get("favorite_margin", 0),
                "home_odds": casino_home_ml,
                "away_odds": casino_away_ml,
                "home_implied_prob": ml_data.get("home_implied", 50),
                "away_implied_prob": ml_data.get("away_implied", 50),
                "prediction_match": predicted_favorite == casino_favorite_team,
                "confidence": _get_ml_confidence(casino_home_ml, casino_away_ml)
            }
    
    ou_data = casino_line.get("over_under", {})
    if ou_data and ou_data.get("line"):
        casino_ou = ou_data.get("line")
        ou_diff = round(predicted_total - casino_ou, 1)
        
        comparison["over_under"] = {
            "casino_line": casino_ou,
            "over_odds": ou_data.get("over_odds"),
            "under_odds": ou_data.get("under_odds"),
            "difference": ou_diff,
            "prediction": _get_ou_prediction(predicted_total, casino_ou, ou_diff),
            "confidence": calculate_over_confidence(predicted_total, casino_ou, ou_diff),
            "value": _get_ou_value(ou_diff),
            "edge": f"+{ou_diff}" if ou_diff > 0 else str(ou_diff)
        }
    
    spread_data = casino_line.get("run_line", {})
    if spread_data and spread_data.get("line"):
        comparison["run_line"] = {
            "casino_line": spread_data.get("line"),
            "home_odds": spread_data.get("home_odds"),
            "away_odds": spread_data.get("away_odds"),
            "spread_favorite": ml_data.get("favorite") if ml_data else None,
            "recommended_spread": _recommend_spread(spread_data, ml_data, predicted_favorite)
        }
    
    comparison["all_bookmakers"] = casino_line.get("all_bookmakers", {})
    
    return comparison


def _get_ml_confidence(home_ml: int, away_ml: int) -> str:
    """Calcula nivel de confianza del Money Line"""
    if not home_ml or not away_ml:
        return "BAJA"
    diff = abs(home_ml - away_ml)
    if diff >= 200:
        return "MUY ALTA"
    elif diff >= 150:
        return "ALTA"
    elif diff >= 80:
        return "MEDIA"
    else:
        return "BAJA"


def _get_ou_prediction(predicted: float, casino: float, diff: float) -> str:
    """Determina recomendación de Over/Under"""
    if abs(diff) < 0.5:
        return "NEUTRAL"
    elif diff > 0:
        return "OVER"
    else:
        return "UNDER"


def _get_ou_value(diff: float) -> str:
    """Determina el valor de la apuesta"""
    if abs(diff) >= 1.5:
        return "MUY ALTO"
    elif abs(diff) >= 1.0:
        return "ALTO"
    elif abs(diff) >= 0.5:
        return "MEDIO"
    else:
        return "BAJO"


def _recommend_spread(spread_data: Dict, ml_data: Dict, predicted_favorite: str) -> Dict:
    """Genera recomendación de Run Line"""
    spread_line = spread_data.get("line", -1.5)
    favorite = ml_data.get("favorite") if ml_data else None
    
    return {
        "recommendation": f"{favorite} {spread_line}" if favorite else "N/A",
        "home_cover_prob": 50,
        "away_cover_prob": 50
    }


def calculate_over_confidence(predicted: float, casino_line: float, diff: float) -> float:
    """Calcula confianza de la recomendación OVER/UNDER"""
    import math
    
    std_dev = 2.0
    z_score = diff / std_dev
    confidence = 0.5 + 0.5 * math.erf(z_score / math.sqrt(2))
    confidence = max(50, min(95, confidence * 100))
    
    return round(confidence, 1)

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: UserDB = Depends(get_current_user)):
    """Página principal del bot"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: UserDB = Depends(get_current_user)):
    """Página del dashboard de estadísticas"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/games/today", response_model=APIResponse)
async def get_today_games(
    include_casino_lines: bool = True,
    current_user: UserDB = Depends(get_current_user)
):
    """
    Obtiene los partidos del día con predicciones avanzadas
    """
    try:
        games = await fetch_today_games()
        
        if not games:
            return APIResponse(
                success=True,
                message="No hay partidos programados para hoy",
                data={"games": [], "count": 0}
            )
        
        casino_lines = None
        if include_casino_lines:
            try:
                casino_lines = await casino_scraper.get_casino_lines()
                logger.info(f"Casino lines fetched: {bool(casino_lines)}")
            except Exception as e:
                logger.warning(f"No se pudieron obtener líneas de casinos: {e}")
        
        games_with_predictions = []
        
        for game in games:
            game_info = parse_game_info(game)
            
            try:
                prediction = await advanced_predictor.generate_prediction(game_info)
            except Exception as pred_error:
                logger.error(f"Error generando predicción para game {game_info.get('game_id')}: {pred_error}")
                prediction = {
                    "predicted_home_score": 4.0,
                    "predicted_away_score": 4.0,
                    "predicted_total": 8.0,
                    "predicted_favorite": game_info.get("home_team", "Home"),
                    "favorite_probability": 50.0,
                    "home_win_probability": 50.0,
                    "away_win_probability": 50.0,
                    "over_line": 8.0,
                    "over_probability": 50.0,
                    "under_probability": 50.0,
                    "over_under_prediction": "OVER",
                    "confidence_level": "low",
                    "confidence_spanish": "BAJA",
                    "confidence_percentage": 50.0,
                    "park_factor": 1.0,
                    "pitcher_home": game_info.get("home_probable_pitcher") or "TBD",
                    "pitcher_away": game_info.get("away_probable_pitcher") or "TBD",
                    "home_pitcher_stats": {},
                    "away_pitcher_stats": {},
                    "home_bullpen_stats": {},
                    "away_bullpen_stats": {},
                    "home_team_stats": {"wins": 0, "losses": 0, "runs_scored_avg": 4.25, "runs_allowed_avg": 4.25},
                    "away_team_stats": {"wins": 0, "losses": 0, "runs_scored_avg": 4.25, "runs_allowed_avg": 4.25},
                    "matchup_analysis": {},
                    "casino_line": {"ou_line": 8.0, "source": "Error", "estimated": True},
                    "casino_source": "Fallback"
                }
            
            if include_casino_lines and casino_lines:
                casino_line = casino_scraper.get_best_line(
                    prediction["home_team"],
                    prediction["away_team"],
                    casino_lines
                )
                
                if casino_line and casino_line.get("available") is not False:
                    prediction["casino_line"] = casino_line
                    prediction["casino_source"] = casino_line.get("source", "The Odds API")
                    prediction["casino_comparison"] = calculate_casino_comparison(prediction, casino_line)
                else:
                    prediction["casino_line"] = get_default_lines(prediction["predicted_total"])
                    prediction["casino_source"] = "Estimado"
                    prediction["casino_comparison"] = {"available": False, "reason": "Líneas no disponibles"}
                    casino_line = None
            else:
                prediction["casino_line"] = get_default_lines(prediction["predicted_total"])
                prediction["casino_source"] = "Estimado"
                prediction["casino_comparison"] = {"available": False, "reason": "No solicitadas"}
                casino_line = None
            
            game_data = {
                **game_info,
                **prediction
            }
            
            try:
                if game_info["game_date"]:
                    dt = datetime.fromisoformat(game_info["game_date"].replace("Z", "+00:00"))
                    game_date = dt.astimezone().date()
                else:
                    game_date = date.today()
            except:
                try:
                    game_date = datetime.strptime(game_info["game_date"], "%Y-%m-%dT%H:%M:%SZ").date() if game_info["game_date"] else date.today()
                except:
                    game_date = date.today()
            
            if casino_line:
                try:
                    _save_line_history(
                        game_info.get("game_id", 0),
                        game_date,
                        prediction,
                        casino_line
                    )
                except Exception as hist_err:
                    logger.warning(f"No se pudo guardar historial: {hist_err}")
            
            prediction_data = {
                "game_id": game_info["game_id"],
                "game_date": game_date,
                "home_team": game_info["home_team"],
                "away_team": game_info["away_team"],
                "predicted_home_score": prediction["predicted_home_score"],
                "predicted_away_score": prediction["predicted_away_score"],
                "predicted_total": prediction["predicted_total"],
                "predicted_favorite": prediction["predicted_favorite"],
                "home_win_probability": prediction["home_win_probability"] / 100 if prediction.get("home_win_probability", 50) > 1 else prediction.get("home_win_probability", 0.5),
                "over_probability": prediction["over_probability"] / 100 if prediction.get("over_probability", 50) > 1 else prediction.get("over_probability", 0.5),
                "over_line": prediction["over_line"],
                "pitcher_home": prediction.get("pitcher_home"),
                "pitcher_away": prediction.get("pitcher_away")
            }
            
            try:
                db_gen = get_db()
                db = next(db_gen)
                existing = get_prediction_by_game(db, game_info["game_id"])
                if not existing:
                    save_prediction(db, prediction_data)
            except Exception as db_err:
                logger.warning(f"No se pudo guardar predicción: {db_err}")
            
            games_with_predictions.append(game_data)
        
        return APIResponse(
            success=True,
            message=f"Se encontraron {len(games_with_predictions)} partidos",
            data={
                "games": games_with_predictions,
                "count": len(games_with_predictions),
                "date": date.today().isoformat(),
                "casino_lines_status": "loaded" if casino_lines else "unavailable"
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo partidos: {e}")
        import traceback
        traceback.print_exc()
        return APIResponse(
            success=False,
            message="Error al obtener partidos",
            error=str(e)
        )


@router.get("/api/games/{game_id}", response_model=APIResponse)
async def get_game_detail(
    game_id: int,
    current_user: UserDB = Depends(get_current_user)
):
    """
    Obtiene detalles de un partido específico con su predicción
    """
    try:
        games = await fetch_today_games()
        
        game = None
        for g in games:
            if g.get("gamePk") == game_id:
                game = g
                break
        
        if not game:
            return APIResponse(
                success=False,
                message=f"No se encontró el partido {game_id}",
                error="Partido no encontrado"
            )
        
        game_info = parse_game_info(game)
        prediction = await advanced_predictor.generate_prediction(game_info)
        
        try:
            casino_lines = await casino_scraper.get_casino_lines()
            casino_line = casino_scraper.get_line_for_game(
                prediction["home_team"],
                prediction["away_team"],
                casino_lines
            )
            
            if casino_line:
                prediction["casino_line"] = casino_line
                prediction["casino_source"] = casino_line.get("source", "Playdoit")
            else:
                prediction["casino_line"] = get_default_lines(prediction["predicted_total"])
                prediction["casino_source"] = "Estimado"
        except Exception as e:
            logger.warning(f"Error obteniendo líneas de casino: {e}")
            prediction["casino_line"] = get_default_lines(prediction["predicted_total"])
            prediction["casino_source"] = "Estimado"
        
        return APIResponse(
            success=True,
            message="Partido encontrado",
            data={
                **game_info,
                **prediction
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo detalle del partido {game_id}: {e}")
        return APIResponse(
            success=False,
            message="Error al obtener detalles",
            error=str(e)
        )
