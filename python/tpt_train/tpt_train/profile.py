"""TPT Profile — per-layer activation stats and weight distributions."""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LayerStats:
    name: str
    layer_type: str
    input_min: float = 0.0
    input_max: float = 0.0
    input_mean: float = 0.0
    input_std: float = 0.0
    weight_min: float = 0.0
    weight_max: float = 0.0
    weight_mean: float = 0.0
    weight_std: float = 0.0
    gradient_norm: float = 0.0
    activation_sparsity: float = 0.0
    recommended_bits: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "layer_type": self.layer_type,
            "input_range": [self.input_min, self.input_max],
            "input_mean": self.input_mean,
            "input_std": self.input_std,
            "weight_range": [self.weight_min, self.weight_max],
            "weight_mean": self.weight_mean,
            "weight_std": self.weight_std,
            "gradient_norm": self.gradient_norm,
            "activation_sparsity": self.activation_sparsity,
            "recommended_bits": self.recommended_bits,
        }


@dataclass
class TptProfile:
    model_name: str
    epoch: int = 0
    layers: list[LayerStats] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "epoch": self.epoch,
            "layer_count": len(self.layers),
            "layers": [l.to_dict() for l in self.layers],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def save(self, path: Path) -> None:
        path.write_text(self.to_json())

    @classmethod
    def from_json(cls, json_str: str) -> TptProfile:
        data = json.loads(json_str)
        layers = []
        for ld in data.get("layers", []):
            lr = ld.get("input_range", [0, 0])
            wr = ld.get("weight_range", [0, 0])
            layers.append(LayerStats(
                name=ld["name"],
                layer_type=ld.get("layer_type", "unknown"),
                input_min=lr[0],
                input_max=lr[1],
                input_mean=ld.get("input_mean", 0),
                input_std=ld.get("input_std", 0),
                weight_min=wr[0],
                weight_max=wr[1],
                weight_mean=ld.get("weight_mean", 0),
                weight_std=ld.get("weight_std", 0),
                gradient_norm=ld.get("gradient_norm", 0),
                activation_sparsity=ld.get("activation_sparsity", 0),
                recommended_bits=ld.get("recommended_bits", 8),
            ))
        return cls(
            model_name=data["model_name"],
            epoch=data.get("epoch", 0),
            layers=layers,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> TptProfile:
        return cls.from_json(path.read_text())


class TptProfileWriter:
    """Collects per-layer statistics during training."""

    def __init__(self, model_name: str):
        self.profile = TptProfile(model_name=model_name)
        self._hooks: list[Any] = []

    def record_layer(
        self,
        name: str,
        layer_type: str,
        input_tensor=None,
        weight_tensor=None,
        gradient_tensor=None,
    ) -> LayerStats:
        """Record statistics for a layer."""
        import numpy as np

        stats = LayerStats(name=name, layer_type=layer_type)

        if input_tensor is not None:
            arr = np.array(input_tensor)
            stats.input_min = float(arr.min())
            stats.input_max = float(arr.max())
            stats.input_mean = float(arr.mean())
            stats.input_std = float(arr.std())
            stats.activation_sparsity = float((arr == 0).sum() / max(arr.size, 1))

        if weight_tensor is not None:
            arr = np.array(weight_tensor)
            stats.weight_min = float(arr.min())
            stats.weight_max = float(arr.max())
            stats.weight_mean = float(arr.mean())
            stats.weight_std = float(arr.std())

        if gradient_tensor is not None:
            arr = np.array(gradient_tensor)
            stats.gradient_norm = float(np.linalg.norm(arr))

        stats.recommended_bits = self._recommend_bits(stats)
        self.profile.layers.append(stats)
        return stats

    def _recommend_bits(self, stats: LayerStats) -> int:
        input_range = abs(stats.input_max - stats.input_min)
        max_abs = max(abs(stats.input_min), abs(stats.input_max))
        if max_abs > 10.0:
            return 32
        elif input_range < 0.01 and max_abs < 1.0:
            return 4
        elif input_range < 1.0:
            return 8
        elif input_range < 10.0:
            return 16
        return 32

    def step(self, epoch: int) -> None:
        """Record the current epoch number."""
        self.profile.epoch = epoch

    def save(self, path: Path) -> None:
        self.profile.save(path)

    def get_profile(self) -> TptProfile:
        return self.profile
