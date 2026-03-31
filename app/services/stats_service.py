"""
Servicio de Análisis y Seguimiento de Rendimiento
Consultas resultados reales, compara con predicciones y genera estadísticas acumuladas
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

from .mlb_api import mlb_client, fetch_today_games, fetch_game_details
from ..models.database import get_db, get_all_predictions, get_predictions_with_results

logger = logging.getLogger(__name__)


class StatsService:
    """Servicio para análisis de predicciones y seguimiento de rendimiento"""
    
    def __init__(self):
        self.cache = {}
    
    async def get_yesterday_results(self) -> List[Dict[str, Any]]:
        """Obtiene los resultados reales de los partidos de ayer"""
        yesterday = date.today() - timedelta(days=1)
        yesterday_str = yesterday.strftime("%m/%d/%Y")
        
        logger.info(f"Consultando resultados de: {yesterday_str}")
        
        games = await mlb_client.get_schedule(date_str=yesterday_str)
        
        if not games:
            logger.warning(f"No se encontraron partidos para {yesterday_str}")
            return []
        
        results = []
        for game in games:
            game_pk = game.get("gamePk")
            teams = game.get("teams", {})
            status = game.get("status", {})
            detailed_state = status.get("detailedState", "Unknown")
            
            home_team = teams.get("home", {}).get("team", {})
            away_team = teams.get("away", {}).get("team", {})
            
            home_runs = teams.get("home", {}).get("score", 0)
            away_runs = teams.get("away", {}).get("score", 0)
            
            game_data = {
                "game_id": game_pk,
                "game_date": yesterday.isoformat(),
                "home_team": home_team.get("name"),
                "home_team_id": home_team.get("id"),
                "away_team": away_team.get("name"),
                "away_team_id": away_team.get("id"),
                "home_score": home_runs,
                "away_score": away_runs,
                "total_runs": home_runs + away_runs,
                "status": detailed_state,
                "is_final": detailed_state in ["Final", "Completed Early", "Game Over"],
                "winner": home_team.get("name") if home_runs > away_runs else (away_team.get("name") if away_runs > home_runs else "Tie"),
                "venue": game.get("venue", {}).get("name")
            }
            results.append(game_data)
        
        logger.info(f"Encontrados {len(results)} partidos de ayer")
        return results
    
    async def get_predictions_for_date(self, target_date: date) -> List[Dict]:
        """Obtiene las predicciones guardadas para una fecha específica"""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            all_predictions = get_all_predictions(db, limit=500)
            
            predictions = []
            for p in all_predictions:
                if p.game_date == target_date:
                    predictions.append({
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
                        "over_line": p.over_line,
                        "actual_home_score": p.actual_home_score,
                        "actual_away_score": p.actual_away_score,
                        "result_registered": p.result_registered
                    })
            
            return predictions
        finally:
            db.close()
    
    def compare_predictions_with_results(
        self, 
        predictions: List[Dict], 
        results: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Compara predicciones con resultados reales"""
        comparisons = []
        
        for pred in predictions:
            pred_home = pred.get("home_team", "").lower()
            pred_away = pred.get("away_team", "").lower()
            
            matched_result = None
            for result in results:
                result_home = result.get("home_team", "").lower()
                result_away = result.get("away_team", "").lower()
                
                if (pred_home in result_home or result_home in pred_home) and \
                   (pred_away in result_away or result_away in pred_away):
                    matched_result = result
                    break
            
            if not matched_result:
                continue
            
            home_score_diff = abs(pred["predicted_home_score"] - matched_result["home_score"])
            away_score_diff = abs(pred["predicted_away_score"] - matched_result["away_score"])
            total_diff = abs((pred["predicted_home_score"] + pred["predicted_away_score"]) - matched_result["total_runs"])
            
            runs_correct = home_score_diff <= 1 and away_score_diff <= 1
            total_correct = total_diff <= 1
            
            predicted_winner = pred.get("predicted_favorite", "")
            actual_winner = matched_result.get("winner", "")
            ml_correct = predicted_winner.lower() in actual_winner.lower() if actual_winner != "Tie" else False
            
            ou_line = pred.get("over_line", 8)
            actual_total = matched_result["total_runs"]
            
            # Fixed: Use over_probability directly instead of score sum
            predicted_over_prob = pred.get("over_probability", 0.5)
            over_correct = actual_total > ou_line
            pred_over = predicted_over_prob > 0.5
            ou_correct = over_correct == pred_over
            
            comparison = {
                "game_id": pred["game_id"],
                "game_date": pred["game_date"],
                "home_team": pred["home_team"],
                "away_team": pred["away_team"],
                "venue": matched_result.get("venue"),
                
                "prediction": {
                    "home_score": pred["predicted_home_score"],
                    "away_score": pred["predicted_away_score"],
                    "total": pred["predicted_total"],
                    "favorite": pred["predicted_favorite"],
                    "over_line": ou_line
                },
                "result": {
                    "home_score": matched_result["home_score"],
                    "away_score": matched_result["away_score"],
                    "total": matched_result["total_runs"],
                    "winner": actual_winner,
                    "status": matched_result["status"]
                },
                "analysis": {
                    "home_diff": home_score_diff,
                    "away_diff": away_score_diff,
                    "total_diff": total_diff,
                    "runs_correct": runs_correct,
                    "total_correct": total_correct,
                    "ml_correct": ml_correct,
                    "ou_correct": ou_correct,
                    "home_winner_correct": (matched_result["home_score"] > matched_result["away_score"]) == 
                                         (pred["predicted_home_score"] > pred["predicted_away_score"]),
                    "away_winner_correct": (matched_result["away_score"] > matched_result["home_score"]) == 
                                          (pred["predicted_away_score"] > pred["predicted_home_score"])
                }
            }
            comparisons.append(comparison)
        
        return comparisons
    
    def calculate_accuracy_stats(self, predictions_with_results: List[Dict]) -> Dict[str, Any]:
        """Calcula estadísticas de precisión"""
        if not predictions_with_results:
            return {
                "total_games": 0,
                "runs_accuracy_pct": 0,
                "total_accuracy_pct": 0,
                "ml_accuracy_pct": 0,
                "ou_accuracy_pct": 0,
                "avg_run_diff": 0,
                "avg_home_diff": 0,
                "avg_away_diff": 0
            }
        
        total = len(predictions_with_results)
        runs_correct = sum(1 for p in predictions_with_results if p["analysis"]["runs_correct"])
        total_correct = sum(1 for p in predictions_with_results if p["analysis"]["total_correct"])
        ml_correct = sum(1 for p in predictions_with_results if p["analysis"]["ml_correct"])
        ou_correct = sum(1 for p in predictions_with_results if p["analysis"]["ou_correct"])
        
        avg_run_diff = sum(p["analysis"]["total_diff"] for p in predictions_with_results) / total
        avg_home_diff = sum(p["analysis"]["home_diff"] for p in predictions_with_results) / total
        avg_away_diff = sum(p["analysis"]["away_diff"] for p in predictions_with_results) / total
        
        return {
            "total_games": total,
            "runs_accuracy_pct": round(runs_correct / total * 100, 1),
            "total_accuracy_pct": round(total_correct / total * 100, 1),
            "ml_accuracy_pct": round(ml_correct / total * 100, 1),
            "ou_accuracy_pct": round(ou_correct / total * 100, 1),
            "avg_run_diff": round(avg_run_diff, 2),
            "avg_home_diff": round(avg_home_diff, 2),
            "avg_away_diff": round(avg_away_diff, 2)
        }
    
    def get_team_tracking(self, predictions_with_results: List[Dict]) -> Dict[str, Dict]:
        """Genera seguimiento detallado por equipo"""
        team_stats = defaultdict(lambda: {
            "games": 0,
            "runs_correct": 0,
            "ml_correct": 0,
            "total_run_diff": 0,
            "home_games": 0,
            "away_games": 0,
            "home_ml_correct": 0,
            "away_ml_correct": 0,
            "predictions": []
        })
        
        for comp in predictions_with_results:
            pred = comp["prediction"]
            result = comp["result"]
            analysis = comp["analysis"]
            
            for team_type, team_name in [("home", comp["home_team"]), ("away", comp["away_team"])]:
                if not team_name:
                    continue
                
                team = team_stats[team_name]
                team["games"] += 1
                team["total_run_diff"] += analysis["total_diff"]
                team["predictions"].append({
                    "date": comp["game_date"],
                    "venue": comp["venue"],
                    "predicted": pred.get(f"{team_type}_score"),
                    "actual": result.get(f"{team_type}_score"),
                    "diff": analysis[f"{team_type}_diff"],
                    "won": (team_type == "home" and result["home_score"] > result["away_score"]) or
                            (team_type == "away" and result["away_score"] > result["home_score"])
                })
                
                if analysis["runs_correct"]:
                    team["runs_correct"] += 1
                
                if team_type == "home":
                    team["home_games"] += 1
                    if analysis["home_winner_correct"]:
                        team["ml_correct"] += 1
                        team["home_ml_correct"] += 1
                else:
                    team["away_games"] += 1
                    if analysis["away_winner_correct"]:
                        team["ml_correct"] += 1
                        team["away_ml_correct"] += 1
        
        result = {}
        for team_name, stats in team_stats.items():
            games = stats["games"]
            result[team_name] = {
                "games": games,
                "runs_accuracy_pct": round(stats["runs_correct"] / games * 100, 1) if games > 0 else 0,
                "ml_accuracy_pct": round(stats["ml_correct"] / games * 100, 1) if games > 0 else 0,
                "avg_run_diff": round(stats["total_run_diff"] / games, 2) if games > 0 else 0,
                "home_games": stats["home_games"],
                "away_games": stats["away_games"],
                "home_ml_pct": round(stats["home_ml_correct"] / stats["home_games"] * 100, 1) if stats["home_games"] > 0 else 0,
                "away_ml_pct": round(stats["away_ml_correct"] / stats["away_games"] * 100, 1) if stats["away_games"] > 0 else 0
            }
        
        return result
    
    async def get_full_analysis(self) -> Dict[str, Any]:
        """Obtiene el análisis completo: resultados de ayer, comparaciones y estadísticas"""
        yesterday_results = await self.get_yesterday_results()
        yesterday_date = date.today() - timedelta(days=1)
        yesterday_predictions = await self.get_predictions_for_date(yesterday_date)
        
        comparisons = self.compare_predictions_with_results(yesterday_predictions, yesterday_results)
        accuracy_stats = self.calculate_accuracy_stats(comparisons)
        team_tracking = self.get_team_tracking(comparisons)
        
        return {
            "yesterday_date": yesterday_date.isoformat(),
            "yesterday_results": yesterday_results,
            "yesterday_predictions": yesterday_predictions,
            "comparisons": comparisons,
            "accuracy_stats": accuracy_stats,
            "team_tracking": team_tracking,
            "generated_at": datetime.now().isoformat()
        }
    
    async def get_all_time_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas acumuladas de todas las predicciones con resultados"""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            predictions_with_results = get_predictions_with_results(db)
            
            comparisons = []
            for p in predictions_with_results:
                pred_fav = p.predicted_favorite or ""
                actual_home = p.actual_home_score or 0
                actual_away = p.actual_away_score or 0
                
                actual_winner = p.home_team if actual_home > actual_away else (p.away_team if actual_away > actual_home else "Tie")
                
                home_score_diff = abs(p.predicted_home_score - actual_home) if p.predicted_home_score else 0
                away_score_diff = abs(p.predicted_away_score - actual_away) if p.predicted_away_score else 0
                total_diff = abs((p.predicted_home_score + p.predicted_away_score) - (actual_home + actual_away)) if p.predicted_home_score else 0
                
                runs_correct = home_score_diff <= 1 and away_score_diff <= 1
                total_correct = total_diff <= 1
                ml_correct = pred_fav.lower() in actual_winner.lower() if actual_winner != "Tie" else False
                
                comparisons.append({
                    "game_id": p.game_id,
                    "game_date": p.game_date.isoformat() if p.game_date else None,
                    "home_team": p.home_team,
                    "away_team": p.away_team,
                    "prediction": {
                        "home_score": p.predicted_home_score,
                        "away_score": p.predicted_away_score,
                        "total": p.predicted_total,
                        "favorite": pred_fav,
                        "over_line": p.over_line
                    },
                    "result": {
                        "home_score": actual_home,
                        "away_score": actual_away,
                        "total": actual_home + actual_away,
                        "winner": actual_winner
                    },
                    "analysis": {
                        "home_diff": home_score_diff,
                        "away_diff": away_score_diff,
                        "total_diff": total_diff,
                        "runs_correct": runs_correct,
                        "total_correct": total_correct,
                        "ml_correct": ml_correct
                    }
                })
            
            all_time_stats = self.calculate_accuracy_stats(comparisons)
            team_tracking = self.get_team_tracking(comparisons)
            
            return {
                "all_time_stats": all_time_stats,
                "team_tracking": team_tracking,
                "total_predictions": len(comparisons),
                "generated_at": datetime.now().isoformat()
            }
        finally:
            db.close()


stats_service = StatsService()
