"""
Backtest Analyzer - Análisis de performance del modelo
Feature importance, métricas, recomendaciones
"""
import logging
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BacktestAnalyzer:
    """
    Analiza resultados de backtesting
    Provee métricas, feature importance, y recomendaciones
    """
    
    def __init__(self, backtest_logger=None):
        self.logger = backtest_logger
    
    def analyze_performance(
        self,
        records: List[Dict],
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Análisis completo de performance"""
        
        from datetime import date, timedelta
        cutoff = date.today() - timedelta(days=period_days)
        
        recent_records = [
            r for r in records 
            if r.get("game_date") and r["game_date"] >= cutoff.isoformat()
        ]
        
        if not recent_records:
            return {"message": f"No records in last {period_days} days"}
        
        total = len(recent_records)
        
        ml_correct = sum(1 for r in recent_records 
                        if r.get("predicted_favorite") == r.get("actual_winner"))
        
        ou_correct = sum(1 for r in recent_records 
                        if self._check_ou_correct(r))
        
        home_errors = [abs(r.get("predicted_home_score", 0) - r.get("actual_home_score", 0)) 
                      for r in recent_records if r.get("actual_home_score")]
        away_errors = [abs(r.get("predicted_away_score", 0) - r.get("actual_away_score", 0)) 
                      for r in recent_records if r.get("actual_away_score")]
        
        avg_home_error = np.mean(home_errors) if home_errors else 0
        avg_away_error = np.mean(away_errors) if away_errors else 0
        
        total_errors = [abs(r.get("predicted_total", 0) - r.get("actual_total", 0)) 
                       for r in recent_records if r.get("actual_total")]
        avg_total_error = np.mean(total_errors) if total_errors else 0
        
        edges = [r for r in recent_records if r.get("edge_detected")]
        edges_with_results = [r for r in edges if r.get("bet_result")]
        
        edge_performance = {"total": len(edges)}
        if edges_with_results:
            wins = sum(1 for r in edges_with_results if r.get("bet_result") == "WIN")
            edge_performance["with_results"] = len(edges_with_results)
            edge_performance["wins"] = wins
            edge_performance["win_rate"] = round(wins / len(edges_with_results) * 100, 1)
        
        return {
            "period_days": period_days,
            "total_predictions": total,
            "ml_accuracy": round(ml_correct / total * 100, 1) if total > 0 else 0,
            "ml_correct": ml_correct,
            "ou_accuracy": round(ou_correct / total * 100, 1) if total > 0 else 0,
            "ou_correct": ou_correct,
            "avg_home_error": round(avg_home_error, 2),
            "avg_away_error": round(avg_away_error, 2),
            "avg_total_error": round(avg_total_error, 2),
            "edge_performance": edge_performance,
            "timestamp": datetime.now().isoformat()
        }
    
    def _check_ou_correct(self, record: Dict) -> bool:
        """Verifica si predicción O/U fue correcta"""
        predicted = record.get("over_prediction", "")
        actual_total = record.get("actual_total", 0)
        over_line = record.get("over_line", 8.0)
        
        if not predicted or not actual_total:
            return False
        
        if predicted == "OVER":
            return actual_total > over_line
        elif predicted == "UNDER":
            return actual_total < over_line
        return False
    
    def analyze_by_team(self, records: List[Dict]) -> Dict[str, Any]:
        """Análisis de performance por equipo"""
        
        team_stats = {}
        
        for r in records:
            if not r.get("result_registered"):
                continue
            
            for team_key in ["home_team", "away_team"]:
                team = r.get(team_key)
                if not team:
                    continue
                
                if team not in team_stats:
                    team_stats[team] = {
                        "games": 0,
                        "predicted_wins": 0,
                        "actual_wins": 0,
                        "total_runs_predicted": 0,
                        "total_runs_actual": 0
                    }
                
                stats = team_stats[team]
                stats["games"] += 1
                
                is_home = team_key == "home_team"
                predicted_score = r.get("predicted_home_score") if is_home else r.get("predicted_away_score")
                actual_score = r.get("actual_home_score") if is_home else r.get("actual_away_score")
                
                if predicted_score and actual_score:
                    stats["total_runs_predicted"] += predicted_score
                    stats["total_runs_actual"] += actual_score
                
                winner = r.get("actual_winner")
                predicted_fav = r.get("predicted_favorite")
                
                if (is_home and predicted_fav == team) or (not is_home and predicted_fav != team and predicted_fav != "Tie"):
                    stats["predicted_wins"] += 1
                
                if (is_home and winner == "Home") or (not is_home and winner == "Away"):
                    stats["actual_wins"] += 1
        
        for team, stats in team_stats.items():
            if stats["games"] > 0:
                stats["win_accuracy"] = round(stats["predicted_wins"] / stats["games"] * 100, 1)
                stats["avg_runs_predicted"] = round(stats["total_runs_predicted"] / stats["games"], 1)
                stats["avg_runs_actual"] = round(stats["total_runs_actual"] / stats["games"], 1)
        
        return team_stats
    
    def analyze_by_pitcher(
        self,
        records: List[Dict],
        min_games: int = 3
    ) -> Dict[str, Any]:
        """Análisis de performance por pitcher"""
        
        pitcher_stats = {}
        
        for r in records:
            if not r.get("result_registered"):
                continue
            
            for pitcher_key in ["pitcher_home", "pitcher_away"]:
                pitcher = r.get(pitcher_key)
                if not pitcher or pitcher == "TBD":
                    continue
                
                if pitcher not in pitcher_stats:
                    pitcher_stats[pitcher] = {
                        "games": 0,
                        "predictions_correct": 0,
                        "avg_run_error": []
                    }
                
                stats = pitcher_stats[pitcher]
                stats["games"] += 1
                
                is_home = pitcher_key == "pitcher_home"
                pred_total = r.get("predicted_total", 0)
                actual_total = r.get("actual_total", 0)
                
                if pred_total and actual_total:
                    stats["avg_run_error"].append(abs(pred_total - actual_total))
        
        filtered = {}
        for pitcher, stats in pitcher_stats.items():
            if stats["games"] >= min_games:
                avg_error = np.mean(stats["avg_run_error"]) if stats["avg_run_error"] else 0
                filtered[pitcher] = {
                    "games": stats["games"],
                    "avg_run_error": round(avg_error, 2)
                }
        
        return filtered
    
    def get_trend(self, records: List[Dict], window: int = 7) -> Dict[str, Any]:
        """Calcula tendencia de accuracy"""
        
        sorted_records = sorted(records, key=lambda x: x.get("game_date", ""))
        
        trends = []
        
        for i in range(0, len(sorted_records), window):
            window_records = sorted_records[i:i+window]
            
            total = len(window_records)
            if total < 3:
                continue
            
            ml_correct = sum(1 for r in window_records 
                            if r.get("predicted_favorite") == r.get("actual_winner"))
            
            ml_accuracy = ml_correct / total * 100
            
            trends.append({
                "start_date": window_records[0].get("game_date"),
                "end_date": window_records[-1].get("game_date"),
                "games": total,
                "ml_accuracy": round(ml_accuracy, 1)
            })
        
        return {"trends": trends}
    
    def generate_recommendations(self, analysis: Dict) -> List[str]:
        """Genera recomendaciones basadas en análisis"""
        
        recommendations = []
        
        ml_accuracy = analysis.get("ml_accuracy", 0)
        if ml_accuracy < 50:
            recommendations.append("ML accuracy below 50% - consider reducing ML weight in ensemble")
        
        ou_accuracy = analysis.get("ou_accuracy", 0)
        if ou_accuracy < 50:
            recommendations.append("O/U accuracy below 50% - review over/under probability calculations")
        
        avg_error = analysis.get("avg_total_error", 0)
        if avg_error > 2.0:
            recommendations.append(f"Average run prediction error is {avg_error} - consider retraining Poisson models")
        
        edge_perf = analysis.get("edge_performance", {})
        if edge_perf.get("win_rate", 0) < 40:
            recommendations.append("Edge detection win rate below 40% - review edge thresholds")
        
        if not recommendations:
            recommendations.append("All metrics within acceptable ranges")
        
        return recommendations


backtest_analyzer = BacktestAnalyzer()