"""
Motor de Predicciones Avanzado con Sabermetría Completa
Incluye: Bullpen stats, métricas avanzadas (xFIP, SIERA), park factors
"""
import logging
import asyncio
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from .mlb_api import mlb_client, fetch_game_details, get_team_statistics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedSabermetricPredictor:
    """Predictor con sabermetría avanzada y análisis de bullpen"""
    
    LEAGUE_AVG_RUNS = 8.5
    AVG_K_PER_9 = 8.5
    AVG_BB_PER_9 = 3.2
    
    def __init__(self):
        self.team_cache = {}
        self.pitcher_cache = {}
        self.bullpen_cache = {}
        self.batting_cache = {}
        self.casino_lines_cache = {}
    
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
                team_data = None
                
                if teams.get("home", {}).get("team", {}).get("id") == team_id:
                    team_data = "home"
                elif teams.get("away", {}).get("team", {}).get("id") == team_id:
                    team_data = "away"
                
                if team_data:
                    if team_data == "home":
                        runs_scored.append(linescore.get("teams", {}).get("home", {}).get("runs", 0))
                        runs_allowed.append(linescore.get("teams", {}).get("away", {}).get("runs", 0))
                        home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
                        away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
                    else:
                        runs_scored.append(linescore.get("teams", {}).get("away", {}).get("runs", 0))
                        runs_allowed.append(linescore.get("teams", {}).get("home", {}).get("runs", 0))
                        away_score = linescore.get("teams", {}).get("away", {}).get("runs", 0)
                        home_score = linescore.get("teams", {}).get("home", {}).get("runs", 0)
                    
                    if (team_data == "home" and home_score > away_score) or \
                       (team_data == "away" and away_score > home_score):
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
                "games_played": len(runs_scored),
                "pythagorean_record": self._calculate_pythagorean(runs_scored, runs_allowed)
            }
            
            logger.info(f"Team {team_id}: {wins}-{losses} ({len(runs_scored)} games), RA: {avg_scored:.2f}, RC: {avg_allowed:.2f}")
            
            self.team_cache[team_id] = stats
            return stats
            
        except Exception as e:
            logger.error(f"Error getting team stats {team_id}: {e}")
            return self._default_team_stats()
    
    def _calculate_pythagorean(self, runs_scored: List, runs_allowed: List) -> Dict[str, float]:
        """Calcula registro pitagórico"""
        try:
            rs = sum(runs_scored)
            ra = sum(runs_allowed)
            if rs + ra > 0:
                exp = 1.83
                win_pct = (rs ** exp) / ((rs ** exp) + (ra ** exp))
                total_games = len(runs_scored)
                expected_wins = win_pct * total_games
                expected_losses = total_games - expected_wins
                return {
                    "expected_wins": round(expected_wins, 1),
                    "expected_losses": round(expected_losses, 1),
                    "pythagorean_win_pct": round(win_pct, 3)
                }
        except:
            pass
        return {"expected_wins": 0, "expected_losses": 0, "pythagorean_win_pct": 0.5}
    
    async def get_bullpen_stats(self, team_id: int) -> Dict[str, float]:
        """Obtiene estadísticas del bullpen"""
        if team_id in self.bullpen_cache:
            return self.bullpen_cache[team_id]
        
        try:
            stats = await mlb_client.get_bullpen_stats(team_id)
            self.bullpen_cache[team_id] = stats
            logger.info(f"Bullpen team {team_id}: ERA {stats.get('era', 0):.2f}, FIP {stats.get('fip', 0):.2f}, K/9 {stats.get('k_per_9', 0):.1f}")
            return stats
        except Exception as e:
            logger.error(f"Error getting bullpen stats {team_id}: {e}")
            return mlb_client._default_bullpen_stats()
    
    async def get_team_batting_stats(self, team_id: int) -> Dict[str, float]:
        """Obtiene estadísticas de bateo de un equipo"""
        if team_id in self.batting_cache:
            return self.batting_cache[team_id]
        
        try:
            stats = await mlb_client.get_team_batting_stats(team_id)
            self.batting_cache[team_id] = stats
            logger.info(f"Batting team {team_id}: AVG {stats.get('batting_avg', 0):.3f}, OPS {stats.get('ops', 0):.3f}, K% {stats.get('k_rate', 0):.1f}%")
            return stats
        except Exception as e:
            logger.error(f"Error getting batting stats {team_id}: {e}")
            return mlb_client._default_batting_stats()
    
    async def get_pitcher_stats(self, pitcher_id: int) -> Dict[str, float]:
        """Obtiene estadísticas avanzadas de un pitcher"""
        if not pitcher_id:
            return self._default_pitcher_stats()
        
        if pitcher_id in self.pitcher_cache:
            return self.pitcher_cache[pitcher_id]
        
        try:
            stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching")
            
            if not stats_data or "stats" not in stats_data:
                logger.warning(f"No season stats for pitcher {pitcher_id}, trying career")
                stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching", use_career=True)
            
            if not stats_data or "stats" not in stats_data:
                return self._default_pitcher_stats()
            
            stats_list = stats_data.get("stats", [])
            if not stats_list:
                logger.warning(f"No stats list for pitcher {pitcher_id}, trying career")
                stats_data = await mlb_client.get_player_stats(pitcher_id, "pitching", use_career=True)
                stats_list = stats_data.get("stats", []) if stats_data else []
            
            splits = []
            if stats_list and len(stats_list) > 0:
                splits = stats_list[0].get("splits", [])
            
            if not splits:
                return self._default_pitcher_stats()
            
            stat = splits[0].get("stat", {})
            ip = float(stat.get("inningsPitched", 0))
            
            k = int(stat.get("strikeouts", 0))
            bb = int(stat.get("baseOnBalls", 0))
            h = int(stat.get("hits", 0))
            hr = int(stat.get("homeRuns", 0))
            runs = int(stat.get("runs", 0))
            hbp = int(stat.get("hitBatsmen", 0))
            ibb = int(stat.get("intentionalWalks", 0))
            
            stats = {
                "era": float(stat.get("era", 4.50)),
                "fip": float(stat.get("fip", 4.50)),
                "whip": float(stat.get("whip", 1.30)),
                "k": k,
                "bb": bb,
                "h": h,
                "hr": hr,
                "ip": ip,
                "wins": int(stat.get("wins", 0)),
                "losses": int(stat.get("losses", 0)),
                "games": int(stat.get("games", 0)),
                "games_started": int(stat.get("gamesStarted", 0)),
                "hbp": hbp,
                "ibb": ibb,
            }
            
            if ip > 0:
                stats["k_per_9"] = round(k / ip * 9, 2)
                stats["bb_per_9"] = round(bb / ip * 9, 2)
                stats["k_bb_ratio"] = round(k / bb, 2) if bb > 0 else float(k)
                stats["hr_per_9"] = round(hr / ip * 9, 2)
                stats["h_per_9"] = round(h / ip * 9, 2)
                stats["k_percent"] = round(k / (k + bb) * 100, 1) if (k + bb) > 0 else 0
                stats["bb_percent"] = round(bb / (k + bb) * 100, 1) if (k + bb) > 0 else 0
                stats["xFIP"] = self._calculate_xFIP(stats)
                stats["SIERA"] = self._calculate_SIERA(stats)
                stats["FIP_minus"] = self._calculate_FIP_minus(stats)
            else:
                stats["k_per_9"] = 0
                stats["bb_per_9"] = 0
                stats["k_bb_ratio"] = 0
                stats["hr_per_9"] = 0
                stats["h_per_9"] = 0
                stats["k_percent"] = 0
                stats["bb_percent"] = 0
                stats["xFIP"] = 4.50
                stats["SIERA"] = 4.50
                stats["FIP_minus"] = 100
            
            stats["is_starter"] = stats.get("games_started", 0) > stats.get("games", 0) / 2
            
            self.pitcher_cache[pitcher_id] = stats
            return stats
            
        except Exception as e:
            logger.error(f"Error getting pitcher {pitcher_id}: {e}")
            return self._default_pitcher_stats()
    
    def _calculate_xFIP(self, stats: Dict) -> float:
        """Calcula xFIP (Expected FIP normalizando HR/FB%)"""
        try:
            k_per_9 = stats.get("k_per_9", 8.5)
            bb_per_9 = stats.get("bb_per_9", 3.2)
            league_hr_per_fb = 0.10
            constant = 3.10
            xFIP = (k_per_9 * 9 + bb_per_9 * 9 + league_hr_per_fb * 9 + constant) / 9
            return round(xFIP, 2)
        except:
            return 4.50
    
    def _calculate_SIERA(self, stats: Dict) -> float:
        """Calcula SIERA (Skill-Interactive ERA) - versión simplificada"""
        try:
            k = stats.get("k", 0)
            bb = stats.get("bb", 0)
            h = stats.get("h", 0)
            hr = stats.get("hr", 0)
            ip = stats.get("ip", 1)
            
            if ip < 1:
                return 4.50
            
            k_rate = k / ip
            bb_rate = bb / ip
            h_rate = h / ip
            hr_rate = hr / ip
            
            siera = 6.145 - 1.57 * k_rate + 0.47 * h_rate + 0.73 * (bb_rate - (k_rate * 0.12)) + 0.092 * hr_rate * -1
            return max(2.0, min(7.0, round(siera, 2)))
        except:
            return 4.50
    
    def _calculate_FIP_minus(self, stats: Dict) -> int:
        """Calcula FIP- (FIP ajustado donde 100 es promedio)"""
        try:
            fip = stats.get("fip", 4.50)
            league_fip = 4.50
            fip_minus = (fip / league_fip) * 100
            return int(round(fip_minus))
        except:
            return 100
    
    def _default_pitcher_stats(self) -> Dict[str, float]:
        """Estadísticas por defecto para pitcher"""
        return {
            "era": 4.50, "fip": 4.50, "whip": 1.30,
            "k": 0, "bb": 0, "h": 0, "hr": 0, "ip": 0,
            "wins": 0, "losses": 0, "games": 0, "games_started": 0,
            "k_per_9": 8.5, "bb_per_9": 3.2, "k_bb_ratio": 2.66,
            "hr_per_9": 1.2, "h_per_9": 8.5, "k_percent": 20, "bb_percent": 8,
            "xFIP": 4.50, "SIERA": 4.50, "FIP_minus": 100, "is_starter": True
        }
    
    def _default_team_stats(self) -> Dict[str, float]:
        """Estadísticas por defecto para equipo"""
        return {
            "runs_scored_avg": self.LEAGUE_AVG_RUNS / 2,
            "runs_allowed_avg": self.LEAGUE_AVG_RUNS / 2,
            "wins": 0, "losses": 0, "win_pct": 0.5, "games_played": 0,
            "pythagorean_record": {"expected_wins": 0, "expected_losses": 0, "pythagorean_win_pct": 0.5}
        }
    
    def calculate_park_factor(self, team_id: int, venue: str = "") -> float:
        """Calcula factor de parque detallado"""
        parks = {
            "Yankee Stadium": {"runs": 1.15, "hr": 1.25, "beta": 1.08},
            "Fenway Park": {"runs": 1.10, "hr": 1.08, "beta": 1.05},
            "Coors Field": {"runs": 1.12, "hr": 1.15, "beta": 1.10},
            "Petco Park": {"runs": 0.95, "hr": 0.90, "beta": 0.95},
            "Oracle Park": {"runs": 0.95, "hr": 0.88, "beta": 0.94},
            "Dodger Stadium": {"runs": 0.98, "hr": 1.02, "beta": 0.98},
            "Wrigley Field": {"runs": 1.02, "hr": 1.05, "beta": 1.02},
            "Minute Maid Park": {"runs": 1.02, "hr": 1.10, "beta": 1.04},
            "T-Mobile Park": {"runs": 0.92, "hr": 0.95, "beta": 0.93},
            "Angel Stadium": {"runs": 0.98, "hr": 1.00, "beta": 0.98},
            "Safeco Field": {"runs": 0.92, "hr": 0.95, "beta": 0.93},
            "Target Field": {"runs": 0.97, "hr": 1.08, "beta": 1.00},
            "Citizens Bank Park": {"runs": 1.05, "hr": 1.18, "beta": 1.08},
            "Citi Field": {"runs": 0.95, "hr": 0.92, "beta": 0.94},
            "Marlins Park": {"runs": 0.97, "hr": 1.02, "beta": 0.98},
        }
        
        for park, factors in parks.items():
            if park.lower() in venue.lower() or venue.lower() in park.lower():
                return factors["runs"]
        
        return 1.0
    
    def calculate_pitcher_matchup_score(
        self,
        home_starter: Dict,
        away_starter: Dict,
        home_bullpen: Dict,
        away_bullpen: Dict,
        home_offense: Dict,
        away_offense: Dict,
        home_batting: Dict,
        away_batting: Dict,
        park_factor: float
    ) -> Dict[str, Any]:
        """
        Calcula puntuación de enfrentamiento completo
        Incluye: Abridor vs Lineup, Bullpen, Matchup advantages, estadísticas de bateo
        """
        home_starter_era = home_starter.get("era", 4.50)
        away_starter_era = away_starter.get("era", 4.50)
        home_bp_era = home_bullpen.get("era", 4.20)
        away_bp_era = away_bullpen.get("era", 4.20)
        
        home_starter_k9 = home_starter.get("k_per_9", 8.5)
        away_starter_k9 = away_starter.get("k_per_9", 8.5)
        
        home_off_avg = home_offense.get("runs_scored_avg", 4.25)
        away_off_avg = away_offense.get("runs_scored_avg", 4.25)
        
        home_ops = home_batting.get("ops", 0.720)
        away_ops = away_batting.get("ops", 0.720)
        home_k_rate = home_batting.get("k_rate", 20.0)
        away_k_rate = away_batting.get("k_rate", 20.0)
        home_woba = home_batting.get("woba", 0.320)
        away_woba = away_batting.get("woba", 0.320)
        
        starter_weight = 0.55
        bullpen_weight = 0.20
        offense_weight = 0.15
        batting_weight = 0.10
        
        home_pitching_era = home_starter_era * starter_weight + home_bp_era * bullpen_weight
        away_pitching_era = away_starter_era * starter_weight + away_bp_era * bullpen_weight
        
        league_era = 4.50
        
        home_pitching_factor = max(0.7, min(1.3, league_era / home_pitching_era))
        away_pitching_factor = max(0.7, min(1.3, league_era / away_pitching_era))
        
        home_offense_factor = home_off_avg / 4.25
        away_offense_factor = away_off_avg / 4.25
        
        ops_factor_home = home_ops / 0.720
        ops_factor_away = away_ops / 0.720
        
        k_matchup_home = 1.0 - (away_starter_k9 / 20.0 - home_k_rate / 20.0) * 0.05
        k_matchup_away = 1.0 - (home_starter_k9 / 20.0 - away_k_rate / 20.0) * 0.05
        
        home_expected_runs = (away_off_avg * away_offense_factor * home_pitching_factor * ops_factor_home * k_matchup_home + 
                            home_off_avg * home_offense_factor * away_pitching_factor) / 2
        
        away_expected_runs = (home_off_avg * home_offense_factor * away_pitching_factor * ops_factor_away * k_matchup_away + 
                            away_off_avg * away_offense_factor * home_pitching_factor) / 2
        
        park_adjustment = (park_factor - 1.0) * 2
        
        home_expected_runs = max(2.0, min(8.0, home_expected_runs * park_factor + park_adjustment * 0.3))
        away_expected_runs = max(2.0, min(8.0, away_expected_runs + park_adjustment * 0.1))
        
        total_runs = home_expected_runs + away_expected_runs
        total_runs = max(5.0, min(12.0, total_runs))
        
        home_ratio = home_expected_runs / total_runs if total_runs > 0 else 0.5
        
        home_win_pct = home_offense.get("win_pct", 0.5)
        away_win_pct = away_offense.get("win_pct", 0.5)
        
        home_prob = (home_ratio * 0.6 + home_win_pct * 0.3 + (home_ops / 1.4) * 0.1) * home_pitching_factor
        away_prob = ((1 - home_ratio) * 0.6 + away_win_pct * 0.3 + (away_ops / 1.4) * 0.1) * away_pitching_factor
        
        total_strength = home_prob + away_prob
        home_prob = home_prob / total_strength if total_strength > 0 else 0.5
        away_prob = 1 - home_prob
        
        home_prob = max(0.3, min(0.7, home_prob))
        away_prob = 1 - home_prob
        
        matchup_analysis = {
            "home_starter_era": home_starter_era,
            "away_starter_era": away_starter_era,
            "starter_advantage": "Home" if home_starter_era < away_starter_era else "Away",
            "starter_era_diff": round(abs(home_starter_era - away_starter_era), 2),
            "home_bullpen_era": home_bp_era,
            "away_bullpen_era": away_bp_era,
            "bullpen_advantage": "Home" if home_bp_era < away_bp_era else "Away",
            "bullpen_era_diff": round(abs(home_bp_era - away_bp_era), 2),
            "home_starter_xFIP": home_starter.get("xFIP", 4.50),
            "away_starter_xFIP": away_starter.get("xFIP", 4.50),
            "home_starter_SIERA": home_starter.get("SIERA", 4.50),
            "away_starter_SIERA": away_starter.get("SIERA", 4.50),
            "home_starter_K9": home_starter.get("k_per_9", 8.5),
            "away_starter_K9": away_starter.get("k_per_9", 8.5),
            "home_bullpen_K9": home_bullpen.get("k_per_9", 8.5),
            "away_bullpen_K9": away_bullpen.get("k_per_9", 8.5),
            "home_batting_avg": home_batting.get("batting_avg", 0.250),
            "away_batting_avg": away_batting.get("batting_avg", 0.250),
            "home_ops": home_ops,
            "away_ops": away_ops,
            "ops_advantage": "Home" if home_ops > away_ops else "Away",
            "ops_diff": round(abs(home_ops - away_ops), 3),
            "home_k_rate": home_k_rate,
            "away_k_rate": away_k_rate,
            "home_woba": home_woba,
            "away_woba": away_woba,
            "home_iso": home_batting.get("iso", 0.150),
            "away_iso": away_batting.get("iso", 0.150),
            "home_bb_rate": home_batting.get("bb_rate", 8.0),
            "away_bb_rate": away_batting.get("bb_rate", 8.0),
        }
        
        return {
            "home_expected_runs": round(home_expected_runs, 1),
            "away_expected_runs": round(away_expected_runs, 1),
            "total_runs": round(total_runs, 1),
            "home_win_prob": round(home_prob, 3),
            "away_win_prob": round(away_prob, 3),
            "park_factor": park_factor,
            "matchup": matchup_analysis
        }
    
    def _evaluate_pitcher(self, pitcher: Dict, opponent: Dict) -> float:
        """Evalúa rendimiento de un pitcher contra un oponente"""
        if not pitcher or not opponent:
            return 4.25
        
        fip = pitcher.get("fip", 4.50)
        xfip = pitcher.get("xFIP", fip)
        k_per_9 = pitcher.get("k_per_9", 8.5)
        bb_per_9 = pitcher.get("bb_per_9", 3.2)
        
        opponent_avg = opponent.get("runs_scored_avg", 4.25)
        
        pitcher_quality = 5.0 - (xfip * 0.8 + fip * 0.2)
        
        k_bonus = (k_per_9 - self.AVG_K_PER_9) * 0.1
        bb_penalty = (bb_per_9 - self.AVG_BB_PER_9) * 0.1
        
        matchup_factor = 5.0 - opponent_avg * 0.15
        
        score = pitcher_quality + k_bonus - bb_penalty + matchup_factor
        
        return max(2.0, min(6.0, score))
    
    def _evaluate_bullpen(self, bullpen: Dict, opponent: Dict) -> float:
        """Evalúa rendimiento del bullpen contra un oponente"""
        if not bullpen:
            return 4.25
        
        fip = bullpen.get("fip", 4.50)
        k_per_9 = bullpen.get("k_per_9", 8.0)
        
        opponent_avg = opponent.get("runs_scored_avg", 4.25)
        
        quality = 5.0 - fip * 0.85
        k_bonus = (k_per_9 - 8.0) * 0.08
        matchup = 5.0 - opponent_avg * 0.12
        
        score = quality + k_bonus + matchup
        
        return max(2.5, min(5.5, score))
    
    def determine_over_line(self, total_runs: float) -> float:
        """Determina línea Over/Under"""
        if total_runs < 6.5:
            return 6.5
        elif total_runs < 7.5:
            return 7.0
        elif total_runs < 8.5:
            return 8.0
        elif total_runs < 9.5:
            return 9.0
        elif total_runs < 10.5:
            return 10.0
        elif total_runs < 11.5:
            return 11.0
        else:
            return 12.0
    
    def calculate_over_probability(self, predicted_total: float, over_line: float) -> Tuple[float, float]:
        """Calcula probabilidad de Over/Under con distribución normal"""
        import math
        
        std_dev = 2.5
        diff = predicted_total - over_line
        
        z_score = diff / std_dev
        over_prob = 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
        over_prob = max(0.15, min(0.85, over_prob))
        
        return round(over_prob, 3), round(1 - over_prob, 3)
    
    def get_confidence_info(self, home_prob: float, away_prob: float, total_runs: float) -> Dict[str, Any]:
        """
        Calcula información de confianza basada en la diferencia de probabilidad entre equipos.
        La confianza indica qué tan "seguro" está el modelo sobre quién ganará.
        
        - diff > 0.20 (20%): Alta confianza - un equipo claramente superior
        - diff > 0.10 (10%): Media confianza - ligera ventaja
        - diff < 0.10: Baja confianza - equipos muy parejos
        """
        diff = abs(home_prob - away_prob)
        
        if diff > 0.20:
            level = "high"
            spanish = "ALTA"
            description = "Un equipo tiene clara ventaja"
        elif diff > 0.15:
            level = "medium"
            spanish = "MEDIA"
            description = "Ligera ventaja para el favorito"
        elif diff > 0.08:
            level = "medium"
            spanish = "MEDIA-BAJA"
            description = "Partido parejo, slight ventaja"
        else:
            level = "low"
            spanish = "BAJA"
            description = "Partido muy parejo"
        
        confidence_pct = 50 + (diff * 100 * 1.5)
        confidence_pct = max(50, min(90, confidence_pct))
        
        return {
            "level": level,
            "spanish": spanish,
            "percentage": round(confidence_pct, 1),
            "description": description,
            "diff": round(diff * 100, 1)
        }
    
    async def generate_prediction(self, game_info: Dict) -> Dict[str, Any]:
        """Genera predicción completa con sabermetría avanzada"""
        game_id = game_info.get("game_id", 0)
        home_team_id = game_info.get("home_team_id", 0) or 0
        away_team_id = game_info.get("away_team_id", 0) or 0
        venue = game_info.get("venue", "")
        home_team_name = game_info.get("home_team", "Home")
        away_team_name = game_info.get("away_team", "Away")
        
        try:
            home_stats = await self.get_team_recent_stats(home_team_id) if home_team_id else self._default_team_stats()
            away_stats = await self.get_team_recent_stats(away_team_id) if away_team_id else self._default_team_stats()
            
            home_bullpen = await self.get_bullpen_stats(home_team_id) if home_team_id else {}
            away_bullpen = await self.get_bullpen_stats(away_team_id) if away_team_id else {}
            
            home_batting = await self.get_team_batting_stats(home_team_id) if home_team_id else mlb_client._default_batting_stats()
            away_batting = await self.get_team_batting_stats(away_team_id) if away_team_id else mlb_client._default_batting_stats()
            
            home_pitcher_id = None
            away_pitcher_id = None
            
            if game_id:
                try:
                    details = await fetch_game_details(game_id)
                    if details and isinstance(details, dict):
                        teams = details.get("teams", {})
                        if isinstance(teams, dict):
                            home_pitchers_data = teams.get("home", {})
                            away_pitchers_data = teams.get("away", {})
                            if isinstance(home_pitchers_data, dict):
                                home_pitchers = home_pitchers_data.get("pitchers") or []
                            else:
                                home_pitchers = []
                            if isinstance(away_pitchers_data, dict):
                                away_pitchers = away_pitchers_data.get("pitchers") or []
                            else:
                                away_pitchers = []
                            home_pitcher_id = home_pitchers[0] if isinstance(home_pitchers, list) and home_pitchers else None
                            away_pitcher_id = away_pitchers[0] if isinstance(away_pitchers, list) and away_pitchers else None
                except Exception as e:
                    logger.warning(f"Error getting pitcher IDs from boxscore: {e}")
                    home_pitcher_id = None
                    away_pitcher_id = None
            
            home_starter = await self.get_pitcher_stats(home_pitcher_id) if home_pitcher_id else self._default_pitcher_stats()
            away_starter = await self.get_pitcher_stats(away_pitcher_id) if away_pitcher_id else self._default_pitcher_stats()
            
            park_factor = self.calculate_park_factor(home_team_id, venue)
            
            matchup = self.calculate_pitcher_matchup_score(
                home_starter, away_starter,
                home_bullpen, away_bullpen,
                home_stats, away_stats,
                home_batting, away_batting,
                park_factor
            )
            
            home_expected = matchup["home_expected_runs"]
            away_expected = matchup["away_expected_runs"]
            total_runs = matchup["total_runs"]
            
            home_score = round(home_expected)
            away_score = round(away_expected)
            
            if abs(home_score + away_score - total_runs) > 1:
                adjustment = round(total_runs - (home_score + away_score))
                home_score += adjustment
            
            home_score = max(1, home_score)
            away_score = max(1, away_score)
            
            over_line = self.determine_over_line(total_runs)
            over_prob, under_prob = self.calculate_over_probability(total_runs, over_line)
            
            favorite = home_team_name if home_score > away_score else away_team_name
            if home_score == away_score:
                favorite = home_team_name if matchup["home_win_prob"] >= matchup["away_win_prob"] else away_team_name
            
            if favorite == home_team_name:
                favorite_prob = round(home_score / (home_score + away_score) * 100, 1) if (home_score + away_score) > 0 else 50.0
            else:
                favorite_prob = round(away_score / (home_score + away_score) * 100, 1) if (home_score + away_score) > 0 else 50.0
            
            confidence = self.get_confidence_info(
                matchup["home_win_prob"],
                matchup["away_win_prob"],
                total_runs
            )
            
            return {
                "game_id": game_id,
                "away_team": away_team_name,
                "home_team": home_team_name,
                "predicted_away_score": float(away_score),
                "predicted_home_score": float(home_score),
                "predicted_total": total_runs,
                "predicted_favorite": favorite,
                "favorite_probability": favorite_prob,
                "home_win_probability": round(matchup["home_win_prob"] * 100, 1),
                "away_win_probability": round(matchup["away_win_prob"] * 100, 1),
                "over_line": over_line,
                "over_probability": round(over_prob * 100, 1),
                "under_probability": round(under_prob * 100, 1),
                "over_under_prediction": "OVER" if total_runs > over_line else "UNDER",
                "confidence_level": confidence["level"],
                "confidence_spanish": confidence["spanish"],
                "confidence_percentage": confidence["percentage"],
                "confidence_description": confidence.get("description", ""),
                "confidence_diff": confidence.get("diff", 0),
                "park_factor": park_factor,
                "venue": venue,
                "pitcher_home": game_info.get("home_probable_pitcher") or "TBD",
                "pitcher_away": game_info.get("away_probable_pitcher") or "TBD",
                "home_pitcher_stats": home_starter,
                "away_pitcher_stats": away_starter,
                "home_bullpen_stats": home_bullpen,
                "away_bullpen_stats": away_bullpen,
                "home_batting_stats": home_batting,
                "away_batting_stats": away_batting,
                "home_team_stats": home_stats,
                "away_team_stats": away_stats,
                "matchup_analysis": matchup["matchup"],
                "casino_line": {"ou_line": over_line, "source": "Pronóstico", "estimated": True},
                "casino_source": "Pronóstico"
            }
            
        except Exception as e:
            logger.error(f"Error generating prediction for game {game_id}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "game_id": game_id,
                "away_team": away_team_name,
                "home_team": home_team_name,
                "predicted_away_score": 4.0,
                "predicted_home_score": 4.0,
                "predicted_total": 8.0,
                "predicted_favorite": home_team_name,
                "favorite_probability": 50.0,
                "home_win_probability": 50.0,
                "away_win_probability": 50.0,
                "over_line": 8.0,
                "over_probability": 50.0,
                "under_probability": 50.0,
                "over_under_prediction": "OVER",
                "confidence_level": "low",
                "confidence_spanish": "BAJA",
                "confidence_percentage": 52.0,
                "park_factor": 1.0,
                "venue": venue,
                "pitcher_home": "TBD",
                "pitcher_away": "TBD",
                "error": str(e)
            }


advanced_predictor = AdvancedSabermetricPredictor()
