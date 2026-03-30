"""
Motor de Predicciones de Apuestas MLB
Usa sabermetría para generar predicciones de Money Line y Over/Under
"""
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from .mlb_api import mlb_client, fetch_game_details, get_team_statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionEngine:
    """Motor de predicciones usando métricas sabermétricas"""
    
    LEAGUE_AVG_RUNS = 8.5
    
    def __init__(self):
        self.team_cache = {}
        self.pitcher_cache = {}
    
    async def get_team_recent_stats(self, team_id: int) -> Dict[str, float]:
        """Calcula estadísticas recientes de un equipo (últimos 15 partidos)"""
        if team_id in self.team_cache:
            return self.team_cache[team_id]
        
        try:
            games = await mlb_client.get_recent_games(team_id, games=15)
            
            runs_scored = []
            runs_allowed = []
            wins = 0
            losses = 0
            
            for game in games:
                linescore = game.get("linescore", {})
                if not linescore:
                    continue
                
                teams = game.get("teams", {})
                
                if teams.get("home", {}).get("team", {}).get("id") == team_id:
                    runs_scored.append(linescore.get("teams", {}).get("home", {}).get("runs", 0))
                    runs_allowed.append(linescore.get("teams", {}).get("away", {}).get("runs", 0))
                    home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
                    away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
                    if home_score > away_score:
                        wins += 1
                    else:
                        losses += 1
                elif teams.get("away", {}).get("team", {}).get("id") == team_id:
                    runs_scored.append(linescore.get("teams", {}).get("away", {}).get("runs", 0))
                    runs_allowed.append(linescore.get("teams", {}).get("home", {}).get("runs", 0))
                    away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
                    home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
                    if away_score > home_score:
                        wins += 1
                    else:
                        losses += 1
            
            avg_scored = sum(runs_scored) / len(runs_scored) if runs_scored else self.LEAGUE_AVG_RUNS / 2
            avg_allowed = sum(runs_allowed) / len(runs_allowed) if runs_allowed else self.LEAGUE_AVG_RUNS / 2
            
            total_games = wins + losses
            
            stats = {
                "runs_scored_avg": round(avg_scored, 2),
                "runs_allowed_avg": round(avg_allowed, 2),
                "wins": wins,
                "losses": losses,
                "win_pct": round(wins / total_games, 3) if total_games > 0 else 0.5,
                "games_played": len(runs_scored)
            }
            
            logger.info(f"Team {team_id}: {wins}-{losses} record, {avg_scored:.2f} RA, {avg_allowed:.2f} RC, {len(runs_scored)} games found")
            
            self.team_cache[team_id] = stats
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del equipo {team_id}: {e}")
            default_stats = {
                "runs_scored_avg": self.LEAGUE_AVG_RUNS / 2,
                "runs_allowed_avg": self.LEAGUE_AVG_RUNS / 2,
                "wins": 0,
                "losses": 0,
                "win_pct": 0.5,
                "games_played": 0
            }
            logger.warning(f"Using default stats for team {team_id}: {default_stats}")
            return default_stats
    
    async def get_pitcher_stats(self, pitcher_id: int) -> Dict[str, float]:
        """Obtiene estadísticas de un pitcher"""
        if not pitcher_id:
            return self._default_pitcher_stats()
        
        if pitcher_id in self.pitcher_cache:
            return self.pitcher_cache[pitcher_id]
        
        try:
            stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching")
            
            if not stats_data or "stats" not in stats_data:
                logger.warning(f"No stats data for pitcher {pitcher_id}, trying career stats")
                stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching", use_career=True)
            
            if not stats_data or "stats" not in stats_data:
                return self._default_pitcher_stats()
            
            splits = stats_data.get("stats", [{}])[0].get("splits", [])
            if not splits:
                logger.warning(f"No splits for pitcher {pitcher_id}, trying career stats")
                stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching", use_career=True)
                splits = stats_data.get("stats", [{}])[0].get("splits", []) if stats_data else []
            
            if not splits:
                return self._default_pitcher_stats()
            
            stat = splits[0].get("stat", {})
            
            stats = {
                "era": float(stat.get("era", 4.50)),
                "fip": float(stat.get("fip", 4.50)),
                "whip": float(stat.get("whip", 1.30)),
                "wins": int(stat.get("wins", 0)),
                "losses": int(stat.get("losses", 0)),
                "games": int(stat.get("games", 0)),
                "games_pitched": int(stat.get("gamesPitched", 0)),
                "strikeouts": int(stat.get("strikeouts", 0)),
                "walks": int(stat.get("walks", 0)),
                "innings_pitched": float(stat.get("inningsPitched", 0)),
                "hr": int(stat.get("homeRuns", 0)),
                "hbp": int(stat.get("hitBatsmen", 0)),
                "bba": int(stat.get("baseOnBallsPlus", 0))
            }
            
            self.pitcher_cache[pitcher_id] = stats
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas del pitcher {pitcher_id}: {e}")
            logger.warning(f"Using default pitcher stats for pitcher {pitcher_id}")
            return self._default_pitcher_stats()
    
    def _default_pitcher_stats(self) -> Dict[str, float]:
        """Estadísticas por defecto para pitcher cuando no hay datos"""
        return {
            "era": 4.50,
            "fip": 4.50,
            "whip": 1.30,
            "wins": 0,
            "losses": 0,
            "games": 0,
            "games_pitched": 0,
            "strikeouts": 0,
            "walks": 0,
            "innings_pitched": 0,
            "hr": 0,
            "hbp": 0,
            "bba": 0
        }
    
    def calculate_park_factor(self, team_id: int, venue: str = "") -> float:
        """Calcula factor de parque (simplificado)"""
        parks = {
            "Yankee Stadium": 1.15,
            "Fenway Park": 1.10,
            "Coors Field": 1.12,
            "Babe Ruth Field": 1.10,
            "Petco Park": 0.95,
            "Oracle Park": 0.95,
            "Dodger Stadium": 0.98,
            "Wrigley Field": 1.02,
            "Minute Maid Park": 1.02,
            "T-Mobile Park": 0.92,
            "Angel Stadium": 0.98,
            "Safeco Field": 0.92,
            "Target Field": 0.97,
            "Citizens Bank Park": 1.05
        }
        
        for park, factor in parks.items():
            if park.lower() in venue.lower() or venue.lower() in park.lower():
                return factor
        
        return 1.0
    
    def predict_total_runs(
        self,
        home_team_stats: Dict,
        away_team_stats: Dict,
        home_pitcher_stats: Dict,
        away_pitcher_stats: Dict,
        park_factor: float = 1.0
    ) -> Tuple[float, float]:
        """Predice el total de carreras esperado"""
        home_avg = home_team_stats.get("runs_scored_avg", self.LEAGUE_AVG_RUNS / 2)
        away_avg = away_team_stats.get("runs_scored_avg", self.LEAGUE_AVG_RUNS / 2)
        
        home_def = home_team_stats.get("runs_allowed_avg", self.LEAGUE_AVG_RUNS / 2)
        away_def = away_team_stats.get("runs_allowed_avg", self.LEAGUE_AVG_RUNS / 2)
        
        home_era = home_pitcher_stats.get("fip", 4.50)
        away_era = away_pitcher_stats.get("fip", 4.50)
        
        home_expected_runs = (home_avg + away_def) / 2
        away_expected_runs = (away_avg + home_def) / 2
        
        pitcher_adjustment = (4.50 - home_era) / 9 * 1.5 + (4.50 - away_era) / 9 * 1.5
        
        total = (home_expected_runs + away_expected_runs) * park_factor + pitcher_adjustment * 0.3
        
        total = max(5.0, min(15.0, total))
        
        if total < 7:
            over_line = 7.0
        elif total < 8:
            over_line = 7.5
        elif total < 9:
            over_line = 8.5
        elif total < 10:
            over_line = 9.5
        else:
            over_line = 10.5
        
        return round(total, 1), over_line
    
    def predict_money_line(
        self,
        home_team_stats: Dict,
        away_team_stats: Dict,
        home_pitcher_stats: Dict,
        away_pitcher_stats: Dict,
        is_home_team_home: bool = True
    ) -> Tuple[str, float, float]:
        """Predice el ganador y probabilidades"""
        home_win_pct = home_team_stats.get("win_pct", 0.5)
        away_win_pct = away_team_stats.get("win_pct", 0.5)
        
        home_fip = home_pitcher_stats.get("fip", 4.50)
        away_fip = away_pitcher_stats.get("fip", 4.50)
        
        home_era = home_pitcher_stats.get("era", 4.50)
        away_era = away_pitcher_stats.get("era", 4.50)
        
        home_pitcher_factor = (4.50 - home_fip) / 9
        away_pitcher_factor = (4.50 - away_fip) / 9
        
        home_strength = home_win_pct * 0.3 + (1 - home_era / 5) * 0.4 + home_pitcher_factor * 0.3
        away_strength = away_win_pct * 0.3 + (1 - away_era / 5) * 0.4 + away_pitcher_factor * 0.3
        
        if is_home_team_home:
            home_strength += 0.03
        
        total_strength = home_strength + away_strength
        home_prob = home_strength / total_strength if total_strength > 0 else 0.5
        away_prob = away_strength / total_strength if total_strength > 0 else 0.5
        
        home_prob = max(0.1, min(0.9, home_prob))
        away_prob = 1 - home_prob
        
        favorite = "Home" if home_prob > away_prob else "Away"
        
        return favorite, round(home_prob, 3), round(away_prob, 3)
    
    def calculate_over_probability(
        self,
        predicted_total: float,
        over_line: float
    ) -> Tuple[float, float]:
        """Calcula probabilidad de Over/Under"""
        diff = predicted_total - over_line
        
        if diff > 1:
            over_prob = 0.75
            under_prob = 0.25
        elif diff > 0.5:
            over_prob = 0.60
            under_prob = 0.40
        elif diff > 0:
            over_prob = 0.55
            under_prob = 0.45
        elif diff > -0.5:
            over_prob = 0.45
            under_prob = 0.55
        elif diff > -1:
            over_prob = 0.40
            under_prob = 0.60
        else:
            over_prob = 0.25
            under_prob = 0.75
        
        return round(over_prob, 3), round(under_prob, 3)
    
    @staticmethod
    def get_confidence_level(home_prob: float) -> str:
        """Determina el nivel de confianza de la predicción"""
        diff = abs(home_prob - 0.5)
        if diff > 0.25:
            return "high"
        elif diff > 0.12:
            return "medium"
        else:
            return "low"
    
    async def generate_prediction(self, game_info: Dict) -> Dict[str, Any]:
        """Genera una predicción completa para un partido"""
        game_id = game_info.get("game_id", 0)
        home_team_id = game_info.get("home_team_id", 0) or 0
        away_team_id = game_info.get("away_team_id", 0) or 0
        venue = game_info.get("venue", "")
        
        try:
            home_stats = await self.get_team_recent_stats(home_team_id) if home_team_id else self._default_team_stats()
            away_stats = await self.get_team_recent_stats(away_team_id) if away_team_id else self._default_team_stats()
            
            home_pitcher_id = None
            away_pitcher_id = None
            
            if game_info.get("home_probable_pitcher") and game_id:
                details = await fetch_game_details(game_id)
                if details:
                    teams = details.get("teams", {})
                    home_pitchers = teams.get("home", {}).get("pitchers") or []
                    away_pitchers = teams.get("away", {}).get("pitchers") or []
                    home_pitcher_id = home_pitchers[0] if home_pitchers else None
                    away_pitcher_id = away_pitchers[0] if away_pitchers else None
            
            home_pitcher_stats = await self.get_pitcher_stats(home_pitcher_id) if home_pitcher_id else self._default_pitcher_stats()
            away_pitcher_stats = await self.get_pitcher_stats(away_pitcher_id) if away_pitcher_id else self._default_pitcher_stats()
            
            park_factor = self.calculate_park_factor(home_team_id, venue)
            
            predicted_total, over_line = self.predict_total_runs(
                home_stats, away_stats, home_pitcher_stats, away_pitcher_stats, park_factor
            )
            
            favorite, home_prob, away_prob = self.predict_money_line(
                home_stats, away_stats, home_pitcher_stats, away_pitcher_stats
            )
            
            over_prob, under_prob = self.calculate_over_probability(predicted_total, over_line)
            
            logger.info(f"Prediction for game {game_id}: total={predicted_total}, home_prob={home_prob}, away_prob={away_prob}")
            
            home_score = round(predicted_total * home_prob)
            away_score = round(predicted_total * away_prob)
            
            logger.info(f"Raw scores before adjustment: home={home_score}, away={away_score}")
            
            if home_score + away_score != int(predicted_total):
                diff = int(predicted_total) - (home_score + away_score)
                home_score += diff
            
            confidence = self.get_confidence_level(home_prob)
            
            return {
                "game_id": game_id,
                "predicted_total": predicted_total,
                "predicted_home_score": float(home_score),
                "predicted_away_score": float(away_score),
                "favorite": favorite,
                "home_win_probability": home_prob,
                "away_win_probability": away_prob,
                "over_probability": over_prob,
                "under_probability": under_prob,
                "over_line": over_line,
                "confidence": confidence,
                "pitcher_home": game_info.get("home_probable_pitcher"),
                "pitcher_away": game_info.get("away_probable_pitcher"),
                "park_factor": park_factor,
                "home_team_stats": home_stats,
                "away_team_stats": away_stats,
                "home_pitcher_stats": home_pitcher_stats,
                "away_pitcher_stats": away_pitcher_stats
            }
            
        except Exception as e:
            logger.error(f"Error generando predicción para game {game_id}: {e}")
            return {
                "game_id": game_id,
                "predicted_total": self.LEAGUE_AVG_RUNS,
                "predicted_home_score": 4.0,
                "predicted_away_score": 4.5,
                "favorite": game_info.get("home_team", "Home"),
                "home_win_probability": 0.5,
                "away_win_probability": 0.5,
                "over_probability": 0.5,
                "under_probability": 0.5,
                "over_line": 8.5,
                "confidence": "low",
                "error": str(e)
            }
    
    def _default_team_stats(self) -> Dict[str, float]:
        """Estadísticas por defecto para equipo"""
        return {
            "runs_scored_avg": self.LEAGUE_AVG_RUNS / 2,
            "runs_allowed_avg": self.LEAGUE_AVG_RUNS / 2,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.5,
            "games_played": 0
        }


prediction_engine = PredictionEngine()
