"""
Training Pipeline - Entrena los modelos ML
Separa claramente training de inference
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from pathlib import Path
import json
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TrainingPipeline:
    """
    Pipeline completo de entrenamiento
    1. Carga datos históricos (predictions + results)
    2. Compute features
    3. Entrena Poisson (home & away)
    4. Entrena Win Classifier
    5. Evalúa y guarda métricas
    """
    
    def __init__(self, models_dir: str = "models/ml"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.poisson_home = None
        self.poisson_away = None
        self.win_classifier = None
        
        self.feature_engine = None
        self.training_history = []
    
    def load_historical_data(
        self,
        predictions_with_results: List[Dict],
        min_games: int = 100
    ) -> List[Dict]:
        """
        Carga datos históricos de la base de datos
        Debe recibir predicciones que ya tienen resultados reales
        """
        logger.info(f"Loading {len(predictions_with_results)} historical games")
        
        valid_games = []
        for pred in predictions_with_results:
            if pred.get("actual_home_score") is None:
                continue
            
            game_data = {
                "game_id": pred.get("game_id"),
                "game_date": pred.get("game_date"),
                "home_team": pred.get("home_team"),
                "away_team": pred.get("away_team"),
                
                "predicted_home": pred.get("predicted_home_score"),
                "predicted_away": pred.get("predicted_away_score"),
                "predicted_total": pred.get("predicted_total"),
                
                "actual_home": pred.get("actual_home_score"),
                "actual_away": pred.get("actual_away_score"),
                "actual_total": pred.get("actual_home_score", 0) + pred.get("actual_away_score", 0),
                
                "home_team_id": pred.get("home_team_id", 0),
                "away_team_id": pred.get("away_team_id", 0),
                
                "home_team_stats": pred.get("home_team_stats", {}),
                "away_team_stats": pred.get("away_team_stats", {}),
                "home_pitcher_stats": pred.get("home_pitcher_stats", {}),
                "away_pitcher_stats": pred.get("away_pitcher_stats", {}),
                "home_bullpen_stats": pred.get("home_bullpen_stats", {}),
                "away_bullpen_stats": pred.get("away_bullpen_stats", {}),
                
                "park_factor": pred.get("park_factor", 1.0),
                "casino_lines": pred.get("casino_lines", {}),
                
                "over_line": pred.get("over_line", 8.5),
                "over_probability": pred.get("over_probability", 0.5)
            }
            
            if game_data["actual_home"] is not None:
                game_data["winner"] = "Home" if game_data["actual_home"] > game_data["actual_away"] \
                                      else "Away" if game_data["actual_away"] > game_data["actual_home"] else "Tie"
            
            valid_games.append(game_data)
        
        logger.info(f"Valid games with results: {len(valid_games)}")
        
        if len(valid_games) < min_games:
            logger.warning(f"Only {len(valid_games)} valid games, need {min_games} for training")
        
        return valid_games
    
    def compute_features_batch(
        self,
        games: List[Dict],
        feature_engine
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Compute features para todos los juegos"""
        from app.ml.features import GameFeatures
        
        game_features = []
        
        for game in games:
            game_date = game.get("game_date")
            if isinstance(game_date, str):
                game_date = datetime.fromisoformat(game_date.replace("Z", "+00:00")).date()
            
            gf = feature_engine.compute_features(
                game_id=game.get("game_id", 0),
                game_date=game_date or date.today(),
                home_team_id=game.get("home_team_id", 0),
                away_team_id=game.get("away_team_id", 0),
                home_team_stats=game.get("home_team_stats", {}),
                away_team_stats=game.get("away_team_stats", {}),
                home_pitcher_stats=game.get("home_pitcher_stats", {}),
                away_pitcher_stats=game.get("away_pitcher_stats", {}),
                home_bullpen_stats=game.get("home_bullpen_stats"),
                away_bullpen_stats=game.get("away_bullpen_stats"),
                park_factor=game.get("park_factor", 1.0),
                casino_lines=game.get("casino_lines"),
                actual_results={
                    "home_score": game.get("actual_home"),
                    "away_score": game.get("actual_away"),
                    "winner": game.get("winner")
                }
            )
            game_features.append(gf)
        
        X, y_home, y_away, y_winner = feature_engine.create_dataset(game_features)
        
        logger.info(f"Created dataset: X={X.shape}, y_home={y_home.shape}, y_away={y_away.shape}, y_winner={y_winner.shape}")
        
        return X, y_home, y_away, y_winner
    
    def train_models(
        self,
        X: np.ndarray,
        y_home: np.ndarray,
        y_away: np.ndarray,
        y_winner: np.ndarray,
        test_size: float = 0.2,
        epochs_poisson: int = 100,
        epochs_classifier: int = 100
    ) -> Dict[str, Any]:
        """Entrena todos los modelos"""
        
        X_train, X_test, y_home_train, y_home_test = train_test_split(
            X, y_home, test_size=test_size, random_state=42
        )
        _, _, y_away_train, y_away_test = train_test_split(X, y_away, test_size=test_size, random_state=42)
        _, _, y_winner_train, y_winner_test = train_test_split(X, y_winner, test_size=test_size, random_state=42)
        
        from app.ml.models.poisson_model import PoissonModel
        from app.ml.models.win_classifier import WinClassifierModel
        
        logger.info("=" * 50)
        logger.info("Training Poisson Home Model")
        logger.info("=" * 50)
        
        self.poisson_home = PoissonModel(input_dim=X.shape[1])
        self.poisson_home.train(
            X_train, y_home_train,
            X_test, y_home_test,
            epochs=epochs_poisson,
            lr=0.001,
            batch_size=32,
            patience=15
        )
        
        logger.info("=" * 50)
        logger.info("Training Poisson Away Model")
        logger.info("=" * 50)
        
        self.poisson_away = PoissonModel(input_dim=X.shape[1])
        self.poisson_away.train(
            X_train, y_away_train,
            X_test, y_away_test,
            epochs=epochs_poisson,
            lr=0.001,
            batch_size=32,
            patience=15
        )
        
        logger.info("=" * 50)
        logger.info("Training Win Classifier Model")
        logger.info("=" * 50)
        
        self.win_classifier = WinClassifierModel(input_dim=X.shape[1])
        train_result = self.win_classifier.train(
            X_train, y_winner_train,
            X_test, y_winner_test,
            epochs=epochs_classifier,
            lr=0.001,
            batch_size=32,
            patience=15
        )
        
        metrics = self.evaluate_models(X_test, y_home_test, y_away_test, y_winner_test)
        
        return {
            "status": "trained",
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "metrics": metrics,
            "classifier_epochs": train_result.get("epochs")
        }
    
    def evaluate_models(
        self,
        X_test: np.ndarray,
        y_home_test: np.ndarray,
        y_away_test: np.ndarray,
        y_winner_test: np.ndarray
    ) -> Dict[str, Any]:
        """Evalúa todos los modelos en test set"""
        
        home_preds = self.poisson_home.predict_batch(X_test)
        away_preds = self.poisson_away.predict_batch(X_test)
        
        home_mae = np.mean(np.abs(home_preds - y_home_test))
        away_mae = np.mean(np.abs(away_preds - y_away_test))
        total_mae = np.mean(np.abs((home_preds + away_preds) - (y_home_test + y_away_test)))
        
        win_probs = self.win_classifier.predict_batch_proba(X_test)
        win_preds = np.argmax(win_probs, axis=1)
        
        ml_accuracy = np.mean(win_preds == y_winner_test)
        
        logger.info("=" * 50)
        logger.info("MODEL EVALUATION")
        logger.info("=" * 50)
        logger.info(f"Home Runs MAE: {home_mae:.2f}")
        logger.info(f"Away Runs MAE: {away_mae:.2f}")
        logger.info(f"Total Runs MAE: {total_mae:.2f}")
        logger.info(f"Win Prediction Accuracy: {ml_accuracy:.2%}")
        logger.info("=" * 50)
        
        return {
            "home_mae": round(home_mae, 2),
            "away_mae": round(away_mae, 2),
            "total_mae": round(total_mae, 2),
            "win_accuracy": round(ml_accuracy, 3)
        }
    
    def save_models(self, version: str = None) -> Dict[str, str]:
        """Guarda todos los modelos con version"""
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        model_paths = {}
        
        home_path = self.models_dir / f"poisson_home_{version}.pt"
        self.poisson_home.save(str(home_path))
        model_paths["poisson_home"] = str(home_path)
        
        away_path = self.models_dir / f"poisson_away_{version}.pt"
        self.poisson_away.save(str(away_path))
        model_paths["poisson_away"] = str(away_path)
        
        classifier_path = self.models_dir / f"win_classifier_{version}.pt"
        self.win_classifier.save(str(classifier_path))
        model_paths["win_classifier"] = str(classifier_path)
        
        meta_path = self.models_dir / f"training_meta_{version}.json"
        meta = {
            "version": version,
            "timestamp": datetime.now().isoformat(),
            "poisson_home": str(home_path),
            "poisson_away": str(away_path),
            "win_classifier": str(classifier_path)
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        
        logger.info(f"Models saved with version: {version}")
        
        return model_paths
    
    def load_models(self, version: str) -> bool:
        """Carga modelos desde disco"""
        from app.ml.models.poisson_model import PoissonModel
        from app.ml.models.win_classifier import WinClassifierModel
        
        try:
            meta_path = self.models_dir / f"training_meta_{version}.json"
            with open(meta_path) as f:
                meta = json.load(f)
            
            self.poisson_home = PoissonModel()
            self.poisson_home.load(meta["poisson_home"])
            
            self.poisson_away = PoissonModel()
            self.poisson_away.load(meta["poisson_away"])
            
            self.win_classifier = WinClassifierModel()
            self.win_classifier.load(meta["win_classifier"])
            
            logger.info(f"Models loaded from version: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            return False


training_pipeline = TrainingPipeline()