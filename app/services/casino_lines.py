"""
Scraper de líneas de casinos
Integración con The Odds API (fuente principal)
y fallback a Playdoit.mx / Caliente.mx
"""
import httpx
import logging
import re
from typing import Optional, Dict, Any
from datetime import datetime, date

from .odds_api import odds_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CasinoLinesScraper:
    """Scraper para obtener líneas de casinos (The Odds API + fallback)"""
    
    def __init__(self):
        self.timeout = 15.0
        self.cache = {}
        self.cache_time = None
    
    async def get_casino_lines(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Obtiene líneas de casinos (The Odds API como fuente principal)"""
        now = datetime.now()
        
        if not force_refresh and self.cache and self.cache_time:
            if (now - self.cache_time).seconds < 300:
                return self.cache
        
        odds_data = await odds_api.get_mlb_odds(force_refresh=force_refresh)
        
        if odds_data and not odds_data.get("error"):
            primary_source = "The Odds API"
            primary_lines = odds_data
            line_alerts = odds_api.get_last_alerts()
        else:
            logger.warning("The Odds API failed, trying Mexican casinos")
            primary_source = "Playdoit"
            playdoit_lines = await self._scrape_playdoit()
            
            if playdoit_lines and playdoit_lines.get("available"):
                primary_lines = playdoit_lines
            else:
                primary_source = "Caliente"
                primary_lines = await self._scrape_caliente()
            
            line_alerts = []
        
        lines = {
            "primary": primary_source,
            "odds_api": odds_data,
            "playdoit": await self._scrape_playdoit() if primary_source != "Playdoit" else None,
            "caliente": await self._scrape_caliente() if primary_source == "Caliente" else None,
            "timestamp": now.isoformat(),
            "primary_lines": primary_lines,
            "line_alerts": line_alerts
        }
        
        self.cache = lines
        self.cache_time = now
        return lines
    
    def get_best_line(self, home_team: str, away_team: str, casino_lines: Dict) -> Optional[Dict]:
        """Obtiene la mejor línea disponible (prioriza The Odds API)"""
        if not home_team or not away_team:
            return None
        
        odds_api_data = casino_lines.get("odds_api")
        if odds_api_data and not odds_api_data.get("error"):
            line = odds_api.get_line_for_game(home_team, away_team, odds_api_data)
            if line:
                return line
        
        primary = casino_lines.get("primary_lines")
        if not primary:
            return None
        
        primary_source = casino_lines.get("primary", "Casino")
        
        if isinstance(primary, dict) and primary.get("games"):
            line = self._find_line_in_source(home_team, away_team, primary)
            if line:
                line["source_used"] = primary_source
                return line
        
        secondary_source = "Caliente" if primary_source == "Playdoit" else "Playdoit"
        secondary = casino_lines.get("caliente") if primary_source == "Playdoit" else casino_lines.get("playdoit")
        if secondary:
            line = self._find_line_in_source(home_team, away_team, secondary)
            if line:
                line["source_used"] = secondary_source
                return line
        
        return None
    
    def _find_line_in_source(self, home_team: str, away_team: str, source_data: Dict) -> Optional[Dict]:
        """Busca línea en una fuente específica"""
        if not source_data or not isinstance(source_data, dict):
            return None
        
        home_team_lower = str(home_team).lower()
        away_team_lower = str(away_team).lower()
        
        games_list = source_data.get("games", [])
        if not isinstance(games_list, list):
            return None
        
        for game in games_list:
            if not isinstance(game, dict):
                continue
            
            game_home = str(game.get("home_team", "")).lower()
            game_away = str(game.get("away_team", "")).lower()
            
            if (home_team_lower in game_home or game_home in home_team_lower) and \
               (away_team_lower in game_away or game_away in away_team_lower):
                return self._parse_game_line(game)
        
        return None
    
    def _parse_game_line(self, game: Dict) -> Dict:
        """Parsea línea de un juego"""
        money_line = game.get("money_line") or {}
        over_under = game.get("over_under") or {}
        
        home_ml = money_line.get("home") if isinstance(money_line, dict) else None
        away_ml = money_line.get("away") if isinstance(money_line, dict) else None
        
        favorite = None
        favorite_margin = 0
        
        if home_ml and away_ml:
            if home_ml < away_ml:
                favorite = "home"
                favorite_margin = abs(home_ml - away_ml)
            elif away_ml < home_ml:
                favorite = "away"
                favorite_margin = abs(away_ml - home_ml)
        
        return {
            "home_ml": home_ml,
            "away_ml": away_ml,
            "favorite": favorite,
            "favorite_margin": favorite_margin,
            "ou_line": over_under.get("line") if isinstance(over_under, dict) else None,
            "ou_over": over_under.get("over") if isinstance(over_under, dict) else None,
            "ou_under": over_under.get("under") if isinstance(over_under, dict) else None,
            "home_team": game.get("home_team"),
            "away_team": game.get("away_team")
        }
    
    async def _scrape_playdoit(self) -> Optional[Dict]:
        """Scrapes lines from playdoit.mx"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json, text/html",
                    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"
                }
                
                response = await client.get(
                    "https://www.playdoit.mx/api/v1/sportsbook/events",
                    params={"sport": "baseball", "category": "mlb"},
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_playdoit_response(data)
                    
        except Exception as e:
            logger.warning(f"Playdoit scrape failed: {e}")
        
        return None
    
    async def _scrape_caliente(self) -> Optional[Dict]:
        """Scrapes lines from caliente.mx"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json, text/html",
                    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8"
                }
                
                response = await client.get(
                    "https://www.caliente.mx/sportsbook/api/events",
                    params={"sport": "mlb"},
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return self._parse_caliente_response(data)
                    
        except Exception as e:
            logger.warning(f"Caliente scrape failed: {e}")
        
        return None
    
    def _parse_playdoit_response(self, data: Dict) -> Optional[Dict]:
        """Parse playdoit API response"""
        try:
            if "events" in data:
                games = []
                for event in data["events"][:15]:
                    if not isinstance(event, dict):
                        continue
                    home_team_data = event.get("home_team", {})
                    away_team_data = event.get("away_team", {})
                    game = {
                        "id": event.get("id"),
                        "home_team": home_team_data.get("name") if isinstance(home_team_data, dict) else str(home_team_data) if home_team_data else "",
                        "away_team": away_team_data.get("name") if isinstance(away_team_data, dict) else str(away_team_data) if away_team_data else "",
                        "start_time": event.get("start_time"),
                        "money_line": self._extract_money_line(event),
                        "over_under": self._extract_over_under(event)
                    }
                    games.append(game)
                return {"source": "Playdoit", "games": games, "available": True}
        except Exception as e:
            logger.warning(f"Playdoit parse error: {e}")
        return {"source": "Playdoit", "games": [], "available": False, "error": "Parse error"}
    
    def _parse_caliente_response(self, data: Dict) -> Optional[Dict]:
        """Parse caliente API response"""
        try:
            if "events" in data:
                games = []
                for event in data["events"][:15]:
                    if not isinstance(event, dict):
                        continue
                    home_team_data = event.get("home_team", {})
                    away_team_data = event.get("away_team", {})
                    game = {
                        "id": event.get("id"),
                        "home_team": home_team_data.get("name") if isinstance(home_team_data, dict) else str(home_team_data) if home_team_data else "",
                        "away_team": away_team_data.get("name") if isinstance(away_team_data, dict) else str(away_team_data) if away_team_data else "",
                        "start_time": event.get("start_time"),
                        "money_line": self._extract_money_line(event),
                        "over_under": self._extract_over_under(event)
                    }
                    games.append(game)
                return {"source": "Caliente", "games": games, "available": True}
        except Exception as e:
            logger.warning(f"Caliente parse error: {e}")
        return {"source": "Caliente", "games": [], "available": False, "error": "Parse error"}
    
    def _extract_money_line(self, event: Dict) -> Optional[Dict]:
        """Extract money line from event"""
        try:
            markets = event.get("markets", [])
            if not isinstance(markets, list):
                return None
            for market in markets:
                if not isinstance(market, dict):
                    continue
                if market.get("type") == "money_line":
                    outcomes = market.get("outcomes", {})
                    if not isinstance(outcomes, dict):
                        continue
                    home_outcome = outcomes.get("home", {})
                    away_outcome = outcomes.get("away", {})
                    return {
                        "home": home_outcome.get("odds", 0) if isinstance(home_outcome, dict) else 0,
                        "away": away_outcome.get("odds", 0) if isinstance(away_outcome, dict) else 0
                    }
        except:
            pass
        return None
    
    def _extract_over_under(self, event: Dict) -> Optional[Dict]:
        """Extract over/under from event"""
        try:
            markets = event.get("markets", [])
            if not isinstance(markets, list):
                return None
            for market in markets:
                if not isinstance(market, dict):
                    continue
                if market.get("type") in ["total", "over_under"]:
                    outcomes = market.get("outcomes", {})
                    if not isinstance(outcomes, dict):
                        continue
                    over_outcome = outcomes.get("over", {})
                    under_outcome = outcomes.get("under", {})
                    return {
                        "line": market.get("line", 0),
                        "over": over_outcome.get("odds", 0) if isinstance(over_outcome, dict) else 0,
                        "under": under_outcome.get("odds", 0) if isinstance(under_outcome, dict) else 0
                    }
        except:
            pass
        return None
    
    def get_line_for_game(self, home_team: str, away_team: str, casino_lines: Dict) -> Optional[Dict]:
        """Busca línea para un partido específico"""
        if not home_team or not away_team:
            return None
        
        home_team_lower = str(home_team).lower()
        away_team_lower = str(away_team).lower()
        
        for casino, data in casino_lines.items():
            if not data or not isinstance(data, dict):
                continue
            games_list = data.get("games", [])
            if not isinstance(games_list, list):
                continue
            
            for game in games_list:
                if not isinstance(game, dict):
                    continue
                
                game_home = str(game.get("home_team", "")).lower()
                game_away = str(game.get("away_team", "")).lower()
                
                if (home_team_lower in game_home or game_home in home_team_lower) and \
                   (away_team_lower in game_away or game_away in away_team_lower):
                    money_line = game.get("money_line") or {}
                    over_under = game.get("over_under") or {}
                    return {
                        "source": casino,
                        "home_ml": money_line.get("home") if isinstance(money_line, dict) else None,
                        "away_ml": money_line.get("away") if isinstance(money_line, dict) else None,
                        "ou_line": over_under.get("line") if isinstance(over_under, dict) else None,
                        "ou_over": over_under.get("over") if isinstance(over_under, dict) else None,
                        "ou_under": over_under.get("under") if isinstance(over_under, dict) else None
                    }
        
        return None


def get_default_lines(predicted_total: float) -> Dict[str, Any]:
    """Genera líneas predeterminadas basadas en el mercado típico de MLB"""
    ou_line = 8.0
    if predicted_total < 7:
        ou_line = 7.0
    elif predicted_total < 8:
        ou_line = 7.5
    elif predicted_total < 9:
        ou_line = 8.5
    elif predicted_total < 10:
        ou_line = 9.5
    else:
        ou_line = 10.5
    
    return {
        "source": "Mercado MLB",
        "ou_line": ou_line,
        "estimated": True,
        "note": "Línea de referencia del mercado (actualiza para líneas reales)"
    }


casino_scraper = CasinoLinesScraper()
