"""Quantization Auto-Search — find optimal per-layer bit-width assignments."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class LayerQuantDecision:
    layer_name: str
    bits: int
    sensitivity: float = 0.0
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "bits": self.bits,
            "sensitivity": round(self.sensitivity, 4),
            "reason": self.reason,
        }


@dataclass
class QuantSearchResult:
    decisions: list[LayerQuantDecision]
    accuracy_budget: float
    estimated_accuracy_loss: float
    search_iterations: int
    target_bits: dict[int, int] = field(default_factory=dict)

    @property
    def avg_bits(self) -> float:
        if not self.decisions:
            return 0.0
        return sum(d.bits for d in self.decisions) / len(self.decisions)

    @property
    def compression_ratio(self) -> float:
        return 32.0 / max(self.avg_bits, 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [d.to_dict() for d in self.decisions],
            "accuracy_budget": self.accuracy_budget,
            "estimated_accuracy_loss": round(self.estimated_accuracy_loss, 4),
            "search_iterations": self.search_iterations,
            "avg_bits": round(self.avg_bits, 2),
            "compression_ratio": round(self.compression_ratio, 2),
        }


class QuantSearchEngine:
    """Search for optimal quantization across layers."""

    def __init__(self, accuracy_budget: float = 0.05):
        self.accuracy_budget = accuracy_budget

    def search(
        self,
        layer_names: list[str],
        sensitivities: list[float] | None = None,
    ) -> QuantSearchResult:
        if sensitivities is None:
            sensitivities = [0.5] * len(layer_names)

        sorted_layers = sorted(
            zip(layer_names, sensitivities),
            key=lambda x: x[1],
            reverse=True,
        )

        decisions = []
        estimated_loss = 0.0
        iterations = 0

        for name, sensitivity in sorted_layers:
            iterations += 1
            if sensitivity > 0.8:
                bits = 32
                reason = "high sensitivity — kept float32"
            elif sensitivity > 0.5:
                bits = 16
                reason = "medium sensitivity — half precision"
            elif sensitivity > 0.2:
                bits = 8
                reason = "low sensitivity — INT8"
            else:
                bits = 4
                reason = "minimal sensitivity — INT4"

            if estimated_loss + sensitivity * 0.01 > self.accuracy_budget:
                bits = max(bits, 8)
                reason += " (budget constraint)"

            decisions.append(LayerQuantDecision(
                layer_name=name,
                bits=bits,
                sensitivity=sensitivity,
                reason=reason,
            ))
            estimated_loss += sensitivity * 0.01

        target_bits = {}
        for d in decisions:
            target_bits[d.bits] = target_bits.get(d.bits, 0) + 1

        return QuantSearchResult(
            decisions=decisions,
            accuracy_budget=self.accuracy_budget,
            estimated_accuracy_loss=estimated_loss,
            search_iterations=iterations,
            target_bits=target_bits,
        )
