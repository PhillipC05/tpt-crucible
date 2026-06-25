"""Swarm topology definitions."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TopologyType(Enum):
    GRID_2D = "grid2d"
    STAR = "star"
    RING = "ring"
    CUSTOM = "custom"


@dataclass
class Topology:
    type: TopologyType
    rows: int = 0
    cols: int = 0
    center: int = 0
    leaves: int = 0
    size: int = 0
    adjacency: list[list[int]] = field(default_factory=list)

    @classmethod
    def grid2d(cls, rows: int, cols: int) -> Topology:
        return cls(type=TopologyType.GRID_2D, rows=rows, cols=cols)

    @classmethod
    def star(cls, center: int, leaves: int) -> Topology:
        return cls(type=TopologyType.STAR, center=center, leaves=leaves)

    @classmethod
    def ring(cls, size: int) -> Topology:
        return cls(type=TopologyType.RING, size=size)

    @classmethod
    def custom(cls, adjacency: list[list[int]]) -> Topology:
        return cls(type=TopologyType.CUSTOM, adjacency=adjacency)

    def node_count(self) -> int:
        if self.type == TopologyType.GRID_2D:
            return self.rows * self.cols
        elif self.type == TopologyType.STAR:
            return self.leaves + 1
        elif self.type == TopologyType.RING:
            return self.size
        return len(self.adjacency)

    def neighbors(self, node_id: int) -> list[int]:
        if self.type == TopologyType.GRID_2D:
            neighbors = []
            row, col = divmod(node_id, self.cols)
            if row > 0:
                neighbors.append(node_id - self.cols)
            if row + 1 < self.rows:
                neighbors.append(node_id + self.cols)
            if col > 0:
                neighbors.append(node_id - 1)
            if col + 1 < self.cols:
                neighbors.append(node_id + 1)
            return neighbors
        elif self.type == TopologyType.STAR:
            if node_id == self.center:
                return [i for i in range(self.node_count()) if i != self.center]
            return [self.center]
        elif self.type == TopologyType.RING:
            prev = self.size - 1 if node_id == 0 else node_id - 1
            nxt = 0 if node_id + 1 == self.size else node_id + 1
            return [prev, nxt]
        return self.adjacency[node_id] if node_id < len(self.adjacency) else []
