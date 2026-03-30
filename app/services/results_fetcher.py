"""
Servicio para obtener resultados de partidos de MLB
Se ejecuta automáticamente para comparar con predicciones guardadas
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://statsapi.mlb.com/api"


class ResultsFetcher:
    """Fetches actual game results from MLB API"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.timeout = 30.0
    
    async def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Método interno para hacer requests GET"""
        url = f"{self.base_url}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error en {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error general en {url}: {e}")
            return None
    
    async def get_completed_games(self, target_date: date) -> List[Dict]:
        """Obtiene todos los partidos completados para una fecha"""
        date_str = target_date.strftime("%m/%d/%Y")
        
        params = {
            "sportId": 1,
            "date": date_str,
            "hydrate": "boxscore,team"
        }
        
        data = await self._get("/v1/schedule", params)
        
        if not data or "dates" not in data or not data["dates"]:
            logger.warning(f"No se encontraron partidos para {date_str}")
            return []
        
        completed_games = []
        
        for d in data["dates"]:
            for game in d.get("games", []):
                if self._is_completed(game):
                    completed_game = self._parse_completed_game(game, target_date)
                    if completed_game:
                        completed_games.append(completed_game)
        
        logger.info(f"Encontrados {len(completed_games)} partidos completados para {date_str}")
        return completed_games
    
    def _is_completed(self, game: Dict) -> bool:
        """Verifica si un partido está completado"""
        status = game.get("status", {})
        abstract_state = status.get("abstractGameState", "")
        detailed_state = status.get("detailedState", "")
        
        return abstract_state == "Final" or detailed_state == "Final"
    
    def _parse_completed_game(self, game: Dict, game_date: date) -> Optional[Dict]:
        """Parsea un partido completado y extrae información relevante"""
        try:
            game_pk = game.get("gamePk")
            teams = game.get("teams", {})
            
            away_team_data = teams.get("away", {})
            home_team_data = teams.get("home", {})
            
            away_team = away_team_data.get("team", {})
            home_team = home_team_data.get("team", {})
            
            away_score = away_team_data.get("score")
            home_score = home_team_data.get("score")
            
            if away_score is None or home_score is None:
                logger.warning(f"Partido {game_pk} no tiene scores")
                return None
            
            return {
                "game_id": game_pk,
                "game_date": game_date,
                "away_team": away_team.get("name", "Away"),
                "away_team_id": away_team.get("id"),
                "home_team": home_team.get("name", "Home"),
                "home_team_id": home_team.get("id"),
                "away_score": int(away_score),
                "home_score": int(home_score),
                "total_runs": int(away_score) + int(home_score),
                "winner": home_team.get("name") if home_score > away_score else away_team.get("name"),
                "loser": away_team.get("name") if home_score > away_score else home_team.get("name"),
                "is_over": home_score > away_score,
                "venue": game.get("venue", {}).get("name", "Unknown"),
                "status": "Final"
            }
        except Exception as e:
            logger.error(f"Error parseando partido {game.get('gamePk')}: {e}")
            return None
    
    async def get_all_completed_games_since(self, start_date: date, end_date: date = None) -> List[Dict]:
        """Obtiene partidos completados en un rango de fechas"""
        if end_date is None:
            end_date = date.today()
        
        all_games = []
        current_date = start_date
        
        while current_date <= end_date:
            games = await self.get_completed_games(current_date)
            all_games.extend(games)
            current_date += timedelta(days=1)
        
        logger.info(f"Total de {len(all_games)} partidos encontrados desde {start_date} hasta {end_date}")
        return all_games
    
    async def get_game_details(self, game_pk: int) -> Optional[Dict]:
        """Obtiene detalles adicionales de un partido específico"""
        params = {
            "hydrate": "team,person,decisions"
        }
        return await self._get(f"/v1/game/{game_pk}/boxscore", params)


results_fetcher = ResultsFetcher()
