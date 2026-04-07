"""
Cliente para la API oficial de MLB Stats API
Maneja todas las consultas a statsapi.mlb.com
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://statsapi.mlb.com/api"


class MLBAPIClient:
    """Cliente asíncrono para MLB Stats API"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.timeout = 60.0
    
    async def _get(self, endpoint: str, params: dict = None) -> Optional[Dict]:
        """Método interno para hacer requests GET"""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"MLB API Request: {url}")
        logger.info(f"MLB API Params: {params}")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                logger.info(f"MLB API Response Status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                logger.info(f"MLB API Response Keys: {data.keys() if data else 'None'}")
                if data and "dates" in data:
                    logger.info(f"MLB API Total dates: {len(data.get('dates', []))}")
                    if data.get('dates'):
                        for d in data['dates']:
                            logger.info(f"MLB API Date: {d.get('date')}, Games: {d.get('totalGames', 0)}")
                return data
        except httpx.TimeoutException as e:
            logger.error(f"Timeout en {url}: {e}")
            return None
        except httpx.HTTPError as e:
            logger.error(f"HTTP Error en {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error general en {url}: {e}")
            return None
    
    async def get_schedule(self, sport_id: int = 1, date_str: str = None) -> Optional[List[Dict]]:
        """Obtiene el calendario de partidos para una fecha"""
        if date_str is None:
            date_str = datetime.now().strftime("%m/%d/%Y")
        
        logger.info(f"Fetching schedule for date: {date_str}")
        
        params = {
            "sportId": sport_id,
            "date": date_str,
            "hydrate": "game(content(summary,editorial-recap)),team,venue,probablePitcher(person),linescore"
        }
        
        data = await self._get("/v1/schedule", params)
        logger.info(f"get_schedule returned data: {bool(data)}")
        
        if not data or "dates" not in data or not data["dates"]:
            logger.warning(f"No games found for date {date_str}. Data: {data}")
            return []
        
        games = []
        for d in data["dates"]:
            for game in d.get("games", []):
                games.append(game)
        
        logger.info(f"Returning {len(games)} games for {date_str}")
        return games
    
    async def get_game_boxscore(self, game_pk: int) -> Optional[Dict]:
        """Obtiene el boxscore de un partido"""
        params = {
            "hydrate": "team,person"
        }
        return await self._get(f"/v1/game/{game_pk}/boxscore", params)
    
    async def get_team_stats(self, team_id: int, date_str: str = None, stat_group: str = "pitching,hitting,fielding") -> Optional[Dict]:
        """Obtiene estadísticas de un equipo"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        params = {
            "season": datetime.now().year,
            "date": date_str,
            "stats": "season",
            "group": stat_group
        }
        return await self._get(f"/v1/teams/{team_id}/stats", params)
    
    async def get_bullpen_stats(self, team_id: int) -> Dict[str, float]:
        """Obtiene estadísticas del bullpen de un equipo"""
        params = {
            "season": datetime.now().year,
            "stats": "season",
            "group": "pitching"
        }
        data = await self._get(f"/v1/teams/{team_id}/stats", params)
        
        if not data or "stats" not in data:
            return self._default_bullpen_stats()
        
        try:
            for stat_group in data.get("stats", []):
                if stat_group.get("group", {}).get("displayName") == "pitching":
                    splits = stat_group.get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        ip = float(stat.get("inningsPitched", 0))
                        
                        if ip > 0:
                            games = int(stat.get("games", 0))
                            era = float(stat.get("era", 4.50))
                            fip = float(stat.get("fip", 4.50))
                            whip = float(stat.get("whip", 1.30))
                            k = int(stat.get("strikeouts", 0))
                            bb = int(stat.get("baseOnBalls", 0))
                            hr = int(stat.get("homeRuns", 0))
                            h = int(stat.get("hits", 0))
                            runs = int(stat.get("runs", 0))
                            
                            k_per_9 = round(k / ip * 9, 2) if ip > 0 else 8.0
                            bb_per_9 = round(bb / ip * 9, 2) if ip > 0 else 3.0
                            
                            return {
                                "games": games,
                                "innings_pitched": ip,
                                "era": era,
                                "fip": fip,
                                "whip": whip,
                                "k": k,
                                "bb": bb,
                                "hr": hr,
                                "h": h,
                                "runs": runs,
                                "k_per_9": k_per_9 if k_per_9 > 0 else 8.0,
                                "bb_per_9": bb_per_9 if bb_per_9 > 0 else 3.0,
                                "k_bb_ratio": round(k / bb, 2) if bb > 0 else 2.67,
                                "h_per_9": round(h / ip * 9, 2) if ip > 0 else 8.5
                            }
        except Exception as e:
            logger.error(f"Error parsing bullpen stats for team {team_id}: {e}")
        
        return self._default_bullpen_stats()
    
    @staticmethod
    def _default_bullpen_stats() -> Dict[str, float]:
        """Estadísticas por defecto del bullpen"""
        return {
            "games": 30,
            "innings_pitched": 100,
            "era": 4.20,
            "fip": 4.10,
            "whip": 1.30,
            "k": 95,
            "bb": 35,
            "hr": 12,
            "h": 85,
            "runs": 47,
            "k_per_9": 8.5,
            "bb_per_9": 3.1,
            "k_bb_ratio": 2.71,
            "h_per_9": 7.7
        }
    
    async def get_team_batting_stats(self, team_id: int) -> Dict[str, float]:
        """Obtiene estadísticas de bateo de un equipo"""
        params = {
            "season": datetime.now().year,
            "stats": "season",
            "group": "hitting"
        }
        data = await self._get(f"/v1/teams/{team_id}/stats", params)
        
        if not data or "stats" not in data:
            return self._default_batting_stats()
        
        try:
            for stat_group in data.get("stats", []):
                if stat_group.get("group", {}).get("displayName") == "hitting":
                    splits = stat_group.get("splits", [])
                    if splits:
                        stat = splits[0].get("stat", {})
                        
                        games = int(stat.get("gamesPlayed", 0))
                        hits = int(stat.get("hits", 0))
                        at_bats = int(stat.get("atBats", 0))
                        runs = int(stat.get("runs", 0))
                        doubles = int(stat.get("doubles", 0))
                        triples = int(stat.get("triples", 0))
                        home_runs = int(stat.get("homeRuns", 0))
                        rbi = int(stat.get("rbi", 0))
                        walks = int(stat.get("baseOnBalls", 0))
                        strikeouts = int(stat.get("strikeOuts", 0))
                        hb = int(stat.get("hitByPitch", 0))
                        sac_flies = int(stat.get("sacFlies", 0))
                        sac_hits = int(stat.get("sacBunts", 0))
                        gidp = int(stat.get("groundIntoDoublePlay", 0))
                        
                        total_bases = hits + doubles + (triples * 2) + (home_runs * 3)
                        
                        if at_bats > 0:
                            avg = hits / at_bats
                            slg = total_bases / at_bats
                        else:
                            avg = 0.0
                            slg = 0.0
                        
                        plate_appearances = at_bats + walks + hb + sac_flies + sac_hits
                        
                        if plate_appearances > 0:
                            obp = (hits + walks + hb) / plate_appearances
                            ops = avg + slg
                            k_rate = (strikeouts / plate_appearances) * 100
                            bb_rate = (walks / plate_appearances) * 100
                            iso = slg - avg
                        else:
                            obp = 0.0
                            ops = 0.0
                            k_rate = 0.0
                            bb_rate = 0.0
                            iso = 0.0
                        
                        singles = hits - doubles - triples - home_runs
                        total_bases_calc = singles + (doubles * 2) + (triples * 3) + (home_runs * 4)
                        
                        if plate_appearances > 0 and walks > 0:
                            woba = ((0.69 * walks) + (0.72 * hb) + (0.89 * singles) + (1.18 * doubles) + (1.52 * triples) + (1.65 * home_runs)) / plate_appearances
                        else:
                            woba = 0.30
                        
                        woba_scale = 1.25
                        wraa = ((woba - 0.320) / woba_scale) * plate_appearances / 600 if plate_appearances > 0 else 0
                        
                        return {
                            "games": games,
                            "at_bats": at_bats,
                            "hits": hits,
                            "runs": runs,
                            "doubles": doubles,
                            "triples": triples,
                            "home_runs": home_runs,
                            "rbi": rbi,
                            "walks": walks,
                            "strikeouts": strikeouts,
                            "batting_avg": round(avg, 3),
                            "obp": round(obp, 3),
                            "slg": round(slg, 3),
                            "ops": round(ops, 3),
                            "iso": round(iso, 3),
                            "k_rate": round(k_rate, 1),
                            "bb_rate": round(bb_rate, 1),
                            "woba": round(woba, 3),
                            "wraa": round(wraa, 1),
                            "total_bases": total_bases,
                            "hr_rate": round((home_runs / plate_appearances) * 100, 1) if plate_appearances > 0 else 0,
                            "babip": round((hits - home_runs) / (at_bats - strikeouts - home_runs + sac_flies), 3) if (at_bats - strikeouts - home_runs + sac_flies) > 0 else 0.300
                        }
        except Exception as e:
            logger.error(f"Error parsing batting stats for team {team_id}: {e}")
        
        return self._default_batting_stats()
    
    @staticmethod
    def _default_batting_stats() -> Dict[str, float]:
        """Estadísticas de bateo por defecto"""
        return {
            "games": 0,
            "at_bats": 0,
            "hits": 0,
            "runs": 0,
            "doubles": 0,
            "triples": 0,
            "home_runs": 0,
            "rbi": 0,
            "walks": 0,
            "strikeouts": 0,
            "batting_avg": 0.250,
            "obp": 0.320,
            "slg": 0.400,
            "ops": 0.720,
            "iso": 0.150,
            "k_rate": 20.0,
            "bb_rate": 8.0,
            "woba": 0.320,
            "wraa": 0.0,
            "total_bases": 0,
            "hr_rate": 3.0,
            "babip": 0.300
        }
    
    async def get_player_stats(self, person_id: int, stats_type: str = "pitching", use_career: bool = False) -> Optional[Dict]:
        """Obtiene estadísticas de un jugador"""
        if use_career:
            params = {
                "stats": "career",
                "group": stats_type
            }
        else:
            params = {
                "season": datetime.now().year,
                "stats": "season",
                "group": stats_type
            }
        return await self._get(f"/v1/people/{person_id}/stats", params)
    
    async def get_team_roster(self, team_id: int) -> Optional[Dict]:
        """Obtiene la lista de jugadores de un equipo"""
        return await self._get(f"/v1/teams/{team_id}/roster", {"rosterType": "40Man"})
    
    async def get_recent_games(self, team_id: int, games: int = 15) -> List[Dict]:
        """Obtiene los últimos N partidos del equipo en temporada 2026"""
        current_year = 2026
        start_date = f"04/01/{current_year}"
        end_date = datetime.now().strftime("%m/%d/%Y")
        
        params = {
            "sportId": 1,
            "startDate": start_date,
            "endDate": end_date,
            "teamId": team_id,
            "hydrate": "team,linescore"
        }
        
        logger.info(f"Fetching 2026 season games for team {team_id} from {start_date} to {end_date}")
        
        data = await self._get("/v1/schedule", params)
        if not data or not isinstance(data, dict):
            logger.warning(f"No data returned for team {team_id}")
            return []
        
        if "dates" not in data or not data["dates"]:
            logger.warning(f"No dates in response for team {team_id}")
            return []
        
        games_list = []
        for d in data["dates"]:
            if not isinstance(d, dict):
                continue
            for game in d.get("games", []):
                if not isinstance(game, dict):
                    continue
                game_teams = game.get("teams", {})
                if game_teams and isinstance(game_teams, dict):
                    games_list.append(game)
                    if len(games_list) >= games:
                        break
            if len(games_list) >= games:
                break
        
        logger.info(f"Found {len(games_list)} games for team {team_id}")
        return games_list
    
    async def get_probable_pitchers(self, date_str: str = None) -> Dict[int, Dict]:
        """Obtiene los pitchers probables para una fecha"""
        if date_str is None:
            date_str = datetime.now().strftime("%m/%d/%Y")
        
        games = await self.get_schedule(date_str=date_str)
        pitchers = {}
        
        for game in games:
            game_pk = game.get("gamePk")
            teams = game.get("teams", {})
            
            home_team = teams.get("home", {}).get("team", {})
            away_team = teams.get("away", {}).get("team", {})
            
            home_probable = teams.get("home", {}).get("probablePitcher", {})
            away_probable = teams.get("away", {}).get("probablePitcher", {})
            
            if home_probable:
                pitchers[home_team.get("id")] = {
                    "id": home_probable.get("id"),
                    "name": home_probable.get("fullName"),
                    "team": home_team.get("name")
                }
            
            if away_probable:
                pitchers[away_team.get("id")] = {
                    "id": away_probable.get("id"),
                    "name": away_probable.get("fullName"),
                    "team": away_team.get("name")
                }
        
        return pitchers


mlb_client = MLBAPIClient()


async def fetch_today_games() -> List[Dict[str, Any]]:
    """Función wrapper para obtener partidos de hoy"""
    today = datetime.now().strftime("%m/%d/%Y")
    games = await mlb_client.get_schedule(date_str=today)
    return games if games else []


async def fetch_game_details(game_pk: int) -> Optional[Dict]:
    """Obtiene detalles de un partido específico"""
    return await mlb_client.get_game_boxscore(game_pk)


async def get_team_statistics(team_id: int) -> Dict[str, Any]:
    """Obtiene estadísticas completas de un equipo"""
    stats = await mlb_client.get_team_stats(team_id)
    return stats if stats else {}


def parse_game_info(game: Dict) -> Dict[str, Any]:
    """Parsea información básica de un partido"""
    if not isinstance(game, dict):
        return {
            "game_id": 0,
            "game_date": None,
            "game_time": "TBD",
            "status": "Unknown",
            "home_team": "Unknown",
            "away_team": "Unknown",
            "home_team_id": 0,
            "away_team_id": 0,
            "venue": "Unknown",
            "home_probable_pitcher": None,
            "away_probable_pitcher": None
        }
    
    teams = game.get("teams", {})
    if not isinstance(teams, dict):
        teams = {}
    
    home_data = teams.get("home", {})
    away_data = teams.get("away", {})
    home_team = home_data.get("team", {}) if isinstance(home_data, dict) else {}
    away_team = away_data.get("team", {}) if isinstance(away_data, dict) else {}
    
    if not isinstance(home_team, dict):
        home_team = {}
    if not isinstance(away_team, dict):
        away_team = {}
    
    game_date = game.get("gameDate", "")
    game_time = "TBD"
    if game_date and isinstance(game_date, str) and "T" in game_date:
        try:
            game_time = game_date.split("T")[1][:5]
        except:
            game_time = "TBD"
    
    status = game.get("status", {})
    if isinstance(status, dict):
        status = status.get("detailedState", "Unknown")
    else:
        status = "Unknown"
    
    venue = game.get("venue", {})
    if isinstance(venue, dict):
        venue = venue.get("name", "Unknown")
    else:
        venue = "Unknown"
    
    home_probable = home_data.get("probablePitcher", {}) if isinstance(home_data, dict) else {}
    away_probable = away_data.get("probablePitcher", {}) if isinstance(away_data, dict) else {}
    
    return {
        "game_id": game.get("gamePk", 0),
        "game_date": game.get("gameDate"),
        "game_time": game_time,
        "status": status,
        "home_team": home_team.get("name", "Unknown") if isinstance(home_team, dict) else "Unknown",
        "away_team": away_team.get("name", "Unknown") if isinstance(away_team, dict) else "Unknown",
        "home_team_id": home_team.get("id", 0) if isinstance(home_team, dict) else 0,
        "away_team_id": away_team.get("id", 0) if isinstance(away_team, dict) else 0,
        "venue": venue,
        "home_probable_pitcher": home_probable.get("fullName") if isinstance(home_probable, dict) else None,
        "away_probable_pitcher": away_probable.get("fullName") if isinstance(away_probable, dict) else None
    }
