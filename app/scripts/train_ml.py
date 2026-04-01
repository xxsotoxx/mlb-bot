"""
ML Training Script - Entrena los modelos con datos históricos
Ejecutar: python -m app.scripts.train_ml
"""
import asyncio
import logging
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    """Entrena los modelos ML con datos históricos"""
    
    logger.info("=" * 60)
    logger.info("ML TRAINING PIPELINE")
    logger.info("=" * 60)
    
    try:
        from app.models.database import get_db, get_game_results
        from app.ml.features import feature_engine
        from app.ml.trainer import TrainingPipeline
        
        logger.info("Loading historical data...")
        
        db_gen = get_db()
        db = next(db_gen)
        
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=180)
        
        game_results = db.query(
            __import__('app.models.database', fromlist=['GameResultDB'])
        ).filter(
            __import__('app.models.database', fromlist=['GameResultDB']).game_date >= start_date,
            __import__('app.models.database', fromlist=['GameResultDB']).game_date <= end_date
        ).all()
        
        logger.info(f"Found {len(game_results)} games with results")
        
        if len(game_results) < 50:
            logger.warning("Not enough data for training. Need at least 50 games.")
            logger.info("Continue with rules-only predictions.")
            return
        
        predictions_data = []
        for result in game_results:
            pred_dict = {
                "game_id": result.game_id,
                "game_date": result.game_date,
                "home_team": result.home_team,
                "away_team": result.away_team,
                "predicted_home_score": result.predicted_home_score,
                "predicted_away_score": result.predicted_away_score,
                "predicted_total": result.predicted_total,
                "actual_home_score": result.actual_home_score,
                "actual_away_score": result.actual_away_score,
                "actual_winner": result.actual_winner,
                "home_team_id": 0,
                "away_team_id": 0,
                "home_team_stats": {},
                "away_team_stats": {},
                "home_pitcher_stats": {},
                "away_pitcher_stats": {},
                "home_bullpen_stats": {},
                "away_bullpen_stats": {},
                "park_factor": 1.0
            }
            predictions_data.append(pred_dict)
        
        db.close()
        
        pipeline = TrainingPipeline(models_dir="models/ml")
        pipeline.feature_engine = feature_engine
        
        logger.info("Computing features...")
        X, y_home, y_away, y_winner = pipeline.compute_features_batch(
            predictions_data, feature_engine
        )
        
        if len(X) < 50:
            logger.warning("Not enough valid features for training")
            return
        
        logger.info(f"Training data: {len(X)} samples, {X.shape[1]} features")
        
        logger.info("Training models...")
        result = pipeline.train_models(
            X, y_home, y_away, y_winner,
            test_size=0.2,
            epochs_poisson=100,
            epochs_classifier=100
        )
        
        logger.info(f"Training result: {result}")
        
        logger.info("Saving models...")
        version = date.today().strftime("%Y%m%d")
        model_paths = pipeline.save_models(version=version)
        
        logger.info("=" * 60)
        logger.info("TRAINING COMPLETE")
        logger.info(f"Models saved with version: {version}")
        logger.info(f"Home MAE: {result['metrics']['home_mae']}")
        logger.info(f"Away MAE: {result['metrics']['away_mae']}")
        logger.info(f"Total MAE: {result['metrics']['total_mae']}")
        logger.info(f"Win Accuracy: {result['metrics']['win_accuracy']:.1%}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())