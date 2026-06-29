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
    protocol: str = "kv_stream"
    """Protocol: 'kv_stream' (default), 'sum_reduce', 'all_gather'."""


@dataclass
class Partition:
    node_id: int
    assigned_layers: list[int] = field(default_factory=list)
    cross_node_edges: list[CrossEdge] = field(default_factory=list)
    assigned_heads: list[int] = field(default_factory=list)
    """Attention head IDs assigned to this node (head-parallel mode)."""
    is_aggregator: bool = False
    """True if this node aggregates head outputs via sum-reduce."""


@dataclass
class PartitionConfig:
    topology: Topology = field(default_factory=lambda: Topology.grid2d(4, 4))
    max_layers_per_node: int = 4
    minimize_cross_node_edges: bool = True
    strategy: str = "layer"
    """Partitioning strategy: 'layer' (round-robin), 'head-parallel', or 'hybrid'."""
    num_heads: int = 32
    """Number of attention heads in the model."""
    head_dim: int = 64
    """Dimension of each attention head."""
    attention_op_types: tuple[str, ...] = (
        "attention", "self_attn", "multi_head_attention",
        "mha", "qkv", "attn",
    )
    """Op type keywords that identify transformer attention sublayers."""
    pipeline_depth: int = 4
    """Number of in-flight tokens for pipeline parallelism (depth 1 = sequential)."""
    op_types_per_layer: list[str] = field(default_factory=list)
    """Op type for each layer index, used for attention detection in hybrid mode."""


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


def detect_attention_layers(op_types_per_layer: list[str], config: PartitionConfig) -> list[bool]:
    """Detect which layers are transformer attention sublayers."""
    attention_keywords = set(config.attention_op_types)
    return [
        any(kw in op.lower() for kw in attention_keywords)
        for op in op_types_per_layer
    ]


def partition_model(
    layer_count: int,
    config: PartitionConfig,
    graph: GraphData | None = None,
) -> list[Partition]:
    """Partition a model's layers across swarm nodes.

    Uses METIS when available for optimal graph partitioning.
    Falls back to round-robin assignment otherwise.
    """
    if config.strategy == "head-parallel":
        return _partition_head_parallel(layer_count, config)
    elif config.strategy == "hybrid":
        return _partition_hybrid(layer_count, config, graph)
    else:
        return _partition_layer(layer_count, config, graph)


def _partition_layer(
    layer_count: int,
    config: PartitionConfig,
    graph: GraphData | None,
) -> list[Partition]:
    """Standard layer-serial partitioning."""
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


def _partition_head_parallel(
    layer_count: int,
    config: PartitionConfig,
) -> list[Partition]:
    """Head-parallel partitioning: distribute attention heads across nodes.

    Each node processes a subset of attention heads for all attention layers.
    Non-attention layers remain on the first node (or distributed round-robin).
    """
    node_count = config.topology.node_count()
    num_heads = config.num_heads
    partitions = [Partition(node_id=i) for i in range(node_count)]

    heads_per_node = max(1, num_heads // node_count)
    for node_id in range(node_count):
        start_head = node_id * heads_per_node
        end_head = min(start_head + heads_per_node, num_heads)
        partitions[node_id].assigned_heads = list(range(start_head, end_head))

    if config.op_types_per_layer:
        attention_mask = detect_attention_layers(config.op_types_per_layer, config)
    else:
        attention_mask = [True] * layer_count

    aggregator_id = 0
    partitions[aggregator_id].is_aggregator = True

    for layer_id in range(layer_count):
        if attention_mask[layer_id]:
            for node_id in range(node_count):
                partitions[node_id].assigned_layers.append(layer_id)
        else:
            partitions[aggregator_id % node_count].assigned_layers.append(layer_id)

    for node_id in range(node_count):
        if node_id != aggregator_id and partitions[node_id].assigned_heads:
            partitions[node_id].cross_node_edges.append(CrossEdge(
                from_node=node_id,
                to_node=aggregator_id,
                tensor_name=f"head_reduce_node{node_id}",
                protocol="sum_reduce",
            ))

    return partitions


def _partition_hybrid(
    layer_count: int,
    config: PartitionConfig,
    graph: GraphData | None,
) -> list[Partition]:
    """Hybrid partitioning: head-parallel for attention, layer-serial for FFN."""
    node_count = config.topology.node_count()
    partitions = [Partition(node_id=i) for i in range(node_count)]

    if config.op_types_per_layer:
        attention_mask = detect_attention_layers(config.op_types_per_layer, config)
    else:
        attention_mask = [True] * layer_count

    num_heads = config.num_heads
    heads_per_node = max(1, num_heads // node_count)
    for node_id in range(node_count):
        start_head = node_id * heads_per_node
        end_head = min(start_head + heads_per_node, num_heads)
        partitions[node_id].assigned_heads = list(range(start_head, end_head))

    aggregator_id = 0
    partitions[aggregator_id].is_aggregator = True

    ffn_layers = [i for i in range(layer_count) if not attention_mask[i]]

    if METIS_AVAILABLE and graph and ffn_layers:
        ffn_graph = GraphData(
            node_count=len(ffn_layers),
            adjacency=[[] for _ in range(len(ffn_layers))],
        )
        ffn_parts = _metis_partition(ffn_graph, node_count)
        for idx, layer_id in enumerate(ffn_layers):
            part = ffn_parts[idx] % node_count
            partitions[part].assigned_layers.append(layer_id)
    else:
        for idx, layer_id in enumerate(ffn_layers):
            partitions[idx % node_count].assigned_layers.append(layer_id)

    for layer_id in range(layer_count):
        if attention_mask[layer_id]:
            for node_id in range(node_count):
                if layer_id not in partitions[node_id].assigned_layers:
                    partitions[node_id].assigned_layers.append(layer_id)

    for node_id in range(node_count):
        if node_id != aggregator_id and partitions[node_id].assigned_heads:
            partitions[node_id].cross_node_edges.append(CrossEdge(
                from_node=node_id,
                to_node=aggregator_id,
                tensor_name=f"head_reduce_node{node_id}",
                protocol="sum_reduce",
            ))

    if graph:
        _compute_cross_edges(partitions, graph)

    partitions.sort(key=lambda p: p.node_id)
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
