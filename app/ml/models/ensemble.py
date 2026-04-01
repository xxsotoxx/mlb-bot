"""
Ensemble Model - Combina múltiples modelos para mejor predicción
"""
import logging
import numpy as np
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnsembleModel:
    """
    Ensambla múltiples modelos:
    - Poisson para runs (home & away)
    - Neural Net para Money Line
    - Reglas del sistema actual
    """
    
    def __init__(
        self,
        poisson_home_model=None,
        poisson_away_model=None,
        win_classifier_model=None,
        rules_based_predictor=None,
        ml_weight: float = 0.6,
        rules_weight: float = 0.4
    ):
        self.poisson_home = poisson_home_model
        self.poisson_away = poisson_away_model
        self.win_classifier = win_classifier_model
        self.rules_predictor = rules_based_predictor
        
        self.ml_weight = ml_weight
        self.rules_weight = rules_weight
        
        self.is_trained = False
    
    def set_models(
        self,
        poisson_home,
        poisson_away,
        win_classifier
    ):
        """Inyecta los modelos ML"""
        self.poisson_home = poisson_home
        self.poisson_away = poisson_away
        self.win_classifier = win_classifier
        self.is_trained = True
    
    def predict(
        self,
        features: np.ndarray,
        rules_prediction: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Predice usando ensemble de ML + reglas
        
        Returns:
            {
                "predicted_home_runs": float,
                "predicted_away_runs": float,
                "predicted_total": float,
                "home_win_prob": float,
                "away_win_prob": float,
                "favorite": str,
                "source": "ml" | "ensemble" | "rules"
            }
        """
        
        if not self.is_trained or self.poisson_home is None:
            if rules_prediction:
                return self._convert_rules_prediction(rules_prediction)
            return self._default_prediction()
        
        ml_home_runs = self._safe_predict(self.poisson_home.predict_runs, features)
        ml_away_runs = self._safe_predict(self.poisson_away.predict_runs, features)
        ml_total = ml_home_runs + ml_away_runs
        
        ml_win_probs = self._safe_predict(self.win_classifier.predict_proba, features)
        
        if rules_prediction:
            rules_home = rules_prediction.get("predicted_home_score", 4.0)
            rules_away = rules_prediction.get("predicted_away_score", 4.0)
            rules_total = rules_home + rules_away
            
            final_home = self.ml_weight * ml_home_runs + self.rules_weight * rules_home
            final_away = self.ml_weight * ml_away_runs + self.rules_weight * rules_away
            final_total = final_home + final_away
            
            ml_prob = ml_win_probs.get("home_win_prob", 0.5)
            rules_prob = rules_prediction.get("home_win_probability", 50) / 100
            
            final_home_prob = self.ml_weight * ml_prob + self.rules_weight * rules_prob
            final_away_prob = 1 - final_home_prob
        else:
            final_home = ml_home_runs
            final_away = ml_away_runs
            final_total = ml_total
            final_home_prob = ml_win_probs.get("home_win_prob", 0.5)
            final_away_prob = ml_win_probs.get("away_win_prob", 0.5)
        
        final_home = round(max(1.0, min(10.0, final_home)), 1)
        final_away = round(max(1.0, min(10.0, final_away)), 1)
        final_total = round(max(3.0, min(15.0, final_home + final_away)), 1)
        
        return {
            "predicted_home_score": final_home,
            "predicted_away_score": final_away,
            "predicted_total": final_total,
            "home_win_probability": round(final_home_prob, 3),
            "away_win_probability": round(final_away_prob, 3),
            "favorite": "Home" if final_home_prob > final_away_prob else "Away",
            "ml_home_runs": ml_home_runs,
            "ml_away_runs": ml_away_runs,
            "ml_total": ml_total,
            "source": "ensemble"
        }
    
    def _safe_predict(self, predict_fn, features):
        """Wrapper para predicciones seguras"""
        try:
            result = predict_fn(features)
            return result if result else 4.5
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return 4.5
    
    def _convert_rules_prediction(self, rules_pred: Dict) -> Dict:
        """Convierte predicción de reglas al formato estándar"""
        return {
            "predicted_home_score": rules_pred.get("predicted_home_score", 4.0),
            "predicted_away_score": rules_pred.get("predicted_away_score", 4.0),
            "predicted_total": rules_pred.get("predicted_total", 8.0),
            "home_win_probability": rules_pred.get("home_win_probability", 50) / 100,
            "away_win_probability": rules_pred.get("away_win_probability", 50) / 100,
            "favorite": rules_pred.get("predicted_favorite", "Home"),
            "source": "rules"
        }
    
    def _default_prediction(self) -> Dict:
        """Predicción por defecto"""
        return {
            "predicted_home_score": 4.0,
            "predicted_away_score": 4.5,
            "predicted_total": 8.5,
            "home_win_probability": 0.5,
            "away_win_probability": 0.5,
            "favorite": "Home",
            "source": "default"
        }


def create_ensemble() -> EnsembleModel:
    """Factory function"""
    return EnsembleModel()