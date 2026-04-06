"""Base de datos PostgreSQL con SQLAlchemy"""
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date

# PostgreSQL connection from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mlb_user:mlbSecure2024!@postgres:5432/mlb_bot"
)

# Create engine with PostgreSQL settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserDB(Base):
    """Modelo de usuario para autenticación"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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


class GameResultDB(Base):
    """Modelo para guardar resultados de partidos y comparaciones"""
    __tablename__ = "game_results"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)
    game_date = Column(Date, index=True)
    
    home_team = Column(String(100))
    away_team = Column(String(100))
    
    predicted_home_score = Column(Float)
    predicted_away_score = Column(Float)
    predicted_total = Column(Float)
    predicted_favorite = Column(String(100))
    over_line = Column(Float)
    over_probability = Column(Float)
    
    actual_home_score = Column(Integer)
    actual_away_score = Column(Integer)
    actual_total = Column(Integer)
    actual_winner = Column(String(100))
    
    ml_correct = Column(Boolean, default=False)
    ou_correct = Column(Boolean, default=False)
    rl_correct = Column(Boolean, default=False)
    
    score_error = Column(Integer, default=0)
    total_error = Column(Float, default=0)
    
    ml_prediction = Column(String(100))
    ml_actual = Column(String(100))
    ou_prediction = Column(String(10))
    ou_actual = Column(String(10))
    
    result_fetched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLPredictionDB(Base):
    """Modelo para guardar predicciones del modelo ML"""
    __tablename__ = "ml_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)
    game_date = Column(Date, index=True)
    
    home_team = Column(String(100))
    away_team = Column(String(100))
    
    ml_predicted_home_score = Column(Float)
    ml_predicted_away_score = Column(Float)
    ml_predicted_total = Column(Float)
    ml_home_win_prob = Column(Float)
    ml_away_win_prob = Column(Float)
    ml_favorite = Column(String(100))
    
    rules_predicted_home_score = Column(Float)
    rules_predicted_away_score = Column(Float)
    rules_predicted_total = Column(Float)
    
    ensemble_predicted_home_score = Column(Float)
    ensemble_predicted_away_score = Column(Float)
    ensemble_predicted_total = Column(Float)
    ensemble_favorite = Column(String(100))
    ensemble_home_prob = Column(Float)
    ensemble_away_prob = Column(Float)
    
    ml_weight = Column(Float, default=0.6)
    rules_weight = Column(Float, default=0.4)
    
    over_line = Column(Float)
    over_probability = Column(Float)
    over_prediction = Column(String(10))
    
    casino_ou_line = Column(Float, nullable=True)
    casino_ml_home = Column(Integer, nullable=True)
    casino_ml_away = Column(Integer, nullable=True)
    
    edge_detected = Column(Boolean, default=False)
    edge_type = Column(String(20), nullable=True)
    edge_recommendation = Column(String(20), nullable=True)
    edge_score = Column(Float, nullable=True)
    edge_confidence = Column(String(10), nullable=True)
    
    actual_home_score = Column(Integer, nullable=True)
    actual_away_score = Column(Integer, nullable=True)
    actual_total = Column(Integer, nullable=True)
    actual_winner = Column(String(100), nullable=True)
    
    ml_correct = Column(Boolean, nullable=True)
    ou_correct = Column(Boolean, nullable=True)
    
    bet_placed = Column(Boolean, default=False)
    bet_result = Column(String(10), nullable=True)
    bet_profit = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MLModelMetadataDB(Base):
    """Modelo para metadata de modelos ML"""
    __tablename__ = "ml_model_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    model_type = Column(String(50))
    version = Column(String(50), unique=True, index=True)
    
    model_path = Column(String(200))
    feature_names = Column(String(500))
    
    training_date = Column(Date)
    training_samples = Column(Integer)
    test_samples = Column(Integer)
    
    home_mae = Column(Float, nullable=True)
    away_mae = Column(Float, nullable=True)
    total_mae = Column(Float, nullable=True)
    win_accuracy = Column(Float, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MLFeatureStoreDB(Base):
    """Modelo para almacenar features pre-computados por juego"""
    __tablename__ = "ml_feature_store"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)
    game_date = Column(Date, index=True)
    
    home_team_id = Column(Integer)
    away_team_id = Column(Integer)
    
    home_runs_scored_avg = Column(Float)
    home_runs_allowed_avg = Column(Float)
    home_win_pct = Column(Float)
    home_pythagorean_pct = Column(Float)
    
    away_runs_scored_avg = Column(Float)
    away_runs_allowed_avg = Column(Float)
    away_win_pct = Column(Float)
    away_pythagorean_pct = Column(Float)
    
    home_pitcher_era = Column(Float)
    home_pitcher_fip = Column(Float)
    home_pitcher_xfip = Column(Float)
    home_pitcher_k_per_9 = Column(Float)
    home_pitcher_bb_per_9 = Column(Float)
    
    away_pitcher_era = Column(Float)
    away_pitcher_fip = Column(Float)
    away_pitcher_xfip = Column(Float)
    away_pitcher_k_per_9 = Column(Float)
    away_pitcher_bb_per_9 = Column(Float)
    
    home_bullpen_era = Column(Float)
    away_bullpen_era = Column(Float)
    
    home_batting_ops = Column(Float)
    away_batting_ops = Column(Float)
    
    park_factor = Column(Float)
    
    rest_days_home = Column(Integer)
    rest_days_away = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyPredictionCache(Base):
    """Modelo para almacenar predicciones diarias en caché"""
    __tablename__ = "daily_predictions_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, unique=True, index=True)
    game_date = Column(Date, index=True)
    
    home_team = Column(String(100))
    away_team = Column(String(100))
    
    game_info_json = Column(String(1000))
    prediction_json = Column(String(4000))
    casino_line_json = Column(String(2000))
    
    created_at = Column(DateTime, default=datetime.utcnow)


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
        PredictionRecordDB.actual_home_score.isnot(None)
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


def save_game_result(db, result_data: dict):
    """Guarda el resultado de un partido con comparación de predicción"""
    existing = db.query(GameResultDB).filter(
        GameResultDB.game_id == result_data.get("game_id")
    ).first()
    
    if existing:
        for key, value in result_data.items():
            setattr(existing, key, value)
        db.commit()
        return existing
    else:
        result = GameResultDB(**result_data)
        db.add(result)
        db.commit()
        return result


def get_game_results(db, days: int = 60):
    """Obtiene resultados de los últimos N días"""
    from datetime import timedelta
    cutoff_date = date.today() - timedelta(days=days)
    
    return db.query(GameResultDB).filter(
        GameResultDB.game_date >= cutoff_date
    ).order_by(GameResultDB.game_date.desc()).all()


def get_accuracy_stats(db, days: int = 60):
    """Calcula estadísticas de precisión del modelo"""
    results = get_game_results(db, days)
    
    if not results:
        return {
            "total_games": 0,
            "ml_accuracy": 0.0,
            "ou_accuracy": 0.0,
            "rl_accuracy": 0.0,
            "avg_score_error": 0.0,
            "avg_total_error": 0.0
        }
    
    total = len(results)
    ml_correct = sum(1 for r in results if r.ml_correct)
    ou_correct = sum(1 for r in results if r.ou_correct)
    rl_correct = sum(1 for r in results if r.rl_correct)
    total_score_errors = sum(r.score_error or 0 for r in results)
    total_errors = sum(r.total_error or 0 for r in results)
    
    return {
        "total_games": total,
        "ml_accuracy": round(ml_correct / total * 100, 1) if total > 0 else 0.0,
        "ml_correct": ml_correct,
        "ou_accuracy": round(ou_correct / total * 100, 1) if total > 0 else 0.0,
        "ou_correct": ou_correct,
        "rl_accuracy": round(rl_correct / total * 100, 1) if total > 0 else 0.0,
        "rl_correct": rl_correct,
        "avg_score_error": round(total_score_errors / total, 2) if total > 0 else 0.0,
        "avg_total_error": round(total_errors / total, 2) if total > 0 else 0.0,
        "days_analyzed": days
    }


def save_ml_prediction(db, prediction_data: dict):
    """Guarda predicción ML en la base de datos"""
    existing = db.query(MLPredictionDB).filter(
        MLPredictionDB.game_id == prediction_data.get("game_id")
    ).first()
    
    if existing:
        for key, value in prediction_data.items():
            if value is not None:
                setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.commit()
        return existing
    else:
        prediction = MLPredictionDB(**prediction_data)
        db.add(prediction)
        db.commit()
        return prediction


def get_ml_predictions(db, limit: int = 100):
    """Obtiene predicciones ML"""
    return db.query(MLPredictionDB).order_by(
        MLPredictionDB.game_date.desc()
    ).limit(limit).all()


def get_ml_predictions_with_results(db):
    """Obtiene predicciones ML con resultados reales"""
    return db.query(MLPredictionDB).filter(
        MLPredictionDB.actual_home_score.isnot(None)
    ).order_by(MLPredictionDB.game_date.desc()).all()


def update_ml_prediction_result(db, game_id: int, home_score: int, away_score: int):
    """Actualiza resultado real de predicción ML"""
    prediction = db.query(MLPredictionDB).filter(
        MLPredictionDB.game_id == game_id
    ).first()
    
    if prediction:
        prediction.actual_home_score = home_score
        prediction.actual_away_score = home_score + away_score
        prediction.actual_total = home_score + away_score
        prediction.actual_winner = "Home" if home_score > away_score else "Away"
        
        if prediction.ml_favorite == prediction.actual_winner:
            prediction.ml_correct = True
        
        actual_over = (home_score + away_score) > prediction.over_line
        pred_over = prediction.over_probability > 0.5
        prediction.ou_correct = actual_over == pred_over
        
        prediction.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False


def save_ml_model_metadata(db, metadata: dict):
    """Guarda metadata de modelo ML"""
    existing = db.query(MLModelMetadataDB).filter(
        MLModelMetadataDB.version == metadata.get("version")
    ).first()
    
    if existing:
        for key, value in metadata.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        return existing
    else:
        model_meta = MLModelMetadataDB(**metadata)
        db.add(model_meta)
        db.commit()
        return model_meta


def get_active_ml_model(db, model_type: str = None):
    """Obtiene modelo ML activo"""
    query = db.query(MLModelMetadataDB).filter(MLModelMetadataDB.is_active == True)
    
    if model_type:
        query = query.filter(MLModelMetadataDB.model_type == model_type)
    
    return query.order_by(MLModelMetadataDB.created_at.desc()).first()


def save_ml_features(db, features_data: dict):
    """Guarda features pre-computados para un juego"""
    existing = db.query(MLFeatureStoreDB).filter(
        MLFeatureStoreDB.game_id == features_data.get("game_id")
    ).first()
    
    if existing:
        for key, value in features_data.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        return existing
    else:
        features = MLFeatureStoreDB(**features_data)
        db.add(features)
        db.commit()
        return features


def get_ml_features_for_games(db, start_date: date, end_date: date):
    """Obtiene features para un rango de fechas"""
    return db.query(MLFeatureStoreDB).filter(
        MLFeatureStoreDB.game_date >= start_date,
        MLFeatureStoreDB.game_date <= end_date
    ).all()


# ==================== USER FUNCTIONS ====================

def get_all_users(db):
    """Obtiene todos los usuarios"""
    return db.query(UserDB).filter(UserDB.is_active == True).all()


def get_user_by_username(db, username: str):
    """Obtiene usuario por nombre de usuario"""
    return db.query(UserDB).filter(UserDB.username == username).first()


def get_user_by_id(db, user_id: int):
    """Obtiene usuario por ID"""
    return db.query(UserDB).filter(UserDB.id == user_id).first()


def create_user(db, username: str, password_hash: str, is_admin: bool = False):
    """Crea un nuevo usuario"""
    user = UserDB(
        username=username,
        password_hash=password_hash,
        is_admin=is_admin,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db, user_id: int):
    """Elimina (desactiva) un usuario"""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if user:
        user.is_active = False
        db.commit()
        return True
    return False


def count_users(db):
    """Cuenta el número de usuarios activos"""
    return db.query(UserDB).filter(UserDB.is_active == True).count()


# ==================== DAILY PREDICTION CACHE FUNCTIONS ====================

def save_daily_prediction_cache(db, cache_data: dict):
    """Guarda una predicción en el caché diario"""
    existing = db.query(DailyPredictionCache).filter(
        DailyPredictionCache.game_id == cache_data.get("game_id")
    ).first()
    
    if existing:
        for key, value in cache_data.items():
            if value is not None:
                setattr(existing, key, value)
        db.commit()
        return existing
    else:
        cache = DailyPredictionCache(**cache_data)
        db.add(cache)
        db.commit()
        return cache


def get_daily_predictions_cache(db, target_date: date = None):
    """Obtiene las predicciones en caché para una fecha"""
    if target_date is None:
        target_date = date.today()
    
    return db.query(DailyPredictionCache).filter(
        DailyPredictionCache.game_date == target_date
    ).order_by(DailyPredictionCache.game_id).all()


def get_daily_prediction_by_game(db, game_id: int):
    """Obtiene una predicción en caché por game_id"""
    return db.query(DailyPredictionCache).filter(
        DailyPredictionCache.game_id == game_id
    ).first()


def delete_old_daily_predictions(db, days: int = 1):
    """Elimina predicciones en caché mayores a N días"""
    from datetime import timedelta
    cutoff_date = date.today() - timedelta(days=days)
    
    deleted = db.query(DailyPredictionCache).filter(
        DailyPredictionCache.game_date < cutoff_date
    ).delete()
    
    db.commit()
    return deleted
