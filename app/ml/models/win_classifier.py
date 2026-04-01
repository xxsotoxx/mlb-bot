"""
Win Classifier Neural Network
Clasifica resultado del partido: Home Win / Away Win / Tie
"""
import logging
import torch
import torch.nn as nn
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WinProbabilityNN(nn.Module):
    """
    Neural Network para predecir probabilidad de victoria
    Arquitectura: Input -> 128 -> 64 -> 32 -> 3 (HomeWin, AwayWin, Tie)
    """
    
    def __init__(self, input_dim: int):
        super().__init__()
        
        self.fc1 = nn.Linear(input_dim, 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.dropout1 = nn.Dropout(0.3)
        
        self.fc2 = nn.Linear(128, 64)
        self.bn2 = nn.BatchNorm1d(64)
        self.dropout2 = nn.Dropout(0.3)
        
        self.fc3 = nn.Linear(64, 32)
        self.bn3 = nn.BatchNorm1d(32)
        self.dropout3 = nn.Dropout(0.2)
        
        self.fc4 = nn.Linear(32, 3)
        
        self._init_weights()
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.fc1(x)
        x = self.bn1(x)
        x = torch.relu(x)
        x = self.dropout1(x)
        
        x = self.fc2(x)
        x = self.bn2(x)
        x = torch.relu(x)
        x = self.dropout2(x)
        
        x = self.fc3(x)
        x = self.bn3(x)
        x = torch.relu(x)
        x = self.dropout3(x)
        
        x = self.fc4(x)
        return x
    
    def predict_proba(self, features: np.ndarray) -> Dict[str, float]:
        """Retorna probabilidades para cada outcome"""
        self.eval()
        with torch.no_grad():
            x = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1).squeeze().numpy()
        
        return {
            "home_win_prob": float(round(probs[0], 3)),
            "away_win_prob": float(round(probs[1], 3)),
            "tie_prob": float(round(probs[2], 3))
        }


class WinClassifierModel:
    """
    Wrapper para entrenamiento e inferencia del clasificador de victoria
    """
    
    def __init__(self, input_dim: int = 43, device: str = "cpu"):
        self.input_dim = input_dim
        self.device = device
        self.model: Optional[WinProbabilityNN] = None
        self.is_trained = False
        self.classes = ["Home", "Away", "Tie"]
        
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
        """Entrena el modelo clasificador"""
        
        self.model = WinProbabilityNN(self.input_dim).to(self.device)
        
        X_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_tensor = torch.tensor(y_train, dtype=torch.long)
        
        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=5)
        
        best_loss = float('inf')
        patience_counter = 0
        best_state = None
        best_val_acc = 0.0
        
        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0
            
            for batch_x, batch_y in dataloader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                optimizer.zero_grad()
                
                outputs = self.model(batch_x)
                loss = criterion(outputs, batch_y)
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(dataloader)
            scheduler.step(avg_loss)
            
            if X_val is not None and y_val is not None:
                val_metrics = self._evaluate(X_val, y_val)
                logger.info(f"Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f} - Val Acc: {val_metrics['accuracy']:.2%}")
                
                if val_metrics['accuracy'] > best_val_acc:
                    best_val_acc = val_metrics['accuracy']
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
        return {"status": "trained", "epochs": epoch + 1, "best_val_acc": best_val_acc}
    
    def _evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
        """Evalúa el modelo"""
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(X_test, dtype=torch.float32).to(self.device)
            y_tensor = torch.tensor(y_test, dtype=torch.long).to(self.device)
            
            outputs = self.model(X_tensor)
            _, preds = torch.max(outputs, 1)
            
            accuracy = (preds == y_tensor).float().mean().item()
            
            from sklearn.metrics import confusion_matrix
            cm = confusion_matrix(y_test, preds.cpu().numpy())
            
        return {
            "accuracy": accuracy,
            "confusion_matrix": cm.tolist()
        }
    
    def predict_proba(self, features: np.ndarray) -> Dict[str, float]:
        """Predice probabilidades de victoria"""
        if not self.is_trained:
            logger.warning("Model not trained, returning default probabilities")
            return {"home_win_prob": 0.5, "away_win_prob": 0.5, "tie_prob": 0.0}
        
        return self.model.predict_proba(features)
    
    def predict(self, features: np.ndarray) -> str:
        """Predice el resultado del partido"""
        probs = self.predict_proba(features)
        
        if probs["home_win_prob"] >= probs["away_win_prob"] and \
           probs["home_win_prob"] >= probs["tie_prob"]:
            return "Home"
        elif probs["away_win_prob"] > probs["home_win_prob"] and \
             probs["away_win_prob"] >= probs["tie_prob"]:
            return "Away"
        else:
            return "Tie"
    
    def predict_batch_proba(self, features: np.ndarray) -> np.ndarray:
        """Predice probabilidades para múltiples juegos"""
        if not self.is_trained:
            return np.full((len(features), 3), [0.5, 0.5, 0.0])
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(features, dtype=torch.float32).to(self.device)
            outputs = self.model(X_tensor)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()
        
        return probs
    
    def get_feature_importance(self, X_sample: np.ndarray) -> Dict[str, float]:
        """Calcula importancia de features usando gradient-based method"""
        self.model.eval()
        
        X_tensor = torch.tensor(X_sample, dtype=torch.float32, requires_grad=True).to(self.device)
        
        output = self.model(X_tensor)
        pred_class = output.argmax(dim=1).item()
        
        output[0][pred_class].backward()
        
        grads = X_tensor.grad.cpu().numpy()[0]
        
        feature_importance = np.abs(grads)
        feature_importance = feature_importance / feature_importance.sum()
        
        return feature_importance.tolist()
    
    def save(self, path: str):
        """Guarda el modelo"""
        if self.model is None:
            raise ValueError("No model to save")
        
        torch.save({
            'model_state': self.model.state_dict(),
            'input_dim': self.input_dim,
            'is_trained': self.is_trained
        }, path)
        logger.info(f"Win classifier saved to {path}")
    
    def load(self, path: str):
        """Carga el modelo"""
        checkpoint = torch.load(path, map_location=self.device)
        
        self.input_dim = checkpoint['input_dim']
        self.is_trained = checkpoint['is_trained']
        
        self.model = WinProbabilityNN(self.input_dim).to(self.device)
        self.model.load_state_dict(checkpoint['model_state'])
        
        logger.info(f"Win classifier loaded from {path}")


def create_win_classifier(input_dim: int = 43) -> WinClassifierModel:
    """Factory function para crear clasificador"""
    return WinClassifierModel(input_dim=input_dim)