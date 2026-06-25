"""Weight packer — quantize and tile weights for CIM memory arrays."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class PackedArray:
    rows: int
    cols: int
    bit_precision: int
    data: bytes
    dtype: str = "uint8"

    @property
    def total_bits(self) -> int:
        return self.rows * self.cols * self.bit_precision

    @property
    def size_bytes(self) -> int:
        return len(self.data)


class CimWeightPacker:
    """Pack weights into CIM memory array format.

    Each row in the array represents a single MAC unit.
    Weights are quantized and tiled to fit the physical array dimensions.
    """

    def __init__(self, array_rows: int = 1024, array_cols: int = 1024, bit_precision: int = 8):
        self.array_rows = array_rows
        self.array_cols = array_cols
        self.bit_precision = bit_precision

    def quantize_weights(self, weights: np.ndarray, bits: int | None = None) -> np.ndarray:
        bits = bits or self.bit_precision
        max_val = (2 ** bits) - 1
        w_min = weights.min()
        w_max = weights.max()

        if w_max - w_min == 0:
            return np.zeros_like(weights, dtype=np.uint8)

        quantized = ((weights - w_min) / (w_max - w_min) * max_val).astype(np.uint8)
        return quantized

    def pack_weights(self, weights: np.ndarray, bits: int | None = None) -> PackedArray:
        bits = bits or self.bit_precision
        quantized = self.quantize_weights(weights, bits)

        rows, cols = quantized.shape
        tiled_rows = ((rows + self.array_rows - 1) // self.array_rows) * self.array_rows
        tiled_cols = ((cols + self.array_cols - 1) // self.array_cols) * self.array_cols

        padded = np.zeros((tiled_rows, tiled_cols), dtype=np.uint8)
        padded[:rows, :cols] = quantized

        data = padded.tobytes()

        return PackedArray(
            rows=tiled_rows,
            cols=tiled_cols,
            bit_precision=bits,
            data=data,
            dtype=f"uint{bits}",
        )

    def serialize_array(self, packed: PackedArray) -> bytes:
        header = np.array([packed.rows, packed.cols, packed.bit_precision], dtype=np.uint32).tobytes()
        return header + packed.data

    def deserialize_array(self, data: bytes) -> PackedArray:
        header = np.frombuffer(data[:12], dtype=np.uint32)
        rows, cols, bits = int(header[0]), int(header[1]), int(header[2])
        return PackedArray(
            rows=rows,
            cols=cols,
            bit_precision=bits,
            data=data[12:],
            dtype=f"uint{bits}",
        )
