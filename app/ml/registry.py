"""
Model Registry - Versioning y gestión de modelos
"""
import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registro de modelos ML
    Maneja versioning, loading/unloading, metadata
    """
    
    def __init__(self, models_dir: str = "models/ml"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_models = {
            "poisson_home": None,
            "poisson_away": None,
            "win_classifier": None
        }
        
        self.active_version: Optional[str] = None
        self.model_metadata: Dict[str, Any] = {}
    
    def save_model_version(
        self,
        version: str,
        model_type: str,
        model_path: str,
        metrics: Dict[str, Any],
        features_info: Dict[str, Any] = None
    ) -> bool:
        """Guarda metadata de una versión de modelo"""
        
        registry_file = self.models_dir / "registry.json"
        
        if registry_file.exists():
            with open(registry_file) as f:
                registry = json.load(f)
        else:
            registry = {"versions": {}}
        
        registry["versions"][version] = {
            "model_type": model_type,
            "model_path": model_path,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics,
            "features_info": features_info or {}
        }
        
        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        
        logger.info(f"Saved model version: {version} ({model_type})")
        return True
    
    def get_latest_version(self, model_type: str = None) -> Optional[str]:
        """Obtiene la versión más reciente de los modelos"""
        
        registry_file = self.models_dir / "registry.json"
        
        if not registry_file.exists():
            return None
        
        with open(registry_file) as f:
            registry = json.load(f)
        
        if model_type:
            for version, meta in registry.get("versions", {}).items():
                if meta.get("model_type") == model_type:
                    return version
            return None
        
        versions = list(registry.get("versions", {}).keys())
        if not versions:
            return None
        
        return sorted(versions, reverse=True)[0]
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """Lista todas las versiones disponibles"""
        
        registry_file = self.models_dir / "registry.json"
        
        if not registry_file.exists():
            return []
        
        with open(registry_file) as f:
            registry = json.load(f)
        
        versions = []
        for version, meta in registry.get("versions", {}).items():
            versions.append({
                "version": version,
                "type": meta.get("model_type"),
                "created_at": meta.get("created_at"),
                "metrics": meta.get("metrics", {})
            })
        
        return sorted(versions, key=lambda x: x["created_at"], reverse=True)
    
    def load_version(self, version: str) -> bool:
        """Carga una versión específica de los modelos"""
        
        from app.ml.models.poisson_model import PoissonModel
        from app.ml.models.win_classifier import WinClassifierModel
        
        registry_file = self.models_dir / "registry.json"
        
        if not registry_file.exists():
            logger.error("Registry not found")
            return False
        
        with open(registry_file) as f:
            registry = json.load(f)
        
        version_info = registry.get("versions", {}).get(version)
        if not version_info:
            logger.error(f"Version {version} not found")
            return False
        
        try:
            if "poisson" in version_info.get("model_type", ""):
                if "home" in version_info.get("model_path", ""):
                    self.current_models["poisson_home"] = PoissonModel()
                    self.current_models["poisson_home"].load(version_info["model_path"])
                elif "away" in version_info.get("model_path", ""):
                    self.current_models["poisson_away"] = PoissonModel()
                    self.current_models["poisson_away"].load(version_info["model_path"])
            
            if "classifier" in version_info.get("model_type", ""):
                self.current_models["win_classifier"] = WinClassifierModel()
                self.current_models["win_classifier"].load(version_info["model_path"])
            
            self.active_version = version
            self.model_metadata = version_info
            
            logger.info(f"Loaded models version: {version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load version {version}: {e}")
            return False
    
    def load_latest(self) -> bool:
        """Carga la versión más reciente"""
        latest = self.get_latest_version()
        if latest:
            return self.load_version(latest)
        return False
    
    def unload_models(self):
        """Des-carga los modelos de memoria"""
        self.current_models = {
            "poisson_home": None,
            "poisson_away": None,
            "win_classifier": None
        }
        self.active_version = None
        logger.info("Models unloaded from memory")
    
    def get_loaded_models(self) -> Dict[str, Any]:
        """Retorna información de modelos cargados"""
        return {
            "active_version": self.active_version,
            "loaded": {
                "poisson_home": self.current_models["poisson_home"] is not None,
                "poisson_away": self.current_models["poisson_away"] is not None,
                "win_classifier": self.current_models["win_classifier"] is not None
            },
            "metadata": self.model_metadata
        }
    
    def is_ready(self) -> bool:
        """Verifica si los modelos están listos para inference"""
        return (
            self.current_models["poisson_home"] is not None and
            self.current_models["poisson_away"] is not None and
            self.current_models["win_classifier"] is not None
        )


model_registry = ModelRegistry()