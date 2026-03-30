"""Base de datos SQLite con SQLAlchemy"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date

DATABASE_URL = "sqlite:///./mlb_predictions.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PredictionRecordDB(Base):
    """Modelo de predicción guardada en BD"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)
    game_date = Column(Date, index=True)
    home_team = Column(String(100))
    away_team = Column(String(100))
    predicted_home_score = Column(Float)
    predicted_away_score = Column(Float)
    predicted_total = Column(Float)
    predicted_favorite = Column(String(100))
    home_win_probability = Column(Float)
    over_probability = Column(Float)
    over_line = Column(Float)
    pitcher_home = Column(String(100), nullable=True)
    pitcher_away = Column(String(100), nullable=True)
    actual_home_score = Column(Integer, nullable=True)
    actual_away_score = Column(Integer, nullable=True)
    result_registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LineHistoryDB(Base):
    """Modelo para guardar histórico de líneas de casino"""
    __tablename__ = "line_history"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(100), index=True)
    game_date = Column(Date, index=True)
    home_team = Column(String(100))
    away_team = Column(String(100))
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    casino_source = Column(String(50))
    
    casino_favorite = Column(String(100), nullable=True)
    casino_home_ml = Column(Integer, nullable=True)
    casino_away_ml = Column(Integer, nullable=True)
    
    casino_ou_line = Column(Float, nullable=True)
    casino_over_odds = Column(Integer, nullable=True)
    casino_under_odds = Column(Integer, nullable=True)
    
    casino_spread_line = Column(Float, nullable=True)
    casino_home_spread_odds = Column(Integer, nullable=True)
    casino_away_spread_odds = Column(Integer, nullable=True)
    
    consensus_favorite = Column(String(100), nullable=True)
    consensus_pct = Column(Float, nullable=True)


def init_db():
    """Inicializa la base de datos"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Obtiene sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_prediction(db, prediction_data: dict):
    """Guarda una predicción en la base de datos"""
    prediction = PredictionRecordDB(**prediction_data)
    db.merge(prediction)
    db.commit()
    return prediction


def update_prediction_result(db, game_id: int, home_score: int, away_score: int):
    """Actualiza el resultado real de un partido"""
    prediction = db.query(PredictionRecordDB).filter(
        PredictionRecordDB.game_id == game_id
    ).first()
    
    if prediction:
        prediction.actual_home_score = home_score
        prediction.actual_away_score = away_score
        prediction.result_registered = True
        db.commit()
        return True
    return False


def get_all_predictions(db, limit: int = 100):
    """Obtiene todas las predicciones"""
    return db.query(PredictionRecordDB).order_by(
        PredictionRecordDB.game_date.desc()
    ).limit(limit).all()


def get_prediction_by_game(db, game_id: int):
    """Obtiene predicción por game_id"""
    return db.query(PredictionRecordDB).filter(
        PredictionRecordDB.game_id == game_id
    ).first()


def get_predictions_with_results(db):
    """Obtiene predicciones que ya tienen resultado"""
    return db.query(PredictionRecordDB).filter(
        PredictionRecordDB.result_registered == True
    ).order_by(PredictionRecordDB.game_date.desc()).all()


def get_dashboard_stats(db):
    """Calcula estadísticas del dashboard"""
    predictions = get_predictions_with_results(db)
    
    if not predictions:
        return {
            "total_predictions": 0,
            "money_line_correct": 0,
            "money_line_total": 0,
            "money_line_percentage": 0.0,
            "over_under_correct": 0,
            "over_under_total": 0,
            "over_under_percentage": 0.0,
            "avg_run_difference": 0.0,
            "recent_form": []
        }
    
    money_line_correct = 0
    over_under_correct = 0
    total_run_diff = 0
    total_runs_diff = 0
    
    for p in predictions:
        home_won = p.actual_home_score > p.actual_away_score
        predicted_home_wins = p.predicted_favorite == p.home_team
        
        if home_won == predicted_home_wins:
            money_line_correct += 1
        
        actual_total = p.actual_home_score + p.actual_away_score
        if (actual_total > p.over_line and p.over_probability > 0.5) or \
           (actual_total < p.over_line and p.over_probability < 0.5):
            over_under_correct += 1
        
        predicted_total = p.predicted_home_score + p.predicted_away_score
        total_runs_diff += abs(actual_total - predicted_total)
    
    total = len(predictions)
    
    return {
        "total_predictions": total,
        "money_line_correct": money_line_correct,
        "money_line_total": total,
        "money_line_percentage": round(money_line_correct / total * 100, 1) if total > 0 else 0.0,
        "over_under_correct": over_under_correct,
        "over_under_total": total,
        "over_under_percentage": round(over_under_correct / total * 100, 1) if total > 0 else 0.0,
        "avg_run_difference": round(total_runs_diff / total, 2) if total > 0 else 0.0,
        "recent_form": [
            {
                "game_date": p.game_date.isoformat() if p.game_date else None,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "predicted": f"{int(p.predicted_home_score)}-{int(p.predicted_away_score)}",
                "actual": f"{p.actual_home_score}-{p.actual_away_score}" if p.result_registered else "N/A"
            }
            for p in predictions[-10:][::-1]
        ]
    }


def save_line_history(db, line_data: dict):
    """Guarda historial de líneas en la base de datos"""
    line_record = LineHistoryDB(**line_data)
    db.add(line_record)
    db.commit()
    return line_record


def get_line_history_for_game(db, game_id: str, limit: int = 50):
    """Obtiene historial de líneas para un juego"""
    return db.query(LineHistoryDB).filter(
        LineHistoryDB.game_id == game_id
    ).order_by(LineHistoryDB.recorded_at.desc()).limit(limit).all()


def get_line_history_for_date(db, target_date_value: date, limit: int = 500):
    """Obtiene historial de líneas para una fecha"""
    return db.query(LineHistoryDB).filter(
        LineHistoryDB.game_date == target_date_value
    ).order_by(LineHistoryDB.recorded_at.desc()).limit(limit).all()


def get_all_line_history(db, limit: int = 1000):
    """Obtiene todo el historial de líneas"""
    return db.query(LineHistoryDB).order_by(
        LineHistoryDB.recorded_at.desc()
    ).limit(limit).all()


def get_latest_line_snapshot(db, game_id: str):
    """Obtiene el snapshot más reciente de líneas para un juego"""
    return db.query(LineHistoryDB).filter(
        LineHistoryDB.game_id == game_id
    ).order_by(LineHistoryDB.recorded_at.desc()).first()


def detect_line_movement(db, game_id: str, threshold: float = 0.5) -> dict:
    """Detecta movimiento de líneas comparando con registros anteriores"""
    history = db.query(LineHistoryDB).filter(
        LineHistoryDB.game_id == game_id
    ).order_by(LineHistoryDB.recorded_at.asc()).all()
    
    if len(history) < 2:
        return {"has_movement": False, "alerts": []}
    
    alerts = []
    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        
        ou_change = 0
        if prev.casino_ou_line and curr.casino_ou_line:
            ou_change = abs(curr.casino_ou_line - prev.casino_ou_line)
        
        if ou_change >= threshold:
            alerts.append({
                "previous_line": prev.casino_ou_line,
                "current_line": curr.casino_ou_line,
                "change": round(ou_change, 1),
                "direction": "UP" if curr.casino_ou_line > prev.casino_ou_line else "DOWN",
                "severity": "HIGH" if ou_change >= 1.0 else "MEDIUM",
                "timestamp": curr.recorded_at.isoformat()
            })
    
    return {
        "has_movement": len(alerts) > 0,
        "alerts": alerts,
        "total_records": len(history)
    }
