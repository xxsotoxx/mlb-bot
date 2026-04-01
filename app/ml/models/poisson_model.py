"""
Poisson Regression Model for Run Prediction
Usa PyTorch para predecir carreras usando distribución de Poisson
"""
import logging
import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PoissonRegression(nn.Module):
    """
    Modelo de regresión de Poisson para predecir carreras
    Usa una capa lineal con exponencial como función de link
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 32):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_dim, 1)
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return torch.exp(x)
    
    def predict_runs(self, features: np.ndarray) -> float:
        """Predice carreras dado un vector de features"""
        self.eval()
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
            pred = self.forward(x).item()
        return round(pred, 2)


class PoissonModel:
    """
    Wrapper para entrenamiento e inferencia del modelo Poisson
    """
    
    def __init__(self, input_dim: int = 43, hidden_dim: int = 32, device: str = "cpu"):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.device = device
        self.model: Optional[PoissonRegression] = None
        self.is_trained = False
        
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        epochs: int = 100,
        lr: float = 0.001,
        batch_size: int = 32,
        patience: int = 10
    ) -> Dict[str, Any]:
        """Entrena el modelo Poisson"""
        
        self.model = PoissonRegression(self.input_dim, self.hidden_dim).to(self.device)
        
        X_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_tensor = torch.tensor(y_train, dtype=torch.float32).reshape(-1, 1)
        
        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        best_loss = float('inf')
        patience_counter = 0
        best_state = None
        
        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0
            
            for batch_x, batch_y in dataloader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                
                pred = self.model(batch_x)
                
                loss = torch.mean(pred - batch_y * torch.log(pred + 1e-8))
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(dataloader)
            
            if X_val is not None and y_val is not None:
                val_mae = self.evaluate(X_val, y_val)
                logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f} - Val MAE: {val_mae:.2f}")
                
                if val_mae < best_loss:
                    best_loss = val_mae
                    best_state = self.model.state_dict().copy()
                    patience_counter = 0
                else:
                    patience_counter += 1
                    
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    if best_state:
                        self.model.load_state_dict(best_state)
                    break
            else:
                if (epoch + 1) % 20 == 0:
                    logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}")
        
        self.is_trained = True
        return {"status": "trained", "epochs": epoch + 1}
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        """Evalúa el modelo en datos de test"""
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(X_test, dtype=torch.float32).to(self.device)
            y_tensor = torch.tensor(y_test, dtype=torch.float32)
            
            predictions = self.model(X_tensor).cpu().numpy().flatten()
            
            mae = np.mean(np.abs(predictions - y_test))
            
        return mae
    
    def predict(self, features: np.ndarray) -> float:
        """Predice carreras para nuevos features"""
        if not self.is_trained:
            logger.warning("Model not trained, returning default prediction")
            return 4.5
        
        return self.model.predict_runs(features)
    
    def predict_batch(self, features: np.ndarray) -> np.ndarray:
        """Predice carreras para múltiples juegos"""
        if not self.is_trained:
            return np.full(len(features), 4.5)
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(features, dtype=torch.float32).to(self.device)
            predictions = self.model(X_tensor).cpu().numpy().flatten()
        
        return predictions
    
    def save(self, path: str):
        """Guarda el modelo a disco"""
        if self.model is None:
            raise ValueError("No model to save")
        
        torch.save({
            'model_state': self.model.state_dict(),
            'input_dim': self.input_dim,
            'hidden_dim': self.hidden_dim,
            'is_trained': self.is_trained
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """Carga el modelo desde disco"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.input_dim = checkpoint['input_dim']
        self.hidden_dim = checkpoint['hidden_dim']
        self.is_trained = checkpoint['is_trained']
        
        self.model = PoissonRegression(self.input_dim, self.hidden_dim).to(self.device)
        self.model.load_state_dict(checkpoint['model_state'])
        
        logger.info(f"Model loaded from {path}")


def create_poisson_model(input_dim: int = 43) -> PoissonModel:
    """Factory function para crear modelo Poisson"""
    return PoissonModel(input_dim=input_dim)