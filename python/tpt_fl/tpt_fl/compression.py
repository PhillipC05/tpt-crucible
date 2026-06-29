"""Gradient compression for federated learning over bandwidth-constrained hardware links."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class CompressedGradient:
    layer_id: str
    indices: list[int]   # sparse indices of non-zero entries
    values: list[float]  # corresponding gradient values
    original_size: int   # total number of elements before compression
    compression_ratio: float

    def decompress(self) -> list[float]:
        grad = [0.0] * self.original_size
        for idx, val in zip(self.indices, self.values):
            if 0 <= idx < self.original_size:
                grad[idx] = val
        return grad


class GradientCompressor:
    """
    Top-K sparsification with error-feedback accumulation.

    Each participant keeps a residual buffer; gradients not transmitted this
    round are added back in the next round, ensuring eventual convergence
    even with aggressive compression.
    """

    def __init__(self, topk_fraction: float = 0.1) -> None:
        if not (0.0 < topk_fraction <= 1.0):
            raise ValueError(f"topk_fraction must be in (0, 1], got {topk_fraction}")
        self.topk_fraction = topk_fraction
        self._residuals: dict[str, list[float]] = {}

    def compress(self, layer_id: str, gradients: list[float]) -> CompressedGradient:
        # Add residuals from previous round
        residuals = self._residuals.get(layer_id, [0.0] * len(gradients))
        if len(residuals) != len(gradients):
            residuals = [0.0] * len(gradients)
        combined = [g + r for g, r in zip(gradients, residuals)]

        k = max(1, math.ceil(len(combined) * self.topk_fraction))
        indexed = sorted(enumerate(combined), key=lambda x: abs(x[1]), reverse=True)
        top_k = indexed[:k]
        selected_indices = [i for i, _ in top_k]
        selected_values = [v for _, v in top_k]

        # Update residuals
        selected_set = set(selected_indices)
        new_residuals = [
            combined[i] if i not in selected_set else 0.0
            for i in range(len(combined))
        ]
        self._residuals[layer_id] = new_residuals

        original_size = len(gradients)
        compression_ratio = original_size / max(k, 1)
        return CompressedGradient(
            layer_id=layer_id,
            indices=selected_indices,
            values=selected_values,
            original_size=original_size,
            compression_ratio=compression_ratio,
        )

    def reset_residuals(self, layer_id: str | None = None) -> None:
        if layer_id:
            self._residuals.pop(layer_id, None)
        else:
            self._residuals.clear()
