"""Graph partitioning for swarm deployment."""

from __future__ import annotations
from dataclasses import dataclass, field
from .topology import Topology

try:
    import pymetis
    METIS_AVAILABLE = True
except ImportError:
    METIS_AVAILABLE = False


@dataclass
class CrossEdge:
    from_node: int
    to_node: int
    tensor_name: str


@dataclass
class Partition:
    node_id: int
    assigned_layers: list[int] = field(default_factory=list)
    cross_node_edges: list[CrossEdge] = field(default_factory=list)


@dataclass
class PartitionConfig:
    topology: Topology = field(default_factory=lambda: Topology.grid2d(4, 4))
    max_layers_per_node: int = 4
    minimize_cross_node_edges: bool = True


@dataclass
class GraphData:
    """Adjacency list representation of a computational graph for partitioning."""
    node_count: int = 0
    adjacency: list[list[int]] = field(default_factory=list)
    node_labels: list[str] = field(default_factory=list)


def build_graph_from_nodes(
    node_count: int,
    edges: list[tuple[int, int]],
) -> GraphData:
    """Build adjacency list from node count and edge list."""
    adjacency = [[] for _ in range(node_count)]
    for from_id, to_id in edges:
        if from_id < node_count and to_id < node_count:
            adjacency[from_id].append(to_id)
            adjacency[to_id].append(from_id)
    return GraphData(node_count=node_count, adjacency=adjacency)


def partition_model(
    layer_count: int,
    config: PartitionConfig,
    graph: GraphData | None = None,
) -> list[Partition]:
    """Partition a model's layers across swarm nodes.

    Uses METIS when available for optimal graph partitioning.
    Falls back to round-robin assignment otherwise.
    """
    node_count = config.topology.node_count()

    if METIS_AVAILABLE and graph and config.minimize_cross_node_edges:
        node_parts = _metis_partition(graph, node_count)
    else:
        node_parts = list(range(layer_count)) if graph is None else _round_robin(graph.node_count, node_count)

    partitions = [Partition(node_id=i) for i in range(node_count)]

    for layer_id in range(len(node_parts)):
        part = node_parts[layer_id] % node_count
        partitions[part].assigned_layers.append(layer_id)

    if graph:
        _compute_cross_edges(partitions, graph)

    return partitions


def _metis_partition(graph: GraphData, num_parts: int) -> list[int]:
    """Partition using METIS."""
    adj = [list(set(neighbors)) for neighbors in graph.adjacency]
    _, node_parts = pymetis.partition(num_parts, adjacency=adj)
    return node_parts


def _round_robin(node_count: int, num_parts: int) -> list[int]:
    """Simple round-robin partitioning."""
    return [i % num_parts for i in range(node_count)]


def _compute_cross_edges(partitions: list[Partition], graph: GraphData) -> None:
    """Compute cross-node edges for each partition."""
    part_of = {}
    for p in partitions:
        for layer_id in p.assigned_layers:
            part_of[layer_id] = p.node_id

    for node_id in range(graph.node_count):
        part_id = part_of.get(node_id, 0)
        for neighbor in graph.adjacency[node_id]:
            neighbor_part = part_of.get(neighbor, 0)
            if part_id != neighbor_part:
                target_partition = next(p for p in partitions if p.node_id == part_id)
                target_partition.cross_node_edges.append(CrossEdge(
                    from_node=part_id,
                    to_node=neighbor_part,
                    tensor_name=f"edge_{node_id}_{neighbor}",
                ))
