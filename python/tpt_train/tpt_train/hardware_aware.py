"""Hardware-in-the-Loop Training — deviation-aware fine-tuning."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class LayerDeviation:
    layer_name: str
    hardware_output: list[float]
    reference_output: list[float]
    mse: float = 0.0
    cosine_similarity: float = 0.0

    def __post_init__(self):
        if self.hardware_output and self.reference_output:
            self.mse = self._compute_mse()
            self.cosine_similarity = self._compute_cosine()

    def _compute_mse(self) -> float:
        n = min(len(self.hardware_output), len(self.reference_output))
        if n == 0:
            return 0.0
        return sum((h - r) ** 2 for h, r in zip(self.hardware_output[:n], self.reference_output[:n])) / n

    def _compute_cosine(self) -> float:
        n = min(len(self.hardware_output), len(self.reference_output))
        if n == 0:
            return 0.0
        dot = sum(h * r for h, r in zip(self.hardware_output[:n], self.reference_output[:n]))
        norm_h = sum(h ** 2 for h in self.hardware_output[:n]) ** 0.5
        norm_r = sum(r ** 2 for r in self.reference_output[:n]) ** 0.5
        if norm_h == 0 or norm_r == 0:
            return 0.0
        return dot / (norm_h * norm_r)


@dataclass
class DeviationProfile:
    model_name: str
    hardware_target: str
    layer_deviations: list[LayerDeviation]
    total_mse: float = 0.0
    avg_cosine: float = 0.0

    def __post_init__(self):
        if self.layer_deviations:
            self.total_mse = sum(d.mse for d in self.layer_deviations) / len(self.layer_deviations)
            self.avg_cosine = sum(d.cosine_similarity for d in self.layer_deviations) / len(self.layer_deviations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "hardware_target": self.hardware_target,
            "total_mse": round(self.total_mse, 6),
            "avg_cosine": round(self.avg_cosine, 4),
            "layer_count": len(self.layer_deviations),
            "layers": [
                {
                    "name": d.layer_name,
                    "mse": round(d.mse, 6),
                    "cosine": round(d.cosine_similarity, 4),
                }
                for d in self.layer_deviations
            ],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> DeviationProfile:
        data = json.loads(path.read_text())
        layers = [
            LayerDeviation(
                layer_name=l["name"],
                hardware_output=[],
                reference_output=[],
                mse=l["mse"],
                cosine_similarity=l["cosine"],
            )
            for l in data.get("layers", [])
        ]
        return cls(
            model_name=data["model_name"],
            hardware_target=data["hardware_target"],
            layer_deviations=layers,
        )


class TPTHardwareAwareCallback:
    """Training callback that applies deviation-based regularization."""

    def __init__(self, deviation_profile: DeviationProfile, weight: float = 0.1):
        self.deviation_profile = deviation_profile
        self.weight = weight
        self._layer_map = {d.layer_name: d for d in deviation_profile.layer_deviations}

    def get_regularization_loss(self, layer_name: str, output: Any) -> float:
        deviation = self._layer_map.get(layer_name)
        if not deviation:
            return 0.0
        mse = deviation.mse
        return self.weight * mse

    def get_layer_importance(self) -> dict[str, float]:
        if not self.deviation_profile.layer_deviations:
            return {}
        max_mse = max(d.mse for d in self.deviation_profile.layer_deviations) or 1.0
        return {
            d.layer_name: d.mse / max_mse
            for d in self.deviation_profile.layer_deviations
        }

    def suggest_focus_layers(self, top_n: int = 5) -> list[str]:
        importance = self.get_layer_importance()
        sorted_layers = sorted(importance.items(), key=lambda x: -x[1])
        return [name for name, _ in sorted_layers[:top_n]]
