"""JAX/Flax training hook — hardware-aware profiling for JAX models."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json
from pathlib import Path


@dataclass
class JaxLayerStats:
    layer_name: str
    param_count: int = 0
    input_min: float = 0.0
    input_max: float = 0.0
    weight_min: float = 0.0
    weight_max: float = 0.0
    recommended_bits: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "param_count": self.param_count,
            "input_range": [self.input_min, self.input_max],
            "weight_range": [self.weight_min, self.weight_max],
            "recommended_bits": self.recommended_bits,
        }


@dataclass
class JaxProfile:
    model_name: str
    epoch: int = 0
    layers: list[JaxLayerStats] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "epoch": self.epoch,
            "layer_count": len(self.layers),
            "layers": [l.to_dict() for l in self.layers],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))


class TPTJaxHook:
    """JAX/Flax training hook for hardware-aware profiling."""

    def __init__(self, model_name: str):
        self.profile = JaxProfile(model_name=model_name)
        self._hooks: list[Any] = []

    def record_layer(
        self,
        name: str,
        params: Any = None,
        activations: Any = None,
    ) -> JaxLayerStats:
        import numpy as np

        stats = JaxLayerStats(layer_name=name)

        if params is not None:
            arr = np.array(params)
            stats.param_count = arr.size
            stats.weight_min = float(arr.min())
            stats.weight_max = float(arr.max())

        if activations is not None:
            arr = np.array(activations)
            stats.input_min = float(arr.min())
            stats.input_max = float(arr.max())

        stats.recommended_bits = self._recommend_bits(stats)
        self.profile.layers.append(stats)
        return stats

    def _recommend_bits(self, stats: JaxLayerStats) -> int:
        weight_range = abs(stats.weight_max - stats.weight_min)
        if weight_range < 0.01:
            return 4
        elif weight_range < 1.0:
            return 8
        elif weight_range < 10.0:
            return 16
        return 32

    def step(self, epoch: int) -> None:
        self.profile.epoch = epoch

    def save(self, path: Path) -> None:
        self.profile.save(path)

    def get_profile(self) -> JaxProfile:
        return self.profile
