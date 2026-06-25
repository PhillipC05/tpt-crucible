"""Array layout — map TPT-IR ops to CIM array dimensions."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayoutConfig:
    array_rows: int = 1024
    array_cols: int = 1024
    bit_precision: int = 8
    num_arrays: int = 1
    sparsity_factor: float = 0.0

    @property
    def total_mac_units(self) -> int:
        return self.array_rows * self.array_cols * self.num_arrays

    @property
    def memory_bits(self) -> int:
        return self.total_mac_units * self.bit_precision


@dataclass
class ArrayTile:
    tile_id: int
    input_offset: int
    weight_offset: int
    output_offset: int
    rows: int
    cols: int


@dataclass
class CimArrayLayout:
    config: LayoutConfig
    tiles: list[ArrayTile] = field(default_factory=list)
    layer_map: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: LayoutConfig) -> CimArrayLayout:
        return cls(config=config)

    def map_layer(self, layer_name: str, input_dim: int, output_dim: int) -> list[ArrayTile]:
        tiles = []
        tile_id = len(self.tiles)

        rows_per_tile = min(cfg := self.config.array_rows, input_dim)
        cols_per_tile = min(cfg := self.config.array_cols, output_dim)

        input_tiles = (input_dim + rows_per_tile - 1) // rows_per_tile
        output_tiles = (output_dim + cols_per_tile - 1) // cols_per_tile

        for i in range(input_tiles):
            for j in range(output_tiles):
                tile = ArrayTile(
                    tile_id=tile_id,
                    input_offset=i * rows_per_tile,
                    weight_offset=j * cols_per_tile,
                    output_offset=(i * output_tiles + j) * cfg,
                    rows=min(rows_per_tile, input_dim - i * rows_per_tile),
                    cols=min(cols_per_tile, output_dim - j * cols_per_tile),
                )
                tiles.append(tile)
                tile_id += 1

        self.tiles.extend(tiles)
        self.layer_map[layer_name] = len(tiles)
        return tiles

    def get_total_tiles(self) -> int:
        return len(self.tiles)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": {
                "array_rows": self.config.array_rows,
                "array_cols": self.config.array_cols,
                "bit_precision": self.config.bit_precision,
                "num_arrays": self.config.num_arrays,
            },
            "total_tiles": self.get_total_tiles(),
            "layer_map": self.layer_map,
        }
