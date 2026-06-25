"""Structured Sparsity — exploit 2:4 sparsity for FPGA MAC array skip-zero gating."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import numpy as np


class SparsityMode(Enum):
    NONE = "none"
    TWO_FOUR = "2:4"
    FOUR_EIGHT = "4:8"
    AUTO = "auto"


@dataclass
class SparsityPattern:
    mode: SparsityMode
    density: float
    mask: list[list[int]] = field(default_factory=list)
    compressed_indices: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "density": round(self.density, 4),
            "non_zero_count": len(self.compressed_indices),
        }


class SparsityAnalyzer:
    """Analyze and enforce structured sparsity patterns."""

    def analyze(self, weights: np.ndarray) -> SparsityPattern:
        total = weights.size
        zeros = np.sum(weights == 0)
        density = 1.0 - (zeros / total)

        if density >= 0.75:
            mode = SparsityMode.NONE
        elif density >= 0.5:
            mode = SparsityMode.TWO_FOUR
        else:
            mode = SparsityMode.FOUR_EIGHT

        return SparsityPattern(
            mode=mode,
            density=density,
        )

    def enforce_2_4(self, weights: np.ndarray) -> tuple[np.ndarray, list[int]]:
        rows, cols = weights.shape
        result = np.zeros_like(weights)
        indices = []

        for i in range(rows):
            row = weights[i]
            abs_row = np.abs(row)
            top_k_indices = np.argsort(abs_row)[-2:]
            for idx in top_k_indices:
                result[i, idx] = row[idx]
                indices.append(i * cols + idx)

        return result, indices

    def enforce_4_8(self, weights: np.ndarray) -> tuple[np.ndarray, list[int]]:
        rows, cols = weights.shape
        result = np.zeros_like(weights)
        indices = []

        for i in range(rows):
            row = weights[i]
            abs_row = np.abs(row)
            top_k_indices = np.argsort(abs_row)[-4:]
            for idx in top_k_indices:
                result[i, idx] = row[idx]
                indices.append(i * cols + idx)

        return result, indices

    def estimate_speedup(self, pattern: SparsityPattern, base_latency_ms: float) -> float:
        if pattern.mode == SparsityMode.NONE:
            return 1.0
        elif pattern.mode == SparsityMode.TWO_FOUR:
            return 1.0 / 0.5
        elif pattern.mode == SparsityMode.FOUR_EIGHT:
            return 1.0 / 0.5
        return 1.0
