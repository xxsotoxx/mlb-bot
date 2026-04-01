"""
Hybrid Predictor - Combina ML + reglas para inferencia
Este es el punto de entrada principal para predicciones
"""
import logging
import numpy as np
from typing import Dict, Optional, Any
from datetime import date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridPredictor:
    """
    Predictor híbrido que combina:
    1. Sistema basado en reglas (AdvancedSabermetricPredictor)
    2. Modelos ML (Poisson + Win Classifier)
    3. Ensemble para mejor predicción
    """
    
    def __init__(
        self,
        use_ml: bool = True,
        ml_weight: float = 0.6,
        rules_weight: float = 0.4
    ):
        self.use_ml = use_ml
        self.ml_weight = ml_weight
        self.rules_weight = rules_weight
        
        self.rules_predictor = None
        self.ml_models = None
        self.registry = None
        self.feature_engine = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa los componentes necesarios"""
        try:
            from app.ml.features import feature_engine
            from app.ml.registry import model_registry
            from app.services.advanced_predictor import advanced_predictor
            
            self.feature_engine = feature_engine
            self.registry = model_registry
            self.rules_predictor = advanced_predictor
            
            logger.info("HybridPredictor initialized")
            
        except Exception as e:
            logger.warning(f"ML components not available: {e}")
            self.use_ml = False
    
    def load_ml_models(self, version: str = None) -> bool:
        """Carga los modelos ML"""
        if not self.use_ml:
            return False
        
        try:
            from app.ml.models.poisson_model import PoissonModel
            from app.ml.models.win_classifier import WinClassifierModel
            
            if version is None:
                version = self.registry.get_latest_version()
            
            if version:
                self.ml_models = {
                    "poisson_home": PoissonModel(),
                    "poisson_away": PoissonModel(),
                    "win_classifier": WinClassifierModel()
                }
                
                meta_path = f"models/ml/training_meta_{version}.json"
                import json
                with open(meta_path) as f:
                    meta = json.load(f)
                
                self.ml_models["poisson_home"].load(meta["poisson_home"])
                self.ml_models["poisson_away"].load(meta["poisson_away"])
                self.ml_models["win_classifier"].load(meta["win_classifier"])
                
                logger.info(f"Loaded ML models version: {version}")
                return True
            else:
                logger.info("No trained models found, using rules only")
                return False
                
        except Exception as e:
            logger.warning(f"Could not load ML models: {e}")
            self.use_ml = False
            return False
    
    async def predict(
        self,
        game_info: Dict[str, Any],
        casino_lines: Dict = None
    ) -> Dict[str, Any]:
        """
        Genera predicción híbrida para un partido
        
        Args:
            game_info: Información del juego (home_team_id, away_team_id, etc.)
            casino_lines: Líneas de casino (opcional)
        
        Returns:
            Predicción completa con scores, probabilidades y análisis de edge
        """
        game_id = game_info.get("game_id", 0)
        
        rules_prediction = await self.rules_predictor.generate_prediction(game_info)
        
        if self.use_ml and self.ml_models:
            try:
                ml_prediction = await self._predict_ml(game_info, casino_lines)
                
                final_prediction = self._combine_predictions(
                    rules_prediction,
                    ml_prediction
                )
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}, using rules only")
                final_prediction = rules_prediction
        else:
            final_prediction = rules_prediction
        
        if casino_lines:
            from app.ml.edge_detector import edge_detector
            edge_info = edge_detector.detect_edge(final_prediction, casino_lines)
            final_prediction["edge_detection"] = edge_info
            final_prediction["casino_lines"] = casino_lines
        
        final_prediction["model_source"] = "ml_ensemble" if (self.use_ml and self.ml_models) else "rules_only"
        
        return final_prediction
    
    async def _predict_ml(
        self,
        game_info: Dict,
        casino_lines: Dict
    ) -> Dict[str, Any]:
        """Predice usando modelos ML"""
        
        home_team_id = game_info.get("home_team_id", 0)
        away_team_id = game_info.get("away_team_id", 0)
        
        home_stats = await self.rules_predictor.get_team_recent_stats(home_team_id) if home_team_id else {}
        away_stats = await self.rules_predictor.get_team_recent_stats(away_team_id) if away_team_id else {}
        
        home_bullpen = await self.rules_predictor.get_bullpen_stats(home_team_id) if home_team_id else {}
        away_bullpen = await self.rules_predictor.get_bullpen_stats(away_team_id) if away_team_id else {}
        
        home_batting = await self.rules_predictor.get_team_batting_stats(home_team_id) if home_team_id else {}
        away_batting = await self.rules_predictor.get_team_batting_stats(away_team_id) if away_team_id else {}
        
        game_date = game_info.get("game_date")
        if isinstance(game_date, str):
            game_date = date.fromisoformat(game_date)
        elif game_date is None:
            game_date = date.today()
        
        home_pitcher_id = game_info.get("home_pitcher_id")
        away_pitcher_id = game_info.get("away_pitcher_id")
        
        home_pitcher = await self.rules_predictor.get_pitcher_stats(home_pitcher_id) if home_pitcher_id else {}
        away_pitcher = await self.rules_predictor.get_pitcher_stats(away_pitcher_id) if away_pitcher_id else {}
        
        park_factor = self.rules_predictor.calculate_park_factor(
            home_team_id, 
            game_info.get("venue", "")
        )
        
        features = self.feature_engine.compute_features(
            game_id=game_id,
            game_date=game_date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_stats=home_stats,
            away_team_stats=away_stats,
            home_pitcher_stats=home_pitcher,
            away_pitcher_stats=away_pitcher,
            home_bullpen_stats=home_bullpen,
            away_bullpen_stats=away_bullpen,
            home_batting_stats=home_batting,
            away_batting_stats=away_batting,
            park_factor=park_factor,
            casino_lines=casino_lines
        )
        
        home_runs = self.ml_models["poisson_home"].predict_runs(features.features)
        away_runs = self.ml_models["poisson_away"].predict_runs(features.features)
        
        win_probs = self.ml_models["win_classifier"].predict_proba(features.features)
        
        return {
            "predicted_home_score": round(home_runs, 1),
            "predicted_away_score": round(away_runs, 1),
            "predicted_total": round(home_runs + away_runs, 1),
            "home_win_probability": round(win_probs.get("home_win_prob", 0.5) * 100, 1),
            "away_win_probability": round(win_probs.get("away_win_prob", 0.5) * 100, 1),
            "favorite": "Home" if win_probs.get("home_win_prob", 0.5) > win_probs.get("away_win_prob", 0.5) else "Away",
            "ml_model": "poisson_nn_ensemble"
        }
    
    def _combine_predictions(
        self,
        rules_pred: Dict,
        ml_pred: Dict
    ) -> Dict:
        """Combina predicciones de reglas y ML"""
        
        rules_home = rules_pred.get("predicted_home_score", 4.0)
        rules_away = rules_pred.get("predicted_away_score", 4.0)
        rules_total = rules_home + rules_away
        
        ml_home = ml_pred.get("predicted_home_score", 4.0)
        ml_away = ml_pred.get("predicted_away_score", 4.0)
        ml_total = ml_pred.get("predicted_total", 8.0)
        
        final_home = self.ml_weight * ml_home + self.rules_weight * rules_home
        final_away = self.ml_weight * ml_away + self.rules_weight * rules_away
        final_total = final_home + final_away
        
        rules_home_prob = rules_pred.get("home_win_probability", 50) / 100
        ml_home_prob = ml_pred.get("home_win_probability", 50) / 100
        
        final_home_prob = self.ml_weight * ml_home_prob + self.rules_weight * rules_home_prob
        final_away_prob = 1 - final_home_prob
        
        final_home = round(max(1.0, min(10.0, final_home)), 1)
        final_away = round(max(1.0, min(10.0, final_away)), 1)
        final_total = round(max(3.0, min(15.0, final_total)), 1)
        
        combined = rules_pred.copy()
        combined["predicted_home_score"] = final_home
        combined["predicted_away_score"] = final_away
        combined["predicted_total"] = final_total
        combined["home_win_probability"] = round(final_home_prob * 100, 1)
        combined["away_win_probability"] = round(final_away_prob * 100, 1)
        combined["favorite"] = "Home" if final_home_prob > final_away_prob else "Away"
        combined["ml_weight_used"] = self.ml_weight
        combined["rules_weight_used"] = self.rules_weight
        
        return combined
    
    def is_ml_available(self) -> bool:
        """Verifica si los modelos ML están disponibles"""
        return self.use_ml and self.ml_models is not None


hybrid_predictor = HybridPredictor()