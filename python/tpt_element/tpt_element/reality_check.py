"""Reality Check — fast ML-based prediction of thermal/noise drift."""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class DriftPrediction:
    node_id: str
    predicted_drift_pct: float
    confidence: float
    failure_probability: float
    mitigations: list[str]


@dataclass
class CircuitFeatures:
    resistance_values: list[float]
    tolerance: float
    temperature_k: float
    voltage_v: float
    component_count: int


class RealityCheckModel:
    """Lightweight ML model trained on SPICE simulation data.

    Predicts thermal/noise drift instantly instead of running
    slow brute-force SPICE simulations for routine checks.
    """

    def __init__(self):
        self.weights: dict[str, np.ndarray] = {}
        self._initialized = False

    def train(self, features: list[CircuitFeatures], drift_labels: list[float]) -> None:
        """Train on SPICE simulation results."""
        X = self._features_to_array(features)
        y = np.array(drift_labels)

        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0) + 1e-8
        X_norm = (X - X_mean) / X_std

        W = np.linalg.lstsq(X_norm, y, rcond=None)[0]

        self.weights = {
            "W": W,
            "X_mean": X_mean,
            "X_std": X_std,
        }
        self._initialized = True

    def predict(self, features: CircuitFeatures) -> DriftPrediction:
        """Predict drift for a single circuit configuration."""
        if not self._initialized:
            return DriftPrediction(
                node_id="unknown",
                predicted_drift_pct=0.0,
                confidence=0.0,
                failure_probability=0.0,
                mitigations=["Model not trained yet. Run SPICE simulations first."],
            )

        X = self._features_to_array([features])
        X_norm = (X - self.weights["X_mean"]) / self.weights["X_std"]
        predicted_drift = float((X_norm @ self.weights["W"])[0])

        confidence = max(0, min(1, 1.0 - abs(predicted_drift) / 10.0))
        failure_prob = min(1.0, abs(predicted_drift) / 5.0)

        mitigations = []
        if failure_prob > 0.5:
            mitigations.append("High drift risk: consider tighter tolerance components")
        if features.tolerance > 0.05:
            mitigations.append(f"Reduce tolerance from {features.tolerance*100:.0f}% to 1%")
        if features.temperature_k > 350:
            mitigations.append("Add active cooling to reduce operating temperature")
        if not mitigations:
            mitigations.append("Circuit appears stable under current conditions")

        return DriftPrediction(
            node_id="analog_core",
            predicted_drift_pct=round(predicted_drift, 4),
            confidence=round(confidence, 4),
            failure_probability=round(failure_prob, 4),
            mitigations=mitigations,
        )

    def save(self, path: Path) -> None:
        """Save model weights to file."""
        np.savez(path, **self.weights)

    def load(self, path: Path) -> None:
        """Load model weights from file."""
        data = np.load(path)
        self.weights = {k: data[k] for k in data.files}
        self._initialized = True

    def _features_to_array(self, features: list[CircuitFeatures]) -> np.ndarray:
        rows = []
        for f in features:
            row = [
                np.mean(f.resistance_values) if f.resistance_values else 0,
                np.std(f.resistance_values) if f.resistance_values else 0,
                np.min(f.resistance_values) if f.resistance_values else 0,
                np.max(f.resistance_values) if f.resistance_values else 0,
                f.tolerance,
                f.temperature_k,
                f.voltage_v,
                f.component_count,
            ]
            rows.append(row)
        return np.array(rows, dtype=np.float64)


def generate_training_data(n_samples: int = 1000) -> tuple[list[CircuitFeatures], list[float]]:
    """Generate synthetic SPICE-like training data."""
    rng = np.random.default_rng(42)
    features_list = []
    drifts = []

    for _ in range(n_samples):
        n_comp = rng.integers(4, 64)
        resistances = rng.lognormal(mean=6, sigma=2, size=n_comp).tolist()
        tolerance = rng.choice([0.01, 0.05, 0.10])
        temp_k = rng.uniform(273, 373)
        voltage = rng.uniform(1.8, 5.0)

        base_drift = tolerance * 10 + (temp_k - 300) * 0.01
        noise = rng.normal(0, 0.5)
        drift = base_drift + noise

        features_list.append(CircuitFeatures(
            resistance_values=resistances,
            tolerance=tolerance,
            temperature_k=temp_k,
            voltage_v=voltage,
            component_count=n_comp,
        ))
        drifts.append(drift)

    return features_list, drifts
