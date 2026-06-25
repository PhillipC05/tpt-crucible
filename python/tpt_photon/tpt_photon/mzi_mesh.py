"""MZI Mesh Generator — SVD decomposition for photonic inference."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np


@dataclass
class MziConfig:
    mesh_size: int = 8
    wavelength_nm: int = 1550
    modulation: str = "thermal"
    phase_bits: int = 8
    nonlinearity: str = "none"

    @property
    def phase_resolution(self) -> float:
        return 2 * math.pi / (2 ** self.phase_bits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mesh_size": self.mesh_size,
            "wavelength_nm": self.wavelength_nm,
            "modulation": self.modulation,
            "phase_bits": self.phase_bits,
            "nonlinearity": self.nonlinearity,
        }


@dataclass
class MziPhaseAngles:
    layer_id: int
    matrix_shape: tuple[int, int]
    phases: np.ndarray
    singular_values: np.ndarray

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "matrix_shape": list(self.matrix_shape),
            "phases_rad": self.phases.tolist(),
            "singular_values": self.singular_values.tolist(),
        }


class MziMeshGenerator:
    """Generate MZI phase configurations from weight matrices."""

    def __init__(self, config: MziConfig | None = None):
        self.config = config or MziConfig()

    def svd_decompose(self, weights: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        U, S, Vt = np.linalg.svd(weights, full_matrices=False)
        return U, S, Vt

    def clement_decomposition(self, U: np.ndarray) -> np.ndarray:
        n = U.shape[0]
        phases = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                angle = np.arctan2(U[j, i].real, U[i, i].real)
                phases[i, j] = angle
        return phases

    def phase_encode(self, weights: np.ndarray, layer_id: int = 0) -> MziPhaseAngles:
        U, S, Vt = self.svd_decompose(weights)
        phases = self.clement_decomposition(U)
        return MziPhaseAngles(
            layer_id=layer_id,
            matrix_shape=weights.shape,
            phases=phases,
            singular_values=S,
        )

    def generate_mesh_config(self, phase_angles: list[MziPhaseAngles]) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "layers": [pa.to_dict() for pa in phase_angles],
            "total_mzis": sum(pa.phases.size for pa in phase_angles),
        }

    def estimate_accuracy(self, original: np.ndarray, reconstructed: np.ndarray) -> float:
        if original.size == 0:
            return 0.0
        mse = np.mean((original - reconstructed) ** 2)
        max_val = np.max(np.abs(original)) or 1.0
        return 1.0 - (mse / (max_val ** 2))
