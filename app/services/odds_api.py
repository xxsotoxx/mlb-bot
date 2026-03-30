"""
Servicio para obtener líneas de casinos via The Odds API
Usa promedio de los 4 mejores bookmakers
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"
ODDS_API_KEY = "80dff8c1bf9b9bf4cb272af12e0cf0d3"

BOOKMAKER_PRIORITY = ["draftkings", "fanduel", "betmgm", "lowvig"]

BOOKMAKER_NAMES = {
    "draftkings": "DraftKings",
    "fanduel": "FanDuel",
    "betmgm": "BetMGM",
    "lowvig": "LowVig.ag"
}


class OddsAPIClient:
    """Cliente para The Odds API"""
    
    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.base_url = ODDS_API_BASE
        self.timeout = 30.0
        self.cache = {}
        self.cache_time = None
        self.line_history = []
        
        self.important_bookmakers = ["draftkings", "fanduel", "betmgm"]
    
    async def get_mlb_odds(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtiene líneas de MLB de The Odds API"""
        now = datetime.now()
        
        if not force_refresh and self.cache and self.cache_time:
            if (now - self.cache_time).seconds < 300:
                return self.cache
        
        try:
            url = f"{self.base_url}/sports/baseball_mlb/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h,totals,spreads",
                "oddsFormat": "american"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Odds API error: {response.status_code}")
                    return {"error": "API request failed", "games": []}
                
                data = response.json()
                remaining = response.headers.get("X-Requests-Remaining", "N/A")
                logger.info(f"Odds API: {len(data)} games, {remaining} requests remaining")
                
                games = []
                for game in data:
                    game_data = self._parse_game_odds(game)
                    games.append(game_data)
                
                self.cache = {
                    "games": games,
                    "timestamp": now.isoformat(),
                    "requests_remaining": remaining
                }
                self.cache_time = now
                
                if len(self.line_history) > 0:
                    self._check_line_movements()
                
                self.line_history.append({
                    "timestamp": now,
                    "games": games
                })
                
                if len(self.line_history) > 100:
                    self.line_history = self.line_history[-100:]
                
                return self.cache
                
        except Exception as e:
            logger.error(f"Error fetching odds: {e}")
            return {"error": str(e), "games": []}
    
    def _parse_game_odds(self, game: Dict) -> Dict:
        """Parsea las probabilidades de un juego"""
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        commence_time = game.get("commence_time", "")
        game_id = game.get("id", "")
        
        bookmakers_data = {}
        all_ou_lines = []
        all_spread_lines = []
        
        for bookmaker in game.get("bookmakers", []):
            bm_key = bookmaker.get("key", "")
            
            if bm_key not in BOOKMAKER_PRIORITY:
                continue
            
            bm_name = BOOKMAKER_NAMES.get(bm_key, bm_key)
            bookmaker_odds = {"name": bm_name, "key": bm_key}
            
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                outcomes = market.get("outcomes", [])
                
                if market_key == "h2h":
                    bookmaker_odds["ml"] = self._parse_ml(outcomes, home_team, away_team)
                
                elif market_key == "totals":
                    bookmaker_odds["totals"] = self._parse_totals(outcomes)
                    ou_data = bookmaker_odds["totals"]
                    if ou_data.get("line"):
                        all_ou_lines.append({
                            "bookmaker": bm_key,
                            "point": ou_data.get("line"),
                            "over_price": ou_data.get("over", {}).get("odds"),
                            "under_price": ou_data.get("under", {}).get("odds")
                        })
                
                elif market_key == "spreads":
                    bookmaker_odds["spreads"] = self._parse_spreads(outcomes, home_team, away_team)
                    spread_data = bookmaker_odds["spreads"]
                    if spread_data.get("home", {}).get("point"):
                        all_spread_lines.append({
                            "bookmaker": bm_key,
                            "line": spread_data.get("home", {}).get("point"),
                            "home_odds": spread_data.get("home", {}).get("odds"),
                            "away_odds": spread_data.get("away", {}).get("odds")
                        })
            
            bookmakers_data[bm_key] = bookmaker_odds
        
        avg_ou = self._calculate_average_ou(all_ou_lines)
        avg_spread = self._calculate_average_spread(all_spread_lines)
        consensus = self._calculate_consensus_by_line(all_ou_lines)
        
        return {
            "id": game_id,
            "home_team": home_team,
            "away_team": away_team,
            "commence_time": commence_time,
            "bookmakers": bookmakers_data,
            "averages": {
                "over_under_line": avg_ou.get("line"),
                "over_odds_avg": avg_ou.get("over_avg"),
                "under_odds_avg": avg_ou.get("under_avg"),
                "spread_line": avg_spread.get("line"),
                "spread_home_avg": avg_spread.get("home_avg"),
                "spread_away_avg": avg_spread.get("away_avg")
            },
            "consensus": consensus,
            "recommended_bookmaker": "Promedio de 4 bookmakers"
        }
    
    def _parse_ml(self, outcomes: List, home_team: str, away_team: str) -> Dict:
        """Parsea money line"""
        home_odds = None
        away_odds = None
        favorite = None
        favorite_margin = 0
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            price = outcome.get("price")
            
            if home_team in name or name in home_team:
                home_odds = price
            elif away_team in name or name in away_team:
                away_odds = price
        
        if home_odds and away_odds:
            if home_odds < away_odds:
                favorite = home_team
                favorite_margin = abs(home_odds - away_odds)
            else:
                favorite = away_team
                favorite_margin = abs(away_odds - home_odds)
        
        return {
            "home": home_odds,
            "away": away_odds,
            "favorite": favorite,
            "favorite_margin": favorite_margin,
            "home_implied": self._odds_to_probability(home_odds) if home_odds else 50,
            "away_implied": self._odds_to_probability(away_odds) if away_odds else 50
        }
    
    def _parse_totals(self, outcomes: List) -> Dict:
        """Parsea over/under"""
        over_line = None
        over_odds = None
        under_line = None
        under_odds = None
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            point = outcome.get("point")
            price = outcome.get("price")
            
            if "over" in name.lower():
                over_line = point
                over_odds = price
            elif "under" in name.lower():
                under_line = point
                under_odds = price
        
        return {
            "line": over_line,
            "over": {"point": over_line, "odds": over_odds},
            "under": {"point": under_line, "odds": under_odds}
        }
    
    def _parse_spreads(self, outcomes: List, home_team: str, away_team: str) -> Dict:
        """Parsea run line/spreads"""
        home_spread = None
        home_spread_odds = None
        away_spread = None
        away_spread_odds = None
        
        for outcome in outcomes:
            name = outcome.get("name", "")
            point = outcome.get("point")
            price = outcome.get("price")
            
            if home_team in name or name in home_team:
                home_spread = point
                home_spread_odds = price
            elif away_team in name or name in away_team:
                away_spread = point
                away_spread_odds = price
        
        return {
            "home": {"point": home_spread, "odds": home_spread_odds},
            "away": {"point": away_spread, "odds": away_spread_odds}
        }
    
    def _calculate_average_ou(self, all_ou: List) -> Dict:
        """Calcula promedio de líneas O/U"""
        if not all_ou:
            return {"line": 8.0, "over_avg": -110, "under_avg": -110}
        
        lines = [o.get("point") for o in all_ou if o.get("point")]
        over_odds = [o.get("over_price") for o in all_ou if o.get("over_price")]
        under_odds = [o.get("under_price") for o in all_ou if o.get("under_price")]
        
        avg_line = sum(lines) / len(lines) if lines else 8.0
        avg_over = sum(over_odds) / len(over_odds) if over_odds else -110
        avg_under = sum(under_odds) / len(under_odds) if under_odds else -110
        
        return {
            "line": round(avg_line, 1),
            "over_avg": round(avg_over, 1),
            "under_avg": round(avg_under, 1)
        }
    
    def _calculate_average_spread(self, all_spreads: List) -> Dict:
        """Calcula promedio de run lines"""
        if not all_spreads:
            return {"line": -1.5, "home_avg": -110, "away_avg": -110}
        
        lines = [o.get("point") for o in all_spreads if o.get("point")]
        home_odds = [o.get("price") for o in all_spreads if o.get("price")]
        away_odds = home_odds[1::2] if len(home_odds) > 1 else home_odds
        
        avg_line = sum(lines) / len(lines) if lines else -1.5
        avg_home = sum(home_odds[:len(home_odds)//2]) / (len(home_odds)//2) if len(home_odds) > 1 else -110
        avg_away = sum(home_odds[len(home_odds)//2:]) / (len(home_odds) - len(home_odds)//2) if len(home_odds) > 1 else -110
        
        return {
            "line": round(avg_line, 1),
            "home_avg": round(avg_home, 1),
            "away_avg": round(avg_away, 1)
        }
    
    def _get_best_bookmaker(self, bookmakers_data: Dict) -> Dict:
        """Obtiene el primer bookmaker disponible de la lista prioritaria"""
        for key in BOOKMAKER_PRIORITY:
            if key in bookmakers_data:
                bm = bookmakers_data[key]
                return {
                    "key": key,
                    "name": BOOKMAKER_NAMES.get(key, key),
                    "has_ml": "ml" in bm,
                    "has_totals": "totals" in bm,
                    "has_spreads": "spreads" in bm
                }
        return {"key": None, "name": "N/A"}
    
    def _odds_to_probability(self, odds: int) -> float:
        """Convierte cuotas americanas a probabilidad implícita"""
        if odds > 0:
            return round(100 / (odds + 100) * 100, 1)
        else:
            return round(abs(odds) / (abs(odds) + 100) * 100, 1)
    
    def _check_line_movements(self):
        """Detecta cambios fuertes en las líneas"""
        if len(self.line_history) < 2:
            return []
        
        alerts = []
        current = self.line_history[-1]["games"]
        previous = self.line_history[-2]["games"]
        
        current_dict = {g["id"]: g for g in current}
        previous_dict = {g["id"]: g for g in previous}
        
        for game_id, current_game in current_dict.items():
            if game_id not in previous_dict:
                continue
            
            prev_game = previous_dict[game_id]
            current_avg = current_game.get("averages", {}).get("over_under_line")
            prev_avg = prev_game.get("averages", {}).get("over_under_line")
            
            if current_avg and prev_avg:
                diff = current_avg - prev_avg
                if abs(diff) >= 0.5:
                    alerts.append({
                        "game": f"{current_game.get('home_team')} vs {current_game.get('away_team')}",
                        "previous_line": prev_avg,
                        "current_line": current_avg,
                        "change": round(diff, 1),
                        "direction": "UP" if diff > 0 else "DOWN",
                        "severity": "HIGH" if abs(diff) >= 1.0 else "MEDIUM"
                    })
                    logger.warning(f"LINE MOVEMENT ALERT: {current_game.get('home_team')} vs {current_game.get('away_team')}: {prev_avg} -> {current_avg} ({'+' if diff > 0 else ''}{diff})")
        
        if alerts:
            self.last_line_alerts = alerts
        
        return alerts
    
    def get_line_for_game(self, home_team: str, away_team: str, odds_data: Dict = None) -> Optional[Dict]:
        """Busca líneas para un juego específico"""
        if not odds_data:
            odds_data = self.cache
        
        games = odds_data.get("games", []) if isinstance(odds_data, dict) else []
        
        home_lower = home_team.lower()
        away_lower = away_team.lower()
        
        for game in games:
            game_home = game.get("home_team", "").lower()
            game_away = game.get("away_team", "").lower()
            
            if (home_lower in game_home or game_home in home_lower) and \
               (away_lower in game_away or game_away in away_lower):
                return self._format_game_lines(game)
        
        return None
    
    def _format_game_lines(self, game: Dict) -> Dict:
        """Formatea las líneas de un juego usando promedio de bookmakers"""
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")
        bookmakers = game.get("bookmakers", {})
        averages = game.get("averages", {})
        consensus = game.get("consensus", {})
        recommended = game.get("recommended_bookmaker", "")
        
        best_bm = self._get_best_bookmaker(bookmakers)
        best_bm_key = best_bm.get("key")
        best_bm_data = bookmakers.get(best_bm_key, {}) if best_bm_key else {}
        best_bm_ml = best_bm_data.get("ml", {})
        
        return {
            "available": True,
            "home_team": home_team,
            "away_team": away_team,
            "source": "The Odds API",
            "recommended_bookmaker": recommended,
            "consensus_line": consensus.get("line"),
            "consensus_bookmaker_count": consensus.get("bookmaker_count"),
            "consensus_total_bookmakers": consensus.get("total_bookmakers"),
            "consensus_pct": consensus.get("consensus_pct"),
            "money_line": {
                "home": best_bm_ml.get("home"),
                "away": best_bm_ml.get("away"),
                "favorite": best_bm_ml.get("favorite"),
                "favorite_margin": best_bm_ml.get("favorite_margin", 0),
                "home_implied": best_bm_ml.get("home_implied", 50),
                "away_implied": best_bm_ml.get("away_implied", 50)
            },
            "over_under": {
                "line": averages.get("over_under_line"),
                "over_odds": averages.get("over_odds_avg"),
                "under_odds": averages.get("under_odds_avg")
            },
            "run_line": {
                "line": averages.get("spread_line", -1.5),
                "home_odds": averages.get("spread_home_avg"),
                "away_odds": averages.get("spread_away_avg")
            },
            "all_bookmakers": bookmakers
        }
    
    def _calculate_consensus_by_line(self, all_ou_lines: List) -> Dict:
        """Calcula consenso por línea O/U más común"""
        if not all_ou_lines:
            return {"line": 8.5, "bookmaker_count": 0, "total_bookmakers": 0, "consensus_pct": 0}
        
        line_counts = {}
        for ou in all_ou_lines:
            point = ou.get("point")
            if point:
                line_counts[point] = line_counts.get(point, 0) + 1
        
        if not line_counts:
            return {"line": 8.5, "bookmaker_count": 0, "total_bookmakers": len(all_ou_lines), "consensus_pct": 0}
        
        consensus_line = max(line_counts.keys())
        consensus_count = max(line_counts.values())
        
        return {
            "line": consensus_line,
            "bookmaker_count": consensus_count,
            "total_bookmakers": len(all_ou_lines),
            "consensus_pct": round((consensus_count / len(all_ou_lines)) * 100, 1)
        }
    
    def get_line_history(self) -> List[Dict]:
        """Obtiene historial de líneas"""
        return [
            {
                "timestamp": entry["timestamp"].isoformat(),
                "games": [
                    {
                        "home_team": g["home_team"],
                        "away_team": g["away_team"],
                        "ou_line": g.get("averages", {}).get("over_under_line"),
                        "favorite": g.get("consensus", {}).get("favorite")
                    }
                    for g in entry["games"]
                ]
            }
            for entry in self.line_history
        ]
    
    def get_last_alerts(self) -> List[Dict]:
        """Obtiene últimas alertas de movimiento de líneas"""
        return getattr(self, "last_line_alerts", [])


odds_api = OddsAPIClient()
