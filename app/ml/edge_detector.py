"""
Edge Detector - Compara predicciones contra líneas de casino
Detecta valor (edge) en las apuestas
"""
import logging
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdgeDetector:
    """
    Detecta edge (valor) comparando:
    - Predicción del modelo vs línea de casino
    - Probabilidades implícitas vs probabilidades del modelo
    """
    
    EDGE_THRESHOLDS = {
        "total_runs": 1.0,
        "win_prob": 0.10,
        "ml_odds": 0.15
    }
    
    CONFIDENCE_MAPPING = {
        "high": {"min_edge": 1.5, "min_prob_diff": 0.15},
        "medium": {"min_edge": 1.0, "min_prob_diff": 0.10},
        "low": {"min_edge": 0.5, "min_prob_diff": 0.05}
    }
    
    def __init__(self):
        self.edge_history = []
    
    def detect_edge(
        self,
        prediction: Dict[str, Any],
        casino_lines: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detecta edge entre predicción y líneas de casino
        
        Returns:
            {
                "has_edge": bool,
                "edge_type": "over_under" | "money_line" | "run_line",
                "recommendation": str,
                "edge_score": float,
                "confidence": "high" | "medium" | "low",
                "details": {}
            }
        """
        
        if not casino_lines:
            return {
                "has_edge": False,
                "reason": "No casino lines available"
            }
        
        edges_found = []
        
        ou_edge = self._check_over_under_edge(
            prediction.get("predicted_total", 8.0),
            prediction.get("over_probability", 0.5),
            casino_lines
        )
        if ou_edge["has_edge"]:
            edges_found.append(ou_edge)
        
        ml_edge = self._check_money_line_edge(
            prediction.get("home_win_probability", 50),
            prediction.get("away_win_probability", 50),
            casino_lines
        )
        if ml_edge["has_edge"]:
            edges_found.append(ml_edge)
        
        if not edges_found:
            return {
                "has_edge": False,
                "reason": "No significant edge detected",
                "prediction_total": prediction.get("predicted_total"),
                "casino_line": self._get_casino_ou_line(casino_lines)
            }
        
        best_edge = max(edges_found, key=lambda x: x["edge_score"])
        
        return best_edge
    
    def _check_over_under_edge(
        self,
        predicted_total: float,
        predicted_over_prob: float,
        casino_lines: Dict
    ) -> Dict[str, Any]:
        """Detecta edge en Over/Under"""
        
        casino_ou = casino_lines.get("over_under")
        if not casino_ou:
            return {"has_edge": False}
        
        casino_line = casino_ou.get("line")
        if not casino_line:
            return {"has_edge": False}
        
        edge_score = abs(predicted_total - casino_line)
        
        has_edge = edge_score >= self.EDGE_THRESHOLDS["total_runs"]
        
        if not has_edge:
            return {"has_edge": False}
        
        if predicted_total > casino_line:
            recommendation = "OVER"
        else:
            recommendation = "UNDER"
        
        confidence = self._get_confidence(edge_score, 0, "total_runs")
        
        return {
            "has_edge": True,
            "edge_type": "over_under",
            "recommendation": recommendation,
            "edge_score": round(edge_score, 2),
            "confidence": confidence,
            "predicted_total": predicted_total,
            "casino_line": casino_line,
            "diff": round(predicted_total - casino_line, 2)
        }
    
    def _check_money_line_edge(
        self,
        home_win_prob: float,
        away_win_prob: float,
        casino_lines: Dict
    ) -> Dict[str, Any]:
        """Detecta edge en Money Line"""
        
        casino_ml = casino_lines.get("money_line")
        if not casino_ml:
            return {"has_edge": False}
        
        home_odds = casino_ml.get("home")
        away_odds = casino_ml.get("away")
        
        if not home_odds or not away_odds:
            return {"has_edge": False}
        
        implied_home = self._odds_to_implied_prob(home_odds)
        implied_away = self._odds_to_implied_prob(away_odds)
        
        prob_diff = abs(home_win_prob / 100 - implied_home)
        
        has_edge = prob_diff >= self.EDGE_THRESHOLDS["win_prob"]
        
        if not has_edge:
            return {"has_edge": False}
        
        if home_win_prob / 100 > implied_home:
            recommendation = "HOME"
        else:
            recommendation = "AWAY"
        
        confidence = self._get_confidence(0, prob_diff, "win_prob")
        
        return {
            "has_edge": True,
            "edge_type": "money_line",
            "recommendation": recommendation,
            "edge_score": round(prob_diff * 100, 1),
            "confidence": confidence,
            "model_prob": f"{home_win_prob:.1f}%",
            "implied_prob": f"{implied_home*100:.1f}%",
            "casino_odds": f"Home: {home_odds}, Away: {away_odds}"
        }
    
    def _odds_to_implied_prob(self, odds: int) -> float:
        """Convierte cuotas americanas a probabilidad implícita"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def _get_confidence(
        self,
        edge_score: float,
        prob_diff: float,
        edge_type: str
    ) -> str:
        """Determina nivel de confianza del edge"""
        
        thresholds = self.CONFIDENCE_MAPPING
        
        if edge_type == "total_runs":
            if edge_score >= thresholds["high"]["min_edge"]:
                return "high"
            elif edge_score >= thresholds["medium"]["min_edge"]:
                return "medium"
            else:
                return "low"
        else:
            if prob_diff >= thresholds["high"]["min_prob_diff"]:
                return "high"
            elif prob_diff >= thresholds["medium"]["min_prob_diff"]:
                return "medium"
            else:
                return "low"
    
    def _get_casino_ou_line(self, casino_lines: Dict) -> Optional[float]:
        """Obtiene línea O/U de casino"""
        ou = casino_lines.get("over_under")
        if ou:
            return ou.get("line")
        return None
    
    def get_bet_recommendation(
        self,
        prediction: Dict,
        casino_lines: Dict,
        bankroll: float = 1000.0,
        unit_size: float = 0.02
    ) -> Dict[str, Any]:
        """
        Genera recomendación de apuesta con stake óptímo
        Usa Kelly Criterion simplificado
        """
        
        edge = self.detect_edge(prediction, casino_lines)
        
        if not edge.get("has_edge"):
            return {
                "should_bet": False,
                "reason": "No edge detected"
            }
        
        confidence = edge.get("confidence", "low")
        
        if confidence == "high":
            kelly_fraction = 0.04
        elif confidence == "medium":
            kelly_fraction = 0.02
        else:
            kelly_fraction = 0.01
        
        stake = bankroll * kelly_fraction
        
        return {
            "should_bet": True,
            "bet_type": edge.get("edge_type"),
            "selection": edge.get("recommendation"),
            "stake": round(stake, 2),
            "kelly_fraction": kelly_fraction,
            "edge_score": edge.get("edge_score"),
            "confidence": confidence,
            "edge_details": edge
        }


edge_detector = EdgeDetector()