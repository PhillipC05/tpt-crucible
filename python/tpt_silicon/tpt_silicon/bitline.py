"""Bitline operation generator — emit low-level CIM op sequences."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BitlineOp:
    op_type: str
    tile_id: int
    row_start: int = 0
    row_end: int = 0
    col_start: int = 0
    col_end: int = 0
    mask: list[int] | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "op_type": self.op_type,
            "tile_id": self.tile_id,
            "row_range": [self.row_start, self.row_end],
            "col_range": [self.col_start, self.col_end],
            "masked": self.mask is not None,
        }


class BitlineOpGenerator:
    """Generate bitline operations for CIM compute."""

    def __init__(self):
        self.ops: list[BitlineOp] = []

    def read_rows(self, tile_id: int, row_start: int, row_end: int) -> BitlineOp:
        op = BitlineOp(op_type="read", tile_id=tile_id, row_start=row_start, row_end=row_end)
        self.ops.append(op)
        return op

    def accumulate(self, tile_id: int) -> BitlineOp:
        op = BitlineOp(op_type="accumulate", tile_id=tile_id)
        self.ops.append(op)
        return op

    def adc_skip(self, tile_id: int, threshold: float = 0.1) -> BitlineOp:
        op = BitlineOp(op_type="adc_skip", tile_id=tile_id, params={"threshold": threshold})
        self.ops.append(op)
        return op

    def masked_read(self, tile_id: int, row_start: int, row_end: int, mask: list[int]) -> BitlineOp:
        op = BitlineOp(
            op_type="masked_read",
            tile_id=tile_id,
            row_start=row_start,
            row_end=row_end,
            mask=mask,
        )
        self.ops.append(op)
        return op

    def matmul_sequence(self, tile_id: int, input_rows: int, weight_cols: int) -> list[BitlineOp]:
        ops = []
        for col in range(0, weight_cols, 32):
            col_end = min(col + 32, weight_cols)
            ops.append(self.read_rows(tile_id, 0, input_rows))
            ops.append(self.accumulate(tile_id))
            ops.append(self.adc_skip(tile_id))
        return ops

    def get_ops(self) -> list[BitlineOp]:
        return list(self.ops)

    def clear(self) -> None:
        self.ops.clear()

    def to_dict(self) -> list[dict[str, Any]]:
        return [op.to_dict() for op in self.ops]
