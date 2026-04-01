"""
ML Routes - Training and model status endpoints (require authentication)
"""
import os
import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db, get_game_results, UserDB
from app.auth.deps import get_current_user
from app.ml.features import feature_engine
from app.ml.trainer import TrainingPipeline
from app.ml.registry import model_registry

router = APIRouter(prefix="/api/ml", tags=["ml"])

logger = logging.getLogger(__name__)


class TrainingResponse(BaseModel):
    status: str
    message: str
    details: Optional[dict] = None


class ModelStatusResponse(BaseModel):
    has_models: bool
    version: Optional[str] = None
    metrics: Optional[dict] = None
    last_trained: Optional[str] = None


class VersionResponse(BaseModel):
    versions: list


# ==================== ML Training ====================

async def train_ml_models_internal() -> dict:
    """Función interna para entrenar modelos ML"""
    try:
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
        
        logger.info(f"Found {len(game_results)} games with results for training")
        
        if len(game_results) < 50:
            db.close()
            return {
                "status": "skipped",
                "message": f"Insufficient data ({len(game_results)} games). Need at least 50.",
                "details": {"available": len(game_results), "required": 50}
            }
        
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
            return {
                "status": "skipped",
                "message": "Not enough valid features for training",
                "details": {"valid_samples": len(X)}
            }
        
        logger.info(f"Training data: {len(X)} samples, {X.shape[1]} features")
        
        logger.info("Training models...")
        result = pipeline.train_models(
            X, y_home, y_away, y_winner,
            test_size=0.2,
            epochs_poisson=50,
            epochs_classifier=50
        )
        
        logger.info(f"Training result: {result}")
        
        logger.info("Saving models...")
        version = date.today().strftime("%Y%m%d")
        model_paths = pipeline.save_models(version=version)
        
        logger.info("=" * 50)
        logger.info("TRAINING COMPLETE")
        logger.info(f"Models saved with version: {version}")
        logger.info(f"Home MAE: {result['metrics']['home_mae']}")
        logger.info(f"Away MAE: {result['metrics']['away_mae']}")
        logger.info(f"Total MAE: {result['metrics']['total_mae']}")
        logger.info(f"Win Accuracy: {result['metrics']['win_accuracy']:.1%}")
        logger.info("=" * 50)
        
        return {
            "status": "success",
            "message": f"Models trained and saved (version: {version})",
            "details": {
                "version": version,
                "train_samples": result.get("train_samples", len(X)),
                "test_samples": result.get("test_samples", 0),
                "metrics": result.get("metrics", {})
            }
        }
        
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Training failed: {str(e)}",
            "details": {}
        }


@router.post("/train", response_model=TrainingResponse)
async def train_ml_models(
    current_user: UserDB = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Entrena los modelos ML con datos históricos
    Requiere autenticación (cualquier usuario activo)
    """
    result = await train_ml_models_internal()
    
    if result["status"] == "success":
        return TrainingResponse(
            status="success",
            message=result["message"],
            details=result.get("details")
        )
    elif result["status"] == "skipped":
        return TrainingResponse(
            status="skipped",
            message=result["message"],
            details=result.get("details")
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )


@router.get("/status", response_model=ModelStatusResponse)
async def get_ml_status(
    current_user: UserDB = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Obtiene el estado de los modelos ML
    Requiere autenticación
    """
    models_dir = Path("models/ml")
    
    if not models_dir.exists() or not list(models_dir.glob("*.pt")):
        return ModelStatusResponse(
            has_models=False,
            version=None,
            metrics=None,
            last_trained=None
        )
    
    latest_version = model_registry.get_latest_version()
    
    if latest_version:
        versions = model_registry.list_versions()
        latest = versions[0] if versions else None
        
        return ModelStatusResponse(
            has_models=True,
            version=latest_version,
            metrics=latest.get("metrics") if latest else None,
            last_trained=latest.get("created_at") if latest else None
        )
    
    return ModelStatusResponse(
        has_models=False,
        version=None,
        metrics=None,
        last_trained=None
    )


@router.get("/versions", response_model=VersionResponse)
async def get_ml_versions(
    current_user: UserDB = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Lista todas las versiones de modelos disponibles
    Requiere autenticación
    """
    versions = model_registry.list_versions()
    
    return VersionResponse(
        versions=[
            {
                "version": v.get("version"),
                "type": v.get("type"),
                "created_at": v.get("created_at"),
                "metrics": v.get("metrics", {})
            }
            for v in versions
        ]
    )


# ==================== ML Training Job for Scheduler ====================

async def train_ml_models_job():
    """
    Job de scheduler para entrenar modelos ML diariamente a las 6:30 AM
    """
    logger.info("=" * 50)
    logger.info("INICIANDO JOB: ML Model Training (6:30 AM)")
    logger.info(f"Fecha: {date.today()}")
    logger.info("=" * 50)
    
    result = await train_ml_models_internal()
    
    if result["status"] == "success":
        logger.info(f"ML Training SUCCESS: {result['message']}")
    elif result["status"] == "skipped":
        logger.info(f"ML Training SKIPPED: {result['message']}")
    else:
        logger.error(f"ML Training FAILED: {result['message']}")
    
    return result