from __future__ import annotations

import numpy as np

from ..perception.features import FeatureVector
from .base import BaseMapper
from .musical_params import MusicalEvent


class MLMapper(BaseMapper):
    """Machine-learning based feature-to-music mapping.

    Uses a scikit-learn model to predict musical parameters from features.
    Falls back to a simple neural-network-like transform if no model is loaded.
    """

    def __init__(self, model_path: str | None = None):
        self._model = None
        if model_path:
            self._load_model(model_path)

    def _load_model(self, path: str) -> None:
        try:
            import joblib

            self._model = joblib.load(path)
        except (ImportError, FileNotFoundError):
            self._model = None

    def _features_to_array(self, features: FeatureVector) -> np.ndarray:
        return np.array([
            features.change_rate,
            features.periodicity,
            features.intensity,
            features.direction,
            features.volatility,
            features.density,
        ]).reshape(1, -1)

    def map(self, features: FeatureVector) -> MusicalEvent:
        if self._model is not None:
            X = self._features_to_array(features)
            pred = self._model.predict(X)[0]
            return MusicalEvent(
                pitch_hint=float(np.clip(pred[0], 0, 1)),
                velocity=float(np.clip(pred[1], 0, 1)),
                duration_hint=float(np.clip(pred[2], 0, 1)),
                density_hint=float(np.clip(pred[3], 0, 1)),
                register_hint=float(np.clip(pred[4], 0, 1)),
                urgency=float(np.clip(pred[5], 0, 1)),
                symbol=features.symbol,
            )

        # Default: deterministic nonlinear transform (acts as a learned-like mapper)
        return self._default_transform(features)

    def _default_transform(self, f: FeatureVector) -> MusicalEvent:
        """A hand-tuned nonlinear mapping that behaves differently from rule-based."""
        sigmoid = lambda x: 1.0 / (1.0 + np.exp(-5 * x))

        return MusicalEvent(
            pitch_hint=float(sigmoid(f.direction + 0.3 * f.change_rate)),
            velocity=float(np.clip(f.intensity ** 0.7 * 0.8 + f.volatility * 0.2, 0, 1)),
            duration_hint=float(np.clip(1.0 - sigmoid(f.volatility + f.density - 0.5), 0, 1)),
            density_hint=float(np.clip(f.density * 0.6 + f.periodicity * 0.4, 0, 1)),
            register_hint=float(sigmoid(f.direction * 0.5 + f.intensity * 0.5)),
            urgency=float(np.clip(f.volatility * f.intensity, 0, 1)),
            symbol=f.symbol,
        )
