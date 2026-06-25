"""Map floating-point weights to physical components."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import numpy as np


class ComponentType(Enum):
    RESISTOR = "resistor"
    MEMRISTOR = "memristor"
    OPAMP_GAIN = "opamp_gain"


@dataclass
class PhysicalComponent:
    component_type: ComponentType
    value: float
    unit: str
    tolerance: float
    position: tuple[int, int]


class WeightMapper:
    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance

    def map_weights(self, weights: np.ndarray) -> list[PhysicalComponent]:
        components = []
        flat = weights.flatten()
        rows, cols = weights.shape if weights.ndim >= 2 else (1, len(flat))

        for idx, w in enumerate(flat):
            row, col = divmod(idx, cols) if cols > 0 else (0, idx)
            resistance = self._weight_to_resistance(float(w))
            components.append(PhysicalComponent(
                component_type=ComponentType.RESISTOR,
                value=resistance,
                unit="ohm",
                tolerance=self.tolerance,
                position=(row, col),
            ))
        return components

    def _weight_to_resistance(self, weight: float) -> float:
        if weight == 0:
            return 1e12
        return abs(1.0 / weight) * 1000

    def compute_confidence_score(self, components: list[PhysicalComponent]) -> float:
        if not components:
            return 0.0
        tolerance_penalty = sum(c.tolerance for c in components) / len(components)
        return max(0.0, 1.0 - tolerance_penalty)
