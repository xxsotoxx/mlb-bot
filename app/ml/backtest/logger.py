"""
Backtest Logger - Registra predicciones vs resultados reales
Permite análisis de performance y mejora continua
"""
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, date
from dataclasses import dataclass, asdict
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PredictionRecord:
    """Registro de una predicción con resultado"""
    game_id: int
    game_date: date
    
    home_team: str
    away_team: str
    
    predicted_home_score: float
    predicted_away_score: float
    predicted_total: float
    predicted_favorite: str
    
    home_win_prob: float
    away_win_prob: float
    
    over_line: float
    over_prob: float
    over_prediction: str
    
    model_source: str
    
    casino_ou_line: Optional[float] = None
    casino_ml_home: Optional[int] = None
    casino_ml_away: Optional[int] = None
    
    edge_detected: bool = False
    edge_type: Optional[str] = None
    edge_recommendation: Optional[str] = None
    
    actual_home_score: Optional[int] = None
    actual_away_score: Optional[int] = None
    actual_total: Optional[int] = None
    actual_winner: Optional[str] = None
    
    result_registered: bool = False
    bet_placed: bool = False
    bet_result: Optional[str] = None
    bet_profit: Optional[float] = None
    
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class BacktestLogger:
    """
    Logger para backtesting
    Registra todas las predicciones y sus resultados para análisis
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.records: List[PredictionRecord] = []
        self.pending_updates: List[Dict] = []
    
    def log_prediction(
        self,
        prediction: Dict[str, Any],
        game_info: Dict[str, Any],
        casino_lines: Dict = None,
        edge_info: Dict = None
    ) -> int:
        """
        Registra una predicción realizada
        
        Args:
            prediction: Resultado de la predicción
            game_info: Información del juego
            casino_lines: Líneas de casino (opcional)
            edge_info: Información de edge detectado (opcional)
        
        Returns:
            ID del registro
        """
        
        game_date = game_info.get("game_date")
        if isinstance(game_date, str):
            try:
                game_date = date.fromisoformat(game_date.split("T")[0])
            except:
                game_date = date.today()
        elif game_date is None:
            game_date = date.today()
        
        record = PredictionRecord(
            game_id=game_info.get("game_id", 0),
            game_date=game_date,
            home_team=game_info.get("home_team", ""),
            away_team=game_info.get("away_team", ""),
            predicted_home_score=prediction.get("predicted_home_score", 4.0),
            predicted_away_score=prediction.get("predicted_away_score", 4.0),
            predicted_total=prediction.get("predicted_total", 8.0),
            predicted_favorite=prediction.get("predicted_favorite", "Home"),
            home_win_prob=prediction.get("home_win_probability", 50),
            away_win_prob=prediction.get("away_win_probability", 50),
            over_line=prediction.get("over_line", 8.0),
            over_prob=prediction.get("over_probability", 50),
            over_prediction="OVER" if prediction.get("over_probability", 50) > 50 else "UNDER",
            model_source=prediction.get("model_source", "rules"),
            casino_ou_line=casino_lines.get("over_under", {}).get("line") if casino_lines else None,
            casino_ml_home=casino_lines.get("money_line", {}).get("home") if casino_lines else None,
            casino_ml_away=casino_lines.get("money_line", {}).get("away") if casino_lines else None,
            edge_detected=edge_info.get("has_edge", False) if edge_info else False,
            edge_type=edge_info.get("edge_type") if edge_info else None,
            edge_recommendation=edge_info.get("recommendation") if edge_info else None
        )
        
        self.records.append(record)
        
        logger.info(f"Logged prediction: {record.home_team} vs {record.away_team}")
        
        return len(self.records) - 1
    
    def log_result(
        self,
        game_id: int,
        home_score: int,
        away_score: int,
        bet_placed: bool = False,
        bet_result: str = None,
        bet_odds: int = None
    ):
        """
        Registra el resultado real de un partido
        
        Args:
            game_id: ID del juego
            home_score: Carreras del equipo local
            away_score: Carreras del equipo visitante
            bet_placed: Si se apostó
            bet_result: WIN/LOSS/PUSH
            bet_odds: Cuotas de la apuesta
        """
        
        for record in self.records:
            if record.game_id == game_id:
                record.actual_home_score = home_score
                record.actual_away_score = away_score
                record.actual_total = home_score + away_score
                record.result_registered = True
                
                if home_score > away_score:
                    record.actual_winner = "Home"
                elif away_score > home_score:
                    record.actual_winner = "Away"
                else:
                    record.actual_winner = "Tie"
                
                if bet_placed:
                    record.bet_placed = True
                    record.bet_result = bet_result
                    
                    if bet_result == "WIN" and bet_odds:
                        if bet_odds > 0:
                            record.bet_profit = bet_odds
                        else:
                            record.bet_profit = 100 / abs(bet_odds) * 100
                    elif bet_result == "LOSS":
                        record.bet_profit = -100
                
                logger.info(f"Updated result for game {game_id}: {home_score}-{away_score}")
                break
    
    def get_prediction_accuracy(self) -> Dict[str, Any]:
        """Calcula precisión de las predicciones"""
        
        completed = [r for r in self.records if r.result_registered]
        
        if not completed:
            return {"total": 0, "message": "No completed predictions"}
        
        total = len(completed)
        
        ml_correct = sum(1 for r in completed if r.predicted_favorite == r.actual_winner)
        
        ou_correct = 0
        for r in completed:
            actual_total = r.actual_total or 0
            if r.over_prediction == "OVER" and actual_total > r.over_line:
                ou_correct += 1
            elif r.over_prediction == "UNDER" and actual_total < r.over_line:
                ou_correct += 1
        
        home_error = sum(abs(r.predicted_home_score - r.actual_home_score) for r in completed if r.actual_home_score) / total
        away_error = sum(abs(r.predicted_away_score - r.actual_away_score) for r in completed if r.actual_away_score) / total
        
        total_error = sum(abs(r.predicted_total - r.actual_total) for r in completed if r.actual_total) / total
        
        bet_results = [r for r in completed if r.bet_placed]
        if bet_results:
            total_profit = sum(r.bet_profit for r in bet_results)
            bets_won = sum(1 for r in bet_results if r.bet_result == "WIN")
            roi = (total_profit / (len(bet_results) * 100)) * 100 if bet_results else 0
        else:
            total_profit = 0
            bets_won = 0
            roi = 0
        
        return {
            "total_predictions": total,
            "ml_accuracy": round(ml_correct / total * 100, 1),
            "ml_correct": ml_correct,
            "ou_accuracy": round(ou_correct / total * 100, 1),
            "ou_correct": ou_correct,
            "avg_home_error": round(home_error, 2),
            "avg_away_error": round(away_error, 2),
            "avg_total_error": round(total_error, 2),
            "bets_placed": len(bet_results),
            "bets_won": bets_won,
            "total_profit": round(total_profit, 2),
            "roi": round(roi, 1)
        }
    
    def get_recent_predictions(self, limit: int = 10) -> List[Dict]:
        """Retorna predicciones recientes"""
        
        recent = sorted(self.records, key=lambda x: x.game_date, reverse=True)[:limit]
        
        return [
            {
                "game_date": r.game_date.isoformat(),
                "home_team": r.home_team,
                "away_team": r.away_team,
                "predicted": f"{int(r.predicted_home_score)}-{int(r.predicted_away_score)}",
                "actual": f"{r.actual_home_score}-{r.actual_away_score}" if r.result_registered else "N/A",
                "predicted_favorite": r.predicted_favorite,
                "actual_winner": r.actual_winner if r.result_registered else "N/A",
                "ml_correct": r.predicted_favorite == r.actual_winner if r.result_registered else None,
                "edge_detected": r.edge_detected,
                "bet_placed": r.bet_placed,
                "bet_result": r.bet_result
            }
            for r in recent
        ]
    
    def export_to_json(self, filepath: str):
        """Exporta todos los registros a JSON"""
        
        data = []
        for r in self.records:
            record_dict = asdict(r)
            record_dict["game_date"] = r.game_date.isoformat()
            record_dict["created_at"] = r.created_at.isoformat()
            data.append(record_dict)
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Exported {len(data)} records to {filepath}")
    
    def get_edge_performance(self) -> Dict[str, Any]:
        """Analiza performance de edges detectados"""
        
        with_edge = [r for r in self.records if r.edge_detected and r.result_registered]
        
        if not with_edge:
            return {"total": 0, "message": "No edges with results"}
        
        total = len(with_edge)
        won = sum(1 for r in with_edge if r.bet_result == "WIN")
        
        return {
            "total_edges": total,
            "edges_won": won,
            "win_rate": round(won / total * 100, 1),
            "total_profit": round(sum(r.bet_profit for r in with_edge if r.bet_profit), 2)
        }


backtest_logger = BacktestLogger()