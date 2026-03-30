"""
Servicio para calcular precisión de predicciones comparando con resultados reales
Calcula: Money Line, Over/Under, Run Line, Error de Score
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import date, datetime, timedelta
from ..models.database import (
    get_db, get_prediction_by_game, get_all_predictions,
    get_predictions_with_results, update_prediction_result,
    save_prediction
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AccuracyCalculator:
    """Calcula métricas de precisión del modelo de predicciones"""
    
    def __init__(self):
        pass
    
    def compare_prediction_with_result(
        self,
        prediction: Dict,
        actual_result: Dict
    ) -> Dict[str, Any]:
        """
        Compara una predicción con el resultado real
        
        Returns:
            Dict con:
            - ml_correct: bool
            - ml_winner_predicted: str
            - ml_actual_winner: str
            - ou_correct: bool
            - ou_prediction: str (OVER/UNDER)
            - ou_actual: str
            - rl_correct: bool (run line)
            - score_error: int (diferencia absoluta total)
            - home_score_error: int
            - away_score_error: int
            - total_error: int (suma de runs vs predicción)
        """
        predicted_home = prediction.get("predicted_home_score", 0)
        predicted_away = prediction.get("predicted_away_score", 0)
        predicted_total = prediction.get("predicted_total", predicted_home + predicted_away)
        predicted_favorite = prediction.get("predicted_favorite", "")
        
        actual_home = actual_result.get("home_score", 0)
        actual_away = actual_result.get("away_score", 0)
        actual_total = actual_result.get("total_runs", actual_home + actual_away)
        actual_winner = actual_result.get("winner", "")
        
        over_line = prediction.get("over_line", 8.0)
        
        ml_correct = predicted_favorite == actual_winner
        
        ou_correct = self._check_over_under(actual_total, over_line, prediction.get("over_probability", 0.5))
        
        rl_correct = self._check_run_line(
            actual_home, actual_away,
            predicted_home, predicted_away,
            over_line
        )
        
        home_score_error = abs(actual_home - predicted_home)
        away_score_error = abs(actual_away - predicted_away)
        total_error = abs(actual_total - predicted_total)
        
        return {
            "game_id": actual_result.get("game_id"),
            "game_date": actual_result.get("game_date"),
            "home_team": prediction.get("home_team"),
            "away_team": prediction.get("away_team"),
            "ml_correct": ml_correct,
            "ml_prediction": predicted_favorite,
            "ml_actual": actual_winner,
            "ou_correct": ou_correct,
            "ou_prediction": "OVER" if prediction.get("over_probability", 0.5) > 0.5 else "UNDER",
            "ou_line": over_line,
            "ou_actual": "OVER" if actual_total > over_line else "UNDER",
            "ou_predicted_total": predicted_total,
            "ou_actual_total": actual_total,
            "rl_correct": rl_correct,
            "score_error": home_score_error + away_score_error,
            "home_score_error": home_score_error,
            "away_score_error": away_score_error,
            "total_error": total_error,
            "predicted_score": f"{int(predicted_home)}-{int(predicted_away)}",
            "actual_score": f"{actual_home}-{actual_away}",
            "predicted_total": predicted_total,
            "actual_total": actual_total
        }
    
    def _check_over_under(self, actual_total: int, over_line: float, over_probability: float) -> bool:
        """Verifica si la predicción Over/Under fue correcta"""
        if over_probability > 0.5:
            return actual_total > over_line
        elif over_probability < 0.5:
            return actual_total < over_line
        else:
            return actual_total == over_line
    
    def _check_run_line(self, actual_home: int, actual_away: int,
                        pred_home: float, pred_away: float,
                        over_line: float) -> bool:
        """
        Verifica run line (generalmente -1.5 para favorito)
        Una versión simplificada: verifica si el ganador cubre -1.5
        """
        spread = 1.5
        
        if actual_home > actual_away:
            margin = actual_home - actual_away
            covers = margin >= spread
        else:
            margin = actual_away - actual_home
            covers = margin >= spread
        
        if pred_home > pred_away:
            pred_margin = pred_home - pred_away
            pred_covers = pred_margin >= spread
        else:
            pred_margin = pred_away - pred_home
            pred_covers = pred_margin >= spread
        
        return covers == pred_covers
    
    def calculate_accuracy_metrics(self, comparisons: List[Dict]) -> Dict[str, Any]:
        """
        Calcula métricas agregadas de precisión
        
        Returns:
            Dict con:
            - total_games: int
            - ml_accuracy: float (% aciertos money line)
            - ou_accuracy: float (% aciertos over/under)
            - rl_accuracy: float (% aciertos run line)
            - avg_score_error: float (error promedio en score)
            - avg_total_error: float (error promedio en total)
            - streak_info: dict
        """
        if not comparisons:
            return {
                "total_games": 0,
                "ml_accuracy": 0.0,
                "ml_correct": 0,
                "ou_accuracy": 0.0,
                "ou_correct": 0,
                "rl_accuracy": 0.0,
                "rl_correct": 0,
                "avg_score_error": 0.0,
                "avg_total_error": 0.0,
                "avg_home_error": 0.0,
                "avg_away_error": 0.0,
                "streak_info": {"current": 0, "best": 0, "type": "N/A"}
            }
        
        total = len(comparisons)
        ml_correct = sum(1 for c in comparisons if c.get("ml_correct", False))
        ou_correct = sum(1 for c in comparisons if c.get("ou_correct", False))
        rl_correct = sum(1 for c in comparisons if c.get("rl_correct", False))
        
        total_score_errors = [c.get("score_error", 0) for c in comparisons]
        total_total_errors = [c.get("total_error", 0) for c in comparisons]
        home_errors = [c.get("home_score_error", 0) for c in comparisons]
        away_errors = [c.get("away_score_error", 0) for c in comparisons]
        
        streak_info = self._calculate_streak(comparisons)
        
        return {
            "total_games": total,
            "ml_accuracy": round(ml_correct / total * 100, 1) if total > 0 else 0.0,
            "ml_correct": ml_correct,
            "ou_accuracy": round(ou_correct / total * 100, 1) if total > 0 else 0.0,
            "ou_correct": ou_correct,
            "rl_accuracy": round(rl_correct / total * 100, 1) if total > 0 else 0.0,
            "rl_correct": rl_correct,
            "avg_score_error": round(sum(total_score_errors) / total, 2) if total > 0 else 0.0,
            "avg_total_error": round(sum(total_total_errors) / total, 2) if total > 0 else 0.0,
            "avg_home_error": round(sum(home_errors) / total, 2) if total > 0 else 0.0,
            "avg_away_error": round(sum(away_errors) / total, 2) if total > 0 else 0.0,
            "streak_info": streak_info
        }
    
    def _calculate_streak(self, comparisons: List[Dict]) -> Dict[str, Any]:
        """Calcula rachas actuales y mejores"""
        if not comparisons:
            return {"current": 0, "best": 0, "type": "N/A"}
        
        current_streak = 0
        best_streak = 0
        best_streak_type = "N/A"
        temp_streak = 0
        temp_type = ""
        
        for c in comparisons:
            ml = c.get("ml_correct", False)
            
            if ml:
                if temp_type == "W":
                    temp_streak += 1
                else:
                    temp_streak = 1
                    temp_type = "W"
                
                if temp_streak > best_streak:
                    best_streak = temp_streak
                    best_streak_type = temp_type
            else:
                temp_streak = 0
                temp_type = ""
            
            current_streak = temp_streak if temp_type == "W" else 0
        
        return {
            "current": current_streak,
            "best": best_streak,
            "type": "Wins" if best_streak_type == "W" else "N/A"
        }
    
    def get_detailed_breakdown(self, comparisons: List[Dict]) -> Dict[str, Any]:
        """Obtiene desglose detallado por tipo de apuesta"""
        overs = [c for c in comparisons if c.get("ou_prediction") == "OVER"]
        unders = [c for c in comparisons if c.get("ou_prediction") == "UNDER"]
        
        favorites = [c for c in comparisons if c.get("ml_prediction") == c.get("home_team")]
        underdogs = [c for c in comparisons if c.get("ml_prediction") == c.get("away_team")]
        
        return {
            "over_performance": {
                "total": len(overs),
                "correct": sum(1 for c in overs if c.get("ou_correct", False)),
                "accuracy": round(sum(1 for c in overs if c.get("ou_correct", False)) / len(overs) * 100, 1) if overs else 0.0
            },
            "under_performance": {
                "total": len(unders),
                "correct": sum(1 for c in unders if c.get("ou_correct", False)),
                "accuracy": round(sum(1 for c in unders if c.get("ou_correct", False)) / len(unders) * 100, 1) if unders else 0.0
            },
            "favorite_performance": {
                "total": len(favorites),
                "correct": sum(1 for c in favorites if c.get("ml_correct", False)),
                "accuracy": round(sum(1 for c in favorites if c.get("ml_correct", False)) / len(favorites) * 100, 1) if favorites else 0.0
            },
            "underdog_performance": {
                "total": len(underdogs),
                "correct": sum(1 for c in underdogs if c.get("ml_correct", False)),
                "accuracy": round(sum(1 for c in underdogs if c.get("ml_correct", False)) / len(underdogs) * 100, 1) if underdogs else 0.0
            },
            "score_ranges": self._analyze_score_ranges(comparisons)
        }
    
    def _analyze_score_ranges(self, comparisons: List[Dict]) -> Dict[str, Any]:
        """Analiza precisión por rango de score predicho"""
        low_total = [c for c in comparisons if c.get("predicted_total", 0) < 7.5]
        mid_total = [c for c in comparisons if 7.5 <= c.get("predicted_total", 0) < 9.5]
        high_total = [c for c in comparisons if c.get("predicted_total", 0) >= 9.5]
        
        return {
            "low_totals": {
                "range": "< 7.5",
                "total": len(low_total),
                "accuracy": round(sum(1 for c in low_total if c.get("ou_correct", False)) / len(low_total) * 100, 1) if low_total else 0.0
            },
            "mid_totals": {
                "range": "7.5 - 9.5",
                "total": len(mid_total),
                "accuracy": round(sum(1 for c in mid_total if c.get("ou_correct", False)) / len(mid_total) * 100, 1) if mid_total else 0.0
            },
            "high_totals": {
                "range": ">= 9.5",
                "total": len(high_total),
                "accuracy": round(sum(1 for c in high_total if c.get("ou_correct", False)) / len(high_total) * 100, 1) if high_total else 0.0
            }
        }
    
    def update_database_results(self, comparisons: List[Dict]) -> int:
        """Actualiza la base de datos con los resultados reales"""
        updated = 0
        for comp in comparisons:
            game_id = comp.get("game_id")
            if game_id:
                try:
                    update_prediction_result(
                        game_id,
                        comp.get("actual_score", "").split("-")[0] if comp.get("actual_score") else 0,
                        comp.get("actual_score", "").split("-")[1] if comp.get("actual_score") else 0
                    )
                    updated += 1
                except Exception as e:
                    logger.error(f"Error actualizando game_id {game_id}: {e}")
        return updated
    
    def get_recent_results(self, days: int = 7) -> List[Dict]:
        """Obtiene resultados de los últimos N días con sus comparaciones"""
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            predictions = db.query(__import__('app.models.database', fromlist=['PredictionRecordDB']).PredictionRecordDB).filter(
                __import__('app.models.database', fromlist=['PredictionRecordDB']).PredictionRecordDB.result_registered == True
            ).order_by(
                __import__('app.models.database', fromlist=['PredictionRecordDB']).PredictionRecordDB.game_date.desc()
            ).limit(days * 15).all()
            
            results = []
            for p in predictions:
                results.append({
                    "game_id": p.game_id,
                    "game_date": p.game_date.isoformat() if p.game_date else None,
                    "home_team": p.home_team,
                    "away_team": p.away_team,
                    "predicted_score": f"{int(p.predicted_home_score)}-{int(p.predicted_away_score)}",
                    "actual_score": f"{p.actual_home_score}-{p.actual_away_score}" if p.actual_home_score else "N/A",
                    "predicted_total": p.predicted_total,
                    "actual_total": (p.actual_home_score or 0) + (p.actual_away_score or 0) if p.actual_home_score else None,
                    "ml_correct": p.predicted_favorite == self._get_winner(p.actual_home_score, p.actual_away_score, p.home_team, p.away_team),
                    "ou_correct": self._check_result_ou(p),
                })
            
            return results
        finally:
            db.close()
    
    def _get_winner(self, home_score: int, away_score: int, home_team: str, away_team: str) -> str:
        """Determina el ganador"""
        if home_score > away_score:
            return home_team
        elif away_score > home_score:
            return away_team
        return "Tie"
    
    def _check_result_ou(self, prediction) -> Optional[bool]:
        """Verifica si la predicción O/U fue correcta"""
        if not prediction.result_registered or prediction.actual_home_score is None:
            return None
        
        actual_total = prediction.actual_home_score + prediction.actual_away_score
        return self._check_over_under(actual_total, prediction.over_line, prediction.over_probability)


accuracy_calculator = AccuracyCalculator()
