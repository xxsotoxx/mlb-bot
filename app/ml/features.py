"""
Feature Engineering for MLB Predictions
Transforma estadísticas crudas en vectores de features para ML
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime, date
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GameFeatures:
    """Features normalizados para un juego"""
    game_id: int
    game_date: date
    
    home_team_id: int
    away_team_id: int
    
    home_runs_scored_avg: float
    home_runs_allowed_avg: float
    home_win_pct: float
    home_pythagorean_pct: float
    
    away_runs_scored_avg: float
    away_runs_allowed_avg: float
    away_win_pct: float
    away_pythagorean_pct: float
    
    home_pitcher_era: float
    home_pitcher_fip: float
    home_pitcher_xfip: float
    home_pitcher_siera: float
    home_pitcher_k_per_9: float
    home_pitcher_bb_per_9: float
    home_pitcher_hr_per_9: float
    home_pitcher_whip: float
    home_pitcher_ip: float
    
    away_pitcher_era: float
    away_pitcher_fip: float
    away_pitcher_xfip: float
    away_pitcher_siera: float
    away_pitcher_k_per_9: float
    away_pitcher_bb_per_9: float
    away_pitcher_hr_per_9: float
    away_pitcher_whip: float
    away_pitcher_ip: float
    
    home_bullpen_era: float
    home_bullpen_fip: float
    home_bullpen_k_per_9: float
    
    away_bullpen_era: float
    away_bullpen_fip: float
    away_bullpen_k_per_9: float
    
    home_batting_avg: float
    home_batting_ops: float
    home_batting_woba: float
    home_batting_k_rate: float
    
    away_batting_avg: float
    away_batting_ops: float
    away_batting_woba: float
    away_batting_k_rate: float
    
    park_factor: float
    
    casino_ou_line: Optional[float] = None
    casino_ml_home: Optional[int] = None
    casino_ml_away: Optional[int] = None
    
    is_home: int = 1
    
    rest_days_home: int = 1
    rest_days_away: int = 1
    
    actual_home_runs: Optional[int] = None
    actual_away_runs: Optional[int] = None
    actual_winner: Optional[str] = None
    
    features: np.ndarray = field(init=False, repr=False)
    
    def __post_init__(self):
        self.features = self._to_vector()
    
    def _to_vector(self) -> np.ndarray:
        """Convierte todos los features a un vector normalizado"""
        values = [
            self._normalize(self.home_runs_scored_avg, 2.0, 6.0),
            self._normalize(self.home_runs_allowed_avg, 2.0, 6.0),
            self._normalize(self.home_win_pct, 0.3, 0.7),
            self._normalize(self.home_pythagorean_pct, 0.3, 0.7),
            self._normalize(self.away_runs_scored_avg, 2.0, 6.0),
            self._normalize(self.away_runs_allowed_avg, 2.0, 6.0),
            self._normalize(self.away_win_pct, 0.3, 0.7),
            self._normalize(self.away_pythagorean_pct, 0.3, 0.7),
            self._normalize(self.home_pitcher_era, 2.0, 7.0),
            self._normalize(self.home_pitcher_fip, 2.0, 7.0),
            self._normalize(self.home_pitcher_xfip, 2.0, 7.0),
            self._normalize(self.home_pitcher_siera, 2.0, 7.0),
            self._normalize(self.home_pitcher_k_per_9, 5.0, 12.0),
            self._normalize(self.home_pitcher_bb_per_9, 1.5, 5.0),
            self._normalize(self.home_pitcher_hr_per_9, 0.5, 2.5),
            self._normalize(self.home_pitcher_whip, 0.9, 1.8),
            self._normalize(self.home_pitcher_ip, 0.0, 200.0),
            self._normalize(self.away_pitcher_era, 2.0, 7.0),
            self._normalize(self.away_pitcher_fip, 2.0, 7.0),
            self._normalize(self.away_pitcher_xfip, 2.0, 7.0),
            self._normalize(self.away_pitcher_siera, 2.0, 7.0),
            self._normalize(self.away_pitcher_k_per_9, 5.0, 12.0),
            self._normalize(self.away_pitcher_bb_per_9, 1.5, 5.0),
            self._normalize(self.away_pitcher_hr_per_9, 0.5, 2.5),
            self._normalize(self.away_pitcher_whip, 0.9, 1.8),
            self._normalize(self.away_pitcher_ip, 0.0, 200.0),
            self._normalize(self.home_bullpen_era, 2.5, 6.0),
            self._normalize(self.home_bullpen_fip, 2.5, 6.0),
            self._normalize(self.home_bullpen_k_per_9, 6.0, 12.0),
            self._normalize(self.away_bullpen_era, 2.5, 6.0),
            self._normalize(self.away_bullpen_fip, 2.5, 6.0),
            self._normalize(self.away_bullpen_k_per_9, 6.0, 12.0),
            self._normalize(self.home_batting_avg, 0.200, 0.300),
            self._normalize(self.home_batting_ops, 0.600, 0.900),
            self._normalize(self.home_batting_woba, 0.280, 0.400),
            self._normalize(self.home_batting_k_rate, 10.0, 30.0),
            self._normalize(self.away_batting_avg, 0.200, 0.300),
            self._normalize(self.away_batting_ops, 0.600, 0.900),
            self._normalize(self.away_batting_woba, 0.280, 0.400),
            self._normalize(self.away_batting_k_rate, 10.0, 30.0),
            self._normalize(self.park_factor, 0.85, 1.20),
            self._normalize(self.rest_days_home, 0, 5),
            self._normalize(self.rest_days_away, 0, 5),
        ]
        return np.array(values, dtype=np.float32)
    
    @staticmethod
    def _normalize(value: float, min_val: float, max_val: float) -> float:
        """Normaliza valor a rango [0, 1]"""
        if max_val == min_val:
            return 0.5
        normalized = (value - min_val) / (max_val - min_val)
        return np.clip(normalized, 0.0, 1.0)
    
    @staticmethod
    def denormalize(normalized: float, min_val: float, max_val: float) -> float:
        """Convierte valor normalizado de vuelta a escala original"""
        return normalized * (max_val - min_val) + min_val


class FeatureEngine:
    """
    Motor de Feature Engineering
    Convierte estadísticas de equipos, pitchers, bullpen en vectores de features
    """
    
    LEAGUE_AVG_RUNS = 8.5
    
    FEATURE_NAMES = [
        "home_runs_scored_avg", "home_runs_allowed_avg", "home_win_pct", "home_pythagorean_pct",
        "away_runs_scored_avg", "away_runs_allowed_avg", "away_win_pct", "away_pythagorean_pct",
        "home_pitcher_era", "home_pitcher_fip", "home_pitcher_xfip", "home_pitcher_siera",
        "home_pitcher_k_per_9", "home_pitcher_bb_per_9", "home_pitcher_hr_per_9", "home_pitcher_whip",
        "home_pitcher_ip",
        "away_pitcher_era", "away_pitcher_fip", "away_pitcher_xfip", "away_pitcher_siera",
        "away_pitcher_k_per_9", "away_pitcher_bb_per_9", "away_pitcher_hr_per_9", "away_pitcher_whip",
        "away_pitcher_ip",
        "home_bullpen_era", "home_bullpen_fip", "home_bullpen_k_per_9",
        "away_bullpen_era", "away_bullpen_fip", "away_bullpen_k_per_9",
        "home_batting_avg", "home_batting_ops", "home_batting_woba", "home_batting_k_rate",
        "away_batting_avg", "away_batting_ops", "away_batting_woba", "away_batting_k_rate",
        "park_factor", "rest_days_home", "rest_days_away"
    ]
    
    def __init__(self):
        self.feature_cache = {}
    
    def compute_features(
        self,
        game_id: int,
        game_date: date,
        home_team_id: int,
        away_team_id: int,
        home_team_stats: Dict,
        away_team_stats: Dict,
        home_pitcher_stats: Dict,
        away_pitcher_stats: Dict,
        home_bullpen_stats: Dict = None,
        away_bullpen_stats: Dict = None,
        home_batting_stats: Dict = None,
        away_batting_stats: Dict = None,
        park_factor: float = 1.0,
        casino_lines: Dict = None,
        rest_days_home: int = 1,
        rest_days_away: int = 1,
        actual_results: Dict = None
    ) -> GameFeatures:
        """Compute features para un juego"""
        
        if home_bullpen_stats is None:
            home_bullpen_stats = self._default_bullpen()
        if away_bullpen_stats is None:
            away_bullpen_stats = self._default_bullpen()
        if home_batting_stats is None:
            home_batting_stats = self._default_batting()
        if away_batting_stats is None:
            away_batting_stats = self._default_batting()
        
        pythagorean_home = self._calculate_pythagorean_pct(
            home_team_stats.get("runs_scored_avg", 4.25),
            home_team_stats.get("runs_allowed_avg", 4.25)
        )
        pythagorean_away = self._calculate_pythagorean_pct(
            away_team_stats.get("runs_scored_avg", 4.25),
            away_team_stats.get("runs_allowed_avg", 4.25)
        )
        
        features = GameFeatures(
            game_id=game_id,
            game_date=game_date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_runs_scored_avg=home_team_stats.get("runs_scored_avg", 4.25),
            home_runs_allowed_avg=home_team_stats.get("runs_allowed_avg", 4.25),
            home_win_pct=home_team_stats.get("win_pct", 0.5),
            home_pythagorean_pct=pythagorean_home,
            away_runs_scored_avg=away_team_stats.get("runs_scored_avg", 4.25),
            away_runs_allowed_avg=away_team_stats.get("runs_allowed_avg", 4.25),
            away_win_pct=away_team_stats.get("win_pct", 0.5),
            away_pythagorean_pct=pythagorean_away,
            home_pitcher_era=home_pitcher_stats.get("era", 4.50),
            home_pitcher_fip=home_pitcher_stats.get("fip", 4.50),
            home_pitcher_xfip=home_pitcher_stats.get("xFIP", 4.50),
            home_pitcher_siera=home_pitcher_stats.get("SIERA", 4.50),
            home_pitcher_k_per_9=home_pitcher_stats.get("k_per_9", 8.5),
            home_pitcher_bb_per_9=home_pitcher_stats.get("bb_per_9", 3.2),
            home_pitcher_hr_per_9=home_pitcher_stats.get("hr_per_9", 1.2),
            home_pitcher_whip=home_pitcher_stats.get("whip", 1.30),
            home_pitcher_ip=home_pitcher_stats.get("ip", 50),
            away_pitcher_era=away_pitcher_stats.get("era", 4.50),
            away_pitcher_fip=away_pitcher_stats.get("fip", 4.50),
            away_pitcher_xfip=away_pitcher_stats.get("xFIP", 4.50),
            away_pitcher_siera=away_pitcher_stats.get("SIERA", 4.50),
            away_pitcher_k_per_9=away_pitcher_stats.get("k_per_9", 8.5),
            away_pitcher_bb_per_9=away_pitcher_stats.get("bb_per_9", 3.2),
            away_pitcher_hr_per_9=away_pitcher_stats.get("hr_per_9", 1.2),
            away_pitcher_whip=away_pitcher_stats.get("whip", 1.30),
            away_pitcher_ip=away_pitcher_stats.get("ip", 50),
            home_bullpen_era=home_bullpen_stats.get("era", 4.20),
            home_bullpen_fip=home_bullpen_stats.get("fip", 4.20),
            home_bullpen_k_per_9=home_bullpen_stats.get("k_per_9", 9.0),
            away_bullpen_era=away_bullpen_stats.get("era", 4.20),
            away_bullpen_fip=away_bullpen_stats.get("fip", 4.20),
            away_bullpen_k_per_9=away_bullpen_stats.get("k_per_9", 9.0),
            home_batting_avg=home_batting_stats.get("batting_avg", 0.250),
            home_batting_ops=home_batting_stats.get("ops", 0.720),
            home_batting_woba=home_batting_stats.get("woba", 0.320),
            home_batting_k_rate=home_batting_stats.get("k_rate", 20.0),
            away_batting_avg=away_batting_stats.get("batting_avg", 0.250),
            away_batting_ops=away_batting_stats.get("ops", 0.720),
            away_batting_woba=away_batting_stats.get("woba", 0.320),
            away_batting_k_rate=away_batting_stats.get("k_rate", 20.0),
            park_factor=park_factor,
            casino_ou_line=casino_lines.get("over_under_line") if casino_lines else None,
            casino_ml_home=casino_lines.get("ml_home") if casino_lines else None,
            casino_ml_away=casino_lines.get("ml_away") if casino_lines else None,
            rest_days_home=rest_days_home,
            rest_days_away=rest_days_away,
            actual_home_runs=actual_results.get("home_score") if actual_results else None,
            actual_away_runs=actual_results.get("away_score") if actual_results else None,
            actual_winner=actual_results.get("winner") if actual_results else None
        )
        
        return features
    
    def _calculate_pythagorean_pct(self, rs: float, ra: float) -> float:
        """Calcula porcentaje pitagórico de victorias"""
        try:
            if rs + ra <= 0:
                return 0.5
            exp = 1.83
            win_pct = (rs ** exp) / ((rs ** exp) + (ra ** exp))
            return round(win_pct, 3)
        except:
            return 0.5
    
    def _default_bullpen(self) -> Dict:
        return {"era": 4.20, "fip": 4.20, "k_per_9": 9.0}
    
    def _default_batting(self) -> Dict:
        return {"batting_avg": 0.250, "ops": 0.720, "woba": 0.320, "k_rate": 20.0}
    
    def create_dataset(self, games_features: List[GameFeatures]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Crea dataset de entrenamiento desde lista de features"""
        X = np.array([gf.features for gf in games_features])
        
        y_home = np.array([gf.actual_home_runs if gf.actual_home_runs is not None else 0 
                          for gf in games_features], dtype=np.float32)
        y_away = np.array([gf.actual_away_runs if gf.actual_away_runs is not None else 0 
                          for gf in games_features], dtype=np.float32)
        
        y_winner = np.array([
            0 if gf.actual_winner == "Away" 
            else 1 if gf.actual_winner == "Home" 
            else 2 for gf in games_features
        ], dtype=np.int64)
        
        return X, y_home, y_away, y_winner
    
    def get_feature_importance_names(self) -> List[str]:
        """Retorna nombres de features para interpretación"""
        return self.FEATURE_NAMES


feature_engine = FeatureEngine()