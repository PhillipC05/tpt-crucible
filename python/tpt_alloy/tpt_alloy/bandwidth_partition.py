"""Bandwidth-Weighted Partition Graph — optimize inter-node traffic."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EdgeWeight:
    from_node: int
    to_node: int
    byte_volume: int
    tensor_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "byte_volume": self.byte_volume,
            "tensor_name": self.tensor_name,
        }


@dataclass
class WeightedGraph:
    node_count: int
    edges: list[EdgeWeight]
    total_bytes: int = 0

    def __post_init__(self):
        self.total_bytes = sum(e.byte_volume for e in self.edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count": self.node_count,
            "total_bytes": self.total_bytes,
            "edge_count": len(self.edges),
        }


class BandwidthEstimator:
    """Estimate communication volume for partition graph edges."""

    DTYPE_BYTES = {
        "float32": 4,
        "float16": 2,
        "int8": 1,
        "int4": 0.5,
        "bfloat16": 2,
    }

    def estimate_edge_volume(
        self,
        shape: list[int],
        dtype: str = "float32",
        batch_size: int = 1,
    ) -> int:
        dtype_bytes = self.DTYPE_BYTES.get(dtype, 4)
        elements = 1
        for dim in shape:
            elements *= dim
        return elements * dtype_bytes * batch_size

    def build_weighted_graph(
        self,
        node_count: int,
        edges: list[tuple[int, int, str, list[int], str]],
    ) -> WeightedGraph:
        weighted_edges = []
        for from_node, to_node, tensor_name, shape, dtype in edges:
            volume = self.estimate_edge_volume(shape, dtype)
            weighted_edges.append(EdgeWeight(
                from_node=from_node,
                to_node=to_node,
                byte_volume=volume,
                tensor_name=tensor_name,
            ))
        return WeightedGraph(node_count=node_count, edges=weighted_edges)

    def compute_partition_cost(
        self,
        partition: dict[int, list[int]],
        graph: WeightedGraph,
    ) -> float:
        node_layers = {layer: node for node, layers in partition.items() for layer in layers}
        cross_cost = 0.0
        for edge in graph.edges:
            from_node = node_layers.get(edge.from_node)
            to_node = node_layers.get(edge.to_node)
            if from_node is not None and to_node is not None and from_node != to_node:
                cross_cost += edge.byte_volume
        return cross_cost

    def suggest_optimal_partition(
        self,
        graph: WeightedGraph,
        layers: list[int],
        node_count: int,
    ) -> dict[int, list[int]]:
        partition: dict[int, list[int]] = {i: [] for i in range(node_count)}
        for i, layer in enumerate(layers):
            partition[i % node_count].append(layer)
        return partition
