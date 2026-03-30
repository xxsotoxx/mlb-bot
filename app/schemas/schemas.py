"""Schemas Pydantic para validación de datos"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class PitcherStats(BaseModel):
    """Estadísticas de un pitcher"""
    id: int
    name: str
    era: float = 0.0
    fip: float = 0.0
    whip: float = 0.0
    wins: int = 0
    losses: int = 0
    games: int = 0
    strikeouts: int = 0
    walks: int = 0
    innings_pitched: float = 0.0


class TeamStats(BaseModel):
    """Estadísticas de un equipo"""
    team_id: int
    team_name: str
    runs_scored_avg: float = 0.0
    runs_allowed_avg: float = 0.0
    home_record: str = "0-0"
    away_record: str = "0-0"
    woba: float = 0.0
    wrc_plus: float = 0.0
    bullpen_era: float = 0.0
    last_15_games: dict = {}


class GameInfo(BaseModel):
    """Información básica de un partido"""
    game_id: int
    game_date: str
    game_time: str
    status: str
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    venue: str
    home_probable_pitcher: Optional[str] = None
    away_probable_pitcher: Optional[str] = None


class Prediction(BaseModel):
    """Predicción para un partido"""
    game_id: int
    predicted_total: float
    predicted_home_score: float
    predicted_away_score: float
    favorite: str
    home_win_probability: float
    away_win_probability: float
    over_probability: float
    under_probability: float
    over_line: float = 7.5
    confidence: str = "medium"


class GameWithPrediction(BaseModel):
    """Partido con predicción completa"""
    game_info: GameInfo
    prediction: Prediction
    home_stats: Optional[TeamStats] = None
    away_stats: Optional[TeamStats] = None
    home_pitcher: Optional[PitcherStats] = None
    away_pitcher: Optional[PitcherStats] = None


class PredictionRecord(BaseModel):
    """Registro de predicción guardada"""
    id: int
    game_id: int
    game_date: date
    home_team: str
    away_team: str
    predicted_home_score: float
    predicted_away_score: float
    predicted_total: float
    predicted_favorite: str
    home_win_probability: float
    over_probability: float
    over_line: float
    actual_home_score: Optional[int] = None
    actual_away_score: Optional[int] = None
    result_registered: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class ResultInput(BaseModel):
    """Input para registrar resultado"""
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)


class DashboardStats(BaseModel):
    """Estadísticas del dashboard"""
    total_predictions: int
    money_line_correct: int
    money_line_total: int
    money_line_percentage: float
    over_under_correct: int
    over_under_total: int
    over_under_percentage: float
    avg_run_difference: float
    recent_form: List[dict] = []


class APIResponse(BaseModel):
    """Respuesta estándar de la API"""
    success: bool
    message: str
    data: Optional[dict] = None
    error: Optional[str] = None
