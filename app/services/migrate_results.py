"""
Migración de datos históricos de predicciones a la tabla game_results
"""
import logging
from datetime import date
from app.models.database import get_db, get_predictions_with_results, save_game_result

logger = logging.getLogger(__name__)


def migrate_historical_results():
    """
    Migra predicciones históricas con resultados a la tabla game_results
    para que el dashboard funcione correctamente
    """
    db_gen = get_db()
    db = next(db_gen)
    
    try:
        predictions = get_predictions_with_results(db)
        
        if not predictions:
            logger.info("No hay predicciones con resultados para migrar")
            return
        
        migrated = 0
        skipped = 0
        
        for p in predictions:
            # Verificar si ya existe en game_results
            from app.models.database import get_game_results
            existing_results = get_game_results(db, days=365)
            
            from app.models.database import GameResultDB
            existing = db.query(GameResultDB).filter(
                GameResultDB.game_id == p.game_id
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            actual_home = p.actual_home_score or 0
            actual_away = p.actual_away_score or 0
            actual_total = actual_home + actual_away
            
            predicted_favorite = p.predicted_favorite or ""
            actual_winner = p.home_team if actual_home > actual_away else (p.away_team if actual_away > actual_home else "Tie")
            
            ml_correct = predicted_favorite.lower() in actual_winner.lower() if actual_winner != "Tie" else False
            
            ou_line = p.over_line or 8.5
            over_prob = p.over_probability or 0.5
            ou_prediction = "OVER" if over_prob > 0.5 else "UNDER"
            ou_actual = "OVER" if actual_total > ou_line else "UNDER"
            ou_correct = (ou_prediction == "OVER" and actual_total > ou_line) or (ou_prediction == "UNDER" and actual_total < ou_line)
            
            result_data = {
                "game_id": p.game_id,
                "game_date": p.game_date,
                "home_team": p.home_team,
                "away_team": p.away_team,
                "predicted_home_score": p.predicted_home_score or 0,
                "predicted_away_score": p.predicted_away_score or 0,
                "predicted_total": p.predicted_total or 0,
                "predicted_favorite": predicted_favorite,
                "over_line": ou_line,
                "over_probability": over_prob,
                "actual_home_score": actual_home,
                "actual_away_score": actual_away,
                "actual_total": actual_total,
                "actual_winner": actual_winner,
                "ml_correct": ml_correct,
                "ou_correct": ou_correct,
                "rl_correct": False,
                "score_error": abs(actual_home - (p.predicted_home_score or 0)) + abs(actual_away - (p.predicted_away_score or 0)),
                "total_error": abs(actual_total - (p.predicted_total or 0)),
                "ml_prediction": predicted_favorite,
                "ml_actual": actual_winner,
                "ou_prediction": ou_prediction,
                "ou_actual": ou_actual
            }
            
            try:
                save_game_result(db, result_data)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrando game_id {p.game_id}: {e}")
        
        logger.info(f"Migración completada: {migrated} nuevos, {skipped} ya existentes")
        
    finally:
        db.close()


if __name__ == "__main__":
    migrate_historical_results()